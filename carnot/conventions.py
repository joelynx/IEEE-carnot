"""Slot-convention examples from other templates (convention-reading candidate, PLAN.md §4c).

For each required slot of a question, find slots in the pool (the tuning set,
D9) with the same named slot_id or the same description, in templates other
than the question's own, and show up to ``per_slot`` of those questions with
the slot's reference value.  The model sees how this benchmark uses a slot of
that name (units, sign, scope), never the question's own template: hidden test
questions have no template in the pool, and evaluation mimics that by always
excluding the query's template.  Generic slot names (trace_1, trace_2, ...)
carry no meaning and are matched by description only.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any, Mapping

from . import common, splits

GENERIC = re.compile(r"trace_\d+\Z")
SUFFIX = re.compile(r"\n\nAnswer format: .*\Z", re.S)


class SlotConventions:
    def __init__(self, pool: str = "tuning", per_slot: int = 2, exclude_ids: set[str] | None = None) -> None:
        d = common.data()
        self.per_slot = per_slot
        self.by_id: dict[str, list[dict]] = defaultdict(list)
        self.by_desc: dict[str, list[dict]] = defaultdict(list)
        ids = sorted(set(splits.load()[pool]) - (exclude_ids or set()))
        for case_id in ids:
            question, gold = d.questions[case_id], d.gold[case_id]
            for slot in question["trace_spec"]["slots"]:
                entry = {"case_id": case_id, "template_id": d.template(case_id), "slot_id": slot["slot_id"],
                         "description": slot["description"].strip(), "unit": slot["result_spec"].get("unit", "enum"),
                         "value": gold["slot_values"][slot["slot_id"]],
                         "question": SUFFIX.sub("", question["question"]).strip()}
                if not GENERIC.fullmatch(slot["slot_id"]):
                    self.by_id[slot["slot_id"]].append(entry)
                self.by_desc[entry["description"].lower()].append(entry)
        self.info = {"pool": pool, "per_slot": per_slot, "pool_size": len(ids),
                     "pool_ids_sha256": common.sha256_text("\n".join(ids))}

    def _pick(self, candidates: list[dict], exclude_template: str | None, key: str) -> list[dict]:
        seen_templates, picked = set(), []
        ordered = sorted(candidates, key=lambda e: hashlib.sha256(f"{key}|{e['case_id']}".encode()).hexdigest())
        for entry in ordered:
            if entry["template_id"] == exclude_template or entry["template_id"] in seen_templates:
                continue
            seen_templates.add(entry["template_id"])
            picked.append(entry)
            if len(picked) == self.per_slot:
                break
        return picked

    def block(self, question: Mapping[str, Any], exclude_template: str | None) -> str | None:
        """Prompt block for one question, or None when no slot has a match in another template."""

        sections = []
        for slot in question["trace_spec"]["slots"]:
            description = slot["description"].strip()
            candidates = list(self.by_id.get(slot["slot_id"], [])) if not GENERIC.fullmatch(slot["slot_id"]) else []
            seen = {e["case_id"] for e in candidates}
            candidates += [e for e in self.by_desc.get(description.lower(), []) if e["case_id"] not in seen]
            picked = self._pick(candidates, exclude_template, f"{slot['slot_id']}|{description}")
            if not picked:
                continue
            lines = [f'Slot "{slot["slot_id"]}" ({description}):']
            for entry in picked:
                lines.append(f'- In another question, slot "{entry["slot_id"]}" ({entry["description"]}, unit {entry["unit"]}) '
                             f'had the reference value {entry["value"]}. That question was:\n  {entry["question"]}')
            sections.append("\n".join(lines))
        if not sections:
            return None
        return ("### How these slot names are used elsewhere in this benchmark\n"
                "Each entry shows a slot with the same name or description in a different question, with its reference "
                "value. Use them only to understand what the slot measures (its units, sign and scope); compute every "
                "value from your own question.\n\n" + "\n\n".join(sections))
