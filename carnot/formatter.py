"""Spec-driven rendering of computed values, plus the toolkit validator gate.

Rendering rules come from the published ``result_spec`` and from the gold
conventions observed in all 3,190 train/dev rows (PLAN.md §2.4, §3.6):

* exact     -> minimal finite decimal when the denominator is 2^a*5^b, else
               irreducible ``n/d``; never a float.
* half_up p -> exact value quantised with ROUND_HALF_UP to p places, padded.
* enum      -> a case-sensitive member of ``allowed_values``.

A field that cannot be rendered validly is dropped (slot omitted, final null);
it is never emitted in a form that would make the whole file invalid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from typing import Any, Mapping

from . import common  # noqa: F401  (puts the toolkit on sys.path)
from finreason_task1.contracts import PREDICTION_SCHEMA_VERSION, validate_prediction_record

# A Decimal with at least this many significant digits came from a
# high-precision irrational helper and is treated as inexact.
INEXACT_DECIMAL_DIGITS = 50


@dataclass
class Rendered:
    text: str | None
    issue: str | None = None
    flags: list[str] = field(default_factory=list)


def fraction_to_exact_text(value: Fraction) -> str:
    """Canonical exact rendering (same rule as the toolkit's B1 baseline)."""

    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        return f"{value.numerator}/{value.denominator}"
    places = max(twos, fives)
    scaled = abs(value.numerator) * 2 ** (places - twos) * 5 ** (places - fives)
    whole, fractional = divmod(scaled, 10**places)
    sign = "-" if value < 0 else ""
    if places == 0 or fractional == 0:
        return f"{sign}{whole}"
    return f"{sign}{whole}.{f'{fractional:0{places}d}'.rstrip('0')}"


def _to_decimal(value: Fraction | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    with localcontext() as context:
        context.prec = 256
        return Decimal(value.numerator) / Decimal(value.denominator)


def round_half_up_text(value: Fraction | Decimal, places: int) -> str:
    with localcontext() as context:
        context.prec = 256
        quantised = _to_decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    if quantised.is_zero():
        quantised = abs(quantised)
    return format(quantised, "f")


def _significant_digits(value: Decimal) -> int:
    digits = value.as_tuple().digits
    stripped = "".join(map(str, digits)).lstrip("0")
    return len(stripped)


def coerce_number(value: Any) -> tuple[Fraction | Decimal | None, list[str], str | None]:
    """Map a sandbox value to Fraction (exact) or Decimal (inexact)."""

    flags: list[str] = []
    if isinstance(value, bool):
        return None, flags, "boolean given for a numeric field"
    if isinstance(value, int):
        return Fraction(value), flags, None
    if isinstance(value, Fraction):
        return value, flags, None
    if isinstance(value, Decimal):
        if not value.is_finite():
            return None, flags, "non-finite value"
        if _significant_digits(value) < INEXACT_DECIMAL_DIGITS:
            flags.append("short_decimal_as_exact")
            return Fraction(value), flags, None
        flags.append("inexact")
        return value, flags, None
    if isinstance(value, float):
        flags.append("float")
        return Decimal(repr(value)), flags, None
    return None, flags, f"unsupported numeric type {type(value).__name__}"


def render(value: Any, spec: Mapping[str, Any]) -> Rendered:
    if spec["type"] == "enum":
        allowed = list(spec["allowed_values"])
        if isinstance(value, bool):
            if set(allowed) == {"true", "false"}:
                return Rendered("true" if value else "false")
            return Rendered(None, "boolean given for a non-boolean enum")
        if not isinstance(value, str):
            return Rendered(None, f"enum value must be a string, got {type(value).__name__}")
        candidate = value.strip().strip("`'\"")
        if candidate in allowed:
            return Rendered(candidate)
        folded = [item for item in allowed if item.casefold() == candidate.casefold()]
        if len(folded) == 1:
            return Rendered(folded[0], flags=["enum_case_normalised"])
        return Rendered(None, f"enum value {value!r} is not in {allowed}")

    number, flags, issue = coerce_number(value)
    if issue is not None or number is None:
        return Rendered(None, issue or "missing value", flags)
    rounding = spec["rounding"]
    if rounding["mode"] == "exact":
        if isinstance(number, Decimal):
            return Rendered(None, "inexact value for an exact field", flags)
        text = fraction_to_exact_text(number)
    else:
        text = round_half_up_text(number, rounding["decimal_places"])
    if len(text) > 256:
        return Rendered(None, "rendered value exceeds 256 characters", flags)
    return Rendered(text, None, flags)


def empty_row(question: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "dataset_version": question["dataset_version"],
        "case_id": question["case_id"],
        "final_answer": None,
        "steps": [],
    }


def build_row(
    question: Mapping[str, Any],
    final_text: str | None,
    slot_texts: Mapping[str, str | None],
) -> tuple[dict[str, Any], list[str]]:
    """Assemble a prediction row and gate it through the toolkit validator.

    Invalid fields are dropped until the row is valid; the list of dropped
    fields is returned for logging.
    """

    row = empty_row(question)
    if final_text is not None:
        row["final_answer"] = {"value": final_text}
    for slot in question["trace_spec"]["slots"]:  # published order
        text = slot_texts.get(slot["slot_id"])
        if text is not None:
            row["steps"].append({"slot_id": slot["slot_id"], "value": text})
    dropped: list[str] = []
    for _ in range(40):
        issues = validate_prediction_record(row, question)
        if not issues:
            return row, dropped
        issue = issues[0]
        if issue.path.startswith("/final_answer"):
            row["final_answer"] = None
            dropped.append("final")
        elif issue.path.startswith("/steps/"):
            index = int(issue.path.split("/")[2])
            dropped.append(row["steps"][index]["slot_id"])
            del row["steps"][index]
        else:
            raise ValueError(f"unexpected row-level validation issue: {issue.as_dict()}")
    raise ValueError("validator gate did not converge")


def parse_gold_value(text: str, spec: Mapping[str, Any]) -> Any:
    """Inverse of rendering for gold strings (used by the round-trip test)."""

    if spec["type"] == "enum":
        return text
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return Fraction(int(numerator), int(denominator))
    return Fraction(Decimal(text))
