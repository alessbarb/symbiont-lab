from __future__ import annotations

from dataclasses import asdict, dataclass
from math import floor
from typing import Iterable

from .budget import (
    BENIGN_FAMILIES,
    THREAT_FAMILIES,
    _ScoredEvent,
    _rate,
    _score_events,
)
from .rng import derive_seed
from .simulation import EventContext, run_simulation


STRATEGIES = ("risk", "novelty", "risk_novelty", "random")


@dataclass(slots=True, frozen=True)
class CausalSelection:
    strategy: str
    budget: int
    selected: int
    forced_selections: int
    budget_utilization: float | None
    threat_recall: float | None
    precision: float | None
    benign_false_positive_rate: float | None
    stealth_recall: float | None
    family_recall: dict[str, float | None]
    selected_by_family: dict[str, int]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class CausalBudgetAnalysis:
    seed: int
    hosts: int
    steps: int
    budget: int
    budget_per_1000: float
    events: int
    outcomes: tuple[CausalSelection, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "hosts": self.hosts,
            "steps": self.steps,
            "budget": self.budget,
            "budget_per_1000": self.budget_per_1000,
            "events": self.events,
            "outcomes": [outcome.as_dict() for outcome in self.outcomes],
        }


def _score(item: _ScoredEvent, strategy: str) -> float:
    if strategy == "risk":
        return item.risk
    if strategy == "novelty":
        return item.novelty
    if strategy == "risk_novelty":
        return item.risk_novelty
    if strategy == "random":
        return item.random_score
    raise ValueError(f"unsupported causal attention strategy: {strategy}")


def _historical_threshold(history: list[float], target_rate: float, fallback: float) -> float:
    """Estimate a score cutoff using only scores observed before the current event."""
    if len(history) < 32:
        return fallback
    ordered = sorted(history)
    quantile = min(max(1.0 - target_rate, 0.0), 1.0)
    index = min(len(ordered) - 1, max(0, floor(quantile * (len(ordered) - 1))))
    return ordered[index]


def _online_indices(
    scored: list[_ScoredEvent],
    *,
    strategy: str,
    budget: int,
) -> tuple[list[int], int]:
    """Irrevocably select event indices without reading future scores.

    Total stream length and the ex-ante budget are known. Score-based strategies
    estimate their cutoff from historical scores only. The final quota guard is
    causal: if remaining budget equals remaining events, every remaining event
    must be selected to honor the precommitted budget.
    """
    total = len(scored)
    budget = min(max(int(budget), 0), total)
    if budget == 0:
        return [], 0

    fallbacks = {
        "risk": 0.43,
        "novelty": 0.35,
        "risk_novelty": 0.43,
    }
    history: list[float] = []
    selected: list[int] = []
    forced = 0

    for index, item in enumerate(scored):
        remaining_budget = budget - len(selected)
        if remaining_budget <= 0:
            break
        remaining_events = total - index
        must_take = remaining_budget >= remaining_events
        score = _score(item, strategy)

        if must_take:
            take = True
            forced += 1
        elif strategy == "random":
            # random_score is independent and deterministic per stream position.
            take = score < remaining_budget / remaining_events
        else:
            target_rate = remaining_budget / remaining_events
            threshold = _historical_threshold(
                history,
                target_rate,
                fallbacks[strategy],
            )
            take = score >= threshold

        if take:
            selected.append(index)
        history.append(score)

    if len(selected) != budget:
        raise RuntimeError("causal selector failed to honor its ex-ante budget")
    return selected, forced


def _selection(
    strategy: str,
    events: list[EventContext],
    selected_indices: Iterable[int],
    budget: int,
    forced: int,
) -> CausalSelection:
    chosen = [events[index] for index in selected_indices]
    threat_total = sum(event.is_threat for event in events)
    benign_total = len(events) - threat_total
    chosen_threats = sum(event.is_threat for event in chosen)
    chosen_benign = len(chosen) - chosen_threats

    totals_by_family: dict[str, int] = {}
    selected_by_family: dict[str, int] = {}
    for event in events:
        totals_by_family[event.truth_label] = totals_by_family.get(event.truth_label, 0) + 1
    for event in chosen:
        selected_by_family[event.truth_label] = selected_by_family.get(event.truth_label, 0) + 1

    family_recall = {
        family: _rate(selected_by_family.get(family, 0), totals_by_family.get(family, 0))
        for family in THREAT_FAMILIES
    }
    return CausalSelection(
        strategy=strategy,
        budget=budget,
        selected=len(chosen),
        forced_selections=forced,
        budget_utilization=_rate(len(chosen), budget),
        threat_recall=_rate(chosen_threats, threat_total),
        precision=_rate(chosen_threats, len(chosen)),
        benign_false_positive_rate=_rate(chosen_benign, benign_total),
        stealth_recall=family_recall["pathogen:stealth_sim"],
        family_recall=family_recall,
        selected_by_family={
            family: selected_by_family.get(family, 0)
            for family in (*BENIGN_FAMILIES, *THREAT_FAMILIES)
        },
    )


def run_causal_attention_budget(
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
    budget_per_1000: float = 12.0,
) -> CausalBudgetAnalysis:
    if budget_per_1000 < 0:
        raise ValueError("budget_per_1000 must be non-negative")

    events: list[EventContext] = []
    run_simulation(
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
    scored = _score_events(events, derive_seed(seed, "causal-attention-scores"))
    budget = min(len(events), round(len(events) * budget_per_1000 / 1000.0))

    outcomes: list[CausalSelection] = []
    for strategy in STRATEGIES:
        indices, forced = _online_indices(scored, strategy=strategy, budget=budget)
        outcomes.append(_selection(strategy, events, indices, budget, forced))

    return CausalBudgetAnalysis(
        seed=seed,
        hosts=hosts,
        steps=steps,
        budget=budget,
        budget_per_1000=budget_per_1000,
        events=len(events),
        outcomes=tuple(outcomes),
    )
