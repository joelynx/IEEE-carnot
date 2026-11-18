"""R0 solver: program-of-thought, N samples, retries, spec-driven rendering (PLAN.md §3.2-3.7).

Per question: build the prompt (system rules + exemplars + question + output
table) -> claude -p -> extract the code block -> sandbox -> render every field
from its result_spec -> retry with the error message if anything is missing
or unrenderable -> vote across samples on rendered strings -> validator gate.
R0 fallback: any field still invalid is omitted (final -> null); never edited.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .formatter import Rendered, build_row, render
from .llm_client import ClaudeCLI
from .sandbox.executor import Sandbox, decode

PERCENT_UNITS = {"percent", "nominal_percent", "real_percent"}
PLAIN_UNITS = {"ratio", "multiple", "dimensionless", "ratio_per_year"}
# Unit-hint versions.  v1: original.  v2: "dimensionless" no longer claims a fraction scale;
# in train gold it holds counts, multipliers, pip differences and squares of the question's
# own quantities (e.g. a variance 225 from a 15-percent deviation), never rescaled percentages.
PLAIN_UNITS_BY_HINTS = {"v1": PLAIN_UNITS, "v2": PLAIN_UNITS - {"dimensionless"}}
DIMENSIONLESS_V2 = ", a pure number with no unit; keep the scale of the question's own quantities (do not rescale percentages to fractions unless the description says so)"
CODE_BLOCK = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.S)
ANSWER_FORMAT = re.compile(r"\n\nAnswer format: .*\Z", re.S)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _norm_sentence(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(".")


def echoed_slots(question: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Slots whose description is repeated verbatim as a sentence of the question text.

    In train such a sentence (e.g. "Report taxable income.") always asks for that slot, while
    the final answer is a different quantity (the tax); models tend to answer the sentence.
    """

    body = ANSWER_FORMAT.sub("", question["question"]).strip()
    sentences = {_norm_sentence(x) for x in SENTENCE_SPLIT.split(body) if x.strip()}
    return [slot for slot in question["trace_spec"]["slots"] if _norm_sentence(slot["description"]) in sentences]


def describe_spec(spec: Mapping[str, Any], hints: str = "v1") -> str:
    if spec["type"] == "enum":
        allowed = ", ".join(f'"{v}"' for v in spec["allowed_values"])
        extra = " (or True/False)" if set(spec["allowed_values"]) == {"true", "false"} else ""
        return f"one of {allowed}{extra}"
    unit = spec["unit"]
    note = ""
    if unit in PERCENT_UNITS:
        note = ", percentage points (5.25 means 5.25 %)"
    elif unit in PLAIN_UNITS_BY_HINTS[hints]:
        note = ", a plain number (0.0525, not 5.25)"
    elif hints == "v2" and unit == "dimensionless":
        note = DIMENSIONLESS_V2
    if spec["rounding"]["mode"] == "exact":
        return f"number in {unit}{note}; checked as an exact value (return it unrounded)"
    places = spec["rounding"]["decimal_places"]
    return f"number in {unit}{note}; rounded half-up to {places} decimal places by the harness (return it unrounded)"


def output_table(question: Mapping[str, Any], hints: str = "v1", echo: bool = False) -> str:
    echoes = {slot["slot_id"]: slot["description"].strip() for slot in echoed_slots(question)} if echo else {}
    final_note = "".join(f' (the final answer is not the quantity in the sentence "{desc}"; that sentence belongs to slot "{sid}")'
                         for sid, desc in echoes.items())
    lines = ['Required outputs (keys of the dict returned by solve()):',
             f'- "final": the final answer — {describe_spec(question["answer_spec"], hints)}{final_note}']
    for slot in question["trace_spec"]["slots"]:
        note = (f' (the question\'s sentence "{echoes[slot["slot_id"]]}" is the instruction for this slot, '
                'not the definition of the final answer)') if slot["slot_id"] in echoes else ""
        lines.append(f'- "{slot["slot_id"]}": {slot["description"].strip()} — {describe_spec(slot["result_spec"], hints)}{note}')
    return "\n".join(lines)


def build_user_prompt(question: Mapping[str, Any], exemplars: Sequence[Mapping[str, Any]], hints: str = "v1",
                      conventions: str | None = None, echo: bool = False) -> str:
    """With the defaults this is the original prompt, byte for byte (cache keys unchanged)."""

    parts = []
    for index, example in enumerate(exemplars, start=1):
        parts.append(
            f"### Example {index}\n{example['question']['question']}\n\n{output_table(example['question'], hints)}\n\n"
            f"### Example {index} program\n```python\n{example['program'].strip()}\n```"
        )
    if conventions:
        parts.append(conventions)
    parts.append(f"### Question\n{question['question']}\n\n{output_table(question, hints, echo)}")
    return "\n\n".join(parts)


def retry_suffix(code: str | None, feedback: str) -> str:
    previous = f"\n\n### Your previous program\n```python\n{code.strip()}\n```" if code else ""
    return f"{previous}\n\nIt was rejected: {feedback}\nWrite a corrected complete program (one code block)."


def extract_code(text: str) -> str | None:
    blocks = CODE_BLOCK.findall(text)
    if blocks:
        with_solve = [b for b in blocks if "def solve" in b]
        return (with_solve or blocks)[-1]
    return text if "def solve" in text else None


