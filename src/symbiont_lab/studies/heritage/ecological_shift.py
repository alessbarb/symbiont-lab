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
    analysis_split_step: int
    world_digest: str
    global_attention_delta: float | None
    global_classification_delta: float | None
    global_false_positive_delta: float | None
    global_brier_delta: float
    global_high_confidence_miss_delta: float
    early_attention_delta: float | None
    early_classification_delta: float | None
    early_false_positive_delta: float | None
    late_attention_delta: float | None
    late_classification_delta: float | None
    late_false_positive_delta: float | None

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
    analysis_split_step: int
    comparisons: tuple[EcologyComparison, ...]
    summaries: dict[float, EcologyRateSummary]

    @property
    def world_digest(self) -> str:
        digest = sha256()
        for item in self.comparisons:
            digest.update(
                (
                    f"{item.source_seed}|{item.target_seed}|{item.target_threat_rate:.12f}|"
                    f"{item.world_digest}\n"
                ).encode("utf-8")
            )
        return digest.hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "source_seeds": self.source_seeds,
            "target_seeds": self.target_seeds,
            "source_threat_rate": self.source_threat_rate,
            "target_threat_rates": self.target_threat_rates,
            "target_offset": self.target_offset,
            "analysis_split_step": self.analysis_split_step,
            "world_digest": self.world_digest,
            "comparisons": [item.as_dict() for item in self.comparisons],
            "summaries": {str(rate): summary.as_dict() for rate, summary in self.summaries.items()},
        }


_METRICS = (
    "global_attention_delta",
    "global_classification_delta",
    "global_false_positive_delta",
    "global_brier_delta",
    "global_high_confidence_miss_delta",
    "early_attention_delta",
    "early_classification_delta",
    "early_false_positive_delta",
    "late_attention_delta",
    "late_classification_delta",
    "late_false_positive_delta",
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


def _metric(payload: dict[str, object], name: str) -> float | None:
    value = payload.get(name)
    return float(value) if isinstance(value, (int, float)) else None


def _analysis_split_step(steps: int) -> int:
    """Split the threat-eligible target lifetime into early and late windows.

    The simulator reserves steps 0..49 for threat-free model warmup. Reusing that
    phase as an "early heritage" metric would therefore make threat recall always
    undefined. The no-drift phase boundary is placed after warmup instead.
    """
    if steps <= 50:
        return steps + 1
    eligible = steps - 50
    return min(steps, 50 + max(1, eligible // 3))


def _run_target(
    *,
    seed: int,
    hosts: int,
    steps: int,
    threat_rate: float,
    poison_fraction: float,
    heterogeneity: float,
    heritage: SpeciesHeritage | None,
    split_step: int,
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
        drift_step=split_step,
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
    split_step: int,
) -> EcologyComparison:
    inherited, inherited_digest = _run_target(
        seed=target_seed,
        hosts=hosts,
        steps=steps,
        threat_rate=target_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        heritage=heritage,
        split_step=split_step,
    )
    naive, naive_digest = _run_target(
        seed=target_seed,
        hosts=hosts,
        steps=steps,
        threat_rate=target_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        heritage=None,
        split_step=split_step,
    )
    if inherited_digest != naive_digest:
        raise RuntimeError("inherited and naive conditions did not receive the same target world")

    inherited_early = _phase(inherited, "pre_drift")
    naive_early = _phase(naive, "pre_drift")
    inherited_late = _phase(inherited, "post_drift")
    naive_late = _phase(naive, "post_drift")

    return EcologyComparison(
        source_seed=source_seed,
        target_seed=target_seed,
        source_threat_rate=source_rate,
        target_threat_rate=target_rate,
        source_patterns=len(heritage.patterns),
        analysis_split_step=split_step,
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
        early_attention_delta=_delta(
            _metric(inherited_early, "attention_recall"),
            _metric(naive_early, "attention_recall"),
        ),
        early_classification_delta=_delta(
            _metric(inherited_early, "classification_recall"),
            _metric(naive_early, "classification_recall"),
        ),
        early_false_positive_delta=_delta(
            _metric(inherited_early, "attention_false_positive_rate"),
            _metric(naive_early, "attention_false_positive_rate"),
        ),
        late_attention_delta=_delta(
            _metric(inherited_late, "attention_recall"),
            _metric(naive_late, "attention_recall"),
        ),
        late_classification_delta=_delta(
            _metric(inherited_late, "classification_recall"),
            _metric(naive_late, "classification_recall"),
        ),
        late_false_positive_delta=_delta(
            _metric(inherited_late, "attention_false_positive_rate"),
            _metric(naive_late, "attention_false_positive_rate"),
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

    Each target condition is paired: inherited and naive populations receive the
    exact same synthetic world. No host-profile regime shift is applied; the
    deliberate ecological intervention is only source-to-target threat prevalence.
    The target threat-eligible lifetime is split into early and late windows so the
    initial value of heritage can be measured separately from later adaptation.
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

    split_step = _analysis_split_step(steps)
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
                    split_step=split_step,
                )
            )

    summaries: dict[float, EcologyRateSummary] = {}
    for target_rate in rates:
        rows = [row for row in comparisons if row.target_threat_rate == target_rate]
        metric_summaries: dict[str, EcologyMetricSummary] = {}
        for metric in _METRICS:
            values = [value for row in rows if (value := getattr(row, metric)) is not None]
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
        analysis_split_step=split_step,
        comparisons=tuple(comparisons),
        summaries=summaries,
    )
