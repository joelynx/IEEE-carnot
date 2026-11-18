"""Generic, train-driven question routing for R1 (PLAN.md §4a, rule `novel_vs_train_v1`).

A question is *novel* iff neither its number-masked text skeleton nor its
(slot_id, description) signature occurs among the released train questions.
This is the §2.4 seen/hidden proxy (analysis/conventions.py) unchanged.  It
reads only the question text and its public trace_spec, is built from train
only, and is applied identically to every question; no ID or text of any
evaluated question is referenced.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from . import common

RULE = "novel_vs_train_v1"
SUFFIX_RE = re.compile(r"\n\nAnswer format: .*\Z", re.S)
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def skeleton(text: str) -> str:
    return NUM.sub("#", " ".join(SUFFIX_RE.sub("", text).lower().split()))


def signature(question: Mapping[str, Any]) -> tuple:
    return tuple((slot["slot_id"], slot["description"]) for slot in question["trace_spec"]["slots"])


class NoveltyRouter:
    def __init__(self) -> None:
        d = common.data()
        train = [d.questions[case_id] for case_id in d.ids("train")]
        self.skeletons = {skeleton(q["question"]) for q in train}
        self.signatures = {signature(q) for q in train}
        self.info = {
            "rule": RULE,
            "reference": "train",
            "reference_case_ids_sha256": common.sha256_text("\n".join(d.ids("train"))),
            "n_skeletons": len(self.skeletons),
            "n_signatures": len(self.signatures),
        }

    def is_novel(self, question: Mapping[str, Any]) -> bool:
        return skeleton(question["question"]) not in self.skeletons and signature(question) not in self.signatures

    def route(self, question: Mapping[str, Any]) -> str:
        return "novel" if self.is_novel(question) else "seen"
