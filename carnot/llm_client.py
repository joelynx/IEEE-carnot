"""Model backend: headless Claude Code (`claude -p`) on the team's subscription.

PLAN.md §3.9 / decision D2.  One subprocess per call; prompt on stdin; our own
system prompt replaces Claude Code's; no tools; customisations off; explicit
model ID and effort; scrubbed environment (no API key, no effort override);
subscription login asserted before use.  Every response is stored in a SQLite
cache keyed by everything that determines it, which is the only route to exact
reproducibility because the CLI exposes no temperature or seed.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import common

FLAGS_VERSION = "v1"
SCRUB_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_EFFORT_LEVEL", "ANTHROPIC_MODEL")
# DISABLE_AUTOUPDATER keeps child calls from updating the CLI mid-campaign: the CLI
# version is part of every cache key, so an update would silently invalidate replay.
FORCE_ENV = {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "DISABLE_AUTOUPDATER": "1"}


class LLMError(RuntimeError):
    pass


class UsageLimitError(LLMError):
    """The subscription allowance is exhausted; the run must pause and resume later."""


class CacheMissError(LLMError):
    """A cache-only replay must never silently call the model."""


@dataclass
class Response:
    text: str
    model_id: str | None
    usage: dict[str, Any]
    cost_equivalent_usd: float | None
    cached: bool
    key: str
    meta: dict[str, Any] = field(default_factory=dict)


def find_claude() -> str:
    appdata = os.environ.get("APPDATA")
    if appdata:
        native = Path(appdata) / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        if native.exists():
            return str(native)
    found = shutil.which("claude")
    if not found:
        raise LLMError("claude CLI not found")
    return found


def child_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in SCRUB_ENV}
    env.update(FORCE_ENV)
    return env


class ClaudeCLI:
    def __init__(self, model: str, effort: str, cache_path: Path | None = None, call_timeout: int = 300,
                 cache_only: bool = False):
        self.exe = find_claude()
        self.model = model
        self.effort = effort
        self.call_timeout = call_timeout
        self.cache_only = cache_only
        self.version = self._run([self.exe, "--version"]).stdout.strip()
        status = json.loads(self._run([self.exe, "auth", "status"]).stdout)
        if status.get("authMethod") != "claude.ai" or not status.get("loggedIn"):
            raise LLMError(f"expected a claude.ai subscription login, got authMethod={status.get('authMethod')!r}")
        self.subscription = status.get("subscriptionType")
        self.workdir = Path(tempfile.mkdtemp(prefix="carnot_claude_"))
        self.sysprompt_dir = common.CACHE_DIR / "sysprompts"
        self.sysprompt_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_path or common.CACHE_DIR / "llm_cache.sqlite3"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(cache_path, check_same_thread=False, timeout=60)
        self.db.execute("PRAGMA journal_mode=WAL")  # several run processes may share the cache
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS calls (key TEXT PRIMARY KEY, created REAL, request TEXT, response TEXT)"
        )
        self.db.commit()
        self.lock = threading.Lock()

    def _run(self, command: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", env=child_env(), timeout=120, **kwargs
        )

    def describe(self) -> dict[str, Any]:
        return {
            "backend": "claude-code-cli",
            "cli_version": self.version,
            "model": self.model,
            "effort": self.effort,
            "flags_version": FLAGS_VERSION,
            "flags": self._flags("<system-prompt-file>"),
            "auth_method": "claude.ai",
            "subscription_type": self.subscription,
        }

    def _flags(self, system_file: str) -> list[str]:
        return [
            "-p", "--safe-mode", "--model", self.model, "--effort", self.effort,
            "--system-prompt-file", system_file, "--tools", "", "--strict-mcp-config",
            "--disable-slash-commands", "--permission-prompts", "none", "--max-turns", "1",
            "--no-session-persistence", "--output-format", "json",
        ]

    def complete(self, system: str, user: str, sample: int = 0, tag: str = "") -> Response:
        request = {
            "model": self.model, "effort": self.effort, "cli_version": self.version,
            "flags_version": FLAGS_VERSION, "system_sha256": common.sha256_text(system),
            "user_sha256": common.sha256_text(user), "sample": sample, "tag": tag,
        }
        key = common.sha256_text(common.canonical_json(request))
        with self.lock:
            row = self.db.execute("SELECT response FROM calls WHERE key = ?", (key,)).fetchone()
        if row is not None:
            payload = json.loads(row[0])
            return self._response(payload, key, cached=True)
        if self.cache_only:
            raise CacheMissError(f"cache-only replay missing response {key}")
        system_file = self.sysprompt_dir / f"{request['system_sha256']}.txt"
        if not system_file.exists():
            common.write_bytes_atomic(system_file, system.encode("utf-8"))
        payload = self._call(str(system_file), user)
        with self.lock:
            self.db.execute(
                "INSERT OR REPLACE INTO calls VALUES (?, ?, ?, ?)",
                (key, time.time(), common.canonical_json(request), json.dumps(payload)),
            )
            self.db.commit()
        return self._response(payload, key, cached=False)

    def _call(self, system_file: str, user: str) -> dict[str, Any]:
        delays = (10, 30, 90)
        last_error = ""
        for attempt in range(len(delays) + 1):
            try:
                completed = subprocess.run(
                    [self.exe, *self._flags(system_file)], input=user, capture_output=True, text=True,
                    encoding="utf-8", env=child_env(), cwd=self.workdir, timeout=self.call_timeout,
                )
                payload = json.loads(completed.stdout) if completed.stdout.strip().startswith("{") else None
            except subprocess.TimeoutExpired:
                payload, completed = None, None
                last_error = "call timed out"
            if payload is not None and payload.get("subtype") == "success" and not payload.get("is_error"):
                return payload
            if payload is not None:
                text = f"{payload.get('subtype')}: {payload.get('result')!s:.500} (api_error_status={payload.get('api_error_status')})"
            else:
                text = ((completed.stderr or completed.stdout)[-600:]
                        or f"no output (exit code {completed.returncode}, stdout {len(completed.stdout)} chars)"
                        ) if completed else last_error
            lowered = text.lower()
            # Documented message: "You've hit your session limit · resets 3:45pm" (or weekly).
            if "hit your" in lowered and "limit" in lowered:
                raise UsageLimitError(text)
            last_error = text
            if attempt < len(delays):
                time.sleep(delays[attempt])
        raise LLMError(f"claude -p failed after retries: {last_error}")

    def _response(self, payload: dict[str, Any], key: str, cached: bool) -> Response:
        model_usage = payload.get("modelUsage") or {}
        model_id = next(iter(model_usage), None)
        return Response(
            text=payload.get("result") or "",
            model_id=model_id,
            usage=payload.get("usage") or {},
            cost_equivalent_usd=payload.get("total_cost_usd"),
            cached=cached,
            key=key,
            meta={k: payload.get(k) for k in ("stop_reason", "duration_ms", "session_id", "num_turns")},
        )
