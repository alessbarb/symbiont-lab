from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, pstdev
from typing import Iterable

from .causal import CausalSelection, STRATEGIES, run_causal_attention_budget


CAUSAL_METRICS = (
    "threat_recall",
    "precision",
    "benign_false_positive_rate",
    "stealth_recall",
    "forced_share",
)


@dataclass(slots=True, frozen=True)
class CausalMetricSummary:
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    defined_runs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class CausalPairedDelta:
    budget_per_1000: float
    strategy: str
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
class CausalStrategySummary:
    budget_per_1000: float
    strategy: str
    runs: int
    metrics: dict[str, CausalMetricSummary]

    def as_dict(self) -> dict[str, object]:
        return {
            "budget_per_1000": self.budget_per_1000,
            "strategy": self.strategy,
            "runs": self.runs,
            "metrics": {name: value.as_dict() for name, value in self.metrics.items()},
        }


@dataclass(slots=True, frozen=True)
class ReplicatedCausalBudgetStudy:
    seeds: tuple[int, ...]
    budgets_per_1000: tuple[float, ...]
    strategies: tuple[str, ...]
    reference_strategy: str
    summaries: dict[float, dict[str, CausalStrategySummary]]
    paired_vs_reference: dict[float, dict[str, dict[str, CausalPairedDelta]]]
    absolute_budgets: dict[float, tuple[int, ...]]

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": self.seeds,
            "budgets_per_1000": self.budgets_per_1000,
            "strategies": self.strategies,
            "reference_strategy": self.reference_strategy,
            "summaries": {
                str(budget): {
                    strategy: summary.as_dict()
                    for strategy, summary in strategies.items()
                }
                for budget, strategies in self.summaries.items()
            },
            "paired_vs_reference": {
                str(budget): {
                    strategy: {
                        metric: delta.as_dict()
                        for metric, delta in metrics.items()
                    }
                    for strategy, metrics in strategies.items()
                }
                for budget, strategies in self.paired_vs_reference.items()
            },
            "absolute_budgets": {
                str(budget): values
                for budget, values in self.absolute_budgets.items()
            },
        }


def _metric(row: CausalSelection, name: str) -> float | None:
    if name == "forced_share":
        return row.forced_selections / row.selected if row.selected else None
    value = getattr(row, name)
    return None if value is None else float(value)


def _summary(values: list[float]) -> CausalMetricSummary:
    if not values:
        return CausalMetricSummary(None, None, None, None, 0)
    return CausalMetricSummary(
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


def run_replicated_causal_budget_study(
    *,
    seeds: Iterable[int] = (101, 127, 149, 173, 199),
    budgets_per_1000: Iterable[float] = (5.0, 12.0, 20.0),
    hosts: int = 100,
    steps: int = 300,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    reference_strategy: str = "random",
) -> ReplicatedCausalBudgetStudy:
    seed_tuple = tuple(int(seed) for seed in seeds)
    budget_tuple = tuple(float(value) for value in budgets_per_1000)

    if not seed_tuple:
        raise ValueError("replicated causal budget study requires at least one seed")
    if len(seed_tuple) > 50:
        raise ValueError("replicated causal budget studies are limited to 50 seeds")
    if len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("replicated causal budget study seeds must be unique")
    if not budget_tuple:
        raise ValueError("provide at least one causal attention budget")
    if len(budget_tuple) > 20:
        raise ValueError("replicated causal budget studies are limited to 20 budgets")
    if len(set(budget_tuple)) != len(budget_tuple):
        raise ValueError("causal attention budgets must be unique")
    if any(value < 0 for value in budget_tuple):
        raise ValueError("causal attention budgets must be non-negative")
    if reference_strategy not in STRATEGIES:
        raise ValueError(f"unknown reference strategy: {reference_strategy}")

    by_budget: dict[float, dict[str, list[CausalSelection]]] = {
        budget: {strategy: [] for strategy in STRATEGIES}
        for budget in budget_tuple
    }
    absolute_budgets: dict[float, list[int]] = {budget: [] for budget in budget_tuple}

    for budget in budget_tuple:
        for seed in seed_tuple:
            run = run_causal_attention_budget(
                hosts=hosts,
                steps=steps,
                seed=seed,
                threat_rate=threat_rate,
                poison_fraction=poison_fraction,
                heterogeneity=heterogeneity,
                drift_step=drift_step,
                drift_fraction=drift_fraction,
                drift_magnitude=drift_magnitude,
                budget_per_1000=budget,
            )
            current = {row.strategy: row for row in run.outcomes}
            if tuple(current) != STRATEGIES:
                raise ValueError("causal strategy set changed across paired runs")
            if len({row.selected for row in run.outcomes}) != 1:
                raise RuntimeError("causal strategies did not receive equal capacity")
            absolute_budgets[budget].append(run.budget)
            for strategy in STRATEGIES:
                by_budget[budget][strategy].append(current[strategy])

    summaries: dict[float, dict[str, CausalStrategySummary]] = {}
    paired: dict[float, dict[str, dict[str, CausalPairedDelta]]] = {}

    for budget in budget_tuple:
        summaries[budget] = {}
        for strategy, outcomes in by_budget[budget].items():
            metrics: dict[str, CausalMetricSummary] = {}
            for metric in CAUSAL_METRICS:
                values = [
                    value
                    for outcome in outcomes
                    if (value := _metric(outcome, metric)) is not None
                ]
                metrics[metric] = _summary(values)
            summaries[budget][strategy] = CausalStrategySummary(
                budget_per_1000=budget,
                strategy=strategy,
                runs=len(outcomes),
                metrics=metrics,
            )

        paired[budget] = {}
        reference = by_budget[budget][reference_strategy]
        for strategy in STRATEGIES:
            if strategy == reference_strategy:
                continue
            metric_deltas: dict[str, CausalPairedDelta] = {}
            for metric in CAUSAL_METRICS:
                values: list[float] = []
                for candidate, baseline in zip(by_budget[budget][strategy], reference):
                    candidate_value = _metric(candidate, metric)
                    baseline_value = _metric(baseline, metric)
                    if candidate_value is None or baseline_value is None:
                        continue
                    values.append(candidate_value - baseline_value)
                summary = _summary(values)
                metric_deltas[metric] = CausalPairedDelta(
                    budget_per_1000=budget,
                    strategy=strategy,
                    reference=reference_strategy,
                    metric=metric,
                    mean=summary.mean,
                    stdev=summary.stdev,
                    minimum=summary.minimum,
                    maximum=summary.maximum,
                    direction_agreement=_direction_agreement(values),
                    pairs=len(values),
                )
            paired[budget][strategy] = metric_deltas

    return ReplicatedCausalBudgetStudy(
        seeds=seed_tuple,
        budgets_per_1000=budget_tuple,
        strategies=STRATEGIES,
        reference_strategy=reference_strategy,
        summaries=summaries,
        paired_vs_reference=paired,
        absolute_budgets={budget: tuple(values) for budget, values in absolute_budgets.items()},
    )


run_causal_budget_study = run_replicated_causal_budget_study
