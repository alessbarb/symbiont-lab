from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from ...host.acclimation import CapabilityBaseline, HostAcclimation


@dataclass(slots=True, frozen=True)
class AttentionCandidate:
    """One thing the organism could spend its bounded attention on this tick.

    ``uncertainty`` and ``cost`` are supplied by the caller — this module
    knows nothing about capabilities, percepts or hosts, only the selection
    problem itself, so it composes with any future attention source without
    modification (roadmap v0.38).
    """

    name: str
    uncertainty: float
    cost: float
    rank_cost: float = 1.0
    observations: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.cost, bool) or not math.isfinite(self.cost) or self.cost <= 0.0:
            raise ValueError("cost must be positive")
        if (
            isinstance(self.rank_cost, bool)
            or not math.isfinite(self.rank_cost)
            or self.rank_cost <= 0.0
        ):
            raise ValueError("rank_cost must be positive")
        # +inf is intentional: an unacclimated capability has no baseline and
        # must outrank every finite candidate. NaN (and -inf) is never a
        # meaningful uncertainty and would make sorting non-deterministic.
        if (
            isinstance(self.uncertainty, bool)
            or math.isnan(self.uncertainty)
            or self.uncertainty < 0.0
        ):
            raise ValueError("uncertainty must be non-negative")
        if (
            isinstance(self.observations, bool)
            or not isinstance(self.observations, int)
            or self.observations < 0
        ):
            raise ValueError("observations must be non-negative")


@dataclass(slots=True, frozen=True)
class AttentionAllocation:
    """One candidate the budget actually selected this tick."""

    name: str
    uncertainty: float
    cost: float


class AttentionBudget:
    """Allocate a hard, bounded attention budget across candidates by
    uncertainty-per-cost (roadmap v0.38).

    "Causal" here means the same discipline as ``symbiont_lab``'s causal
    attention-budget experiments: a selection is made only from the
    uncertainty/cost known *before* observing, never from any downstream
    outcome — there is no such thing as a future score to inspect here in
    the first place, since a candidate's cost and uncertainty are computed
    from state that already exists this tick. This is a selection
    mechanism, not a threat or classification judgment (see
    ``docs/adr/ADR-0003-attention-is-not-classification.md``): nothing here
    ever produces or consumes a threat label.

    The allocation itself is a greedy uncertainty/cost-ratio heuristic, not
    an exact 0/1 knapsack solve — deliberately: it is O(n log n), one pass,
    and ties break on ``name`` for determinism, rather than optimizing
    total uncertainty exactly. A future milestone can swap the strategy
    without changing this class's contract (bounded budget in, bounded
    selection out).
    """

    def __init__(self, *, budget: float) -> None:
        if isinstance(budget, bool) or not math.isfinite(budget) or budget <= 0.0:
            raise ValueError("budget must be positive")
        self._budget = budget

    @property
    def budget(self) -> float:
        return self._budget

    def allocate(self, candidates: Iterable[AttentionCandidate]) -> tuple[AttentionAllocation, ...]:
        def score(c: AttentionCandidate) -> float:
            # Diminishing returns prevent a noisy, repeatedly sampled signal
            # from monopolising the bounded budget.
            diminishing = 1.0 / (1.0 + 0.05 * c.observations)
            return (c.uncertainty * diminishing) / (c.cost * c.rank_cost)

        ranked = sorted(candidates, key=lambda c: (-score(c), c.name))
        selected: list[AttentionAllocation] = []
        remaining = self._budget
        for candidate in ranked:
            if candidate.cost <= remaining:
                selected.append(
                    AttentionAllocation(
                        name=candidate.name, uncertainty=candidate.uncertainty, cost=candidate.cost
                    )
                )
                remaining -= candidate.cost
        return tuple(selected)


