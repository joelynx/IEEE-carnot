"""Selectors using rendered candidates only, with no access to gold or case IDs."""

from collections import Counter
from typing import Mapping, Sequence


def final_first_complete(samples: Sequence[Mapping[str, str]], fields: Sequence[str]) -> dict:
    """Choose a complete executed row supporting a plurality final; abstain otherwise.

    Ties: checkpoint agreement within the tied final's group, then input index.
    The caller retains its existing field-plurality row when this abstains.
    """
    finals = Counter(s["final"] for s in samples if "final" in s)
    if not finals:
        return {"index": None, "reason": "no_final"}
    leaders = {v for v, n in finals.items() if n == max(finals.values())}
    eligible = [i for i, s in enumerate(samples) if s.get("final") in leaders and all(f in s for f in fields)]
    if not eligible:
        return {"index": None, "reason": "no_complete_plurality_sample"}

    def agreement(i):
        peers = [s for s in samples if s.get("final") == samples[i]["final"]]
        return sum(sum(s.get(f) == samples[i][f] for s in peers) for f in fields if f != "final")

    chosen = min(eligible, key=lambda i: (-agreement(i), i))
    return {"index": chosen, "reason": "final_plurality_checkpoint_agreement"}
