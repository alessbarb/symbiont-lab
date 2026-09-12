from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
import random
from typing import Iterable

from .rng import derive_seed
from .simulation import EventContext, SimulationResult, run_simulation


THREAT_FAMILIES = (
    "pathogen:ransom_sim",
    "pathogen:bot_sim",
    "pathogen:stealth_sim",
)

BENIGN_FAMILIES = (
    "benign:normal",
    "benign:update",
    "benign:backup",
    "benign:build",
)


@dataclass(slots=True, frozen=True)
class BudgetSelection:
    strategy: str
    selected: int
    events: int
    investigations_per_1000: float
    threat_recall: float | None
    precision: float | None
    benign_false_positive_rate: float | None
    stealth_recall: float | None
    family_recall: dict[str, float | None]
    selected_by_family: dict[str, int]
    benign_special_share: float | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class BudgetAnalysis:
    seed: int
    hosts: int
    steps: int
    natural_budget: int
    natural_budget_per_1000: float
    matched: tuple[BudgetSelection, ...]
    curves: dict[str, tuple[BudgetSelection, ...]]

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "hosts": self.hosts,
            "steps": self.steps,
            "natural_budget": self.natural_budget,
            "natural_budget_per_1000": self.natural_budget_per_1000,
            "matched": [item.as_dict() for item in self.matched],
            "curves": {
                name: [item.as_dict() for item in items]
                for name, items in self.curves.items()
            },
        }


@dataclass(slots=True)
class _WarmupStats:
    n: int = 0
    sums: list[float] | None = None
    sums_sq: list[float] | None = None

    def add(self, values: tuple[float, ...]) -> None:
        if self.sums is None:
            self.sums = [0.0] * len(values)
            self.sums_sq = [0.0] * len(values)
        assert self.sums_sq is not None
        self.n += 1
        for index, value in enumerate(values):
            self.sums[index] += value
            self.sums_sq[index] += value * value

    def novelty(self, values: tuple[float, ...]) -> float:
        if self.n < 6 or self.sums is None or self.sums_sq is None:
            return 0.0
        z_scores: list[float] = []
        for index, value in enumerate(values):
            mean = self.sums[index] / self.n
            variance = max(self.sums_sq[index] / self.n - mean * mean, 0.0)
            std = max(sqrt(variance), 0.12)
            z_scores.append(abs(value - mean) / std)
        return min(sum(min(score, 8.0) for score in z_scores) / len(z_scores) / 4.0, 1.0)


@dataclass(slots=True, frozen=True)
class _ScoredEvent:
    event: EventContext
    risk: float
    novelty: float
    random_score: float

    @property
    def risk_novelty(self) -> float:
        return min(1.0, 0.80 * self.risk + 0.20 * self.novelty)


def _raw_risk(event: EventContext) -> float:
    obs = event.observation
    return min(
        1.0,
        0.12 * obs.cpu
        + 0.18 * obs.network
        + 0.28 * obs.file_changes
        + 0.16 * obs.new_processes
        + 0.26 * obs.persistence_changes,
    )


def _score_events(events: list[EventContext], seed: int) -> list[_ScoredEvent]:
    warmup: dict[int, _WarmupStats] = {}
    random_rng = random.Random(derive_seed(seed, "attention-budget-random"))
    scored: list[_ScoredEvent] = []

    for event in events:
        stats = warmup.setdefault(event.host_index, _WarmupStats())
        vector = event.observation.vector()
        novelty = stats.novelty(vector)
        scored.append(
            _ScoredEvent(
                event=event,
                risk=_raw_risk(event),
                novelty=novelty,
                random_score=random_rng.random(),
            )
        )
        if event.phase == "warmup":
            stats.add(vector)

    return scored


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _selection_from_events(
    strategy: str,
    all_events: list[EventContext],
    selected_events: Iterable[EventContext],
) -> BudgetSelection:
    chosen = list(selected_events)
    threat_total = sum(event.is_threat for event in all_events)
    benign_total = len(all_events) - threat_total
    chosen_threats = sum(event.is_threat for event in chosen)
    chosen_benign = len(chosen) - chosen_threats

    totals_by_family: dict[str, int] = {}
    selected_by_family: dict[str, int] = {}
    for event in all_events:
        totals_by_family[event.truth_label] = totals_by_family.get(event.truth_label, 0) + 1
    for event in chosen:
        selected_by_family[event.truth_label] = selected_by_family.get(event.truth_label, 0) + 1

    family_recall = {
        family: _rate(selected_by_family.get(family, 0), totals_by_family.get(family, 0))
        for family in THREAT_FAMILIES
    }
    special_benign = sum(
        selected_by_family.get(family, 0)
        for family in ("benign:update", "benign:backup", "benign:build")
    )
    return BudgetSelection(
        strategy=strategy,
        selected=len(chosen),
        events=len(all_events),
        investigations_per_1000=1000.0 * len(chosen) / max(len(all_events), 1),
        threat_recall=_rate(chosen_threats, threat_total),
        precision=_rate(chosen_threats, len(chosen)),
        benign_false_positive_rate=_rate(chosen_benign, benign_total),
        stealth_recall=family_recall["pathogen:stealth_sim"],
        family_recall=family_recall,
        selected_by_family={
            family: selected_by_family.get(family, 0)
            for family in (*BENIGN_FAMILIES, *THREAT_FAMILIES)
        },
        benign_special_share=_rate(special_benign, len(chosen)),
    )


