"""The question's "Answer format:" sentence as a function of its answer_spec.

Reproduces the released train and dev questions exactly (tested on all of them).
Only forms attested in train are produced; anything else raises, so a
synthetic question never carries wording the organisers have not used.
"""

from __future__ import annotations

from typing import Any, Mapping

ATTESTED_DECIMAL_PLACES = {2, 4}


def answer_format(spec: Mapping[str, Any]) -> str:
    if spec["type"] == "enum":
        values = list(spec["allowed_values"])
        if set(values) == {"true", "false"}:
            if values != ["false", "true"]:
                raise ValueError('boolean enums are listed as ["false", "true"] in train')
            return "return exactly the lowercase token `true` or `false` and no additional text."
        return ("return exactly one of these case-sensitive tokens and no additional text: "
                + ", ".join(f"`{value}`" for value in values) + ".")
    unit = spec["unit"]
    if spec["rounding"]["mode"] == "exact":
        return (f"return only the exact numeric value interpreted in `{unit}`, using finite-decimal notation when it "
                "terminates in base 10 and an irreducible `numerator/denominator` fraction otherwise, with no unit "
                "label or additional text.")
    places = spec["rounding"]["decimal_places"]
    if places not in ATTESTED_DECIMAL_PLACES:
        raise ValueError(f"final answers are rounded to {sorted(ATTESTED_DECIMAL_PLACES)} decimal places in train, not {places}")
    return (f"use exact arithmetic through all intermediate steps, round only the final value half up to {places} "
            f"decimal digits, and return only the numeric value interpreted in `{unit}` with no unit label or additional text.")


def with_answer_format(body: str, spec: Mapping[str, Any]) -> str:
    return f"{body.rstrip()}\n\nAnswer format: {answer_format(spec)}"
