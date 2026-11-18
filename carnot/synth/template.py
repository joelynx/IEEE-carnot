"""Synthetic templates: checking, parameter sampling, instance generation (PLAN.md §4b).

A template is JSON written by the author model:

  {"name": "...", "domain_id": "...", "topic_id": "...", "difficulty": "basic|intermediate|advanced",
   "params": {"V": {"kind": "int", "min": 10000, "max": 90000, "step": 1000},
              "c": {"kind": "decimal", "min": "-6", "max": "6", "step": "0.25"},
              "side": {"kind": "choice", "values": ["buyer", "seller"]}},
   "question_template": "... {V} ... {c} ... {side} ...",
   "answer_spec": {...}, "slots": [{"slot_id": "...", "description": "...", "result_spec": {...}}],
   "program": "def solve():\n    V = P['V']\n    ...\n    return {'final': ..., '<slot_id>': ...}"}

Our trusted code samples parameters (seeded), fills the question text, appends
the attested "Answer format:" sentence, and runs the program in the sandbox
with ``P`` injected.  Gold strings come from the same formatter that
round-trips all released gold.  Every record passes the toolkit's own
validate_question / validate_gold_row, the gold row scores 1/1 with
score_case, and every question must be *novel* under the R1/R2 routing rule.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Mapping

from finreason_task1.contracts import (
    GOLD_SCHEMA_VERSION, IDENTIFIER_PATTERN, QUESTION_SCHEMA_VERSION, validate_gold_row, validate_question,
)
from finreason_task1.scoring import score_case

from .. import common
from ..formatter import build_row, render
from ..routing import NoveltyRouter
from ..sandbox.executor import Sandbox, decode
from .answer_format import with_answer_format

DATASET_VERSION = "carnot-synth-v1"
DIFFICULTIES = ("basic", "intermediate", "advanced")
# House-rule versions (PLAN.md §4b).  v2: train-like style.  v3: advanced-only, harder
# problems (3-4 slots; length up to the longest advanced train question).
RULES = {
    "v2": {"difficulties": DIFFICULTIES, "slots": None, "length": "p90"},
    "v3": {"difficulties": ("advanced",), "slots": (3, 4), "length": "max"},
    "v4": {"difficulties": ("intermediate", "advanced"), "slots": (2, 4), "length": "max"},
}
PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
FORMULA_CHARS = re.compile(r"[=*/^]")
MAX_SLOT_WORDS = 15  # longest slot description in the tuning set (median 4)
_ROUTER: NoveltyRouter | None = None
_LIMITS: dict[str, dict[str, int]] | None = None


class TemplateError(ValueError):
    pass


def router() -> NoveltyRouter:
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = NoveltyRouter()
    return _ROUTER


def body_limits(kind: str = "p90") -> dict[str, int]:
    """Question-body length per difficulty in the tuning set: 90th percentile ("p90") or maximum ("max")."""

    global _LIMITS
    if _LIMITS is None:
        from .. import splits
        d = common.data()
        lengths: dict[str, list[int]] = {}
        for case_id in splits.load()["tuning"]:
            body = d.questions[case_id]["question"].split("\n\nAnswer format:")[0]
            lengths.setdefault(d.manifest[case_id]["difficulty"], []).append(len(body))
        _LIMITS = {"p90": {k: sorted(v)[int(0.9 * len(v))] for k, v in lengths.items()},
                   "max": {k: max(v) for k, v in lengths.items()}}
    return _LIMITS[kind]


def check_template(tpl: Mapping[str, Any], rules: str = "v2") -> None:
    """Static checks; raises TemplateError with a message the author can act on."""

    allowed = RULES[rules]["difficulties"]

    required = {"name", "domain_id", "topic_id", "difficulty", "params", "question_template", "answer_spec", "slots", "program"}
    missing = required - set(tpl)
    if missing:
        raise TemplateError(f"missing keys: {sorted(missing)}")
    if tpl["difficulty"] not in allowed:
        raise TemplateError(f"difficulty must be one of {allowed}")
    if not IDENTIFIER_PATTERN.fullmatch(str(tpl["name"])):
        raise TemplateError("name must be a lowercase snake_case identifier")
    params = tpl["params"]
    if not isinstance(params, dict) or not params:
        raise TemplateError("params must be a non-empty object")
    for name, spec in params.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise TemplateError(f"param name {name!r} must be an identifier")
        kind = spec.get("kind")
        if kind == "int":
            if not all(isinstance(spec.get(k), int) for k in ("min", "max", "step")) or spec["step"] <= 0 or spec["min"] > spec["max"]:
                raise TemplateError(f"param {name}: int needs integer min <= max and step > 0")
        elif kind == "decimal":
            try:
                low, high, step = (Fraction(str(spec[k])) for k in ("min", "max", "step"))
            except (KeyError, ValueError, ZeroDivisionError):
                raise TemplateError(f"param {name}: decimal needs min, max, step as decimal strings") from None
            if step <= 0 or low > high or (high - low) / step != int((high - low) / step):
                raise TemplateError(f"param {name}: (max - min) must be a whole number of steps")
        elif kind == "choice":
            values = spec.get("values")
            if not isinstance(values, list) or len(values) < 2 or not all(isinstance(v, (str, int)) for v in values):
                raise TemplateError(f"param {name}: choice needs >= 2 string or integer values")
        else:
            raise TemplateError(f"param {name}: kind must be int, decimal or choice")
    used = set(PLACEHOLDER.findall(tpl["question_template"]))
    if used - set(params):
        raise TemplateError(f"question_template uses undefined params: {sorted(used - set(params))}")
    if set(params) - used:
        raise TemplateError(f"every param must appear in question_template; unused: {sorted(set(params) - used)}")
    if "Answer format" in tpl["question_template"]:
        raise TemplateError("do not write the 'Answer format:' sentence; it is appended from answer_spec")
    slot_ids = [s.get("slot_id") for s in tpl["slots"]]
    if len(set(slot_ids)) != len(slot_ids) or "final" in slot_ids:
        raise TemplateError("slot_ids must be unique and must not be 'final'")
    if RULES[rules]["slots"]:
        low, high = RULES[rules]["slots"]
        if not low <= len(slot_ids) <= high:
            raise TemplateError(f"write {low} to {high} slots (got {len(slot_ids)})")
    for slot in tpl["slots"]:
        description = str(slot.get("description", ""))
        if FORMULA_CHARS.search(description):
            raise TemplateError(f"slot {slot.get('slot_id')!r}: descriptions are words only, never formulas "
                                "(no = * / ^), as in every train slot description")
        if len(description.split()) > MAX_SLOT_WORDS:
            raise TemplateError(f"slot {slot.get('slot_id')!r}: description has {len(description.split())} words; "
                                f"train descriptions have at most {MAX_SLOT_WORDS} (median 4)")
    if "def solve" not in tpl["program"]:
        raise TemplateError("program must define solve()")


def _display(value: Any, spec: Mapping[str, Any]) -> str:
    if spec["kind"] != "decimal":
        return str(value)
    step_text = str(spec["step"])
    places = len(step_text.split(".")[1]) if "." in step_text else 0
    scaled = value * 10**places
    if scaled.denominator != 1:
        raise TemplateError("decimal param off its step grid")
    sign = "-" if scaled < 0 else ""
    digits = str(abs(scaled.numerator)).rjust(places + 1, "0")
    text = digits if places == 0 else f"{digits[:-places]}.{digits[-places:]}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return sign + text


def sample(params: Mapping[str, Any], rng: random.Random) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name in sorted(params):
        spec = params[name]
        if spec["kind"] == "int":
            values[name] = rng.randrange(spec["min"], spec["max"] + 1, spec["step"])
        elif spec["kind"] == "decimal":
            low, high, step = (Fraction(str(spec[k])) for k in ("min", "max", "step"))
            values[name] = low + step * rng.randint(0, int((high - low) / step))
        else:
            values[name] = rng.choice(spec["values"])
    return values


def _literal(value: Any, spec: Mapping[str, Any]) -> str:
    if spec["kind"] == "decimal":
        return f'Q("{_display(value, spec)}")'
    return repr(value)


def program_source(tpl: Mapping[str, Any], values: Mapping[str, Any]) -> str:
    entries = ", ".join(f"{name!r}: {_literal(values[name], tpl['params'][name])}" for name in sorted(values))
    return f"P = {{{entries}}}\n\n{tpl['program'].strip()}\n"


def question_body(tpl: Mapping[str, Any], values: Mapping[str, Any]) -> str:
    return PLACEHOLDER.sub(lambda m: _display(values[m.group(1)], tpl["params"][m.group(1)]), tpl["question_template"])


def template_id(tpl: Mapping[str, Any], author: str, rules: str = "v2") -> str:
    prefix = f"syn.{author}" if rules == "v2" else f"syn.{author}.{rules}"
    return f"{prefix}.{tpl['domain_id']}.{tpl['topic_id']}.{tpl['name']}.{tpl['difficulty']}.v1"


def case_id(tid: str, seed: int) -> str:
    return "t1_syn" + hashlib.sha256(f"{tid}#{seed}".encode()).hexdigest()[:20]


@dataclass
class Instance:
    seed: int
    params: dict[str, str]
    question: dict[str, Any]
    gold: dict[str, Any]
    manifest: dict[str, Any]


@dataclass
class Generation:
    instances: list[Instance] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def make_instance(tpl: Mapping[str, Any], author: str, seed: int, sandbox: Sandbox, rules: str = "v2") -> Instance:
    tid = template_id(tpl, author, rules)
    values = sample(tpl["params"], random.Random(f"{tid}#{seed}"))
    reply = sandbox.run(program_source(tpl, values))
    shown = {k: _display(v, tpl["params"][k]) for k, v in values.items()}
    if not reply.get("ok"):
        raise TemplateError(f"seed {seed}, params {shown}: program failed at {reply.get('stage')}: {reply.get('error')}")
    outputs = {k: decode(v) for k, v in reply["values"].items()}
    fields = [("final", tpl["answer_spec"])] + [(s["slot_id"], s["result_spec"]) for s in tpl["slots"]]
    texts = {}
    for name, spec in fields:
        if name not in outputs:
            raise TemplateError(f"seed {seed}: solve() did not return {name!r}")
        rendered = render(outputs[name], spec)
        if rendered.text is None:
            raise TemplateError(f"seed {seed}, params {shown}: {name!r} = {outputs[name]!r} cannot be rendered for "
                                f"{spec}: {rendered.issue}")
        texts[name] = rendered.text
    body = question_body(tpl, values)
    kind = RULES[rules]["length"]
    limit = body_limits(kind)[tpl["difficulty"]]
    if len(body) > limit:
        where = "at the 90th percentile" if kind == "p90" else "at their longest"
        raise TemplateError(f"seed {seed}: question text is {len(body)} characters; {tpl['difficulty']} questions in "
                            f"train are at most {limit} {where}; state inputs and conventions concisely")
    cid = case_id(tid, seed)
    question = {
        "schema_version": QUESTION_SCHEMA_VERSION, "dataset_version": DATASET_VERSION, "case_id": cid,
        "question": with_answer_format(question_body(tpl, values), tpl["answer_spec"]),
        "answer_spec": tpl["answer_spec"],
        "trace_spec": {"slots": [{"slot_id": s["slot_id"], "description": s["description"], "position": i,
                                  "result_spec": s["result_spec"]} for i, s in enumerate(tpl["slots"], start=1)]},
    }
    try:
        validate_question(question)
    except Exception as exc:  # noqa: BLE001  (toolkit ContractError)
        raise TemplateError(f"question rejected by the toolkit validator: {exc}") from None
    gold = {"schema_version": GOLD_SCHEMA_VERSION, "dataset_version": DATASET_VERSION, "case_id": cid,
            "final_value": texts["final"], "slot_values": {s["slot_id"]: texts[s["slot_id"]] for s in tpl["slots"]}}
    try:
        validate_gold_row(gold, question)
    except Exception as exc:  # noqa: BLE001
        raise TemplateError(f"gold rejected by the toolkit validator: {exc}") from None
    row, dropped = build_row(question, gold["final_value"], gold["slot_values"])
    result = score_case(question, gold, row)
    if dropped or result.fac != 1 or result.matched_slots != result.total_slots:
        raise TemplateError(f"seed {seed}: gold does not score 1/1 against itself (dropped {dropped})")
    if not router().is_novel(question):
        raise TemplateError("the question is not novel: its text skeleton or slot signature already occurs in train; "
                            "write a genuinely different calculation with different slots")
    manifest = {"case_id": cid, "dataset_version": DATASET_VERSION, "domain_id": tpl["domain_id"], "topic_id": tpl["topic_id"],
                "difficulty": tpl["difficulty"], "template_id": tid, "structure_stratum": "synthetic", "author": author,
                "rules": rules,
                "question_sha256": common.sha256_text(question["question"])}
    return Instance(seed, shown, question, gold, manifest)


def generate(tpl: Mapping[str, Any], author: str, n: int, sandbox: Sandbox, max_seeds: int | None = None,
             seed_start: int = 0, rules: str = "v2") -> Generation:
    """n valid instances from seeds seed_start, seed_start + 1, ...; a seed may fail only by raising
    ValueError inside solve().  Evaluation instances use seed_start 0; probes use a disjoint range."""

    check_template(tpl, rules)
    out = Generation()
    for seed in range(seed_start, seed_start + (max_seeds or 4 * n)):
        if len(out.instances) == n:
            break
        try:
            out.instances.append(make_instance(tpl, author, seed, sandbox, rules))
        except TemplateError as exc:
            message = str(exc)
            if "ValueError" in message:  # the template's own validity guard: resample
                out.errors.append(message)
                continue
            raise
    if len(out.instances) < n:
        raise TemplateError(f"only {len(out.instances)} of {n} instances were valid; last errors: {out.errors[-3:]}")
    finals = {i.gold["final_value"] for i in out.instances}
    if len(finals) < 2:
        raise TemplateError(f"all {n} instances have the same final answer {finals}; parameters must change the outcome")
    return out
