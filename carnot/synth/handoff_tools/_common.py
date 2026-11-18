"""Shared helpers for the handoff tools.  Runs inside the handoff folder; Python 3.10+, standard library only."""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "lib"))

REF = PKG / "reference"
OUT = PKG / "outputs"
LOGS = OUT / "logs"
AUTHOR = "nonclaude"
RULES = "v3"
N_INSTANCES = 6
MAX_CHECKS = 3      # first draft + 2 revisions, as the Fable author had
MAX_ATTEMPTS = 3    # first program + 2 retries, as the R1/R2 solver has
PHASE1_DONE = OUT / "PHASE1_COMPLETE.json"


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def log(name: str, record: dict) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    with (LOGS / f"{name}.jsonl").open("ab") as handle:
        handle.write((json.dumps({**record, "at": now()}, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))


def read_log(name: str) -> list[dict]:
    path = LOGS / f"{name}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def setup_engine():
    """The authoritative template engine, with the novelty index and length limits shipped as data."""

    from carnot.common import canonical_json, sha256_text
    from carnot.routing import signature, skeleton
    from carnot.synth import template as engine

    index = load_json(REF / "novelty_index.json")
    skeletons, signatures = set(index["skeleton_sha256"]), set(index["signature_sha256"])

    class HashedRouter:
        def is_novel(self, question) -> bool:
            sig = canonical_json([list(pair) for pair in signature(question)])
            return sha256_text(skeleton(question["question"])) not in skeletons and sha256_text(sig) not in signatures

    engine._ROUTER = HashedRouter()
    engine._LIMITS = load_json(REF / "length_limits.json")
    return engine


def sandbox():
    from carnot.sandbox.executor import Sandbox

    return Sandbox("local", timeout=5)
