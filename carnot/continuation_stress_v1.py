"""Development-only stress panel (PLAN.md section 7.4): paired variants grouped with their source.

  python -m carnot.continuation_stress_v1 prepare-bond          # hand-written pilot family_09 variants (no model)
  python -m carnot.continuation_stress_v1 author-variants       # Fable variants of six fixed wave-1 families
  python -m carnot.continuation_stress_v1 check                 # the same oracle gates as new families
  python -m carnot.continuation_stress_v1 panel --name stress1

Variants sample parameters with their source template's identity, so a seed gives every member
of a group the same inputs; paraphrase and distractor variants keep the source program.
Descendants stay grouped with their source and never count as independent units.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Mapping

from . import common
from .config import load_config, make_sandbox
from .continuation_families_v1 import (AUTHOR_EFFORT, AUTHOR_ID, AUTHOR_MODEL, DATA, PROMPTS, RULES, blind_check,
                                       compare_programs, coverage_sets, endpoint_and_coverage, family_dir, log_decision,
                                       manifest, now, run_parallel, second_implementation)
from .continuation_state_v1 import PRIOR
from .formatter import build_row, render
from .improvement_validation_v1 import StrictClient, read_json, save_json
from .sandbox.executor import decode
from .synth.answer_format import with_answer_format
from .synth.author import parse
from .synth.template import (DATASET_VERSION, TemplateError, _display, body_limits, case_id, check_template,
                             question_body, router, sample, template_id)
from finreason_task1.contracts import GOLD_SCHEMA_VERSION, QUESTION_SCHEMA_VERSION, validate_gold_row, validate_question
from finreason_task1.scoring import score_case

STRESS = DATA / "stress"
VARIANT_PROMPT = PROMPTS / "stress_variant_v1.txt"
STRESS_AUTHOR = "fable_c1s"
VARIANT_TYPES = ("paraphrase", "minimal_pair", "distractor")
SUFFIX = {"paraphrase": "para", "minimal_pair": "pair", "distractor": "dist"}
N_DRAWS, N_SCORED = 12, 4
BOND_SOURCE = PRIOR / "pilot" / "family_09" / "template.json"
BOND_SEEDS = range(100, 160)
BOND_OLD = ("The year-1 coupon rate is {C1_PCT} percent; from year 2 onward the rate changes by {STEP_BP} basis "
            "points (negative means a cut).")
BOND_TEXT = {
    "orig": BOND_OLD,
    "once": ("The year-1 coupon rate is {C1_PCT} percent; the year-2 and year-3 rates both equal the year-1 rate plus "
             "{STEP_BP} basis points, a single change (negative means a cut)."),
    "recur": ("The year-1 coupon rate is {C1_PCT} percent; the rate changes by {STEP_BP} basis points at the start of "
              "year 2 and by a further {STEP_BP} basis points at the start of year 3 (negative means a cut)."),
    "para": ("The coupon rate is {C1_PCT} percent in year 1, and beginning in year 2 it moves by {STEP_BP} basis "
             "points (a negative value is a cut)."),
}
BOND_COVERAGE = [
    {"FACE": 1000, "A1_PCT": 20, "A2_PCT": 20, "C1_PCT": "3.0", "STEP_BP": -100, "Y_PCT": "8.0", "CALL_PCT": "104.0", "DAYS": 30},
    {"FACE": 5000, "A1_PCT": 40, "A2_PCT": 40, "C1_PCT": "7.0", "STEP_BP": 150, "Y_PCT": "2.0", "CALL_PCT": "100.0", "DAYS": 330},
    {"FACE": 3000, "A1_PCT": 30, "A2_PCT": 25, "C1_PCT": "5.0", "STEP_BP": 0, "Y_PCT": "5.0", "CALL_PCT": "102.0", "DAYS": 180},
]
RECUR_OLD = ("    c2 = c1 + Fraction(P[\"STEP_BP\"], 10000)\n", "    cf3 = c2 * P2 + P2\n",
             "    if c2 <= 0:\n        raise ValueError(\"coupon rate from year 2 must be positive\")\n")
RECUR_NEW = ("    c2 = c1 + Fraction(P[\"STEP_BP\"], 10000)\n    c3 = c2 + Fraction(P[\"STEP_BP\"], 10000)\n",
             "    cf3 = c3 * P2 + P2\n",
             "    if c2 <= 0 or c3 <= 0:\n        raise ValueError(\"coupon rates in years 2 and 3 must be positive\")\n")
STRESS_SOURCE_RULE = "lowest design index among wave-1 development families, one per mechanism class"


# ---------------------------------------------------------------- instances paired by seed


def variant_instance(tpl: Mapping[str, Any], sampling_tid: str, seed: int, box) -> dict:
    """carnot.synth.template.make_instance with parameter values drawn under the source's identity."""

    tid = template_id(tpl, STRESS_AUTHOR, RULES)
    values = sample(tpl["params"], random.Random(f"{sampling_tid}#{seed}"))
    from .synth.template import program_source
    reply = box.run(program_source(tpl, values))
    shown = {k: _display(v, tpl["params"][k]) for k, v in values.items()}
    if not reply.get("ok"):
        raise TemplateError(f"seed {seed}, params {shown}: program failed at {reply.get('stage')}: {reply.get('error')}")
    outputs = {k: decode(v) for k, v in reply["values"].items()}
    texts = {}
    for name, spec in [("final", tpl["answer_spec"])] + [(s["slot_id"], s["result_spec"]) for s in tpl["slots"]]:
        rendered = render(outputs[name], spec) if name in outputs else None
        if rendered is None or rendered.text is None:
            raise TemplateError(f"seed {seed}: {name!r} cannot be rendered")
        texts[name] = rendered.text
    body = question_body(tpl, values)
    limit = body_limits("max")[tpl["difficulty"]]
    if len(body) > limit:
        raise TemplateError(f"seed {seed}: question text is {len(body)} characters; the limit is {limit}")
    cid = case_id(tid, seed)
    question = {"schema_version": QUESTION_SCHEMA_VERSION, "dataset_version": DATASET_VERSION, "case_id": cid,
                "question": with_answer_format(body, tpl["answer_spec"]), "answer_spec": tpl["answer_spec"],
                "trace_spec": {"slots": [{"slot_id": s["slot_id"], "description": s["description"], "position": i,
                                          "result_spec": s["result_spec"]} for i, s in enumerate(tpl["slots"], start=1)]}}
    validate_question(question)
    gold = {"schema_version": GOLD_SCHEMA_VERSION, "dataset_version": DATASET_VERSION, "case_id": cid,
            "final_value": texts["final"], "slot_values": {s["slot_id"]: texts[s["slot_id"]] for s in tpl["slots"]}}
    validate_gold_row(gold, question)
    row, dropped = build_row(question, gold["final_value"], gold["slot_values"])
    result = score_case(question, gold, row)
    if dropped or result.fac != 1 or result.matched_slots != result.total_slots:
        raise TemplateError(f"seed {seed}: gold does not score 1/1 against itself")
    if not router().is_novel(question):
        raise TemplateError("variant question is not novel under the routing rule")
    manifest_row = {"case_id": cid, "dataset_version": DATASET_VERSION, "domain_id": tpl["domain_id"],
                    "topic_id": tpl["topic_id"], "difficulty": tpl["difficulty"], "template_id": tid,
                    "structure_stratum": "synthetic_stress", "author": STRESS_AUTHOR, "rules": RULES,
                    "question_sha256": common.sha256_text(question["question"])}
    return {"seed": seed, "params": shown, "question": question, "gold": gold, "manifest": manifest_row}


