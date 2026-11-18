"""Frozen run configurations (JSON) and factories for the backends they name."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import common
from .llm_client import ClaudeCLI
from .sandbox.executor import Sandbox

REQUIRED = ("name", "model", "effort", "system_prompt", "exemplars", "n_samples", "max_retries", "sandbox")


def load_config(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    config = json.loads(raw)
    missing = [key for key in REQUIRED if key not in config]
    if missing:
        raise ValueError(f"config {path} lacks {missing}")
    routing = config.get("routing")
    if routing is not None:
        novel = routing.get("novel", {})
        if routing.get("rule") != "novel_vs_train_v1" or not {"model", "effort", "n_samples"} <= set(novel):
            raise ValueError(f"config {path}: routing needs rule novel_vs_train_v1 and novel.model/effort/n_samples")
    for block in (config, (config.get("routing") or {}).get("novel", {})):
        if not isinstance(block.get("echo_notes", False), bool):
            raise ValueError(f"config {path}: echo_notes must be true or false")
        if block.get("unit_hints", "v1") not in ("v1", "v2"):
            raise ValueError(f"config {path}: unit_hints must be v1 or v2")
        conventions = block.get("slot_conventions")
        if conventions is not None and (conventions.get("pool") != "tuning" or int(conventions.get("per_slot", 0)) < 1):
            raise ValueError(f"config {path}: slot_conventions needs pool 'tuning' and per_slot >= 1")
    config["_path"] = str(Path(path).as_posix())
    config["_sha256"] = common.sha256_bytes(raw)
    return config


def make_llm(config: dict[str, Any], route: str = "seen") -> ClaudeCLI:
    """Client for a route: "seen" uses the top-level model/effort, "novel" the routing.novel block."""

    settings = config if route == "seen" else config["routing"]["novel"]
    return ClaudeCLI(settings["model"], settings["effort"])


def make_sandbox(config: dict[str, Any]) -> Sandbox:
    box = config["sandbox"]
    return Sandbox(box["backend"], box.get("docker_image"), float(box.get("timeout", 5)))


def system_prompt_path(config: dict[str, Any], route: str = "seen") -> Path:
    """Resolve an optional novel-route prompt without changing old configurations."""
    block = config if route == "seen" else config["routing"]["novel"]
    return common.ROOT / block.get("system_prompt", config["system_prompt"])


def solver_options(config: dict[str, Any], route: str = "seen") -> dict[str, Any]:
    """unit_hints and slot_conventions for a route ("seen": top level; "novel": the routing.novel block)."""

    from .conventions import SlotConventions

    block = config if route == "seen" else config["routing"]["novel"]
    conventions = block.get("slot_conventions")
    return {"hints": block.get("unit_hints", "v1"), "echo": block.get("echo_notes", False),
            "conventions": SlotConventions(conventions["pool"], int(conventions["per_slot"])) if conventions else None}
