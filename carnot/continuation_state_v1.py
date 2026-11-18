"""Continuation campaign (PLAN.md, 21 Oct 2026): state verification and dependency identities.

  python -m carnot.continuation_state_v1 verify            # read-only checks; prints a summary
  python -m carnot.continuation_state_v1 baseline-manifest # writes baseline_manifest.json once

No model calls.  Every check fails closed: a mismatching historical record is reported,
never regenerated.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import common

ROOT = common.ROOT / "experiments" / "improvement_continuation_20261021"
PRIOR = common.ROOT / "experiments" / "improvement_20261020"
ACCEPTED_RUN = "runs/20261012T165330Z_r4_test928_S"
ACCEPTED = {
    f"{ACCEPTED_RUN}/submission.zip": "cec784e29f40f277d86ee6a38701e22ca117f1102abd5541083cefc8c60e0cc3",
    f"{ACCEPTED_RUN}/predictions.jsonl": "e0ef54ebb142a85e3d7c6ec305c6530058b919db3c63e8328810099627913067",
}
PRIOR_PLAN = ("docs/task1-plan-through-20261021.md", "194175efba4ad2d6bbee331eccc02a867084b37a7fe5a64805b51ab4cf57a4ef")
PRIOR_RECORDS = ("execution_seal.json", "preregistration.json", "diversity_preregistration.json",
                 "verifier_preregistration.json", "sampling_control_preregistration.json")
# The execution seal documents this single amendment to the original preregistration.
DOCUMENTED_AMENDMENTS = {("preregistration.json", "carnot/improvement_campaign.py")}
HISTORICAL_LEDGERS = {"lockbox_looks": 2, "development_uploads": 2}
SKIP_PARTS = {"__pycache__", "tests"}
NEW_PREFIXES = ("carnot/continuation_", "carnot/improvement_validation_v1")  # written by this continuation


def sha(path: str | Path) -> str:
    return common.sha256_file(common.ROOT / path)


def prior_record_hashes() -> dict[str, dict[str, str]]:
    return {name: json.loads((PRIOR / name).read_text(encoding="utf-8"))["hashes"] for name in PRIOR_RECORDS}


def sealed_paths() -> dict[str, list[str]]:
    sealed: dict[str, list[str]] = {}
    for name, hashes in prior_record_hashes().items():
        for path in hashes:
            sealed.setdefault(path, []).append(name)
    return sealed


def verify_accepted() -> None:
    for path, expected in ACCEPTED.items():
        if sha(path) != expected:
            raise RuntimeError(f"accepted R4 artifact changed: {path}")


def verify_prior() -> dict:
    """Final manifest, every prior seal and the baseline audit's protected hashes."""

    checked, mismatches = 0, []
    manifest = json.loads((PRIOR / "final_manifest.json").read_text(encoding="utf-8-sig"))
    for name, expected in manifest["hashes"].items():
        checked += 1
        if common.sha256_file(PRIOR / name) != expected:
            mismatches.append(("final_manifest.json", name))
    for name, hashes in prior_record_hashes().items():
        for path, expected in hashes.items():
            checked += 1
            if sha(path) != expected and (name, path) not in DOCUMENTED_AMENDMENTS:
                mismatches.append((name, path))
    seal = json.loads((PRIOR / "execution_seal.json").read_text(encoding="utf-8"))
    if seal["hashes"]["carnot/improvement_campaign.py"] != sha("carnot/improvement_campaign.py"):
        mismatches.append(("execution_seal.json", "carnot/improvement_campaign.py"))
    audit = json.loads((PRIOR / "baseline_audit.json").read_text(encoding="utf-8"))
    for path, expected in audit["protected"].items():
        checked += 1
        if sha(path) != expected:
            mismatches.append(("baseline_audit.json", path))
    if sha(PRIOR_PLAN[0]) != PRIOR_PLAN[1]:
        mismatches.append(("PLAN.md", PRIOR_PLAN[0]))
    if mismatches:
        raise RuntimeError(f"historical records do not verify: {mismatches}")
    return {"checked_hashes": checked, "documented_amendments": sorted(map(list, DOCUMENTED_AMENDMENTS)),
            "final_manifest_status": manifest["status"]}


