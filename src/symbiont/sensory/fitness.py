from __future__ import annotations

import math


def sensory_fitness(
    *,
    predictive_contribution: float,
    downstream_contribution: float,
    novelty: float,
    reliability: float,
    redundancy: float,
    cost: float,
) -> float:
    """Bounded organism-side sensor fitness.

    Inputs are descriptive/local.  No evaluator label or task truth is
    accepted by this API.
    """
    values = (predictive_contribution, downstream_contribution, novelty, reliability, redundancy, cost)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) for v in values):
        raise ValueError("sensory fitness inputs must be finite")
    p, d, n, q, r, c = (max(0.0, min(1.0, float(v))) for v in values)
    return max(0.0, min(1.0, 0.30 * p + 0.20 * d + 0.15 * n + 0.20 * q - 0.10 * r - 0.05 * c))
