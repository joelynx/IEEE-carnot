"""Seal checked data and comparison implementation before the first candidate run."""

import json
from datetime import datetime, timezone

from . import common
from .campaign_integrity import require_family_checks
from .improvement_campaign import ROOT, PILOT, save, verify_protected


def main():
    verify_protected()
    if (ROOT / "execution_seal.json").exists():
        raise SystemExit("execution seal already exists")
    if list(PILOT.glob("family_*/evaluation_*.json")):
        raise SystemExit("cannot preregister after candidate results exist")
    prereg = json.loads((ROOT / "preregistration.json").read_text())
    amended = {"carnot/improvement_campaign.py"}
    for path, expected in prereg["hashes"].items():
        if path not in amended and common.sha256_file(common.ROOT / path) != expected:
            raise SystemExit(f"preregistered recipe changed: {path}")
    directories = sorted(p.parent for p in PILOT.glob("family_*/instances.jsonl"))
    if len(directories) != 24:
        raise SystemExit("24 checked families required")
    paths = list(prereg["hashes"]) + ["carnot/campaign_integrity.py", "carnot/improvement_quality.py",
        "carnot/improvement_report.py", "carnot/prospective.py", "carnot/selection.py",
        "carnot/llm_client.py", "carnot/formatter.py", "carnot/improvement_seal.py",
        "carnot/improvement_adjudicate.py"]
    for directory in directories:
        require_family_checks(directory)
        for name in ("template.json", "instances.jsonl", "blind_check.json", "endpoint_check.json"):
            paths.append((directory / name).relative_to(common.ROOT).as_posix())
        if (directory / "adjudication.json").exists():
            paths.append((directory / "adjudication.json").relative_to(common.ROOT).as_posix())
    save(ROOT / "execution_seal.json", {
        "at": datetime.now(timezone.utc).isoformat(), "before_candidate_results": True,
        "amendment": "Resume integrity checks, endpoint gating and successful-preflight gating added. "
                     "Candidate prompts, settings, data-generation recipe and statistical policy unchanged. "
                     "Pre-evaluation reference corrections are documented in per-family adjudication.json records.",
        "original_campaign_sha256": prereg["hashes"]["carnot/improvement_campaign.py"],
        "hashes": {p: common.sha256_file(common.ROOT / p) for p in sorted(set(paths))}})
    print("Sealed 24 checked families and comparison implementation before R4/R5-P evaluation.")


if __name__ == "__main__":
    main()
