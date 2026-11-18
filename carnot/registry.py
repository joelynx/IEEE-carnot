"""Submission registry (PLAN.md §5.9): packaged candidates and their upload receipts.

  python -m carnot.registry list
  python -m carnot.registry receipt --archive-sha256 <sha> --phase test --receipt <id> [--accepted-at <utc>]
  python -m carnot.registry portal --archive-sha256 <sha> --phase development --response-file <json>

Entries are appended, never rewritten, so the history of what was uploaded
(and which run, config and hashes produced it) stays auditable.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from . import common

REGISTRY = common.ROOT / "submissions" / "registry.jsonl"


def entries() -> list[dict]:
    if not REGISTRY.exists():
        return []
    return [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    receipt = sub.add_parser("receipt")
    receipt.add_argument("--archive-sha256", required=True)
    receipt.add_argument("--phase", required=True, choices=["development", "test"])
    receipt.add_argument("--receipt", required=True)
    receipt.add_argument("--accepted-at", default=None)
    portal = sub.add_parser("portal", help="store the portal's JSON response verbatim (scores, rank)")
    portal.add_argument("--archive-sha256", required=True)
    portal.add_argument("--phase", required=True, choices=["development", "test"])
    portal.add_argument("--response-file", required=True)
    args = parser.parse_args(argv)
    if args.command == "list":
        for entry in entries():
            print(json.dumps(entry))
        return 0
    packaged = [e for e in entries() if e.get("archive_sha256") == args.archive_sha256 and "receipt_id" in e]
    if not packaged:
        raise SystemExit("no packaged candidate with that archive SHA-256")
    source = packaged[0]
    if args.command == "portal":
        with open(args.response_file, encoding="utf-8") as handle:
            response = json.load(handle)
        common.append_jsonl(REGISTRY, {
            "event": "portal_response", "phase": args.phase, "run_id": source["run_id"],
            "archive_sha256": args.archive_sha256, "response": response,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
        print("recorded")
        return 0
    common.append_jsonl(REGISTRY, {
        "event": "upload_receipt", "phase": args.phase, "run_id": source["run_id"], "config": source["config"],
        "config_sha256": source["config_sha256"], "archive_sha256": args.archive_sha256,
        "predictions_jsonl_sha256": source["predictions_jsonl_sha256"], "uploaded": True,
        "receipt_id": args.receipt, "accepted_at": args.accepted_at,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    print("recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
