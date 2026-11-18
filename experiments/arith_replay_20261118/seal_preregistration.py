"""Seal the pre-registration of the arithmetic replay before the first binary64 execution.

Run once, after the user's approval and after the exact reproduction step has passed:

  python -I experiments/arith_replay_20261118/seal_preregistration.py

It records the SHA-256 of the runner and of the two twin modules and sets the status that
run_arith_replay.py requires for its binary64 step.  It refuses to run twice, to seal an
unapproved design, or to seal when the exact replay did not reproduce the stored runs.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREREG = HERE / "preregistration.json"
SEALED = ("sandbox_binary64/finq.py", "sandbox_binary64/runner.py", "run_arith_replay.py")


def main() -> int:
    record = json.loads(PREREG.read_text(encoding="utf-8"))
    if record["status"] != "approved_exact_replay_pending" or "approval" not in record:
        raise SystemExit(f"nothing to seal: status is {record['status']!r}")
    if (HERE / "results" / "overview.json").exists() or any((HERE / "results").glob("*/binary64_*")):
        raise SystemExit("binary64 results already exist; refusing to seal after the fact")
    reproduction = json.loads((HERE / "results" / "exact_reproduction.json").read_text(encoding="utf-8"))
    if not reproduction["reproduced_all"]:
        raise SystemExit("the exact replay did not reproduce the stored runs")
    record["status"] = "frozen_before_binary64_execution"
    record["frozen_at"] = datetime.now(timezone.utc).isoformat()
    record["exact_replay_before_sealing"] = {
        split: {"programs": entry["programs"], "reproduced": entry["reproduced"], "sandbox": entry["sandbox"]}
        for split, entry in reproduction["runs"].items()}
    record["sealed_files_sha256"] = {
        relative: hashlib.sha256((HERE / relative).read_bytes()).hexdigest() for relative in SEALED}
    PREREG.write_bytes((json.dumps(record, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print(json.dumps({k: record[k] for k in ("status", "frozen_at", "exact_replay_before_sealing", "sealed_files_sha256")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
