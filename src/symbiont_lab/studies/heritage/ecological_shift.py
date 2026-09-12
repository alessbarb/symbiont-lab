from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from statistics import mean, pstdev
from typing import Iterable

from symbiont.core.collective import CollectiveMemory
from symbiont.core.heritage import SpeciesHeritage, apply_heritage, distill_heritage
from symbiont.simulation import EventContext, SimulationResult, _run_population, run_simulation


@dataclass(slots=True, frozen=True)
class EcologyComparison:
    source_seed: int
    target_seed: int
    source_threat_rate: float
    target_threat_rate: float
    source_patterns: int
    world_digest: str
    global_attention_delta: float | None
    global_classification_delta: float | None
    global_false_positive_delta: float | None
    global_brier_delta: float
    global_high_confidence_miss_delta: float
    warmup_attention_delta: float | None
    warmup_classification_delta: float | None
    warmup_false_positive_delta: float | None
    post_warmup_attention_delta: float | None
    post_warmup_classification_delta: float | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class EcologyMetricSummary:
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    direction_agreement: float | None
    pairs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class EcologyRateSummary:
    target_threat_rate: float
    comparisons: int
    metrics: dict[str, EcologyMetricSummary]

    def as_dict(self) -> dict[str, object]:
        return {
            "target_threat_rate": self.target_threat_rate,
            "comparisons": self.comparisons,
            "metrics": {name: value.as_dict() for name, value in self.metrics.items()},
        }


@dataclass(slots=True, frozen=True)
class EcologyHeritageStudy:
    source_seeds: tuple[int, ...]
    target_seeds: tuple[int, ...]
    source_threat_rate: float
    target_threat_rates: tuple[float, ...]
    target_offset: int
    comparisons: tuple[EcologyComparison, ...]
    summaries: dict[float, EcologyRateSummary]

    def as_dict(self) -> dict[str, object]:
        return {
            "source_seeds": self.source_seeds,
            "target_seeds": self.target_seeds,
            "source_threat_rate": self.source_threat_rate,
            "target_threat_rates": self.target_threat_rates,
            "target_offset": self.target_offset,
            "comparisons": [item.as_dict() for item in self.comparisons],
            "summaries": {
                str(rate): summary.as_dict() for rate, summary in self.summaries.items()
            },
        }


_METRICS = (
    "global_attention_delta",
    "global_classification_delta",
    "global_false_positive_delta",
    "global_brier_delta",
    "global_high_confidence_miss_delta",
    "warmup_attention_delta",
    "warmup_classification_delta",
    "warmup_false_positive_delta",
    "post_warmup_attention_delta",
    "post_warmup_classification_delta",
)


def _delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _digest_event(digest, event: EventContext) -> None:
    vector = ",".join(f"{value:.12f}" for value in event.observation.vector())
    digest.update(
        (
            f"{event.step}|{event.host_index}|{event.truth_label}|{event.phase}|"
            f"{event.drift_state}|{vector}\n"
        ).encode("utf-8")
    )


def _phase(result: SimulationResult, name: str) -> dict[str, object]:
    phases = result.evaluation_breakdown.get("phases", {})
    value = phases.get(name)
    return value if isinstance(value, dict) else {}


def _post_warmup(result: SimulationResult, metric: str) -> float | None:
    phases = result.evaluation_breakdown.get("phases", {})
    if metric == "attention_recall":
        numerator_key, denominator_key = "attention_tp", "threats"
    elif metric == "classification_recall":
        numerator_key, denominator_key = "classification_tp", "threats"
    else:
        raise ValueError(f"unsupported post-warmup metric: {metric}")

    numerator = 0
    denominator = 0
    for phase_name, payload in phases.items():
        if phase_name == "warmup" or not isinstance(payload, dict):
            continue
        numerator += int(payload.get(numerator_key, 0))
        denominator += int(payload.get(denominator_key, 0))
    return numerator / denominator if denominator else None


def _run_target(
    *,
    seed: int,
    hosts: int,
    steps: int,
    threat_rate: float,
    poison_fraction: float,
    heterogeneity: float,
    heritage: SpeciesHeritage | None,
) -> tuple[SimulationResult, str]:
    digest = sha256()

    def capture(event: EventContext) -> None:
        _digest_event(digest, event)

    common = dict(
        hosts=hosts,
        steps=steps,
        seed=seed,
        threat_rate=threat_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        drift_step=steps + 1,
        drift_fraction=0.0,
        drift_magnitude=0.0,
        on_event=capture,
    )

    if heritage is None:
        result, _ = run_simulation(**common)
    else:
        collective = CollectiveMemory()
        apply_heritage(collective, heritage)
        result, _ = _run_population(
            **common,
            collective=collective,
        )
    return result, digest.hexdigest()