def variant_draws(tpl, sampling_tid, seeds, box) -> list[dict]:
    check_template(tpl, RULES)
    out, too_long = [], []
    for seed in seeds:
        if len(out) == N_DRAWS:
            break
        try:
            out.append(variant_instance(tpl, sampling_tid, seed, box))
        except TemplateError as exc:
            # A validity guard or a draw whose numbers push the text over the length rule is skipped;
            # seeds are aligned across the variants of a group afterwards.
            if "question text is" in str(exc):
                too_long.append(str(exc))
                continue
            if "ValueError" in str(exc):
                continue
            raise
    if len(out) < N_DRAWS:
        reason = f"; {len(too_long)} draws were too long, e.g. {too_long[0]}" if too_long else ""
        raise TemplateError(f"only {len(out)} valid draws{reason}")
    return out


def write_variant(directory: Path, tpl, sampling_tid: str, draws: list[dict], group: str, kind: str, extra=None):
    save_json(directory / "template.json", tpl)
    common.write_jsonl(directory / "draws.jsonl", draws)
    save_json(directory / "sampling.json", {"sampling_template_id": sampling_tid, "group": group, "variant": kind,
                                            **(extra or {})})


# ---------------------------------------------------------------- bond variants (hand-written)


def prepare_bond() -> None:
    source = read_json(BOND_SOURCE)
    if BOND_OLD not in source["question_template"]:
        raise SystemExit("bond source wording changed")
    sampling_tid = template_id(source, "fable_r5", "v4")
    if any((STRESS / f"bond_{kind}" / "template.json").exists() for kind in BOND_TEXT):
        raise SystemExit("bond variants already prepared")
    box = make_sandbox(load_config("configs/r4.json"))
    templates, draws = {}, {}
    try:
        for kind, sentence in BOND_TEXT.items():
            tpl = dict(source, name=f"{source['name']}_{kind}", coverage_params=BOND_COVERAGE,
                       question_template=source["question_template"].replace(BOND_OLD, sentence))
            if kind == "recur":
                program = tpl["program"]
                for old, new in zip(RECUR_OLD, RECUR_NEW):
                    if old not in program:
                        raise SystemExit("bond program changed")
                    program = program.replace(old, new)
                tpl["program"] = program
            templates[kind], draws[kind] = tpl, variant_draws(tpl, sampling_tid, BOND_SEEDS, box)
    finally:
        box.close()
    # Score the same four seeds in every variant: the first seeds valid for all of them.
    common_seeds = [s for s in BOND_SEEDS if all(s in {d["seed"] for d in draws[k]} for k in draws)][:N_SCORED]
    if len(common_seeds) < N_SCORED:
        raise SystemExit("bond variants share fewer than four valid seeds")
    for kind, tpl in templates.items():
        ordered = sorted(draws[kind], key=lambda d: (d["seed"] not in common_seeds, d["seed"]))
        directory = STRESS / f"bond_{kind}"
        write_variant(directory, tpl, sampling_tid, ordered, "bond_family_09", kind,
                      {"source": BOND_SOURCE.relative_to(common.ROOT).as_posix(), "hand_written": True,
                       "scored_seeds": common_seeds})
        log_decision({"event": "stress_variant_prepared", "family": directory.name, "hand_written": True})
        print(f"prepared {directory.name}: scored seeds {common_seeds}; finals "
              f"{[d['gold']['final_value'] for d in ordered[:N_SCORED]]}")


