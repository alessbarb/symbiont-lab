from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, pstdev
from typing import Iterable

from .second_look import SecondLookOutcome, run_second_look_study

EVIDENCE_METRICS = (
    "brier_gain",
    "mean_entropy_reduction",
    "corrected_rate",
    "introduced_rate",
    "net_correction_rate",
    "selected_threat_share",
    "stealth_share",
    "stealth_correction_rate",
)


@dataclass(slots=True, frozen=True)
class EvidenceMetricSummary:
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    defined_runs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class EvidenceStrategySummary:
    strategy: str
    runs: int
    metrics: dict[str, EvidenceMetricSummary]

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "runs": self.runs,
            "metrics": {name: value.as_dict() for name, value in self.metrics.items()},
        }


@dataclass(slots=True, frozen=True)
class EvidencePairedDelta:
    metric: str
    strategy: str
    reference: str
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    direction_agreement: float | None
    pairs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ReplicatedEvidenceStudy:
    seeds: tuple[int, ...]
    strategies: tuple[str, ...]
    reference_strategy: str
    summaries: dict[str, EvidenceStrategySummary]
    paired_vs_reference: dict[str, dict[str, EvidencePairedDelta]]
    budgets: tuple[int, ...]
    budgets_per_1000: tuple[float, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": self.seeds,
            "strategies": self.strategies,
            "reference_strategy": self.reference_strategy,
            "summaries": {name: summary.as_dict() for name, summary in self.summaries.items()},
            "paired_vs_reference": {
                strategy: {metric: delta.as_dict() for metric, delta in metrics.items()}
                for strategy, metrics in self.paired_vs_reference.items()
            },
            "budgets": self.budgets,
            "budgets_per_1000": self.budgets_per_1000,
        }


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _metric(outcome: SecondLookOutcome, metric: str) -> float | None:
    if metric == "brier_gain":
        return outcome.brier_gain
    if metric == "mean_entropy_reduction":
        return outcome.mean_entropy_reduction
    if metric == "corrected_rate":
        return _rate(outcome.corrected_errors, outcome.selected)
    if metric == "introduced_rate":
        return _rate(outcome.introduced_errors, outcome.selected)
    if metric == "net_correction_rate":
        return _rate(
            outcome.corrected_errors - outcome.introduced_errors,
            outcome.selected,
        )
    if metric == "selected_threat_share":
        return outcome.selected_threat_share
    if metric == "stealth_share":
        return _rate(outcome.stealth_selected, outcome.selected)
    if metric == "stealth_correction_rate":
        return _rate(outcome.stealth_corrected, outcome.stealth_selected)
    raise ValueError(f"unsupported evidence metric: {metric}")


def _summary(values: list[float]) -> EvidenceMetricSummary:
    if not values:
        return EvidenceMetricSummary(None, None, None, None, 0)
    return EvidenceMetricSummary(
        mean=mean(values),
        stdev=pstdev(values) if len(values) > 1 else 0.0,
        minimum=min(values),
        maximum=max(values),
        defined_runs=len(values),
    )


def _direction_agreement(values: list[float]) -> float | None:
    if not values:
        return None
    avg = mean(values)
    if abs(avg) < 1e-12:
        return sum(abs(value) < 1e-12 for value in values) / len(values)
    if avg > 0:
        return sum(value > 0 for value in values) / len(values)
    return sum(value < 0 for value in values) / len(values)


def run_replicated_evidence_study(
    *,
    seeds: Iterable[int] = (3, 7, 11, 17, 23),
    hosts: int = 100,
    steps: int = 300,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    budget: int | None = None,
    sensor_noise: float = 0.18,
    reference_strategy: str = "random",
) -> ReplicatedEvidenceStudy:
    seed_tuple = tuple(int(seed) for seed in seeds)
    if not seed_tuple:
        raise ValueError("replicated evidence study requires at least one seed")
    if len(seed_tuple) > 50:
        raise ValueError("replicated evidence studies are limited to 50 seeds")
    if len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("replicated evidence study seeds must be unique")

    runs = [
        run_second_look_study(
            hosts=hosts,
            steps=steps,
            seed=seed,
            threat_rate=threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=drift_step,
            drift_fraction=drift_fraction,
            drift_magnitude=drift_magnitude,
            budget=budget,
            sensor_noise=sensor_noise,
        )
        for seed in seed_tuple
    ]
    strategies = tuple(outcome.strategy for outcome in runs[0].outcomes)
    if reference_strategy not in strategies:
        raise ValueError(f"unknown reference strategy: {reference_strategy}")

    by_strategy: dict[str, list[SecondLookOutcome]] = {name: [] for name in strategies}
    for run in runs:
        current = {outcome.strategy: outcome for outcome in run.outcomes}
        if tuple(current) != strategies:
            raise ValueError("second-look strategy set changed across paired seeds")
        for strategy in strategies:
            by_strategy[strategy].append(current[strategy])

    summaries: dict[str, EvidenceStrategySummary] = {}
    for strategy, outcomes in by_strategy.items():
        metrics: dict[str, EvidenceMetricSummary] = {}
        for metric in EVIDENCE_METRICS:
            values = [
                value for outcome in outcomes if (value := _metric(outcome, metric)) is not None
            ]
            metrics[metric] = _summary(values)
        summaries[strategy] = EvidenceStrategySummary(
            strategy=strategy,
            runs=len(outcomes),
            metrics=metrics,
        )

    paired: dict[str, dict[str, EvidencePairedDelta]] = {}
    reference = by_strategy[reference_strategy]
    for strategy in strategies:
        if strategy == reference_strategy:
            continue
        strategy_deltas: dict[str, EvidencePairedDelta] = {}
        for metric in EVIDENCE_METRICS:
            values: list[float] = []
            for candidate, baseline in zip(by_strategy[strategy], reference):
                candidate_value = _metric(candidate, metric)
                baseline_value = _metric(baseline, metric)
                if candidate_value is None or baseline_value is None:
                    continue
                values.append(candidate_value - baseline_value)
            summary = _summary(values)
            strategy_deltas[metric] = EvidencePairedDelta(
                metric=metric,
                strategy=strategy,
                reference=reference_strategy,
                mean=summary.mean,
                stdev=summary.stdev,
                minimum=summary.minimum,
                maximum=summary.maximum,
                direction_agreement=_direction_agreement(values),
                pairs=len(values),
            )
        paired[strategy] = strategy_deltas

    return ReplicatedEvidenceStudy(
        seeds=seed_tuple,
        strategies=strategies,
        reference_strategy=reference_strategy,
        summaries=summaries,
        paired_vs_reference=paired,
        budgets=tuple(run.budget for run in runs),
        budgets_per_1000=tuple(run.budget_per_1000 for run in runs),
    )
