from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, pstdev
from typing import Iterable

from .stress import HeritageStressCondition, HeritageStressStudy, run_heritage_stress_study

PERFORMANCE_METRICS = (
    "attention_recall",
    "attention_precision",
    "attention_false_positive_rate",
    "classification_recall",
    "classification_precision",
    "classification_false_positive_rate",
    "calibration_error",
    "brier_score",
    "high_confidence_miss_rate",
)

HERITAGE_DIAGNOSTICS = (
    "observed_prior_patterns",
    "prior_mae",
    "live_mae",
    "combined_mae",
    "correction_gain",
    "live_override_rate",
    "exported_patterns",
    "reexported_patterns",
    "direction_flips",
    "evaluable_reexports",
    "improved_reexports",
    "worsened_reexports",
    "mean_reexport_mae_gain",
    "reexport_rate",
)


@dataclass(slots=True, frozen=True)
class StressMetricSummary:
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    defined_runs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class StressConditionSummary:
    name: str
    runs: int
    metrics: dict[str, StressMetricSummary]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "runs": self.runs,
            "metrics": {name: value.as_dict() for name, value in self.metrics.items()},
        }


@dataclass(slots=True, frozen=True)
class StressPairedDelta:
    condition: str
    reference: str
    metric: str
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    direction_agreement: float | None
    pairs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ReplicatedHeritageStressStudy:
    source_seeds: tuple[int, ...]
    target_seeds: tuple[int, ...]
    target_offset: int
    source_pattern_counts: tuple[int, ...]
    conditions: tuple[str, ...]
    summaries: dict[str, StressConditionSummary]
    paired_vs_naive: dict[str, dict[str, StressPairedDelta]]
    world_digests: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "source_seeds": self.source_seeds,
            "target_seeds": self.target_seeds,
            "target_offset": self.target_offset,
            "source_pattern_counts": self.source_pattern_counts,
            "conditions": self.conditions,
            "summaries": {name: summary.as_dict() for name, summary in self.summaries.items()},
            "paired_vs_naive": {
                condition: {metric: delta.as_dict() for metric, delta in metrics.items()}
                for condition, metrics in self.paired_vs_naive.items()
            },
            "world_digests": self.world_digests,
        }


def _summary(values: list[float]) -> StressMetricSummary:
    if not values:
        return StressMetricSummary(None, None, None, None, 0)
    return StressMetricSummary(
        mean=mean(values),
        stdev=pstdev(values) if len(values) > 1 else 0.0,
        minimum=min(values),
        maximum=max(values),
        defined_runs=len(values),
    )


def _metric(condition: HeritageStressCondition, name: str) -> float | None:
    value = getattr(condition, name)
    if value is None:
        return None
    return float(value)


def _direction_agreement(values: list[float]) -> float | None:
    if not values:
        return None
    avg = mean(values)
    if abs(avg) < 1e-12:
        return sum(abs(value) < 1e-12 for value in values) / len(values)
    if avg > 0:
        return sum(value > 0 for value in values) / len(values)
    return sum(value < 0 for value in values) / len(values)


def run_replicated_heritage_stress_study(
    *,
    source_seeds: Iterable[int] = (3, 7, 11, 17, 23),
    target_offset: int = 1009,
    hosts: int = 100,
    steps: int = 300,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    heritage_limit: int = 24,
) -> ReplicatedHeritageStressStudy:
    sources = tuple(int(seed) for seed in source_seeds)
    if not sources:
        raise ValueError("replicated heritage stress requires at least one source seed")
    if len(sources) > 50:
        raise ValueError("replicated heritage stress is limited to 50 source seeds")
    if len(set(sources)) != len(sources):
        raise ValueError("replicated heritage stress source seeds must be unique")
    if target_offset == 0:
        raise ValueError("target_offset must produce a distinct target world")

    targets = tuple(seed + int(target_offset) for seed in sources)
    if set(targets) & set(sources):
        raise ValueError("target_offset must not make any target seed collide with a source seed")
    runs: list[HeritageStressStudy] = []
    for source_seed, target_seed in zip(sources, targets):
        runs.append(
            run_heritage_stress_study(
                source_seed=source_seed,
                target_seed=target_seed,
                hosts=hosts,
                steps=steps,
                threat_rate=threat_rate,
                poison_fraction=poison_fraction,
                heterogeneity=heterogeneity,
                drift_step=drift_step,
                drift_fraction=drift_fraction,
                drift_magnitude=drift_magnitude,
                heritage_limit=heritage_limit,
            )
        )

    condition_names = tuple(condition.name for condition in runs[0].conditions)
    by_condition: dict[str, list[HeritageStressCondition]] = {name: [] for name in condition_names}
    world_digests: list[str] = []

    for run in runs:
        current = {condition.name: condition for condition in run.conditions}
        if tuple(current) != condition_names:
            raise ValueError("heritage stress condition set changed across paired worlds")
        digests = {condition.world_digest for condition in run.conditions}
        if len(digests) != 1:
            raise RuntimeError("a heritage stress pair did not share one target world")
        world_digests.append(next(iter(digests)))
        for name in condition_names:
            by_condition[name].append(current[name])

    all_metrics = (*PERFORMANCE_METRICS, *HERITAGE_DIAGNOSTICS)
    summaries: dict[str, StressConditionSummary] = {}
    for name, conditions in by_condition.items():
        metrics: dict[str, StressMetricSummary] = {}
        for metric_name in all_metrics:
            values = [
                value
                for condition in conditions
                if (value := _metric(condition, metric_name)) is not None
            ]
            metrics[metric_name] = _summary(values)
        summaries[name] = StressConditionSummary(
            name=name,
            runs=len(conditions),
            metrics=metrics,
        )

    naive = by_condition["naive"]
    paired: dict[str, dict[str, StressPairedDelta]] = {}
    for name in condition_names:
        if name == "naive":
            continue
        condition_deltas: dict[str, StressPairedDelta] = {}
        for metric_name in PERFORMANCE_METRICS:
            values: list[float] = []
            for candidate, baseline in zip(by_condition[name], naive):
                candidate_value = _metric(candidate, metric_name)
                baseline_value = _metric(baseline, metric_name)
                if candidate_value is None or baseline_value is None:
                    continue
                values.append(candidate_value - baseline_value)
            summary = _summary(values)
            condition_deltas[metric_name] = StressPairedDelta(
                condition=name,
                reference="naive",
                metric=metric_name,
                mean=summary.mean,
                stdev=summary.stdev,
                minimum=summary.minimum,
                maximum=summary.maximum,
                direction_agreement=_direction_agreement(values),
                pairs=len(values),
            )
        paired[name] = condition_deltas

    return ReplicatedHeritageStressStudy(
        source_seeds=sources,
        target_seeds=targets,
        target_offset=int(target_offset),
        source_pattern_counts=tuple(run.source_patterns for run in runs),
        conditions=condition_names,
        summaries=summaries,
        paired_vs_naive=paired,
        world_digests=tuple(world_digests),
    )