# ---------------------------------------------------------------- Fable variants of wave-1 families


def stress_sources() -> list[dict]:
    chosen = {}
    for f in sorted(manifest()["families"], key=lambda f: f["design_index"]):
        if f["partition"] == "development" and f["wave"] == 1 and f["mechanism_class"] not in chosen:
            chosen[f["mechanism_class"]] = f
    return [chosen[c] for c in sorted(chosen, key=lambda c: chosen[c]["design_index"])]


def author_variant(job) -> dict:
    f, kind = job
    source_dir = family_dir(f)
    directory = STRESS / f"{f['family_id']}_{SUFFIX[kind]}"
    if (directory / "template.json").exists():
        return {"variant": directory.name, "status": "already_authored"}
    quality = source_dir / "quality.json"
    if not quality.exists() or read_json(quality)["verdict"] != "accepted":
        return {"variant": directory.name, "status": "source_not_accepted"}
    source = read_json(source_dir / "template.json")
    sampling_tid = template_id(source, AUTHOR_ID, RULES)
    seeds = [d["seed"] for d in common.read_jsonl(source_dir / "draws.jsonl")]
    scored = seeds[:N_SCORED]
    llm = StrictClient(AUTHOR_MODEL, AUTHOR_EFFORT)
    box = make_sandbox(load_config("configs/r4.json"))
    system = VARIANT_PROMPT.read_text(encoding="utf-8")
    base = prompt = json.dumps({"variant_type": kind, "template": {k: source[k] for k in
                               ("question_template", "params", "answer_spec", "slots", "program")}}, ensure_ascii=False, indent=1)
    base = prompt = base + ("\nCharacter limit for the question text after substituting values: "
                            f"{body_limits('max')[source['difficulty']]}\n")
    attempts = []
    try:
        for attempt in range(3):
            response = llm.complete(system, prompt, tag=f"c1-stress-{directory.name}-{attempt}")
            attempts.append({"attempt": attempt, "cache_key": response.key, "cached": response.cached,
                             "model": response.model_id, "usage": response.usage,
                             "cost_equivalent_usd": response.cost_equivalent_usd})
            try:
                draft = parse(response.text)
                # Toolkit identifiers allow 64 characters; trim the source name so the suffix always fits.
                tpl = dict(source, name=f"{source['name'][:59].rstrip('_')}_{SUFFIX[kind]}",
                           question_template=draft["question_template"])
                if kind == "minimal_pair":
                    if not isinstance(draft.get("program"), str) or draft["program"].strip() == source["program"].strip():
                        raise TemplateError("a minimal pair needs a changed reference program")
                    tpl["program"] = draft["program"]
                elif tpl["question_template"].strip() == source["question_template"].strip():
                    raise TemplateError("the question text is unchanged")
                coverage_sets(tpl)
                ordered = scored + [s for s in seeds if s not in scored] + [s for s in range(48) if s not in seeds]
                draws = variant_draws(tpl, sampling_tid, ordered, box)
                if kind == "minimal_pair":
                    src = {d["seed"]: d["gold"]["final_value"] for d in common.read_jsonl(source_dir / "draws.jsonl")}
                    changed = sum(1 for d in draws[:N_SCORED] if d["seed"] in src and src[d["seed"]] != d["gold"]["final_value"])
                    if changed < 2:
                        raise TemplateError("the changed rule must change the final answer for most typical draws")
                elif [d["seed"] for d in draws[:N_SCORED]] != scored:
                    raise TemplateError("an equivalent variant must stay valid on the source's scored draws")
            except (TemplateError, KeyError, TypeError) as exc:
                attempts[-1]["error"] = str(exc)[:1000]
                prompt = base + "\nPrevious draft:\n" + response.text + "\nValidation error:\n" + str(exc) + \
                    "\nReturn a corrected complete JSON object."
                continue
            write_variant(directory, tpl, sampling_tid, draws, f["family_id"], kind,
                          {"change": draft.get("change"), "source_template_sha256": common.sha256_file(source_dir / "template.json")})
            save_json(directory / "author_log.json", {"attempts": attempts, "status": "generated"})
            log_decision({"event": "stress_variant_authored", "family": directory.name, "attempts": len(attempts)})
            return {"variant": directory.name, "status": "generated", "attempts": len(attempts)}
        save_json(directory / "author_log.json", {"attempts": attempts, "status": "failed"})
        return {"variant": directory.name, "status": "failed"}
    finally:
        box.close()


