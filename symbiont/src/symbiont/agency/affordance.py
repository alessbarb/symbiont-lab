"""ActionAffordance projection (Agency Acquisition v1 §34-§36).

An affordance states only: "this competence appears executable now and is
expected to produce this Effect in this situation".  It is derived afresh from
current organism-owned state every time it is needed: never checkpointed,
without lifecycle, without motor authority and without actuator semantics.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


def affordance_id_for(
    *,
    competence_id: str,
    anticipated_effect_id: str,
    context_ref: str | None,
    embodiment_id: str | None,
) -> str:
    material = (
        f"{competence_id}|{anticipated_effect_id}|{context_ref or '*'}|{embodiment_id or '*'}"
    )
    return "affordance." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class ActionAffordance:
    affordance_id: str

    competence_id: str
    anticipated_effect_id: str

    context_ref: str | None
    embodiment_id: str | None

    prediction_confidence: float
    controllability: float
    executability_confidence: float

    prediction_ref: str | None
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.affordance_id.startswith("affordance."):
            raise ValueError("affordance_id must be opaque")
        if not self.competence_id:
            raise ValueError("an affordance names an acquired competence")
        if not self.anticipated_effect_id.startswith("effect."):
            raise ValueError("anticipated effect must be organism-owned")
        for name in ("prediction_confidence", "controllability", "executability_confidence"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if any(ref.startswith(("actuator.", "motor.", "channel.")) for ref in self.evidence_refs):
            raise ValueError("an affordance never carries actuator semantics")


__all__ = ["ActionAffordance", "affordance_id_for"]
