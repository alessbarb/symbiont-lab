from __future__ import annotations

import math
from enum import StrEnum
from typing import Sequence


class TransductionKind(StrEnum):
    """Closed primitive catalogue for v1 sensory transduction."""

    IDENTITY = "identity"
    DIFFERENCE = "difference"
    INTEGRATE = "integrate"
    THRESHOLD = "threshold"
    MIX = "mix"


def apply_transduction(
    kind: TransductionKind,
    values: Sequence[float],
    *,
    gain: float,
    decay: float,
    threshold: float,
    previous: float | None,
    integrator: float,
) -> tuple[float, float | None, float]:
    """Execute one bounded primitive and return output + transient state.

    The implementation deliberately avoids dynamic code, callbacks or an
    expression language.  More complex transducers are represented by
    structural combinations in later schema versions, never executable text.
    """
    if not values:
        raise ValueError("transduction requires at least one value")
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError("transduction values must be finite")
    if not math.isfinite(gain) or not 0.0 < gain <= 8.0:
        raise ValueError("gain must be finite and within (0, 8]")
    if not math.isfinite(decay) or not 0.0 <= decay <= 1.0:
        raise ValueError("decay must be within [0, 1]")
    if not math.isfinite(threshold):
        raise ValueError("threshold must be finite")

    primary = float(values[0])
    next_previous = primary
    next_integrator = integrator

    if kind is TransductionKind.IDENTITY:
        output = primary
    elif kind is TransductionKind.DIFFERENCE:
        output = 0.0 if previous is None else primary - previous
    elif kind is TransductionKind.INTEGRATE:
        next_integrator = decay * integrator + (1.0 - decay) * primary
        output = next_integrator
    elif kind is TransductionKind.THRESHOLD:
        output = 1.0 if primary >= threshold else 0.0
    elif kind is TransductionKind.MIX:
        output = sum(float(value) for value in values) / len(values)
    else:  # pragma: no cover - enum construction prevents this
        raise ValueError(f"unsupported transduction kind: {kind}")

    output *= gain
    # A kernel ceiling prevents pathological parameter combinations from
    # creating non-finite activations before the cognition normalizer.
    output = max(-1_000_000.0, min(1_000_000.0, output))
    return output, next_previous, next_integrator