def ledgers() -> dict:
    looks = [json.loads(line) for line in (common.EXPERIMENTS_DIR / "lockbox_access.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    look_numbers = sorted({e["reason"].split(":")[0] for e in looks if e.get("event") == "lockbox_look"})
    registry = [json.loads(line) for line in (common.ROOT / "submissions" / "registry.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()]
    uploads = [r for r in registry if r.get("uploaded")]  # receipt rows omit "split"; the run ID names it
    dev_uploads = sorted({r["run_id"] for r in uploads if "_leaderboard580_" in r["run_id"]})
    test_uploads = sorted({r["run_id"] for r in uploads if "_test928_" in r["run_id"]})
    latest_test = [r for r in uploads if "_test928_" in r["run_id"]][-1]
    result = {"lockbox_look_events": len([e for e in looks if e.get("event") == "lockbox_look"]),
              "lockbox_looks_counted": look_numbers, "development_uploads": dev_uploads,
              "test_uploads": test_uploads, "latest_accepted_test_upload": {k: latest_test[k] for k in
                                                                            ("run_id", "archive_sha256", "receipt_id")}}
    if len(look_numbers) != HISTORICAL_LEDGERS["lockbox_looks"] or len(dev_uploads) != HISTORICAL_LEDGERS["development_uploads"]:
        raise RuntimeError(f"ledger counts differ from the historical record: {result}")
    if latest_test["archive_sha256"] != ACCEPTED[f"{ACCEPTED_RUN}/submission.zip"]:
        raise RuntimeError("latest accepted test upload is not the protected R4 archive")
    return result


def cache_summary() -> dict:
    path = common.CACHE_DIR / "llm_cache.sqlite3"
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        rows = db.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
        versions = sorted({json.loads(r)["cli_version"] for (r,) in db.execute("SELECT request FROM calls")})
    finally:
        db.close()
    return {"rows": rows, "cli_versions": versions, "bytes": path.stat().st_size}


def dependency_files() -> list[str]:
    paths = []
    for pattern in ("carnot/**/*.py", "carnot/prompts/*", "configs/*.json", "finreason_task1/*.py"):
        for p in sorted(common.ROOT.glob(pattern)):
            relative = p.relative_to(common.ROOT).as_posix()
            if p.is_file() and not SKIP_PARTS & set(p.relative_to(common.ROOT).parts)                     and not relative.startswith(NEW_PREFIXES):
                paths.append(relative)
    paths += ["exemplars/r0_exemplars.json", "splits/splits_v1.json", "scripts/task1_cli.py",
              "development_files/release_manifest.json", "test_questions/test_release_manifest.json"]
    return sorted(set(paths))


def baseline_manifest() -> None:
    target = ROOT / "baseline_manifest.json"
    if target.exists():
        raise SystemExit("baseline manifest already frozen; refusing to overwrite")
    verify_accepted()
    prior = verify_prior()
    sealed = sealed_paths()
    protected = json.loads((PRIOR / "baseline_audit.json").read_text(encoding="utf-8"))["protected"]
    files = {}
    for path in dependency_files():
        status = ("sealed_prior_experiment" if path in sealed else
                  "protected_r4" if path in protected else "unsealed_existing")
        files[path] = {"sha256": sha(path), "status": status, "sealed_by": sealed.get(path, [])}
    record = {"at": datetime.now(timezone.utc).isoformat(), "purpose": "Identities of every existing dependency "
              "before continuation code is written; frozen modules are imported, never edited.",
              "accepted_r4": ACCEPTED, "prior_verification": prior,
              "release_manifests": common.verify_release(), "files": files,
              "prior_final_manifest_sha256": common.sha256_file(PRIOR / "final_manifest.json")}
    common.write_bytes_atomic(target, (json.dumps(record, indent=2) + "\n").encode("utf-8"))
    print(f"wrote {target.relative_to(common.ROOT)} with {len(files)} dependencies")


def verify_baseline_manifest(allowed_changes: set[str] = frozenset()) -> None:
    """Fail if any pre-existing dependency changed since the continuation began."""

    record = json.loads((ROOT / "baseline_manifest.json").read_text(encoding="utf-8"))
    changed = [p for p, v in record["files"].items() if p not in allowed_changes and sha(p) != v["sha256"]]
    if changed:
        raise RuntimeError(f"existing dependencies changed after the continuation baseline: {changed}")


def verify() -> dict:
    verify_accepted()
    summary = {"prior": verify_prior(), "ledgers": ledgers(), "cache": cache_summary(),
               "release_manifests": common.verify_release()}
    if (ROOT / "baseline_manifest.json").exists():
        verify_baseline_manifest()
        summary["baseline_manifest"] = "verified"
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["verify", "baseline-manifest"])
    args = parser.parse_args(argv)
    if args.action == "verify":
        print(json.dumps(verify(), indent=1))
    else:
        baseline_manifest()
    return 0


if __name__ == "__main__":
    sys.exit(main())
