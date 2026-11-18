"""Paths, strict LF-only I/O, hashing, and canonical data loading."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finreason_task1.contracts import load_jsonl  # noqa: E402

DEV_DIR = ROOT / "development_files"
TEST_DIR = ROOT / "test_questions"
SPLITS_DIR = ROOT / "splits"
RUNS_DIR = ROOT / "runs"
EXPERIMENTS_DIR = ROOT / "experiments"
CACHE_DIR = ROOT / "cache"

RELEASE_MANIFESTS = (
    (DEV_DIR / "release_manifest.json", DEV_DIR),
    (TEST_DIR / "test_release_manifest.json", TEST_DIR),
)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load JSONL through the toolkit's strict loader (LF only, no BOM, no duplicate keys)."""

    loaded = load_jsonl(path)
    if not loaded.valid:
        raise ValueError(f"{path} failed strict JSONL loading: {loaded.as_dict()['errors'][:3]}")
    return [dict(record) for record in loaded.records]


def write_bytes_atomic(path: str | Path, content: bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    """Canonical UTF-8 JSONL with LF line endings, whatever the platform."""

    return b"".join((canonical_json(row) + "\n").encode("utf-8") for row in rows)


def write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> str:
    content = jsonl_bytes(rows)
    write_bytes_atomic(path, content)
    return sha256_bytes(content)


def append_jsonl(path: str | Path, row: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("ab") as handle:
        handle.write((canonical_json(row) + "\n").encode("utf-8"))


class LockHeld(RuntimeError):
    pass


class RunLock:
    """Exclusive lock held for the life of the process; the OS drops it if the process dies.

    Guards against two copies of a run sharing the subscription and the cache.
    """

    def __init__(self, path: str | Path, holder: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            info = self.path.with_suffix(".holder")
            held_by = info.read_text(encoding="utf-8") if info.exists() else "unknown"
            raise LockHeld(f"another run is active ({held_by.strip()}); refusing to start a second copy") from None
        write_bytes_atomic(self.path.with_suffix(".holder"), f"pid {os.getpid()}: {holder}\n".encode("utf-8"))


def verify_release() -> dict[str, str]:
    """Check every downloaded file against its release manifest; return manifest hashes."""

    hashes: dict[str, str] = {}
    for manifest_path, directory in RELEASE_MANIFESTS:
        manifest = json.loads(manifest_path.read_bytes())
        for artifact in manifest["artifacts"]:
            content = (directory / artifact["path"]).read_bytes()
            if len(content) != artifact["bytes"] or sha256_bytes(content) != artifact["sha256"]:
                raise ValueError(f"{directory / artifact['path']} does not match its release manifest")
        hashes[manifest_path.name] = sha256_file(manifest_path)
    return hashes


SPLIT_SOURCES = {
    "train": ("train_questions.jsonl", "train_gold.jsonl", "train_manifest.jsonl"),
    "dev": ("dev_questions.jsonl", "dev_gold.jsonl", "dev_manifest.jsonl"),
}


class Data:
    """All public Task 1 data, indexed by case_id."""

    def __init__(self) -> None:
        self.questions: dict[str, dict[str, Any]] = {}
        self.gold: dict[str, dict[str, Any]] = {}
        self.manifest: dict[str, dict[str, Any]] = {}
        self.source: dict[str, str] = {}
        for split, (questions, gold, manifest) in SPLIT_SOURCES.items():
            for row in read_jsonl(DEV_DIR / questions):
                self.questions[row["case_id"]] = row
                self.source[row["case_id"]] = split
            for row in read_jsonl(DEV_DIR / gold):
                self.gold[row["case_id"]] = row
            for row in read_jsonl(DEV_DIR / manifest):
                self.manifest[row["case_id"]] = row
        for row in read_jsonl(DEV_DIR / "leaderboard_questions.jsonl"):
            self.questions[row["case_id"]] = row
            self.source[row["case_id"]] = "leaderboard"
        for row in read_jsonl(TEST_DIR / "test_questions.jsonl"):
            self.questions[row["case_id"]] = row
            self.source[row["case_id"]] = "test"

    def ids(self, source: str) -> list[str]:
        return sorted(case_id for case_id, origin in self.source.items() if origin == source)

    def template(self, case_id: str) -> str | None:
        row = self.manifest.get(case_id)
        return None if row is None else row["template_id"]


_DATA: Data | None = None


def data() -> Data:
    global _DATA
    if _DATA is None:
        _DATA = Data()
    return _DATA
