"""Scoring through the organiser toolkit, unchanged (PLAN.md §5.1).

``score`` calls ``finreason_task1.scoring.score_submission`` on any gold subset
whose manifest satisfies the scorer's own constraints (every topic keeps all
difficulty cells, all 12 domains present).  Per-case weights for the paired
bootstrap are obtained by one-hot probing of that same scorer, so no scoring
logic is re-implemented here.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import common
from .formatter import empty_row
from finreason_task1.scoring import score_case, score_submission


def subset(case_ids: Iterable[str]) -> tuple[dict, dict, list]:
    d = common.data()
    ids = sorted(case_ids)
    questions = {case_id: d.questions[case_id] for case_id in ids}
    gold = {case_id: d.gold[case_id] for case_id in ids}
    manifest = [d.manifest[case_id] for case_id in ids]
    return questions, gold, manifest


def target_row(case_id: str) -> dict[str, Any]:
    """Gold re-serialised as a perfect prediction row."""

    d = common.data()
    question, gold = d.questions[case_id], d.gold[case_id]
    row = empty_row(question)
    row["final_answer"] = {"value": gold["final_value"]}
    row["steps"] = [
        {"slot_id": slot["slot_id"], "value": gold["slot_values"][slot["slot_id"]]}
        for slot in question["trace_spec"]["slots"]
    ]
    return row


def score(predictions: Sequence[Mapping[str, Any]], case_ids: Iterable[str]) -> dict[str, Any]:
    questions, gold, manifest = subset(case_ids)
    report = score_submission(questions, gold, predictions, manifest)
    by_id = {row["case_id"]: row for row in predictions}
    cases = []
    for case_id in sorted(questions):
        result = score_case(questions[case_id], gold[case_id], by_id[case_id])
        cases.append(
            {
                "case_id": case_id,
                "fac": result.fac,
                "matched_slots": result.matched_slots,
                "total_slots": result.total_slots,
            }
        )
    return {"report": report.as_dict(), "cases": cases}


def probe_weights(case_ids: Iterable[str]) -> dict[str, dict[str, str]]:
    """Exact per-case weights of seen_fac and seen_checkpoint, by one-hot probing."""

    questions, gold, manifest = subset(case_ids)
    blank = {case_id: empty_row(questions[case_id]) for case_id in questions}
    weights: dict[str, dict[str, str]] = {}
    for case_id in questions:
        perfect = target_row(case_id)
        final_only = dict(blank[case_id], final_answer=perfect["final_answer"])
        steps_only = dict(blank[case_id], steps=perfect["steps"])
        fac = score_submission(
            questions, gold, [final_only if k == case_id else blank[k] for k in questions], manifest
        ).seen_fac
        ckpt = score_submission(
            questions, gold, [steps_only if k == case_id else blank[k] for k in questions], manifest
        ).seen_checkpoint
        weights[case_id] = {"fac": str(fac), "checkpoint": str(ckpt or Fraction(0))}
    return weights


def cached_weights(name: str, case_ids: Sequence[str]) -> dict[str, dict[str, Fraction]]:
    path = common.EXPERIMENTS_DIR / "weights" / f"{name}.json"
    ids_sha = common.sha256_text("\n".join(sorted(case_ids)))
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
        if stored["case_ids_sha256"] == ids_sha:
            return {k: {m: Fraction(v) for m, v in w.items()} for k, w in stored["weights"].items()}
    weights = probe_weights(case_ids)
    common.write_bytes_atomic(
        path,
        (common.canonical_json({"case_ids_sha256": ids_sha, "weights": weights}) + "\n").encode(),
    )
    return {k: {m: Fraction(v) for m, v in w.items()} for k, w in weights.items()}
