"""Append the amendment of 18 November 2026 to the sealed pre-registration (run once).

The amendment corrects a factual statement about the inputs that an independent check found
after the run.  Nothing else in the file is touched: the original wording stays, and the
sealed hashes, the design and the results are unaffected.

  python -I experiments/arith_replay_20261118/amend_preregistration.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PREREG = Path(__file__).resolve().parent / "preregistration.json"
AMENDMENT = {
    "id": "A1",
    "kind": "correction of a factual statement about the inputs, found after the run",
    "wrong_statement": "inputs.overlap: 'the two runs hold different programs for them'; inputs.known_from_program_text_before_registration and procedure step 2 count 2,894 programs.",
    "correction": "The tuning-noex run took its responses for the 580 tuning-eval questions from the response cache (its summary records 1,734 fresh and 580 cached calls), so the 580 programs of the tuning-eval run are among its 2,314 programs, with the same cache keys and the same text. There are 2,314 distinct programs; 2,894 is the number of executions per arm.",
    "effect": "None on the design, the sealed files or any result file. The two runs are not two samples: the second contains the first. The reporting therefore adds counts for the 1,734 programs that are only in the tuning-noex run (paper/working_notes/verify/arith_replay_checks.py), and no text treats the tuning-noex figures as independent of the tuning-eval figures.",
    "found_by": "an independent read-only check of the paper's numbers against the result files, before the paper was finalised",
}


def main() -> int:
    record = json.loads(PREREG.read_text(encoding="utf-8"))
    if record["status"] != "frozen_before_binary64_execution":
        raise SystemExit("the pre-registration is not sealed")
    if any(item.get("id") == AMENDMENT["id"] for item in record["amendments"]):
        raise SystemExit("amendment A1 is already recorded")
    record["amendments"].append({"at": datetime.now(timezone.utc).isoformat(), **AMENDMENT})
    PREREG.write_bytes((json.dumps(record, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print(json.dumps(record["amendments"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
