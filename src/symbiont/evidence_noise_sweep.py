from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, pstdev
from typing import Iterable

from .evidence import SecondLookOutcome, run_second_look_study


NOISE_METRICS = (
    "brier_gain",
    "net_correction_rate",
    "mean_entropy_reduction",
    "stealth_correction_rate",
)


@dataclass(slots=True, frozen=True)
class NoiseMetricSummary:
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    positive_fraction: float | None
    defined_runs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class NoiseStrategySummary:
    noise: float
    strategy: str
    runs: int
    metrics: dict[str, NoiseMetricSummary]

    def as_dict(self) -> dict[str, object]:
        return {
            "noise": self.noise,
            "strategy": self.strategy,
            "runs": self.runs,
            "metrics": {name: value.as_dict() for name, value in self.metrics.items()},
        }


@dataclass(slots=True, frozen=True)
class NoisePairedDelta:
    strategy: str
    noise: float
    reference_noise: float
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
class EvidenceNoiseSweep:
    seeds: tuple[int, ...]
    noise_levels: tuple[float, ...]
    budget: int
    budget_per_1000: float
    strategies: tuple[str, ...]
    summaries: dict[float, dict[str, NoiseStrategySummary]]
    paired_vs_lowest_noise: dict[float, dict[str, dict[str, NoisePairedDelta]]]

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": self.seeds,
            "noise_levels": self.noise_levels,
            "budget": self.budget,
            "budget_per_1000": self.budget_per_1000,
            "strategies": self.strategies,
            "summaries": {
                str(noise): {
                    strategy: summary.as_dict()
                    for strategy, summary in strategies.items()
                }
                for noise, strategies in self.summaries.items()
            },
            "paired_vs_lowest_noise": {
                str(noise): {
                    strategy: {
                        metric: delta.as_dict()
                        for metric, delta in metrics.items()
                    }
                    for strategy, metrics in strategies.items()
                }
                for noise, strategies in self.paired_vs_lowest_noise.items()
            },
        }


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _metric(outcome: SecondLookOutcome, name: str) -> float | None:
    if name == "brier_gain":
        return outcome.brier_gain
    if name == "net_correction_rate":
        return _rate(outcome.corrected_errors - outcome.introduced_errors, outcome.selected)
    if name == "mean_entropy_reduction":
        return outcome.mean_entropy_reduction
    if name == "stealth_correction_rate":
        return _rate(outcome.stealth_corrected, outcome.stealth_selected)
    raise ValueError(f"unsupported noise metric: {name}")


