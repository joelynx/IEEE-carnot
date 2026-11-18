"""Anonymous candidate selection with executed evidence; no gold input."""

import json
import random
import re

from .formatter import render
from .sandbox.executor import decode
from .solver import output_table


def candidate_packet(question, samples):
    fields = ["final"] + [s["slot_id"] for s in question["trace_spec"]["slots"]]
    representatives, seen = [], set()
    for index, sample in enumerate(samples):
        texts = sample["texts"]
        if not all(k in texts for k in fields):
            continue
        signature = tuple(texts[k] for k in fields)
        if signature in seen:
            continue
        program = next((a["code"] for a in reversed(sample["attempts"])
                        if a.get("rendered") == texts and a.get("sandbox", {}).get("ok") and a.get("code")), None)
        if program is None:
            continue
        seen.add(signature)
        representatives.append({"original_index": index, "program": program, "outputs": texts})
    random.Random("carnot-r5v-order-" + question["case_id"]).shuffle(representatives)
    anonymous = [{"candidate_index": i, "program": c["program"], "outputs": c["outputs"]}
                 for i, c in enumerate(representatives)]
    prompt = json.dumps({"question": question["question"],
                         "required_outputs": output_table(question, "v2", True), "candidates": anonymous},
                        ensure_ascii=False, indent=2)
    return representatives, prompt


def check_evidence(raw, candidates, question, sandbox):
    """Return an existing sample index only when all supporting outputs match it."""
    result = {"selected_original_index": None, "reason": "malformed_response"}
    try:
        text = raw.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
        parsed = json.loads(fenced.group(1) if fenced else text)
        if not isinstance(parsed, dict) or "selected_index" not in parsed:
            return result
        index = parsed.get("selected_index")
        if index is None:
            return {**result, "reason": "verifier_abstained", "interpretation": parsed.get("interpretation")}
        if type(index) is not int or not 0 <= index < len(candidates):
            return {**result, "reason": "invalid_index"}
        interpretation, code = parsed.get("interpretation"), parsed.get("evidence_program")
        if not isinstance(interpretation, str) or not interpretation.strip() or not isinstance(code, str) or "def solve" not in code:
            return {**result, "reason": "missing_evidence"}
        reply = sandbox.run(code)
        result.update(interpretation=interpretation, evidence_program=code,
                      sandbox={k: reply.get(k) for k in ("ok", "stage", "error", "elapsed_ms")})
        if not reply.get("ok"):
            return {**result, "reason": "evidence_execution_failed"}
        fields = [("final", question["answer_spec"])] + [
            (s["slot_id"], s["result_spec"]) for s in question["trace_spec"]["slots"]]
        values = {k: decode(v) for k, v in reply["values"].items()}
        rendered = {k: render(values[k], spec).text if k in values else None for k, spec in fields}
        result["rendered_evidence"] = rendered
        if any(v is None or v != candidates[index]["outputs"][k] for k, v in rendered.items()):
            return {**result, "reason": "evidence_does_not_support_candidate"}
        return {**result, "reason": "supported_existing_candidate", "selected_anonymous_index": index,
                "selected_original_index": candidates[index]["original_index"]}
    except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
        return {**result, "error": type(exc).__name__}