# ---------------------------------------------------------------- checks and panel


def check_variant(directory: Path) -> dict:
    tpl = read_json(directory / "template.json")
    box = make_sandbox(load_config("configs/r4.json"))
    try:
        endpoint = endpoint_and_coverage(directory, tpl, box)
        second = second_implementation({"family_id": directory.name}, directory, tpl, box)
        blind = blind_check(directory, box)
    finally:
        box.close()
    gates = {"endpoints": endpoint["unexpected_failures"] == 0, "coverage": endpoint["coverage_valid"] >= 1,
             "second_implementation": second["passed"], "blind_solver": blind["all_agree"]}
    verdict = "accepted" if all(gates.values()) else "disputed"
    review = read_json(directory / "adjudication.json") if (directory / "adjudication.json").exists() else None
    if verdict == "disputed" and review and review.get("decision") == "accept_reference" \
            and review.get("template_sha256") == common.sha256_file(directory / "template.json") \
            and review.get("draws_sha256") == common.sha256_file(directory / "draws.jsonl") \
            and [k for k, v in gates.items() if not v] == ["blind_solver"]:
        verdict = "accepted"
    save_json(directory / "quality.json", {"family": directory.name, "at": now(), "gates": gates, "verdict": verdict,
                                           "accepted_by_review": review["rationale"] if review and verdict == "accepted"
                                           and not all(gates.values()) else None,
                                           "template_sha256": common.sha256_file(directory / "template.json"),
                                           "draws_sha256": common.sha256_file(directory / "draws.jsonl")})
    log_decision({"event": "stress_checked", "family": directory.name, "verdict": verdict, "gates": gates})
    return {"variant": directory.name, "verdict": verdict, "gates": gates}


