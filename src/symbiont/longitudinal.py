from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean

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
    inherited_detection_rate: float
    control_detection_rate: float
    detection_delta: float
    inherited_precision: float
    control_precision: float
    precision_delta: float
    inherited_false_positive_rate: float
    control_false_positive_rate: float
    false_positive_delta: float
    inherited_classification_recall: float
    control_classification_recall: float
    classification_recall_delta: float
    inherited_classification_precision: float
    control_classification_precision: float
    classification_precision_delta: float
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
    mean_detection_delta: float
    mean_precision_delta: float
    mean_false_positive_delta: float
    mean_classification_recall_delta: float
    mean_classification_precision_delta: float
    mean_calibration_delta: float
    mean_blind_spot_delta: float
    final_heritage: SpeciesHeritage

    def as_dict(self) -> dict[str, object]:
        return {
            "generations": [generation.as_dict() for generation in self.generations],
            "mean_detection_delta": self.mean_detection_delta,
            "mean_precision_delta": self.mean_precision_delta,
            "mean_false_positive_delta": self.mean_false_positive_delta,
            "mean_classification_recall_delta": self.mean_classification_recall_delta,
            "mean_classification_precision_delta": self.mean_classification_precision_delta,
            "mean_calibration_delta": self.mean_calibration_delta,
            "mean_blind_spot_delta": self.mean_blind_spot_delta,
            "final_heritage": self.final_heritage.as_dict(),
        }


def _value(value: float | None) -> float:
    return value if value is not None else 0.0


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

        inherited_classification_recall = _value(inherited_result.classification_recall)
        control_classification_recall = _value(control_result.classification_recall)
        inherited_classification_precision = _value(inherited_result.classification_precision)
        control_classification_precision = _value(control_result.classification_precision)

        comparisons.append(
            GenerationComparison(
                generation=generation,
                seed=generation_seed,
                inherited_patterns=len(heritage.patterns),
                exported_patterns=len(next_heritage.patterns),
                retained_patterns=retained,
                retention_rate=retention,
                inherited_detection_rate=inherited_result.detection_rate,
                control_detection_rate=control_result.detection_rate,
                detection_delta=inherited_result.detection_rate - control_result.detection_rate,
                inherited_precision=inherited_result.precision,
                control_precision=control_result.precision,
                precision_delta=inherited_result.precision - control_result.precision,
                inherited_false_positive_rate=inherited_result.false_positive_rate,
                control_false_positive_rate=control_result.false_positive_rate,
                false_positive_delta=(
                    inherited_result.false_positive_rate - control_result.false_positive_rate
                ),
                inherited_classification_recall=inherited_classification_recall,
                control_classification_recall=control_classification_recall,
                classification_recall_delta=(
                    inherited_classification_recall - control_classification_recall
                ),
                inherited_classification_precision=inherited_classification_precision,
                control_classification_precision=control_classification_precision,
                classification_precision_delta=(
                    inherited_classification_precision - control_classification_precision
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

    return LongitudinalResult(
        generations=tuple(comparisons),
        mean_detection_delta=mean(item.detection_delta for item in comparisons),
        mean_precision_delta=mean(item.precision_delta for item in comparisons),
        mean_false_positive_delta=mean(item.false_positive_delta for item in comparisons),
        mean_classification_recall_delta=mean(
            item.classification_recall_delta for item in comparisons
        ),
        mean_classification_precision_delta=mean(
            item.classification_precision_delta for item in comparisons
        ),
        mean_calibration_delta=mean(item.calibration_delta for item in comparisons),
        mean_blind_spot_delta=mean(item.blind_spot_delta for item in comparisons),
        final_heritage=heritage,
    )