def _summary(values: list[float]) -> NoiseMetricSummary:
    if not values:
        return NoiseMetricSummary(None, None, None, None, None, 0)
    return NoiseMetricSummary(
        mean=mean(values),
        stdev=pstdev(values) if len(values) > 1 else 0.0,
        minimum=min(values),
        maximum=max(values),
        positive_fraction=sum(value > 0 for value in values) / len(values),
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


def run_evidence_noise_sweep(
    *,
    seeds: Iterable[int] = (211, 223, 239, 251, 269),
    noise_levels: Iterable[float] = (0.08, 0.18, 0.30, 0.45),
    hosts: int = 100,
    steps: int = 300,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    budget_per_1000: float = 12.0,
) -> EvidenceNoiseSweep:
    seed_tuple = tuple(int(seed) for seed in seeds)
    noise_tuple = tuple(float(level) for level in noise_levels)
    if not seed_tuple:
        raise ValueError("noise sweep requires at least one seed")
    if len(seed_tuple) > 50:
        raise ValueError("noise sweep is limited to 50 seeds")
    if len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("noise sweep seeds must be unique")
    if not noise_tuple:
        raise ValueError("noise sweep requires at least one level")
    if len(noise_tuple) > 20:
        raise ValueError("noise sweep is limited to 20 levels")
    if len(set(noise_tuple)) != len(noise_tuple):
        raise ValueError("noise levels must be unique")
    if any(level < 0.01 for level in noise_tuple):
        raise ValueError("noise levels must be at least 0.01")
    if budget_per_1000 < 0:
        raise ValueError("budget_per_1000 must be non-negative")

    noise_tuple = tuple(sorted(noise_tuple))
    total_events = hosts * steps
    budget = min(total_events, round(total_events * budget_per_1000 / 1000.0))

    by_noise: dict[float, dict[str, list[SecondLookOutcome]]] = {}
    expected_strategies: tuple[str, ...] | None = None
    pre_brier_by_seed_strategy: dict[tuple[int, str], float | None] = {}
    selected_by_seed_strategy: dict[tuple[int, str], int] = {}

    for noise in noise_tuple:
        by_noise[noise] = {}
        for seed in seed_tuple:
            run = run_second_look_study(
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
                sensor_noise=noise,
            )
            current = {outcome.strategy: outcome for outcome in run.outcomes}
            strategies = tuple(current)
            if expected_strategies is None:
                expected_strategies = strategies
                for strategy in strategies:
                    by_noise[noise][strategy] = []
            elif strategies != expected_strategies:
                raise ValueError("second-look strategy set changed across noise sweep")
            for strategy in strategies:
                by_noise[noise].setdefault(strategy, []).append(current[strategy])
                key = (seed, strategy)
                previous_selected = selected_by_seed_strategy.setdefault(key, current[strategy].selected)
                previous_pre = pre_brier_by_seed_strategy.setdefault(key, current[strategy].pre_brier)
                if current[strategy].selected != previous_selected:
                    raise RuntimeError("sensor noise changed the selected evidence set")
                if current[strategy].pre_brier != previous_pre:
                    raise RuntimeError("sensor noise changed pre-measurement evidence selection")

    strategies = expected_strategies or ()
    summaries: dict[float, dict[str, NoiseStrategySummary]] = {}
    for noise in noise_tuple:
        summaries[noise] = {}
        for strategy in strategies:
            outcomes = by_noise[noise][strategy]
            metrics: dict[str, NoiseMetricSummary] = {}
            for metric in NOISE_METRICS:
                values = [
                    value
                    for outcome in outcomes
                    if (value := _metric(outcome, metric)) is not None
                ]
                metrics[metric] = _summary(values)
            summaries[noise][strategy] = NoiseStrategySummary(
                noise=noise,
                strategy=strategy,
                runs=len(outcomes),
                metrics=metrics,
            )

    reference_noise = noise_tuple[0]
    paired: dict[float, dict[str, dict[str, NoisePairedDelta]]] = {}
    reference = by_noise[reference_noise]
    for noise in noise_tuple[1:]:
        paired[noise] = {}
        for strategy in strategies:
            paired[noise][strategy] = {}
            for metric in NOISE_METRICS:
                values: list[float] = []
                for candidate, baseline in zip(by_noise[noise][strategy], reference[strategy]):
                    candidate_value = _metric(candidate, metric)
                    baseline_value = _metric(baseline, metric)
                    if candidate_value is None or baseline_value is None:
                        continue
                    values.append(candidate_value - baseline_value)
                summary = _summary(values)
                paired[noise][strategy][metric] = NoisePairedDelta(
                    strategy=strategy,
                    noise=noise,
                    reference_noise=reference_noise,
                    metric=metric,
                    mean=summary.mean,
                    stdev=summary.stdev,
                    minimum=summary.minimum,
                    maximum=summary.maximum,
                    direction_agreement=_direction_agreement(values),
                    pairs=len(values),
                )

    return EvidenceNoiseSweep(
        seeds=seed_tuple,
        noise_levels=noise_tuple,
        budget=budget,
        budget_per_1000=budget_per_1000,
        strategies=strategies,
        summaries=summaries,
        paired_vs_lowest_noise=paired,
    )
