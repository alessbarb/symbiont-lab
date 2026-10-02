"""Cognitive acquisition ablation (apparatus-side decision, neutral core switches).

The organism exposes configurable capabilities; deciding to switch them off
for a controlled comparison belongs to the Lab. Apply after restoring State X
and before the first tick of the arm. The switches are not organism state:
they stay out of state identity, and the runtime records their effective values
as provenance and reapplies them if the arm is restarted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CognitiveAcquisitionAblation:
    plasticity_enabled: bool = False
    predictor_promotion: bool = False

    def apply(self, runtime: Any) -> None:
        runtime.set_cognitive_plasticity_enabled(self.plasticity_enabled)
        runtime.set_predictor_promotion_enabled(self.predictor_promotion)

    def as_dict(self) -> dict[str, bool]:
        return {
            "plasticity_enabled": self.plasticity_enabled,
            "predictor_promotion": self.predictor_promotion,
        }