def panel(name: str) -> None:
    out = STRESS / "panels"
    if (out / f"{name}.json").exists():
        raise SystemExit("stress panel already frozen")
    questions, gold, families, skipped = [], [], {}, []
    for directory in sorted(p for p in STRESS.iterdir() if (p / "template.json").exists()):
        quality = directory / "quality.json"
        if not quality.exists() or read_json(quality)["verdict"] != "accepted":
            skipped.append(directory.name)
            continue
        meta = read_json(directory / "sampling.json")
        for item in common.read_jsonl(directory / "draws.jsonl")[:N_SCORED]:
            cid = item["question"]["case_id"]
            questions.append({"question": item["question"], "manifest": item["manifest"], "family": directory.name})
            gold.append({"case_id": cid, "gold": item["gold"]})
            families[cid] = {"family": directory.name, "group": meta["group"], "variant": meta["variant"], "seed": item["seed"]}
    q_sha = common.write_jsonl(out / f"{name}_questions.jsonl", questions)
    g_sha = common.write_jsonl(out / f"{name}_gold.jsonl", gold)
    ids = sorted(families)
    save_json(out / f"{name}.json", {
        "panel_id": f"c1-stress-{name}", "kind": "synthetic", "partition": "stress", "created": now(),
        "source_rule": STRESS_SOURCE_RULE, "case_ids": ids, "case_ids_sha256": common.sha256_text("\n".join(ids)),
        "families": families, "skipped": skipped,
        "question_files": [{"path": (out / f"{name}_questions.jsonl").relative_to(common.ROOT).as_posix(), "sha256": q_sha}],
        "gold_files": [{"path": (out / f"{name}_gold.jsonl").relative_to(common.ROOT).as_posix(), "sha256": g_sha}]})
    print(json.dumps({"cases": len(ids), "variants": len({v['family'] for v in families.values()}), "skipped": skipped}))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["prepare-bond", "author-variants", "check", "panel", "sources"])
    parser.add_argument("--name")
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args(argv)
    if args.action == "sources":
        print(json.dumps([{k: f[k] for k in ("family_id", "mechanism_class", "domain_id", "topic_id")} for f in stress_sources()], indent=1))
        return 0
    if args.action == "panel":
        panel(args.name)
        return 0
    if args.action == "prepare-bond":  # sandbox only, no model calls: no campaign lock needed
        prepare_bond()
        return 0
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", f"continuation stress {args.action}")  # noqa: F841
    if args.action == "author-variants":
        jobs = [(f, kind) for f in stress_sources() for kind in VARIANT_TYPES]
        run_parallel(author_variant, jobs, args.concurrency)
    else:
        dirs = sorted(p for p in STRESS.iterdir() if (p / "template.json").exists() and not (p / "quality.json").exists())
        run_parallel(check_variant, dirs, args.concurrency)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