def uncertainty_from_baseline(baseline: CapabilityBaseline | None) -> float:
    """A purely statistical uncertainty score for one capability's baseline
    (roadmap v0.38).

    Unacclimated (``None``) is maximal uncertainty — there is no basis yet
    to say anything about it, so it always wins allocation over an
    established one. Otherwise this is the coefficient of variation
    (stdev relative to mean): a baseline that varies a lot relative to its
    own scale is one the organism knows least precisely. Purely descriptive
    — never a threat, anomaly or classification signal, the same
    discipline as everything else in :mod:`symbiont.host` (see
    ``docs/adr/ADR-0003-attention-is-not-classification.md``).
    """
    if baseline is None:
        return float("inf")
    if baseline.mean == 0.0:
        return baseline.stdev
    return abs(baseline.stdev / baseline.mean)


def bounded_uncertainty_from_baseline(baseline: CapabilityBaseline | None) -> float:
    """Bounded uncertainty used by the anti-capture scheduler."""
    if baseline is None:
        return float("inf")
    spread = abs(float(baseline.stdev))
    scale = abs(float(baseline.mean))
    return spread / (scale + spread + 1e-12)


def attend_to_host(
    acclimation: HostAcclimation,
    *,
    budget: float = 1.0,
    costs: dict[str, float] | None = None,
    rank_costs: dict[str, float] | None = None,
    eligible_capability_ids: Iterable[str] | None = None,
) -> tuple[AttentionAllocation, ...]:
    """Allocate a hard attention budget across a host's known capabilities
    by uncertainty and cost (roadmap v0.38).

    This is cognition's first real dependency on :mod:`symbiont.host`
    (Milestone C): every capability :meth:`HostAcclimation.observe` has ever
    seen is a candidate by default, weighted by :func:`uncertainty_from_baseline`;
    an unacclimated capability always outranks an established one. ``costs``
    defaults every candidate to 1.0 — real per-capability costs (e.g. a more
    intrusive or slower sense) are a caller concern this function composes
    with, not one it invents. ``rank_costs`` (roadmap v0.53) is a *separate*,
    ranking-only bias — it reorders which candidates look most worth
    attending to without changing how much of the hard budget any candidate
    consumes, which stays governed by ``costs`` alone. Conflating the two
    would let a caller-supplied learned cost silently defeat the budget's
    semantics (e.g. a candidate learned to cost a fraction of a second could
    let far more than the intended number of candidates fit).

    ``HostAcclimation`` never forgets a capability id once observed, even
    after that sense is no longer part of the live host manifest (roadmap
    safety finding A05) — without a filter, a removed or renamed sense's
    permanently-unacclimated (infinite-uncertainty) baseline would win
    every allocation forever and starve every real, currently-live
    candidate of the entire budget. Pass ``eligible_capability_ids`` (e.g.
    this tick's actually-sampled capability ids) to restrict candidates to
    what is genuinely still current; omit it only when the caller has no
    such notion of current vs. historical (candidates then default to
    every capability ever observed, as before).
    """
    resolved_costs = costs if costs is not None else {}
    resolved_rank_costs = rank_costs if rank_costs is not None else {}
    eligible = set(eligible_capability_ids) if eligible_capability_ids is not None else None
    candidates = [
        AttentionCandidate(
            name=capability_id,
            uncertainty=bounded_uncertainty_from_baseline(baseline),
            cost=resolved_costs.get(capability_id, 1.0),
            rank_cost=resolved_rank_costs.get(capability_id, 1.0),
            # Feed established sample count into the generic scheduler so its
            # diminishing-return term is not inert for host attention. A
            # capability below acclimation deliberately has no baseline and
            # starts at zero observations; it becomes finite after the host
            # has supplied enough aggregate evidence.
            observations=baseline.count if baseline is not None else 0,
        )
        for capability_id in acclimation.known_capabilities
        for baseline in (acclimation.baseline(capability_id),)
        if eligible is None or capability_id in eligible
    ]
    return AttentionBudget(budget=budget).allocate(candidates)