def _policy_selection(result: SimulationResult, total_events: int) -> BudgetSelection:
    breakdown = result.evaluation_breakdown
    families = dict(breakdown.get("families", {}))
    global_counts = dict(breakdown.get("global", {}))
    family_recall: dict[str, float | None] = {}
    selected_by_family: dict[str, int] = {}
    for family in (*BENIGN_FAMILIES, *THREAT_FAMILIES):
        metrics = dict(families.get(family, {}))
        selected_by_family[family] = int(metrics.get("investigated", 0) or 0)
        if family in THREAT_FAMILIES:
            value = metrics.get("attention_recall")
            family_recall[family] = None if value is None else float(value)

    special_benign = sum(
        selected_by_family.get(family, 0)
        for family in ("benign:update", "benign:backup", "benign:build")
    )
    return BudgetSelection(
        strategy="policy",
        selected=result.investigated,
        events=total_events,
        investigations_per_1000=1000.0 * result.investigated / max(total_events, 1),
        threat_recall=result.attention_recall,
        precision=result.attention_precision,
        benign_false_positive_rate=result.attention_false_positive_rate,
        stealth_recall=family_recall.get("pathogen:stealth_sim"),
        family_recall=family_recall,
        selected_by_family=selected_by_family,
        benign_special_share=_rate(special_benign, result.investigated),
    )


def _ranked_selection(
    strategy: str,
    scored: list[_ScoredEvent],
    budget: int,
) -> BudgetSelection:
    budget = min(max(int(budget), 0), len(scored))
    if strategy == "risk":
        key = lambda item: item.risk
    elif strategy == "novelty":
        key = lambda item: item.novelty
    elif strategy == "risk_novelty":
        key = lambda item: item.risk_novelty
    elif strategy == "random":
        key = lambda item: item.random_score
    else:
        raise ValueError(f"unsupported attention strategy: {strategy}")

    ranked = sorted(
        scored,
        key=lambda item: (key(item), -item.event.step, -item.event.host_index),
        reverse=True,
    )
    return _selection_from_events(
        strategy,
        [item.event for item in scored],
        [item.event for item in ranked[:budget]],
    )


def run_attention_budget_analysis(
    *,
    hosts: int = 100,
    steps: int = 300,
    seed: int = 7,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    curve_budgets_per_1000: tuple[float, ...] = (2.0, 5.0, 10.0, 20.0, 40.0),
) -> BudgetAnalysis:
    events: list[EventContext] = []
    result, _ = run_simulation(
        hosts=hosts,
        steps=steps,
        seed=seed,
        threat_rate=threat_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        drift_step=drift_step,
        drift_fraction=drift_fraction,
        drift_magnitude=drift_magnitude,
        on_event=events.append,
    )
    scored = _score_events(events, seed)
    natural_budget = result.investigated
    strategies = ("risk", "novelty", "risk_novelty", "random")

    matched = [_policy_selection(result, len(events))]
    matched.extend(
        _ranked_selection(strategy, scored, natural_budget)
        for strategy in strategies
    )

    curves: dict[str, tuple[BudgetSelection, ...]] = {}
    for strategy in strategies:
        points: list[BudgetSelection] = []
        for per_1000 in curve_budgets_per_1000:
            budget = round(len(events) * max(0.0, per_1000) / 1000.0)
            points.append(_ranked_selection(strategy, scored, budget))
        curves[strategy] = tuple(points)

    return BudgetAnalysis(
        seed=seed,
        hosts=hosts,
        steps=steps,
        natural_budget=natural_budget,
        natural_budget_per_1000=1000.0 * natural_budget / max(len(events), 1),
        matched=tuple(matched),
        curves=curves,
    )
