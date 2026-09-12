from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from statistics import mean, pstdev
from typing import Callable, Iterable

from symbiont_lab.experiments.spec import ExperimentSpec
from symbiont.simulation import SimulationResult, run_simulation


COMPARABLE_PARAMETERS: dict[str, tuple[float, float]] = {
    "threat_rate": (0.0, 1.0),
    "poison_fraction": (0.0, 1.0),
    "heterogeneity": (0.0, 1.0),
    "drift_fraction": (0.0, 1.0),
    "drift_magnitude": (0.0, 0.60),
}

# Research-facing names. Legacy detection_rate/precision/FPR remain available on
# SimulationResult but are intentionally excluded here because they describe
# attention allocation, not classification.
METRICS = (
    "attention_recall",
    "attention_precision",
    "attention_false_positive_rate",
    "classification_recall",
    "classification_precision",
    "classification_false_positive_rate",
    "calibration_error",
    "high_confidence_miss_rate",
    "recent_drift_false_positive_rate",
    "top_probe_utility",
    "self_confidence",
    "epistemic_pressure",
)

LEGACY_SERIALIZED_ALIASES = {
    "detection_rate": "attention_recall",
    "precision": "attention_precision",
    "false_positive_rate": "attention_false_positive_rate",
    "blind_spot_rate": "high_confidence_miss_rate",
}


@dataclass(slots=True, frozen=True)
class MetricSummary:
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    defined_runs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class PairedDeltaSummary:
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    direction_agreement: float | None
    pairs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ConditionSummary:
    name: str
    parameter_value: float
    runs: int
    metrics: dict[str, MetricSummary]

    def as_dict(self, *, legacy_aliases: bool = False) -> dict[str, object]:
        metrics = {name: value.as_dict() for name, value in self.metrics.items()}
        if legacy_aliases:
            for alias, canonical in LEGACY_SERIALIZED_ALIASES.items():
                metrics[alias] = dict(metrics[canonical])
        return {
            "name": self.name,
            "parameter_value": self.parameter_value,
            "runs": self.runs,
            "metrics": metrics,
        }


@dataclass(slots=True, frozen=True)
class StudyResult:
    title: str
    parameter: str
    seeds: tuple[int, ...]
    baseline: ConditionSummary
    variant: ConditionSummary
    paired_deltas: dict[str, PairedDeltaSummary]

    def delta(self, metric: str) -> float | None:
        canonical = LEGACY_SERIALIZED_ALIASES.get(metric, metric)
        return self.paired_deltas[canonical].mean

    def as_dict(self) -> dict[str, object]:
        deltas = {metric: self.delta(metric) for metric in METRICS}
        paired = {
            metric: summary.as_dict() for metric, summary in self.paired_deltas.items()
        }
        for alias, canonical in LEGACY_SERIALIZED_ALIASES.items():
            deltas[alias] = deltas[canonical]
            paired[alias] = dict(paired[canonical])
        return {
            "title": self.title,
            "parameter": self.parameter,
            "seeds": self.seeds,
            "baseline": self.baseline.as_dict(legacy_aliases=True),
            "variant": self.variant.as_dict(legacy_aliases=True),
            "deltas": deltas,
            "paired_deltas": paired,
        }


def _bounded_parameter(parameter: str, value: float) -> float:
    if parameter not in COMPARABLE_PARAMETERS:
        raise ValueError(f"unsupported study parameter: {parameter}")
    low, high = COMPARABLE_PARAMETERS[parameter]
    return min(high, max(low, float(value)))


def _run(spec: ExperimentSpec) -> SimulationResult:
    result, _ = run_simulation(
        spec.hosts,
        spec.steps,
        spec.seed,
        spec.threat_rate,
        spec.poison_fraction,
        spec.heterogeneity,
        spec.drift_step,
        spec.drift_fraction,
        spec.drift_magnitude,
    )
    return result


def _metric_value(result: SimulationResult, metric: str) -> float | None:
    value = getattr(result, metric)
    resolved = value() if callable(value) else value
    return None if resolved is None else float(resolved)