@dataclass
class SampleResult:
    texts: dict[str, str]          # field -> rendered string (valid fields only)
    issues: dict[str, str]         # field -> why it could not be rendered
    attempts: list[dict[str, Any]]


class Solver:
    def __init__(self, llm: ClaudeCLI, sandbox: Sandbox, system_prompt: str, max_retries: int = 2,
                 hints: str = "v1", conventions=None, echo: bool = False):
        self.llm = llm
        self.sandbox = sandbox
        self.system = system_prompt
        self.max_retries = max_retries
        self.hints = hints
        self.conventions = conventions  # SlotConventions or None
        self.echo = echo  # notes for slot descriptions repeated in the question text

    def _render_all(self, question, values) -> tuple[dict[str, str], dict[str, str], list[str]]:
        fields = [("final", question["answer_spec"])] + [
            (slot["slot_id"], slot["result_spec"]) for slot in question["trace_spec"]["slots"]
        ]
        texts, issues, flags = {}, {}, []
        for name, spec in fields:
            if name not in values:
                issues[name] = "missing key"
                continue
            rendered: Rendered = render(values[name], spec)
            flags += [f"{name}:{flag}" for flag in rendered.flags]
            if rendered.text is None:
                issues[name] = rendered.issue or "unrenderable"
            else:
                texts[name] = rendered.text
        return texts, issues, flags

    def prompt(self, question: Mapping[str, Any], exemplars, exclude_template: str | None = None) -> str:
        block = self.conventions.block(question, exclude_template) if self.conventions else None
        return build_user_prompt(question, exemplars, self.hints, block, self.echo)

    def solve_sample(self, question: Mapping[str, Any], exemplars, sample: int, exclude_template: str | None = None) -> SampleResult:
        base = self.prompt(question, exemplars, exclude_template)
        attempts: list[dict[str, Any]] = []
        best: tuple[int, dict, dict] = (-1, {}, {})
        code: str | None = None
        feedback: str | None = None
        for attempt in range(self.max_retries + 1):
            user = base if feedback is None else base + retry_suffix(code, feedback)
            response = self.llm.complete(self.system, user, sample=sample, tag=f"attempt{attempt}")
            record = {"attempt": attempt, "cache_key": response.key, "cached": response.cached,
                      "model_id": response.model_id, "usage": response.usage,
                      "cost_equivalent_usd": response.cost_equivalent_usd, "meta": response.meta}
            attempts.append(record)
            code = extract_code(response.text)
            record["code"] = code
            if code is None:
                record["raw_text"] = response.text[:2000]
                feedback = "no Python code block defining solve() was found."
                continue
            reply = self.sandbox.run(code)
            record["sandbox"] = {k: reply.get(k) for k in ("ok", "stage", "error", "elapsed_ms")}
            if not reply.get("ok"):
                feedback = f"the program failed at the {reply.get('stage')} stage: {reply.get('error')}"
                continue
            values = {k: decode(v) for k, v in reply["values"].items()}
            texts, issues, flags = self._render_all(question, values)
            record.update(rendered=texts, issues=issues, flags=flags)
            if len(texts) > best[0]:
                best = (len(texts), texts, issues)
            if not issues:
                break
            feedback = "; ".join(f'output "{k}": {v}' for k, v in issues.items())
        _, texts, issues = best
        if best[0] < 0:
            fields = ["final"] + [s["slot_id"] for s in question["trace_spec"]["slots"]]
            issues = {name: "no successful attempt" for name in fields}
        return SampleResult(texts=texts, issues=issues, attempts=attempts)

    def solve(self, question: Mapping[str, Any], exemplars, n_samples: int = 1, sample_offset: int = 0,
              exclude_template: str | None = None) -> dict[str, Any]:
        """sample_offset > 0 draws fresh samples (new cache keys) for run-to-run noise estimates.
        exclude_template keeps slot-convention examples out of the question's own template."""

        samples = [self.solve_sample(question, exemplars, sample, exclude_template)
                   for sample in range(sample_offset, sample_offset + n_samples)]
        fields = ["final"] + [slot["slot_id"] for slot in question["trace_spec"]["slots"]]
        chosen: dict[str, str | None] = {}
        votes: dict[str, dict[str, int]] = {}
        for name in fields:
            counts = Counter(s.texts[name] for s in samples if name in s.texts)
            votes[name] = dict(counts)
            if not counts:
                chosen[name] = None
                continue
            top = max(counts.values())
            leaders = [text for text, count in counts.items() if count == top]
            if len(leaders) == 1:
                chosen[name] = leaders[0]
            else:  # tie: the leader held by the sample agreeing most with per-field plurality, then lowest index
                def agreement(sample: SampleResult) -> int:
                    return sum(
                        1 for f in fields
                        if f in sample.texts and Counter(x.texts.get(f) for x in samples).most_common(1)[0][0] == sample.texts[f]
                    )
                ranked = sorted(
                    (i for i, s in enumerate(samples) if s.texts.get(name) in leaders),
                    key=lambda i: (-agreement(samples[i]), i),
                )
                chosen[name] = samples[ranked[0]].texts[name]
        row, dropped = build_row(question, chosen["final"], {k: v for k, v in chosen.items() if k != "final"})
        return {
            "row": row,
            "dropped_by_gate": dropped,
            "votes": votes,
            "samples": [{"texts": s.texts, "issues": s.issues, "attempts": s.attempts} for s in samples],
        }


def load_system_prompt(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
