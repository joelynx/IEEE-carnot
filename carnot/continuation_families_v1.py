"""Package D: new synthetic family panel (design, authoring, oracle gates, panels, seal).

  python -m carnot.continuation_families_v1 assign
  python -m carnot.continuation_families_v1 author --select partition=development,wave=1
  python -m carnot.continuation_families_v1 check  --select partition=development,wave=1
  python -m carnot.continuation_families_v1 status [--select ...]
  python -m carnot.continuation_families_v1 panel  --select partition=development,wave=1 --name wave1
  python -m carnot.continuation_families_v1 seal

Authoring and checking are candidate-blind: no candidate recipe, output or score is read here.
Status output for confirmation families shows verdicts only, never question text or gold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from . import common
from .config import load_config, make_sandbox
from .continuation_state_v1 import PRIOR, ROOT
from .formatter import render
from .improvement_quality import endpoints
from .improvement_validation_v1 import StrictClient, read_json, save_json
from .llm_client import UsageLimitError
from .sandbox.executor import decode
from .solver import Solver, extract_code, load_system_prompt
from .synth.author import parse, topic_examples
from .synth.crosscheck import field_verdicts
from .synth.template import TemplateError, _display, body_limits, generate, program_source, sample, template_id

DATA = ROOT / "data"
DESIGN = DATA / "family_design.json"
MANIFEST = DATA / "family_manifest.json"
DECISIONS = DATA / "quality_decisions.jsonl"
PROMPTS = common.ROOT / "carnot" / "prompts"
AUTHOR_PROMPT = PROMPTS / "synth_author_v5.txt"
SECOND_PROMPT = PROMPTS / "oracle_second_impl_v1.txt"
CHECKER_PROMPT = PROMPTS / "oracle_checker_neutral_v1.txt"
AUTHOR_MODEL, AUTHOR_EFFORT, CHECKER_EFFORT = "claude-fable-5-1", "high", "medium"
AUTHOR_ID, RULES = "fable_c1", "v4"
N_DRAWS, N_SCORED, MAX_REPAIRS = 12, 4, 2
PARTITION_SEED = "carnot-continuation-v1-partition"
CLASSES = ["T", "S", "U", "R", "O", "D"]
SLOTS = (("intermediate", "A", 0), ("intermediate", "B", 3), ("advanced", "A", 1), ("advanced", "B", 4))
_RESERVE = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_decision(event: Mapping[str, Any]) -> None:
    common.append_jsonl(DECISIONS, {"at": now(), **event})


# ---------------------------------------------------------------- design and assignment


def validate_design(design: Mapping[str, Any]) -> list[dict]:
    d = common.data()
    topics: dict[str, set] = {}
    for row in d.manifest.values():
        topics.setdefault(row["domain_id"], set()).add(row["topic_id"])
    domains = sorted(topics)
    pairs = {p["pair_id"]: p for p in design["pairs"]}
    if len(pairs) != 48 or len(design["pairs"]) != 48:
        raise RuntimeError("design needs 48 distinct pairs")
    families, briefs = [], set()
    for i, domain in enumerate(domains):
        for difficulty, slot, shift in SLOTS:
            pair = pairs[f"{domain}:{difficulty}:{slot}"]
            expected = CLASSES[(i + shift) % 6]
            if (pair["domain_id"], pair["difficulty"], pair["slot"], pair["mechanism_class"]) != (domain, difficulty, slot, expected):
                raise RuntimeError(f"{pair['pair_id']}: violates the preregistered class table (expected {expected})")
            if len(pair["members"]) != 2:
                raise RuntimeError(f"{pair['pair_id']}: two members required")
            for member, entry in enumerate(pair["members"]):
                if entry["topic_id"] not in topics[domain] or entry["brief"] in briefs:
                    raise RuntimeError(f"{pair['pair_id']}: unknown topic or duplicated brief")
                briefs.add(entry["brief"])
                families.append({"design_index": len(families), "pair_id": pair["pair_id"], "member": member,
                                 "domain_id": domain, "topic_id": entry["topic_id"], "difficulty": difficulty,
                                 "slot": slot, "mechanism_class": pair["mechanism_class"], "brief": entry["brief"]})
    counts = Counter((f["mechanism_class"]) for f in families)
    if set(counts.values()) != {16}:
        raise RuntimeError(f"class balance violated: {counts}")
    return families


def assign() -> None:
    if MANIFEST.exists():
        raise SystemExit("family manifest already frozen")
    design = read_json(DESIGN)
    families = validate_design(design)
    for f in families:
        rng = random.Random(int(hashlib.sha256(f"{PARTITION_SEED}#{f['pair_id']}".encode()).hexdigest(), 16))
        dev_member = rng.randrange(2)
        f["partition"] = "development" if f["member"] == dev_member else "confirmation"
        f["wave"] = (1 if f["slot"] == "A" else 2) if f["partition"] == "development" else None
        f["family_id"] = f"c1_{f['design_index']:02d}"
    save_json(MANIFEST, {"at": now(), "design_sha256": common.sha256_file(DESIGN), "partition_seed": PARTITION_SEED,
                         "author": {"model": AUTHOR_MODEL, "effort": AUTHOR_EFFORT, "author_id": AUTHOR_ID, "rules": RULES,
                                    "prompt_sha256": common.sha256_file(AUTHOR_PROMPT)},
                         "checks": {"second_implementation": {"model": AUTHOR_MODEL, "effort": AUTHOR_EFFORT,
                                                              "prompt_sha256": common.sha256_file(SECOND_PROMPT)},
                                    "blind": {"model": AUTHOR_MODEL, "effort": CHECKER_EFFORT,
                                              "prompt_sha256": common.sha256_file(CHECKER_PROMPT)}},
                         "draws_validated": N_DRAWS, "draws_scored": N_SCORED, "families": families})
    summary = Counter((f["partition"], f["wave"]) for f in families)
    print(json.dumps({str(k): v for k, v in summary.items()}, indent=1))


def manifest() -> dict:
    record = read_json(MANIFEST)
    if record["design_sha256"] != common.sha256_file(DESIGN):
        raise RuntimeError("family design changed after assignment")
    return record


def select(spec: str | None) -> list[dict]:
    families = manifest()["families"]
    if not spec:
        return families
    wanted = dict(item.split("=", 1) for item in spec.split(","))
    out = []
    for f in families:
        if "ids" in wanted and f["family_id"] not in wanted["ids"].split("+"):
            continue
        if "partition" in wanted and f["partition"] != wanted["partition"]:
            continue
        if "wave" in wanted and str(f["wave"]) != wanted["wave"]:
            continue
        out.append(f)
    return out


def family_dir(f: Mapping[str, Any], replacement: str = "") -> Path:
    return DATA / f["partition"] / (f["family_id"] + (f"_{replacement}" if replacement else ""))


def active_dir(f: Mapping[str, Any]) -> Path:
    """The replacement directory once the original is quarantined."""

    replaced = family_dir(f, "r1")
    return replaced if (replaced / "template.json").exists() else family_dir(f)


# ---------------------------------------------------------------- authoring


def pilot_designs(domain: str, topic: str) -> list[str]:
    prereg = read_json(PRIOR / "preregistration.json")
    return [a["mechanism"] for a in prereg["assignments"] if a["domain_id"] == domain and a["topic_id"] == topic]


REVISION = DATA / "design_revision_v1.json"
AUTHOR_PROMPT_V6 = PROMPTS / "synth_author_v6.txt"


def revised(f: Mapping[str, Any]) -> bool:
    """The single preregistered design revision applies to wave 2 and all confirmation families."""

    return REVISION.exists() and f.get("wave") != 1


def secondary_class(primary: str) -> str:
    return CLASSES[(CLASSES.index(primary) + 2) % 6]


def author_system(f: Mapping[str, Any]) -> str:
    if revised(f):
        record = read_json(REVISION)
        if record["author_prompt_sha256"] != common.sha256_file(AUTHOR_PROMPT_V6):
            raise RuntimeError("revised author prompt changed after the revision was frozen")
        return AUTHOR_PROMPT_V6.read_text(encoding="utf-8")
    return AUTHOR_PROMPT.read_text(encoding="utf-8")


def author_prompt(f: Mapping[str, Any]) -> str:
    design = read_json(DESIGN)
    assignment = {"domain_id": f["domain_id"], "topic_id": f["topic_id"], "difficulty": f["difficulty"],
                  "mechanism_class": design["classes"][f["mechanism_class"]], "brief": f["brief"]}
    if revised(f):
        assignment["secondary_mechanism"] = design["classes"][secondary_class(f["mechanism_class"])]
    prompt = json.dumps(assignment) + f"\nCharacter limit: {body_limits('max')[f['difficulty']]}\n"
    prompt += "Existing tuning templates, for avoiding structural duplication:\n"
    for e in topic_examples(f["domain_id"], f["topic_id"]):
        prompt += json.dumps({"question": e["question"]["question"], "difficulty": e["difficulty"]}) + "\n"
    earlier = pilot_designs(f["domain_id"], f["topic_id"])
    if earlier:
        prompt += "Earlier synthetic designs in this topic, also not to be duplicated:\n" + "\n".join(earlier) + "\n"
    return prompt


def grid_value(spec: Mapping[str, Any], value: Any) -> Any:
    if spec["kind"] == "int":
        if type(value) is not int or not spec["min"] <= value <= spec["max"] or (value - spec["min"]) % spec["step"]:
            raise TemplateError(f"coverage value {value!r} is not on the int grid {spec}")
        return value
    if spec["kind"] == "decimal":
        try:
            x = Fraction(str(value))
        except (ValueError, ZeroDivisionError):
            raise TemplateError(f"coverage value {value!r} is not a decimal") from None
        low, high, step = (Fraction(str(spec[k])) for k in ("min", "max", "step"))
        if not low <= x <= high or ((x - low) / step).denominator != 1:
            raise TemplateError(f"coverage value {value!r} is not on the decimal grid {spec}")
        return x
    if value not in spec["values"]:
        raise TemplateError(f"coverage value {value!r} is not one of {spec['values']}")
    return value


def coverage_sets(tpl: Mapping[str, Any]) -> list[dict]:
    sets = tpl.get("coverage_params")
    if not isinstance(sets, list) or not 2 <= len(sets) <= 4:
        raise TemplateError("coverage_params must be a list of 2 to 4 parameter assignments")
    out = []
    for entry in sets:
        if not isinstance(entry, dict) or set(entry) != set(tpl["params"]):
            raise TemplateError("each coverage_params entry must assign every parameter exactly once")
        out.append({k: grid_value(tpl["params"][k], v) for k, v in entry.items()})
    return out


def known_template_ids(exclude: Path | None = None) -> set[str]:
    ids = set()
    for path in DATA.glob("*/c1_*/template.json"):
        if exclude is not None and path.parent == exclude:
            continue
        ids.add(template_id(read_json(path), AUTHOR_ID, RULES))
    return ids


def author_one(f: Mapping[str, Any], replacement: str = "") -> dict:
    directory = family_dir(f, replacement)
    if (directory / "template.json").exists():
        return {"family": directory.name, "status": "already_authored"}
    llm = StrictClient(AUTHOR_MODEL, AUTHOR_EFFORT)
    box = make_sandbox(load_config("configs/r4.json"))
    system = author_system(f)
    base = prompt = author_prompt(f)
    suffix = f"-{replacement}" if replacement else ""
    attempts = []
    try:
        for attempt in range(MAX_REPAIRS + 1):
            response = llm.complete(system, prompt, tag=f"c1-author-{f['family_id']}{suffix}-{attempt}")
            record = {"attempt": attempt, "cache_key": response.key, "cached": response.cached, "model": response.model_id,
                      "usage": response.usage, "cost_equivalent_usd": response.cost_equivalent_usd}
            attempts.append(record)
            try:
                tpl = parse(response.text)
                for k in ("domain_id", "topic_id", "difficulty"):
                    if tpl.get(k) != f[k]:
                        raise TemplateError(f"{k} must be {f[k]!r}")
                coverage_sets(tpl)
                generated = generate(tpl, AUTHOR_ID, N_DRAWS, box, rules=RULES)
                tid = template_id(tpl, AUTHOR_ID, RULES)
                with _RESERVE:
                    if tid in known_template_ids(exclude=directory):
                        raise TemplateError(f"template name {tpl['name']!r} is already used in this topic; choose another name")
                    save_json(directory / "template.json", tpl)
            except TemplateError as exc:
                record["error"] = str(exc)[:1500]
                save_json(directory / "author_log.json", {"family": dict(f), "attempts": attempts, "status": "repair"})
                prompt = (base + "\nPrevious draft:\n" + response.text + "\nValidation error:\n" + str(exc)
                          + "\nReturn a corrected complete JSON template.")
                continue
            common.write_jsonl(directory / "draws.jsonl", [
                {"seed": i.seed, "params": i.params, "question": i.question, "gold": i.gold, "manifest": i.manifest}
                for i in generated.instances])
            save_json(directory / "author_log.json", {
                "family": dict(f), "attempts": attempts, "status": "generated", "template_id": tid,
                "draws_validated": N_DRAWS, "rejected_draws": generated.errors, "replacement": replacement or None,
                "template_sha256": common.sha256_file(directory / "template.json"),
                "draws_sha256": common.sha256_file(directory / "draws.jsonl"),
                "prompt_sha256": common.sha256_text(system), "design_revision": revised(f),
                "secondary_class": secondary_class(f["mechanism_class"]) if revised(f) else None})
            log_decision({"event": "authored", "family": directory.name, "attempts": len(attempts)})
            return {"family": directory.name, "status": "generated", "attempts": len(attempts)}
        save_json(directory / "author_log.json", {"family": dict(f), "attempts": attempts, "status": "failed"})
        log_decision({"event": "authoring_failed", "family": directory.name, "attempts": len(attempts)})
        return {"family": directory.name, "status": "failed", "attempts": len(attempts)}
    finally:
        box.close()


# ---------------------------------------------------------------- oracle gates


def fields(tpl: Mapping[str, Any]) -> list[tuple[str, dict]]:
    return [("final", tpl["answer_spec"])] + [(s["slot_id"], s["result_spec"]) for s in tpl["slots"]]


def evaluate_program(box, tpl, program: str, values: Mapping[str, Any]) -> dict:
    """Run one program on one parameter set and render every field with the exact formatter."""

    reply = box.run(program_source(dict(tpl, program=program), values))
    if not reply.get("ok"):
        declared = "ValueError" in str(reply.get("error"))
        return {"ok": False, "declared_invalid": declared, "stage": reply.get("stage"), "error": str(reply.get("error"))[:300]}
    outputs = {k: decode(v) for k, v in reply["values"].items()}
    texts, issues = {}, {}
    for name, spec in fields(tpl):
        if name not in outputs:
            issues[name] = "missing"
            continue
        r = render(outputs[name], spec)
        if r.text is None:
            issues[name] = r.issue or "unrenderable"
        else:
            texts[name] = r.text
    return {"ok": not issues, "declared_invalid": False, "texts": texts, "issues": issues}


def draw_values(tpl: Mapping[str, Any], seed: int, sampling_tid: str | None = None) -> dict:
    """Exact parameter values of a draw, recomputed from its seed (draws store display strings).

    Stress variants sample with their source template's identity so that they share its values.
    """

    tid = sampling_tid or template_id(tpl, AUTHOR_ID, RULES)
    return sample(tpl["params"], random.Random(f"{tid}#{seed}"))


def sampling_identity(directory: Path) -> str | None:
    path = directory / "sampling.json"
    return read_json(path)["sampling_template_id"] if path.exists() else None


def parameter_sets(tpl: Mapping[str, Any], directory: Path) -> list[tuple[str, dict]]:
    sets = []
    sampling_tid = sampling_identity(directory)
    for d in common.read_jsonl(directory / "draws.jsonl"):
        values = draw_values(tpl, d["seed"], sampling_tid)
        if {k: _display(v, tpl["params"][k]) for k, v in values.items()} != d["params"]:
            raise RuntimeError(f"{directory.name}: draw {d['seed']} parameters do not reproduce from its seed")
        sets.append((f"draw_{d['seed']}", values))
    sets += [(f"endpoint_{label}", p) for label, p in endpoints(tpl["params"])]
    sets += [(f"coverage_{i}", p) for i, p in enumerate(coverage_sets(tpl))]
    return sets


def second_prompt(tpl: Mapping[str, Any]) -> str:
    outputs = [{"key": "final", "result_spec": tpl["answer_spec"]}] + [
        {"key": s["slot_id"], "description": s["description"], "result_spec": s["result_spec"]} for s in tpl["slots"]]
    return json.dumps({"question_template": tpl["question_template"], "parameters": tpl["params"],
                       "required_outputs": outputs}, ensure_ascii=False, indent=1)


def compare_programs(box, tpl, second: str, sets) -> dict:
    rows, mismatches, second_errors, reference_errors, compared = [], [], [], [], 0
    for label, values in sets:
        ref = evaluate_program(box, tpl, tpl["program"], values)
        if not ref["ok"]:
            if not ref["declared_invalid"]:
                reference_errors.append({"set": label, **{k: ref.get(k) for k in ("stage", "error", "issues")}})
            rows.append({"set": label, "reference": "declared_invalid" if ref["declared_invalid"] else "error"})
            continue
        alt = evaluate_program(box, tpl, second, values)
        compared += 1
        if not alt["ok"]:
            second_errors.append({"set": label, **{k: alt.get(k) for k in ("stage", "error", "issues")}})
            rows.append({"set": label, "reference": "ok", "second": "error"})
            continue
        diff = {k: [ref["texts"][k], alt["texts"].get(k)] for k in ref["texts"] if alt["texts"].get(k) != ref["texts"][k]}
        if diff:
            mismatches.append({"set": label, "fields": diff})
        rows.append({"set": label, "reference": "ok", "second": "match" if not diff else "mismatch"})
    return {"compared": compared, "mismatches": mismatches, "second_errors": second_errors,
            "reference_unexpected_errors": reference_errors, "rows": rows}


def second_implementation(f, directory: Path, tpl, box) -> dict:
    path = directory / "second_impl.json"
    template_sha = common.sha256_file(directory / "template.json")
    if path.exists():
        prior = read_json(path)
        if prior["template_sha256"] == template_sha and prior["draws_sha256"] == common.sha256_file(directory / "draws.jsonl"):
            return prior
    llm = StrictClient(AUTHOR_MODEL, AUTHOR_EFFORT)
    system = SECOND_PROMPT.read_text(encoding="utf-8")
    base = prompt = second_prompt(tpl)
    sets = parameter_sets(tpl, directory)
    calls, result, code = [], None, None
    for attempt in range(2):  # one repair, for execution or format errors only
        response = llm.complete(system, prompt, tag=f"c1-second-{directory.name}-{attempt}")
        calls.append({"attempt": attempt, "cache_key": response.key, "cached": response.cached, "model": response.model_id,
                      "usage": response.usage, "cost_equivalent_usd": response.cost_equivalent_usd})
        code = extract_code(response.text)
        if code is None:
            prompt = base + "\n\nYour previous reply contained no Python code block defining solve(). Reply with one code block."
            continue
        result = compare_programs(box, tpl, code, sets)
        if result["second_errors"] and attempt == 0:
            errors = "; ".join(f"{e['set']}: {e.get('stage')} {e.get('error') or e.get('issues')}" for e in result["second_errors"][:3])
            prompt = (base + f"\n\n### Your previous program\n```python\n{code.strip()}\n```\n\nIt failed to execute or "
                      f"return every output for some valid parameter values: {errors}\nWrite a corrected complete program.")
            continue
        break
    record = {"family": directory.name, "template_sha256": template_sha,
              "draws_sha256": common.sha256_file(directory / "draws.jsonl"), "calls": calls, "program": code,
              "result": result, "passed": bool(result) and not result["mismatches"] and not result["second_errors"]
              and not result["reference_unexpected_errors"] and result["compared"] >= N_DRAWS,
              "value_mismatches_fed_back": False}
    save_json(path, record)
    return record


def endpoint_and_coverage(directory: Path, tpl, box) -> dict:
    checks = []
    for label, values in [(f"endpoint_{l}", p) for l, p in endpoints(tpl["params"])] + \
                         [(f"coverage_{i}", p) for i, p in enumerate(coverage_sets(tpl))]:
        r = evaluate_program(box, tpl, tpl["program"], values)
        checks.append({"set": label, "params": {k: str(v) for k, v in values.items()}, "ok": r["ok"],
                       "declared_invalid": r["declared_invalid"], "issues": r.get("issues"), "error": r.get("error")})
    unexpected = [c for c in checks if not c["ok"] and not c["declared_invalid"]]
    record = {"family": directory.name, "template_sha256": common.sha256_file(directory / "template.json"),
              "checks": checks, "unexpected_failures": len(unexpected),
              "declared_invalid": sum(c["declared_invalid"] for c in checks),
              "coverage_valid": sum(1 for c in checks if c["set"].startswith("coverage_") and c["ok"]),
              "semantic_correctness": "not_established_by_endpoint_execution"}
    save_json(directory / "endpoint_check.json", record)
    return record


def blind_check(directory: Path, box) -> dict:
    path = directory / "blind_check.json"
    draws_sha = common.sha256_file(directory / "draws.jsonl")
    if path.exists() and read_json(path)["draws_sha256"] == draws_sha:
        return read_json(path)
    solver = Solver(StrictClient(AUTHOR_MODEL, CHECKER_EFFORT), box, load_system_prompt(CHECKER_PROMPT), 2,
                    hints="v2", echo=True)
    checks = []
    for item in common.read_jsonl(directory / "draws.jsonl")[:N_SCORED]:
        outcome = solver.solve(item["question"], [], 1, 0)
        texts = outcome["samples"][0]["texts"]
        checks.append({"case_id": item["question"]["case_id"], "verdicts": field_verdicts(item["question"], item["gold"], texts),
                       "outcome": outcome})
    record = {"family": directory.name, "draws_sha256": draws_sha, "checks": checks,
              "all_agree": all(all(c["verdicts"].values()) for c in checks)}
    save_json(path, record)
    return record


def check_one(f: Mapping[str, Any]) -> dict:
    directory = active_dir(f)
    if not (directory / "template.json").exists():
        return {"family": directory.name, "status": "not_authored"}
    tpl = read_json(directory / "template.json")
    box = make_sandbox(load_config("configs/r4.json"))
    try:
        endpoint = endpoint_and_coverage(directory, tpl, box)
        second = second_implementation(f, directory, tpl, box)
        blind = blind_check(directory, box)
    finally:
        box.close()
    gates = {"generation": True, "endpoints": endpoint["unexpected_failures"] == 0,
             "coverage": endpoint["coverage_valid"] >= 1, "second_implementation": second["passed"],
             "blind_solver": blind["all_agree"]}
    verdict = "accepted" if all(gates.values()) else "disputed"
    adjudication = directory / "adjudication.json"
    accepted_by_review = None
    if verdict == "disputed" and adjudication.exists():
        review = read_json(adjudication)
        # Decision (c): only the blind solver disagrees, the second implementation agrees, the wording is
        # unambiguous; valid only for the exact template and draws that were reviewed.
        if review.get("decision") == "accept_reference" \
                and review.get("template_sha256") == common.sha256_file(directory / "template.json") \
                and review.get("draws_sha256") == common.sha256_file(directory / "draws.jsonl") \
                and [k for k, v in gates.items() if not v] == ["blind_solver"]:
            verdict, accepted_by_review = "accepted", review["rationale"]
    quality = {"family": directory.name, "at": now(), "gates": gates, "verdict": verdict,
               "accepted_by_review": accepted_by_review,
               "template_sha256": common.sha256_file(directory / "template.json"),
               "draws_sha256": common.sha256_file(directory / "draws.jsonl")}
    save_json(directory / "quality.json", quality)
    log_decision({"event": "checked", "family": directory.name, "verdict": verdict, "gates": gates})
    return {"family": directory.name, "verdict": verdict, "gates": gates}


def adjudicate(family_id: str, decision: str, rationale: str, slot_descriptions: Mapping[str, str] | None = None) -> None:
    """Record a pre-scoring oracle decision; (b) clarifications keep seeds, parameters and gold."""

    f = next(x for x in manifest()["families"] if x["family_id"] == family_id)
    directory = active_dir(f)
    if (directory / "adjudication.json").exists():
        raise SystemExit("one adjudication round per family")
    archive = directory / "before_adjudication_v1"
    archive.mkdir(exist_ok=True)
    names = [n for n in ("template.json", "draws.jsonl", "endpoint_check.json", "second_impl.json", "blind_check.json",
                         "quality.json") if (directory / n).exists()]
    for name in names:
        (archive / name).write_bytes((directory / name).read_bytes())
    record = {"at": now(), "family": directory.name, "decision": decision, "rationale": rationale,
              "before_candidate_evaluation": True, "original_hashes": {n: common.sha256_file(archive / n) for n in names}}
    if decision == "clarify_wording":
        tpl = read_json(directory / "template.json")
        for slot in tpl["slots"]:
            if slot["slot_id"] in (slot_descriptions or {}):
                slot["description"] = slot_descriptions[slot["slot_id"]]
        box = make_sandbox(load_config("configs/r4.json"))
        try:
            generated = generate(tpl, AUTHOR_ID, N_DRAWS, box, rules=RULES)
        finally:
            box.close()
        old = common.read_jsonl(archive / "draws.jsonl")
        if [(i.seed, i.params, i.gold["final_value"], i.gold["slot_values"]) for i in generated.instances] != \
                [(d["seed"], d["params"], d["gold"]["final_value"], d["gold"]["slot_values"]) for d in old]:
            raise SystemExit("clarification changed seeds, parameters or gold")
        save_json(directory / "template.json", tpl)
        common.write_jsonl(directory / "draws.jsonl", [
            {"seed": i.seed, "params": i.params, "question": i.question, "gold": i.gold, "manifest": i.manifest}
            for i in generated.instances])
        for name in ("second_impl.json", "blind_check.json", "quality.json"):
            (directory / name).unlink(missing_ok=True)
        record["requires_fresh_gates"] = True
    elif decision != "accept_reference":
        raise SystemExit(f"unknown decision {decision}")
    record["template_sha256"] = common.sha256_file(directory / "template.json")
    record["draws_sha256"] = common.sha256_file(directory / "draws.jsonl")
    save_json(directory / "adjudication.json", record)
    log_decision({"event": "adjudicated", "family": directory.name, "decision": decision})
    print(json.dumps(record, indent=1))


# ---------------------------------------------------------------- panels and seal


def panel(spec: str, name: str) -> None:
    chosen = select(spec)
    partitions = {f["partition"] for f in chosen}
    if len(partitions) != 1:
        raise SystemExit("a panel holds one partition")
    partition = partitions.pop()
    out = DATA / partition / "panels"
    if (out / f"{name}.json").exists():
        raise SystemExit(f"panel {name} already frozen")
    questions, gold, families, shortfall = [], [], {}, []
    for f in chosen:
        directory = active_dir(f)
        quality = directory / "quality.json"
        if not quality.exists() or read_json(quality)["verdict"] != "accepted" \
                or read_json(quality)["template_sha256"] != common.sha256_file(directory / "template.json") \
                or read_json(quality)["draws_sha256"] != common.sha256_file(directory / "draws.jsonl"):
            shortfall.append(f["family_id"])
            continue
        for item in common.read_jsonl(directory / "draws.jsonl")[:N_SCORED]:
            case_id = item["question"]["case_id"]
            questions.append({"question": item["question"], "manifest": item["manifest"], "family": directory.name})
            gold.append({"case_id": case_id, "gold": item["gold"]})
            families[case_id] = {"family": directory.name, "family_id": f["family_id"], "domain_id": f["domain_id"],
                                 "difficulty": f["difficulty"], "mechanism_class": f["mechanism_class"],
                                 "pair_id": f["pair_id"]}
    q_sha = common.write_jsonl(out / f"{name}_questions.jsonl", questions)
    g_sha = common.write_jsonl(out / f"{name}_gold.jsonl", gold)
    ids = sorted(families)
    save_json(out / f"{name}.json", {
        "panel_id": f"c1-{partition}-{name}", "kind": "synthetic", "partition": partition, "created": now(),
        "selection": spec, "case_ids": ids, "case_ids_sha256": common.sha256_text("\n".join(ids)), "families": families,
        "shortfall": shortfall,
        "question_files": [{"path": (out / f"{name}_questions.jsonl").relative_to(common.ROOT).as_posix(), "sha256": q_sha}],
        "gold_files": [{"path": (out / f"{name}_gold.jsonl").relative_to(common.ROOT).as_posix(), "sha256": g_sha}]})
    print(json.dumps({"panel": f"{partition}/{name}", "families": len(set(v["family"] for v in families.values())),
                      "cases": len(ids), "shortfall": shortfall}, indent=1))


def seal() -> None:
    target = DATA / "seal.json"
    if target.exists():
        raise SystemExit("confirmation already sealed")
    files = sorted(p for p in (DATA / "confirmation").rglob("*") if p.is_file())
    save_json(target, {"at": now(), "partition": "confirmation", "scored": False,
                       "files": {p.relative_to(common.ROOT).as_posix(): common.sha256_file(p) for p in files}})
    print(f"sealed {len(files)} confirmation files")


def verify_seal() -> None:
    record = read_json(DATA / "seal.json")
    for path, expected in record["files"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"sealed confirmation file changed: {path}")


def status(spec: str | None) -> None:
    rows = []
    for f in select(spec):
        directory = active_dir(f)
        entry = {"family": directory.name, "partition": f["partition"], "wave": f["wave"], "class": f["mechanism_class"],
                 "difficulty": f["difficulty"][:3]}
        log = directory / "author_log.json"
        entry["authored"] = read_json(log)["status"] if log.exists() else "-"
        quality = directory / "quality.json"
        if quality.exists():
            q = read_json(quality)
            entry["verdict"] = q["verdict"]
            entry["failed_gates"] = [k for k, v in q["gates"].items() if not v]
        rows.append(entry)
    for r in rows:
        print(json.dumps(r))
    print(json.dumps(Counter((r["partition"], r.get("verdict", r["authored"])) for r in rows).most_common()))


# ---------------------------------------------------------------- CLI


def run_parallel(worker, jobs, concurrency: int) -> list[dict]:
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(worker, job) for job in jobs]
        try:
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(json.dumps(result), flush=True)
        except UsageLimitError:
            for future in futures:
                future.cancel()
            raise
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["assign", "author", "check", "status", "panel", "seal", "replace"])
    parser.add_argument("--select")
    parser.add_argument("--name")
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args(argv)
    if args.action == "assign":
        assign()
        return 0
    if args.action == "status":
        status(args.select)
        return 0
    if args.action == "panel":
        panel(args.select, args.name)
        return 0
    if args.action == "seal":
        seal()
        return 0
    if not 1 <= args.concurrency <= 3:
        raise SystemExit("concurrency is bounded at 3")
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", f"continuation families {args.action} {args.select}")  # noqa: F841
    chosen = select(args.select)
    if args.action == "author":
        run_parallel(author_one, chosen, args.concurrency)
    elif args.action == "replace":
        for partition in {f["partition"] for f in chosen}:
            existing = len(list((DATA / partition).glob("c1_*_r1")))
            new = sum(1 for f in chosen if f["partition"] == partition and not family_dir(f, "r1").exists())
            if existing + new > 12:
                raise SystemExit(f"{partition}: at most 12 replacements are preregistered")
        for f in chosen:
            log_decision({"event": "quarantined", "family": f["family_id"], "reason": "see preceding decisions"})
        run_parallel(lambda f: author_one(f, "r1"), chosen, args.concurrency)
    else:
        run_parallel(check_one, chosen, args.concurrency)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
