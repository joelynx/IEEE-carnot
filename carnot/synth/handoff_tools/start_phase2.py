"""Close phase 1 and unseal the phase-2 cross-check questions.

  python tools/start_phase2.py

Phase 1 is complete when every assignment has either a final template that
passes its check now (outputs/templates/assignment_XX.json, unchanged since its
PASS) or a failure note (outputs/templates/assignment_XX.FAILED.md).  Then the
questions are unpacked to phase2/items/ and the templates are frozen.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))  # works with python -I too

from _common import OUT, PHASE1_DONE, PKG, REF, load_json, log, read_log, sha256_file, write_json


def main() -> int:
    if PHASE1_DONE.exists():
        print("Phase 2 is already open: see phase2/items/.")
        return 0
    checks = read_log("check_log")
    finals, missing = {}, []
    for assignment in load_json(REF / "assignments.json"):
        index = assignment["index"]
        template = OUT / "templates" / f"assignment_{index:02d}.json"
        failed = OUT / "templates" / f"assignment_{index:02d}.FAILED.md"
        passes = [r for r in checks if r["assignment"] == index and r["status"] == "PASS"]
        if passes and template.exists() and sha256_file(template) == passes[-1]["file_sha256"]:
            finals[f"{index:02d}"] = {"status": "PASS", "template_sha256": passes[-1]["file_sha256"],
                                      "template_id": passes[-1]["template_id"], "drafts": len([r for r in checks if r["assignment"] == index])}
        elif failed.exists() and failed.read_text(encoding="utf-8").strip():
            finals[f"{index:02d}"] = {"status": "FAILED", "note_sha256": sha256_file(failed),
                                      "drafts": len([r for r in checks if r["assignment"] == index])}
        else:
            reason = "changed after its PASS" if passes else "no PASS and no FAILED note"
            missing.append(f"assignment_{index:02d} ({reason})")
    if missing:
        print("Phase 1 is not complete:\n  " + "\n  ".join(missing))
        return 2
    sealed = (PKG / "phase2" / "crosscheck_items.bin").read_bytes()
    items = json.loads(zlib.decompress(base64.b64decode(sealed)).decode("utf-8"))
    for item in items:
        write_json(PKG / "phase2" / "items" / f"{item['item']}.json", item)
    summary = {"templates": finals, "passed": sum(v["status"] == "PASS" for v in finals.values()),
               "failed": sum(v["status"] == "FAILED" for v in finals.values()), "phase2_items": len(items)}
    write_json(PHASE1_DONE, summary)
    log("phase_log", {"event": "phase1_complete", **{k: summary[k] for k in ("passed", "failed", "phase2_items")}})
    print(f"Phase 1 complete: {summary['passed']} passed, {summary['failed']} failed. "
          f"{len(items)} cross-check questions are in phase2/items/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
