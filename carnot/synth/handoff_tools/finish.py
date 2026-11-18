"""Close the run: verify both phases and write outputs/SUMMARY.json.

  python tools/finish.py

Phase 2 is complete when every item has a complete answer or has used all its
attempts.  The summary records counts and the SHA-256 of every output file, so
the results can be checked when the folder comes back.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # works with python -I too

from _common import MAX_ATTEMPTS, OUT, PHASE1_DONE, PKG, load_json, log, read_log, sha256_file, write_json


def main() -> int:
    if not PHASE1_DONE.exists():
        print("Not finished: phase 1 is not complete (python tools/start_phase2.py).")
        return 2
    attempts = read_log("solve_log")
    items = sorted(p.stem for p in (PKG / "phase2" / "items").glob("item_*.json"))
    open_items = []
    for item in items:
        mine = [r for r in attempts if r["item"] == item]
        if not (mine and (mine[-1]["complete"] or len(mine) >= MAX_ATTEMPTS)):
            open_items.append(item)
    if open_items:
        print("Not finished: these items still need an answer or their remaining attempts:\n  " + ", ".join(open_items))
        return 2
    report = OUT / "REPORT.md"
    files = {str(p.relative_to(PKG)).replace("\\", "/"): sha256_file(p) for p in sorted(OUT.rglob("*"))
             if p.is_file() and p.name not in ("SUMMARY.json", ".keep")}
    summary = {
        "phase1": load_json(PHASE1_DONE),
        "phase2": {"items": len(items),
                   "answered": sum(1 for i in items if any(r["item"] == i and r["complete"] for r in attempts)),
                   "attempts": len(attempts)},
        "report_written": report.exists() and bool(report.read_text(encoding="utf-8").strip()),
        "output_sha256": files,
    }
    write_json(OUT / "SUMMARY.json", summary)
    log("phase_log", {"event": "finished", "answered": summary["phase2"]["answered"], "items": len(items)})
    print(f"Finished: {summary['phase1']['passed']} templates passed, {summary['phase2']['answered']}/{len(items)} "
          f"cross-check questions answered. outputs/SUMMARY.json written."
          + ("" if summary["report_written"] else " Now write outputs/REPORT.md, then run this command again."))
    return 0 if summary["report_written"] else 1


if __name__ == "__main__":
    sys.exit(main())
