"""Host side of the sandbox: start one isolated worker and send it programs.

Backends (PLAN.md §3.3, decision D7):
  wsl    - WSL2 Ubuntu inside `unshare -rmn`: new user, mount and network
           namespaces (network unreachable), Windows drives hidden behind a
           tmpfs, sandbox code copied to a private temp dir; rlimits per program.
  docker - pinned python image, --network none, read-only root, no capabilities.
  local  - plain subprocess on the host (timeout only).  Unit tests only.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
from fractions import Fraction
from decimal import Decimal
from pathlib import Path
from typing import Any

SANDBOX_DIR = Path(__file__).resolve().parent
SANDBOX_FILES = ("worker.py", "runner.py", "policy.py", "finq.py")


def _wsl_path(path: Path) -> str:
    drive, rest = path.drive, path.as_posix()[len(path.drive):]
    return f"/mnt/{drive[0].lower()}{rest}"


def backend_command(backend: str, docker_image: str | None = None) -> list[str]:
    if backend == "wsl":
        source = _wsl_path(SANDBOX_DIR)
        files = " ".join(f'"{source}/{name}"' for name in SANDBOX_FILES)
        script = (
            f'D=$(mktemp -d) && cp {files} "$D"/ && '
            'mount -t tmpfs tmpfs /mnt && exec python3 -I -u "$D"/worker.py'
        )
        # --exec: no outer login shell, so "$D" is expanded only by sh inside the namespace.
        return ["wsl.exe", "-d", "Ubuntu", "--exec", "unshare", "-rmn", "sh", "-c", script]
    if backend == "docker":
        if not docker_image:
            raise ValueError("docker backend needs a pinned image")
        return [
            "docker", "run", "-i", "--rm", "--network", "none", "--memory", "1g", "--cpus", "2",
            "--pids-limit", "128", "--read-only", "--tmpfs", "/tmp:size=16m", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "-v", f"{SANDBOX_DIR}:/sandbox:ro",
            docker_image, "python", "-I", "-u", "/sandbox/worker.py",
        ]
    if backend == "local":
        return [sys.executable, "-I", "-u", str(SANDBOX_DIR / "worker.py")]
    raise ValueError(f"unknown sandbox backend {backend!r}")


class Sandbox:
    def __init__(self, backend: str = "wsl", docker_image: str | None = None, timeout: float = 5.0):
        self.backend = backend
        self.command = backend_command(backend, docker_image)
        self.timeout = timeout
        self.lock = threading.Lock()
        self.process: subprocess.Popen | None = None
        self.info: dict[str, Any] = {}
        self.counter = 0

    def _start(self) -> None:
        self.process = subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1,
        )
        ready = self.process.stdout.readline()
        if not ready:
            error = self.process.stderr.read()[-500:]
            raise RuntimeError(f"sandbox worker failed to start: {error}")
        self.info = json.loads(ready)
        self.info["backend"] = self.backend

    def run(self, code: str) -> dict[str, Any]:
        with self.lock:
            for attempt in range(2):
                if self.process is None or self.process.poll() is not None:
                    self._start()
                self.counter += 1
                try:
                    self.process.stdin.write(json.dumps({"id": self.counter, "code": code, "timeout": self.timeout}) + "\n")
                    self.process.stdin.flush()
                    line = self.process.stdout.readline()
                    if line:
                        return json.loads(line)
                except (BrokenPipeError, OSError):
                    pass
                self.close()
            return {"ok": False, "stage": "crash", "error": "sandbox worker died"}

    def close(self) -> None:
        if self.process is not None:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=10)
            except Exception:  # noqa: BLE001
                self.process.kill()
            for stream in (self.process.stdout, self.process.stderr):
                if stream is not None:
                    stream.close()
            self.process = None


def decode(encoded: dict[str, Any]) -> Any:
    kind = encoded["t"]
    if kind == "frac":
        return Fraction(int(encoded["n"]), int(encoded["d"]))
    if kind == "dec":
        return Decimal(encoded["v"])
    if kind == "float":
        return float(encoded["v"])
    if kind in ("str", "bool"):
        return encoded["v"]
    return None


def available_backends() -> list[str]:
    found = ["local"]
    if shutil.which("wsl.exe"):
        found.append("wsl")
    if shutil.which("docker"):
        found.append("docker")
    return found
