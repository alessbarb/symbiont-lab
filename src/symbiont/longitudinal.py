from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Iterable

from .collective import CollectiveMemory
from .heritage import SpeciesHeritage, apply_heritage, distill_heritage
from .simulation import SimulationResult, _run_population, run_simulation


@dataclass(slots=True, frozen=True)
class GenerationComparison:
    generation: int
    seed: int
    inherited_patterns: int
    exported_patterns: int
    retained_patterns: int
    retention_rate: float
    inherited_detection_rate: float | None
    control_detection_rate: float | None
    detection_delta: float | None
    inherited_precision: float | None
    control_precision: float | None
    precision_delta: float | None
    inherited_false_positive_rate: float | None
    control_false_positive_rate: float | None
    false_positive_delta: float | None
    inherited_classification_recall: float | None
    control_classification_recall: float | None
    classification_recall_delta: float | None
    inherited_classification_precision: float | None
    control_classification_precision: float | None
    classification_precision_delta: float | None
    inherited_calibration_error: float
    control_calibration_error: float
    calibration_delta: float
    inherited_blind_spot_rate: float
    control_blind_spot_rate: float
    blind_spot_delta: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class LongitudinalResult:
    generations: tuple[GenerationComparison, ...]
    heritage_effect_generations: int
    mean_detection_delta: float | None
    mean_precision_delta: float | None
    mean_false_positive_delta: float | None
    mean_classification_recall_delta: float | None
    mean_classification_precision_delta: float | None
    mean_calibration_delta: float | None
    mean_blind_spot_delta: float | None
    final_heritage: SpeciesHeritage

    def as_dict(self) -> dict[str, object]:
        return {
            "generations": [generation.as_dict() for generation in self.generations],
            "heritage_effect_generations": self.heritage_effect_generations,
            "mean_detection_delta": self.mean_detection_delta,
            "mean_precision_delta": self.mean_precision_delta,
            "mean_false_positive_delta": self.mean_false_positive_delta,
            "mean_classification_recall_delta": self.mean_classification_recall_delta,
            "mean_classification_precision_delta": self.mean_classification_precision_delta,
            "mean_calibration_delta": self.mean_calibration_delta,
            "mean_blind_spot_delta": self.mean_blind_spot_delta,
            "final_heritage": self.final_heritage.as_dict(),
        }


def _delta(inherited: float | None, control: float | None) -> float | None:
    if inherited is None or control is None:
        return None
    return inherited - control


def _mean_defined(values: Iterable[float | None]) -> float | None:
    defined = [value for value in values if value is not None]
    return mean(defined) if defined else None


def _run_with_heritage(
    *,
    hosts: int,
    steps: int,
    seed: int,
    threat_rate: float,
    poison_fraction: float,
    heterogeneity: float,
    drift_step: int | None,
    drift_fraction: float,
    drift_magnitude: float,
    heritage: SpeciesHeritage | None,
) -> tuple[SimulationResult, CollectiveMemory]:
    """Run the canonical simulator with bounded inherited collective priors."""
    collective = CollectiveMemory()
    apply_heritage(collective, heritage)
    return _run_population(
        hosts=hosts,
        steps=steps,
        seed=seed,
        threat_rate=threat_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        drift_step=drift_step,
        drift_fraction=drift_fraction,
        drift_magnitude=drift_magnitude,
        collective=collective,
    )


