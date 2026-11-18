"""Fail-closed artifact checks for resumable synthetic comparisons."""

import json
from pathlib import Path

from . import common


def require_preflight(record):
    if record.get("fac") != 1 or record.get("matched_slots") != record.get("total_slots"):
        raise RuntimeError("training smoke did not pass")


def require_family_checks(directory: Path):
    instances_hash = common.sha256_file(directory / "instances.jsonl")
    template_hash = common.sha256_file(directory / "template.json")
    blind = json.loads((directory / "blind_check.json").read_text(encoding="utf-8"))
    endpoints = json.loads((directory / "endpoint_check.json").read_text(encoding="utf-8"))
    if not blind.get("all_agree") or blind.get("instances_sha256") != instances_hash:
        raise RuntimeError(f"{directory.name}: unresolved or stale blind check")
    if endpoints.get("unexpected_failures") != 0 or endpoints.get("template_sha256") != template_hash:
        raise RuntimeError(f"{directory.name}: unresolved or stale endpoint check")
    return instances_hash


def require_evaluation_identity(record, config_hash, system_hash, instances_hash):
    expected = {"config_sha256": config_hash, "system_sha256": system_hash,
                "instances_sha256": instances_hash}
    for field, value in expected.items():
        if record.get(field) != value:
            raise RuntimeError(f"saved evaluation has a different {field}; use a new artifact identity")
