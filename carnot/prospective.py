"""Prospective uncertainty gates, separate from the historical comparison heuristic."""

import math
import random


def zero_event_upper(n, alpha=0.05):
    """Exact one-sided binomial bound with zero events in n independent units."""
    if not isinstance(n, int) or n <= 0 or not 0 < alpha < 1:
        raise ValueError("positive independent-unit count and 0 < alpha < 1 required")
    return -math.expm1(math.log(alpha) / n)


def decision(delta, lower95, margin=0.001, *, all_differences_zero=False,
             independent_units=None, invariant=False):
    """A zero-difference bootstrap alone cannot establish generalization safety.

    invariant means the compared behavior is identical by construction, not merely
    that a small evaluated sample had identical predictions.
    """
    if not math.isfinite(margin) or margin <= 0:
        raise ValueError("margin must be finite and positive")
    bound = None
    if invariant:
        status = "invariant"
    elif all_differences_zero:
        bound = zero_event_upper(independent_units) if independent_units else None
        status = "non_inferior" if bound is not None and bound < margin else "inconclusive"
    else:
        status = "non_inferior" if lower95 > -margin else "inconclusive"
    return {"delta": delta, "one_sided_95_lower": lower95, "margin": margin,
            "status": status, "zero_event_95_upper": bound,
            "note": "Zero-event bound concerns independent family-level regression events; "
                    "it is not evidence of correctness on the private Test distribution."}


def paired_family_interval(differences, seed="carnot-r5-family-bootstrap", replicates=10000):
    """Each input is one family's mean delta; descendants never count separately."""
    if not differences or replicates < 100:
        raise ValueError("families and at least 100 replicates required")
    rng = random.Random(seed)
    n = len(differences)
    draws = sorted(sum(rng.choice(differences) for _ in range(n)) / n for _ in range(replicates))
    at = lambda q: draws[math.floor(q * (len(draws) - 1))]
    return {"delta": sum(differences) / n, "ci95": [at(0.025), at(0.975)],
            "one_sided_95_lower": at(0.05), "families": n, "replicates": replicates}