def _comparison(
    *,
    source_seed: int,
    target_seed: int,
    source_rate: float,
    target_rate: float,
    heritage: SpeciesHeritage,
    hosts: int,
    steps: int,
    poison_fraction: float,
    heterogeneity: float,
) -> EcologyComparison:
    inherited, inherited_digest = _run_target(
        seed=target_seed,
        hosts=hosts,
        steps=steps,
        threat_rate=target_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        heritage=heritage,
    )
    naive, naive_digest = _run_target(
        seed=target_seed,
        hosts=hosts,
        steps=steps,
        threat_rate=target_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        heritage=None,
    )
    if inherited_digest != naive_digest:
        raise RuntimeError("inherited and naive conditions did not receive the same target world")

    inherited_warmup = _phase(inherited, "warmup")
    naive_warmup = _phase(naive, "warmup")

    return EcologyComparison(
        source_seed=source_seed,
        target_seed=target_seed,
        source_threat_rate=source_rate,
        target_threat_rate=target_rate,
        source_patterns=len(heritage.patterns),
        world_digest=inherited_digest,
        global_attention_delta=_delta(inherited.attention_recall, naive.attention_recall),
        global_classification_delta=_delta(
            inherited.classification_recall,
            naive.classification_recall,
        ),
        global_false_positive_delta=_delta(
            inherited.attention_false_positive_rate,
            naive.attention_false_positive_rate,
        ),
        global_brier_delta=inherited.brier_score - naive.brier_score,
        global_high_confidence_miss_delta=(
            inherited.high_confidence_miss_rate - naive.high_confidence_miss_rate
        ),
        warmup_attention_delta=_delta(
            inherited_warmup.get("attention_recall"),
            naive_warmup.get("attention_recall"),
        ),
        warmup_classification_delta=_delta(
            inherited_warmup.get("classification_recall"),
            naive_warmup.get("classification_recall"),
        ),
        warmup_false_positive_delta=_delta(
            inherited_warmup.get("attention_false_positive_rate"),
            naive_warmup.get("attention_false_positive_rate"),
        ),
        post_warmup_attention_delta=_delta(
            _post_warmup(inherited, "attention_recall"),
            _post_warmup(naive, "attention_recall"),
        ),
        post_warmup_classification_delta=_delta(
            _post_warmup(inherited, "classification_recall"),
            _post_warmup(naive, "classification_recall"),
        ),
    )


def _summarize(values: list[float]) -> EcologyMetricSummary:
    if not values:
        return EcologyMetricSummary(None, None, None, None, None, 0)
    avg = mean(values)
    if abs(avg) < 1e-12:
        agreement = sum(abs(value) < 1e-12 for value in values) / len(values)
    elif avg > 0:
        agreement = sum(value > 0 for value in values) / len(values)
    else:
        agreement = sum(value < 0 for value in values) / len(values)
    return EcologyMetricSummary(
        mean=avg,
        stdev=pstdev(values) if len(values) > 1 else 0.0,
        minimum=min(values),
        maximum=max(values),
        direction_agreement=agreement,
        pairs=len(values),
    )


def run_ecological_shift_study(
    *,
    source_seeds: Iterable[int] = (307, 331, 353, 379, 401),
    source_threat_rate: float = 0.018,
    target_threat_rates: Iterable[float] = (0.006, 0.018, 0.054),
    target_offset: int = 4001,
    hosts: int = 100,
    steps: int = 300,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    heritage_limit: int = 24,
) -> EcologyHeritageStudy:
    """Measure when inherited abstract priors help or hurt after prevalence shift.

    The source generation learns at ``source_threat_rate``. Each paired target
    condition receives the exact same synthetic world with and without inherited
    priors. Internal regime drift is disabled so the deliberate intervention is
    only the source-to-target threat prevalence change.
    """
    sources = tuple(int(seed) for seed in source_seeds)
    rates = tuple(float(rate) for rate in target_threat_rates)
    if not sources:
        raise ValueError("ecological heritage study requires at least one source seed")
    if len(sources) > 50:
        raise ValueError("ecological heritage study is limited to 50 source seeds")
    if len(set(sources)) != len(sources):
        raise ValueError("ecological heritage source seeds must be unique")
    if not rates:
        raise ValueError("provide at least one target threat rate")
    if len(rates) > 20:
        raise ValueError("ecological heritage study is limited to 20 target rates")
    if len(set(rates)) != len(rates):
        raise ValueError("target threat rates must be unique")
    if not 0.0 <= source_threat_rate <= 1.0 or any(not 0.0 <= rate <= 1.0 for rate in rates):
        raise ValueError("threat rates must be between 0 and 1")
    if target_offset == 0:
        raise ValueError("target_offset must separate source and target worlds")
    if heritage_limit < 0:
        raise ValueError("heritage_limit must be non-negative")

    targets = tuple(seed + int(target_offset) for seed in sources)
    if any(seed < 0 for seed in targets):
        raise ValueError("target_offset must produce non-negative target seeds")
    if set(targets) & set(sources):
        raise ValueError("target_offset must not make any target seed collide with a source seed")

    comparisons: list[EcologyComparison] = []
    for source_seed, target_seed in zip(sources, targets):
        _, source_collective = run_simulation(
            hosts=hosts,
            steps=steps,
            seed=source_seed,
            threat_rate=source_threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=steps + 1,
            drift_fraction=0.0,
            drift_magnitude=0.0,
        )
        heritage = distill_heritage(
            source_collective,
            generation=1,
            max_patterns=heritage_limit,
        )
        for target_rate in rates:
            comparisons.append(
                _comparison(
                    source_seed=source_seed,
                    target_seed=target_seed,
                    source_rate=source_threat_rate,
                    target_rate=target_rate,
                    heritage=heritage,
                    hosts=hosts,
                    steps=steps,
                    poison_fraction=poison_fraction,
                    heterogeneity=heterogeneity,
                )
            )

    summaries: dict[float, EcologyRateSummary] = {}
    for target_rate in rates:
        rows = [row for row in comparisons if row.target_threat_rate == target_rate]
        metric_summaries: dict[str, EcologyMetricSummary] = {}
        for metric in _METRICS:
            values = [
                value
                for row in rows
                if (value := getattr(row, metric)) is not None
            ]
            metric_summaries[metric] = _summarize(values)
        summaries[target_rate] = EcologyRateSummary(
            target_threat_rate=target_rate,
            comparisons=len(rows),
            metrics=metric_summaries,
        )

    return EcologyHeritageStudy(
        source_seeds=sources,
        target_seeds=targets,
        source_threat_rate=float(source_threat_rate),
        target_threat_rates=rates,
        target_offset=int(target_offset),
        comparisons=tuple(comparisons),
        summaries=summaries,
    )
