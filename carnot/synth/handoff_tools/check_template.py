"""Phase 1: check one template draft exactly as our pipeline will.

  python tools/check_template.py outputs/templates/assignment_07.json

Prints PASS or REJECTED with the reason.  Every call is logged to
outputs/logs/check_log.jsonl and the checked draft is copied to outputs/drafts/.
At most 3 checks per assignment (first draft + 2 revisions).  After a PASS, a
preview of the generated questions is written to outputs/previews/.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # works with python -I too

from _common import (AUTHOR, MAX_CHECKS, N_INSTANCES, OUT, PHASE1_DONE, REF, RULES, load_json, log, read_log,
                     sandbox, setup_engine, sha256_bytes, write_json)

NAME = re.compile(r"assignment_(\d\d)\.json\Z")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    path = Path(argv[0])
    match = NAME.fullmatch(path.name)
    if not match or path.resolve().parent != (OUT / "templates").resolve():
        print("REFUSED: save each template as outputs/templates/assignment_XX.json (XX = the two-digit assignment index).")
        return 2
    if PHASE1_DONE.exists():
        print("REFUSED: phase 1 is complete and templates are frozen.")
        return 2
    index = int(match.group(1))
    assignments = {a["index"]: a for a in load_json(REF / "assignments.json")}
    if index not in assignments:
        print(f"REFUSED: there is no assignment {index:02d}.")
        return 2
    previous = [r for r in read_log("check_log") if r["assignment"] == index]
    if len(previous) >= MAX_CHECKS:
        print(f"REFUSED: all {MAX_CHECKS} checks for assignment {index:02d} are used. Record it as failed: write "
              f"outputs/templates/assignment_{index:02d}.FAILED.md (see INSTRUCTIONS.md, Phase 1).")
        return 2
    if any(r["status"] == "PASS" for r in previous):
        print(f"REFUSED: assignment {index:02d} already passed; its template is final.")
        return 2
    draft = len(previous) + 1
    raw = path.read_bytes()
    drafts = OUT / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    (drafts / f"assignment_{index:02d}_draft{draft}.json").write_bytes(raw)
    record = {"assignment": index, "draft": draft, "file_sha256": sha256_bytes(raw), "rules": RULES}
    engine = setup_engine()
    box = sandbox()
    try:
        try:
            tpl = json.loads(raw.decode("utf-8"))
            if not isinstance(tpl, dict):
                raise engine.TemplateError("the file must hold one JSON object")
            for key in ("domain_id", "topic_id", "difficulty"):
                if tpl.get(key) != assignments[index][key]:
                    raise engine.TemplateError(f"{key} must be {assignments[index][key]!r}")
            generation = engine.generate(tpl, AUTHOR, N_INSTANCES, box, rules=RULES)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            record.update(status="REJECTED", error=f"the file is not valid JSON: {exc}")
        except engine.TemplateError as exc:
            record.update(status="REJECTED", error=str(exc))
        except Exception as exc:  # a fault in the tool, not in the template
            record.update(status="TOOL_ERROR", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc()[-2000:])
        else:
            record.update(status="PASS", template_id=engine.template_id(tpl, AUTHOR, RULES),
                          instances=[{"case_id": i.question["case_id"], "final": i.gold["final_value"]} for i in generation.instances])
            preview = [f"# Preview: assignment {index:02d} ({record['template_id']})", ""]
            for inst in generation.instances:
                preview += [f"## Seed {inst.seed}: {inst.params}", "", inst.question["question"], "",
                            f"Reference: final = {inst.gold['final_value']}; slots = {json.dumps(inst.gold['slot_values'])}", ""]
            (OUT / "previews").mkdir(parents=True, exist_ok=True)
            (OUT / "previews" / f"assignment_{index:02d}.md").write_bytes("\n".join(preview).encode("utf-8"))
    finally:
        box.close()
    log("check_log", record)
    remaining = MAX_CHECKS - draft
    if record["status"] == "PASS":
        print(f"PASS: assignment {index:02d}, draft {draft}. Preview: outputs/previews/assignment_{index:02d}.md")
        return 0
    if record["status"] == "TOOL_ERROR":
        print(f"TOOL_ERROR (a fault in the checking tool, not your template; this draft still counts): {record['error']}\n"
              "Describe it in outputs/REPORT.md. Do not edit the tools.")
        return 3
    print(f"REJECTED: {record['error']}\nChecks left for this assignment: {remaining}.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