def run_longitudinal_species(
    *,
    generations: int = 5,
    hosts: int = 100,
    steps: int = 300,
    seed: int = 7,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    heritage_limit: int = 24,
) -> LongitudinalResult:
    if generations < 1:
        raise ValueError("generations must be at least 1")
    if generations > 50:
        raise ValueError("longitudinal experiments are limited to 50 generations")

    heritage = SpeciesHeritage(generation=0)
    comparisons: list[GenerationComparison] = []

    for generation in range(1, generations + 1):
        generation_seed = seed + (generation - 1) * 1009
        inherited_result, inherited_collective = _run_with_heritage(
            hosts=hosts,
            steps=steps,
            seed=generation_seed,
            threat_rate=threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=drift_step,
            drift_fraction=drift_fraction,
            drift_magnitude=drift_magnitude,
            heritage=heritage,
        )
        control_result, _ = run_simulation(
            hosts=hosts,
            steps=steps,
            seed=generation_seed,
            threat_rate=threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=drift_step,
            drift_fraction=drift_fraction,
            drift_magnitude=drift_magnitude,
        )
        next_heritage = distill_heritage(
            inherited_collective,
            generation=generation,
            max_patterns=heritage_limit,
        )
        inherited_fingerprints = {pattern.fingerprint for pattern in heritage.patterns}
        exported_fingerprints = {pattern.fingerprint for pattern in next_heritage.patterns}
        retained = len(inherited_fingerprints & exported_fingerprints)
        retention = retained / len(inherited_fingerprints) if inherited_fingerprints else 0.0

        inherited_attention_recall = inherited_result.attention_recall
        control_attention_recall = control_result.attention_recall
        inherited_attention_precision = inherited_result.attention_precision
        control_attention_precision = control_result.attention_precision
        inherited_attention_fpr = inherited_result.attention_false_positive_rate
        control_attention_fpr = control_result.attention_false_positive_rate
        inherited_classification_recall = inherited_result.classification_recall
        control_classification_recall = control_result.classification_recall
        inherited_classification_precision = inherited_result.classification_precision
        control_classification_precision = control_result.classification_precision

        comparisons.append(
            GenerationComparison(
                generation=generation,
                seed=generation_seed,
                inherited_patterns=len(heritage.patterns),
                exported_patterns=len(next_heritage.patterns),
                retained_patterns=retained,
                retention_rate=retention,
                inherited_detection_rate=inherited_attention_recall,
                control_detection_rate=control_attention_recall,
                detection_delta=_delta(inherited_attention_recall, control_attention_recall),
                inherited_precision=inherited_attention_precision,
                control_precision=control_attention_precision,
                precision_delta=_delta(inherited_attention_precision, control_attention_precision),
                inherited_false_positive_rate=inherited_attention_fpr,
                control_false_positive_rate=control_attention_fpr,
                false_positive_delta=_delta(inherited_attention_fpr, control_attention_fpr),
                inherited_classification_recall=inherited_classification_recall,
                control_classification_recall=control_classification_recall,
                classification_recall_delta=_delta(
                    inherited_classification_recall,
                    control_classification_recall,
                ),
                inherited_classification_precision=inherited_classification_precision,
                control_classification_precision=control_classification_precision,
                classification_precision_delta=_delta(
                    inherited_classification_precision,
                    control_classification_precision,
                ),
                inherited_calibration_error=inherited_result.calibration_error,
                control_calibration_error=control_result.calibration_error,
                calibration_delta=(
                    inherited_result.calibration_error - control_result.calibration_error
                ),
                inherited_blind_spot_rate=inherited_result.blind_spot_rate,
                control_blind_spot_rate=control_result.blind_spot_rate,
                blind_spot_delta=(
                    inherited_result.blind_spot_rate - control_result.blind_spot_rate
                ),
            )
        )
        heritage = next_heritage

    # Generation one is a parity control: it has no inherited intervention yet.
    # Do not dilute the estimated heritage effect with that structural zero.
    intervention = [item for item in comparisons if item.inherited_patterns > 0]

    return LongitudinalResult(
        generations=tuple(comparisons),
        heritage_effect_generations=len(intervention),
        mean_detection_delta=_mean_defined(item.detection_delta for item in intervention),
        mean_precision_delta=_mean_defined(item.precision_delta for item in intervention),
        mean_false_positive_delta=_mean_defined(
            item.false_positive_delta for item in intervention
        ),
        mean_classification_recall_delta=_mean_defined(
            item.classification_recall_delta for item in intervention
        ),
        mean_classification_precision_delta=_mean_defined(
            item.classification_precision_delta for item in intervention
        ),
        mean_calibration_delta=_mean_defined(
            item.calibration_delta for item in intervention
        ),
        mean_blind_spot_delta=_mean_defined(
            item.blind_spot_delta for item in intervention
        ),
        final_heritage=heritage,
    )
