"""Phase 0: confirm this environment can run the tools.

  python tools/selfcheck.py

Checks the Python version, runs the template engine on tools/sample_template.json
(a practice template, not an assignment) and solves one of its questions through
the answer tool's rendering path.  Writes outputs/environment.json.
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # works with python -I too

from _common import OUT, PKG, log, sandbox, setup_engine, write_json

PROGRAM = """def solve():
    balance = Q("{B}")
    rate = Q("{f}") / 100
    fee = balance * rate
    return {{"final": balance - fee, "engine_fee_rate_trace": rate, "engine_fee_usd_trace": fee}}
"""


def main() -> int:
    result = {"python": sys.version.split()[0], "platform": platform.platform(), "executable": sys.executable}
    if sys.version_info < (3, 10):
        result["ok"] = False
        write_json(OUT / "environment.json", result)
        print(f"FAIL: Python 3.10 or newer is needed (found {result['python']}).")
        return 1
    engine = setup_engine()
    from carnot.formatter import render
    from carnot.sandbox.executor import decode

    sample = json.loads((PKG / "tools" / "sample_template.json").read_text(encoding="utf-8"))
    box = sandbox()
    try:
        generation = engine.generate(sample, "selfcheck", 2, box, rules="v2")
        first = generation.instances[0]
        reply = box.run(PROGRAM.format(B=first.params["B"], f=first.params["f"]))
    finally:
        box.close()
    values = {k: decode(v) for k, v in reply["values"].items()} if reply.get("ok") else {}
    spec = first.question["answer_spec"]
    rendered = render(values.get("final"), spec).text if values else None
    result["ok"] = rendered == first.gold["final_value"]
    result["detail"] = {"sample_final": first.gold["final_value"], "solved_final": rendered}
    write_json(OUT / "environment.json", result)
    log("phase_log", {"event": "selfcheck", "ok": result["ok"], "python": result["python"]})
    print("OK: the tools work in this environment." if result["ok"] else f"FAIL: {result['detail']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
