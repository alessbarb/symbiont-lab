from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.environment.rng import derive_seed
from symbiont.simulation import EventContext, run_simulation
from symbiont_lab.studies.common.causal_selection import (
    online_indices as _causal_online_indices,
)

from .retrospective import (
    BENIGN_FAMILIES,
    THREAT_FAMILIES,
    _rate,
    _score_events,
    _ScoredEvent,
)

STRATEGIES = ("risk", "novelty", "risk_novelty", "random")
NOVELTY_MIN_HISTORY = 6


@dataclass(slots=True, frozen=True)
class CausalSelection:
    strategy: str
    budget: int
    selected: int
    forced_selections: int
    zero_score_selections: int
    budget_utilization: float | None
    threat_recall: float | None
    precision: float | None
    benign_false_positive_rate: float | None
    stealth_recall: float | None
    family_recall: dict[str, float | None]
    selected_by_family: dict[str, int]
    selected_by_phase: dict[str, int]

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
    eligible_events: int
    outcomes: tuple[CausalSelection, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "hosts": self.hosts,
            "steps": self.steps,
            "budget": self.budget,
            "budget_per_1000": self.budget_per_1000,
            "events": self.events,
            "eligible_events": self.eligible_events,
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


def _common_eligible(item: _ScoredEvent) -> bool:
    """Use one startup eligibility rule for every compared selector."""
    if item.event is None:
        return True
    return not (item.event.phase == "warmup" and item.event.step < NOVELTY_MIN_HISTORY)


def _online_indices(
    scored: list[_ScoredEvent],
    *,
    strategy: str,
    budget: int,
) -> tuple[list[int], int]:
    """Select causally while preserving the v0.24 eligibility and thresholds."""
    if strategy not in STRATEGIES:
        raise ValueError(f"unsupported causal attention strategy: {strategy}")
    fallbacks = {
        "risk": 0.43,
        "novelty": 0.35,
        "risk_novelty": 0.43,
        "random": 0.0,
    }
    return _causal_online_indices(
        scored,
        budget=budget,
        score=lambda item: _score(item, strategy),
        eligible=_common_eligible,
        tie_break=lambda item: item.random_score,
        fallback=fallbacks[strategy],
        random_mode=strategy == "random",
    )


def _selection(
    strategy: str,
    events: list[EventContext],
    scored: list[_ScoredEvent],
    selected_indices: Iterable[int],
    budget: int,
    forced: int,
) -> CausalSelection:
    indices = list(selected_indices)
    chosen = [events[index] for index in indices]
    threat_total = sum(event.is_threat for event in events)
    benign_total = len(events) - threat_total
    chosen_threats = sum(event.is_threat for event in chosen)
    chosen_benign = len(chosen) - chosen_threats

    totals_by_family: dict[str, int] = {}
    selected_by_family: dict[str, int] = {}
    selected_by_phase: dict[str, int] = {}
    for event in events:
        totals_by_family[event.truth_label] = totals_by_family.get(event.truth_label, 0) + 1
    for event in chosen:
        selected_by_family[event.truth_label] = selected_by_family.get(event.truth_label, 0) + 1
        selected_by_phase[event.phase] = selected_by_phase.get(event.phase, 0) + 1

    family_recall = {
        family: _rate(selected_by_family.get(family, 0), totals_by_family.get(family, 0))
        for family in THREAT_FAMILIES
    }
    zero_scores = sum(abs(_score(scored[index], strategy)) <= 1e-12 for index in indices)
    return CausalSelection(
        strategy=strategy,
        budget=budget,
        selected=len(chosen),
        forced_selections=forced,
        zero_score_selections=zero_scores,
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
        selected_by_phase=selected_by_phase,
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
    eligible_events = sum(_common_eligible(item) for item in scored)
    requested_budget = round(len(events) * budget_per_1000 / 1000.0)
    budget = min(eligible_events, max(0, requested_budget))

    outcomes: list[CausalSelection] = []
    for strategy in STRATEGIES:
        indices, forced = _online_indices(scored, strategy=strategy, budget=budget)
        outcomes.append(_selection(strategy, events, scored, indices, budget, forced))

    return CausalBudgetAnalysis(
        seed=seed,
        hosts=hosts,
        steps=steps,
        budget=budget,
        budget_per_1000=budget_per_1000,
        events=len(events),
        eligible_events=eligible_events,
        outcomes=tuple(outcomes),
    )