def _summary(values: list[float]) -> tuple[float | None, float | None, float | None, float | None]:
    if not values:
        return None, None, None, None
    return (
        mean(values),
        pstdev(values) if len(values) > 1 else 0.0,
        min(values),
        max(values),
    )


def _summarize(
    name: str,
    parameter_value: float,
    results: Iterable[SimulationResult],
) -> ConditionSummary:
    items = list(results)
    if not items:
        raise ValueError("study condition requires at least one run")
    metrics: dict[str, MetricSummary] = {}
    for metric in METRICS:
        values = [
            value
            for result in items
            if (value := _metric_value(result, metric)) is not None
        ]
        avg, stdev, minimum, maximum = _summary(values)
        metrics[metric] = MetricSummary(
            mean=avg,
            stdev=stdev,
            minimum=minimum,
            maximum=maximum,
            defined_runs=len(values),
        )
    return ConditionSummary(
        name=name,
        parameter_value=parameter_value,
        runs=len(items),
        metrics=metrics,
    )


def _paired_delta_summaries(
    baseline_results: list[SimulationResult],
    variant_results: list[SimulationResult],
) -> dict[str, PairedDeltaSummary]:
    if len(baseline_results) != len(variant_results) or not baseline_results:
        raise ValueError("paired study results must have equal non-zero lengths")

    summaries: dict[str, PairedDeltaSummary] = {}
    for metric in METRICS:
        values: list[float] = []
        for baseline, variant in zip(baseline_results, variant_results):
            baseline_value = _metric_value(baseline, metric)
            variant_value = _metric_value(variant, metric)
            if baseline_value is None or variant_value is None:
                continue
            values.append(variant_value - baseline_value)

        avg, stdev, minimum, maximum = _summary(values)
        if avg is None:
            agreement = None
        elif abs(avg) < 1e-12:
            agreement = sum(abs(value) < 1e-12 for value in values) / len(values)
        elif avg > 0:
            agreement = sum(value > 0 for value in values) / len(values)
        else:
            agreement = sum(value < 0 for value in values) / len(values)
        summaries[metric] = PairedDeltaSummary(
            mean=avg,
            stdev=stdev,
            minimum=minimum,
            maximum=maximum,
            direction_agreement=agreement,
            pairs=len(values),
        )
    return summaries


def run_comparative_study(
    base_spec: ExperimentSpec,
    *,
    parameter: str,
    baseline_value: float,
    variant_value: float,
    seeds: Iterable[int],
    title: str = "Comparative study",
    on_progress: Callable[[int, int, str, int], None] | None = None,
) -> StudyResult:
    seed_tuple = tuple(int(seed) for seed in seeds)
    if not seed_tuple:
        raise ValueError("study requires at least one seed")
    baseline_value = _bounded_parameter(parameter, baseline_value)
    variant_value = _bounded_parameter(parameter, variant_value)

    baseline_results: list[SimulationResult] = []
    variant_results: list[SimulationResult] = []
    total = len(seed_tuple) * 2
    completed = 0

    for seed in seed_tuple:
        baseline_spec = replace(
            base_spec,
            seed=seed,
            delay=0.0,
            **{parameter: baseline_value},
        )
        baseline_results.append(_run(baseline_spec))
        completed += 1
        if on_progress:
            on_progress(completed, total, "baseline", seed)

    for seed in seed_tuple:
        variant_spec = replace(
            base_spec,
            seed=seed,
            delay=0.0,
            **{parameter: variant_value},
        )
        variant_results.append(_run(variant_spec))
        completed += 1
        if on_progress:
            on_progress(completed, total, "variant", seed)

    return StudyResult(
        title=title,
        parameter=parameter,
        seeds=seed_tuple,
        baseline=_summarize("baseline", baseline_value, baseline_results),
        variant=_summarize("variant", variant_value, variant_results),
        paired_deltas=_paired_delta_summaries(baseline_results, variant_results),
    )
