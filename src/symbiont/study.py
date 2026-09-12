from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from statistics import mean, pstdev
from typing import Iterable

from .experiment import ExperimentSpec
from .simulation import SimulationResult, run_simulation


COMPARABLE_PARAMETERS: dict[str, tuple[float, float]] = {
    "threat_rate": (0.0, 1.0),
    "poison_fraction": (0.0, 1.0),
    "heterogeneity": (0.0, 1.0),
    "drift_fraction": (0.0, 1.0),
    "drift_magnitude": (0.0, 0.60),
}

METRICS = (
    "detection_rate",
    "precision",
    "false_positive_rate",
    "calibration_error",
    "blind_spot_rate",
    "recent_drift_false_positive_rate",
    "top_probe_utility",
    "self_confidence",
    "epistemic_pressure",
)


@dataclass(slots=True, frozen=True)
class MetricSummary:
    mean: float
    stdev: float
    minimum: float
    maximum: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ConditionSummary:
    name: str
    parameter_value: float
    runs: int
    metrics: dict[str, MetricSummary]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "parameter_value": self.parameter_value,
            "runs": self.runs,
            "metrics": {name: value.as_dict() for name, value in self.metrics.items()},
        }


@dataclass(slots=True, frozen=True)
class StudyResult:
    title: str
    parameter: str
    seeds: tuple[int, ...]
    baseline: ConditionSummary
    variant: ConditionSummary

    def delta(self, metric: str) -> float:
        return self.variant.metrics[metric].mean - self.baseline.metrics[metric].mean

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "parameter": self.parameter,
            "seeds": self.seeds,
            "baseline": self.baseline.as_dict(),
            "variant": self.variant.as_dict(),
            "deltas": {metric: self.delta(metric) for metric in METRICS},
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


def _metric_value(result: SimulationResult, metric: str) -> float:
    value = getattr(result, metric)
    return float(value() if callable(value) else value)


def _summarize(name: str, parameter_value: float, results: Iterable[SimulationResult]) -> ConditionSummary:
    items = list(results)
    if not items:
        raise ValueError("study condition requires at least one run")
    metrics: dict[str, MetricSummary] = {}
    for metric in METRICS:
        values = [_metric_value(result, metric) for result in items]
        metrics[metric] = MetricSummary(
            mean=mean(values),
            stdev=pstdev(values) if len(values) > 1 else 0.0,
            minimum=min(values),
            maximum=max(values),
        )
    return ConditionSummary(name=name, parameter_value=parameter_value, runs=len(items), metrics=metrics)


def run_comparative_study(
    base_spec: ExperimentSpec,
    *,
    parameter: str,
    baseline_value: float,
    variant_value: float,
    seeds: Iterable[int],
    title: str = "Comparative study",
) -> StudyResult:
    seed_tuple = tuple(int(seed) for seed in seeds)
    if not seed_tuple:
        raise ValueError("study requires at least one seed")
    baseline_value = _bounded_parameter(parameter, baseline_value)
    variant_value = _bounded_parameter(parameter, variant_value)

    baseline_results: list[SimulationResult] = []
    variant_results: list[SimulationResult] = []
    for seed in seed_tuple:
        baseline_spec = replace(
            base_spec,
            seed=seed,
            delay=0.0,
            **{parameter: baseline_value},
        )
        variant_spec = replace(
            base_spec,
            seed=seed,
            delay=0.0,
            **{parameter: variant_value},
        )
        baseline_results.append(_run(baseline_spec))
        variant_results.append(_run(variant_spec))

    return StudyResult(
        title=title,
        parameter=parameter,
        seeds=seed_tuple,
        baseline=_summarize("baseline", baseline_value, baseline_results),
        variant=_summarize("variant", variant_value, variant_results),
    )
