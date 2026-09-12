from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Sequence

from symbiont.core.collective import CollectiveMemory
from symbiont.core.heritage import SpeciesHeritage, apply_heritage, distill_heritage
from symbiont.simulation import SimulationResult, run_simulation


@dataclass(slots=True, frozen=True)
class EcologicalShiftOutcome:
    seed: int
    drift_step: int
    drift_fraction: float
    drift_magnitude: float
    naive_result: SimulationResult
    adapted_result: SimulationResult

    @property
    def recall_delta(self) -> float | None:
        if (
            self.adapted_result.classification_recall is not None
            and self.naive_result.classification_recall is not None
        ):
            return (
                self.adapted_result.classification_recall
                - self.naive_result.classification_recall
            )
        return None

    @property
    def precision_delta(self) -> float | None:
        if (
            self.adapted_result.classification_precision is not None
            and self.naive_result.classification_precision is not None
        ):
            return (
                self.adapted_result.classification_precision
                - self.naive_result.classification_precision
            )
        return None

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "drift_step": self.drift_step,
            "drift_fraction": self.drift_fraction,
            "drift_magnitude": self.drift_magnitude,
            "recall_delta": self.recall_delta,
            "precision_delta": self.precision_delta,
        }


def run_ecological_shift_study(
    *,
    source_seeds: Sequence[int],
    target_seeds: Sequence[int],
    hosts: int = 100,
    steps: int = 300,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int = 150,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
) -> list[EcologicalShiftOutcome]:
    """Study the robustness of species heritage when the target ecology shifts."""
    outcomes: list[EcologicalShiftOutcome] = []

    for src_seed, tgt_seed in zip(source_seeds, target_seeds):
        # 1. Run source generation to distill ancestral heritage
        _, source_collective = run_simulation(
            hosts=hosts,
            steps=steps,
            seed=src_seed,
            threat_rate=threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=drift_step,
            drift_fraction=drift_fraction,
            drift_magnitude=drift_magnitude,
        )
        heritage = distill_heritage(source_collective, generation=1)

        # 2. Run naive baseline in target environment
        naive_result, _ = run_simulation(
            hosts=hosts,
            steps=steps,
            seed=tgt_seed,
            threat_rate=threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=drift_step,
            drift_fraction=drift_fraction,
            drift_magnitude=drift_magnitude,
        )

        # 3. Run target with inherited priors in target environment
        adapted_collective = CollectiveMemory()
        apply_heritage(adapted_collective, heritage)
        adapted_result, _ = run_simulation(
            hosts=hosts,
            steps=steps,
            seed=tgt_seed,
            threat_rate=threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=drift_step,
            drift_fraction=drift_fraction,
            drift_magnitude=drift_magnitude,
            collective=adapted_collective,
        )

        outcomes.append(
            EcologicalShiftOutcome(
                seed=tgt_seed,
                drift_step=drift_step,
                drift_fraction=drift_fraction,
                drift_magnitude=drift_magnitude,
                naive_result=naive_result,
                adapted_result=adapted_result,
            )
        )
    return outcomes
