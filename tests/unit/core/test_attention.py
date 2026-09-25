from __future__ import annotations

import pytest
from symbiont.core.attention import (
    AttentionBudget,
    AttentionCandidate,
    attend_to_host,
    uncertainty_from_baseline,
)

from symbiont.host.acclimation import CapabilityBaseline, HostAcclimation
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


def _reading(capability_id: str, value: float) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source="test",
        value=value,
        unit=Unit.RATIO,
        monotonic_timestamp_ns=0,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def test_candidate_rejects_non_positive_cost():
    with pytest.raises(ValueError):
        AttentionCandidate(name="a", uncertainty=1.0, cost=0.0)


def test_candidate_rejects_negative_uncertainty():
    with pytest.raises(ValueError):
        AttentionCandidate(name="a", uncertainty=-1.0, cost=1.0)


def test_candidate_rejects_nan_uncertainty_but_allows_unacclimated_infinity():
    with pytest.raises(ValueError):
        AttentionCandidate(name="a", uncertainty=float("nan"), cost=1.0)

    assert AttentionCandidate(name="a", uncertainty=float("inf"), cost=1.0).uncertainty == float(
        "inf"
    )


@pytest.mark.parametrize("field", ["cost", "rank_cost"])
def test_candidate_rejects_non_finite_ranking_costs(field):
    kwargs = {"name": "a", "uncertainty": 1.0, "cost": 1.0, field: float("inf")}
    with pytest.raises(ValueError):
        AttentionCandidate(**kwargs)


def test_budget_rejects_non_positive_value():
    with pytest.raises(ValueError):
        AttentionBudget(budget=0.0)


@pytest.mark.parametrize("budget", [float("nan"), float("inf")])
def test_budget_rejects_non_finite_value(budget):
    with pytest.raises(ValueError):
        AttentionBudget(budget=budget)


def test_allocates_highest_uncertainty_per_cost_first():
    budget = AttentionBudget(budget=1.0)
    candidates = [
        AttentionCandidate(name="cheap-uncertain", uncertainty=4.0, cost=1.0),
        AttentionCandidate(name="expensive-certain", uncertainty=1.0, cost=1.0),
    ]

    allocations = budget.allocate(candidates)

    assert [a.name for a in allocations] == ["cheap-uncertain"]


def test_fits_as_many_as_the_budget_allows():
    budget = AttentionBudget(budget=2.0)
    candidates = [
        AttentionCandidate(name="a", uncertainty=3.0, cost=1.0),
        AttentionCandidate(name="b", uncertainty=2.0, cost=1.0),
        AttentionCandidate(name="c", uncertainty=1.0, cost=1.0),
    ]

    allocations = budget.allocate(candidates)

    assert {a.name for a in allocations} == {"a", "b"}


def test_infinite_uncertainty_always_wins_over_finite():
    budget = AttentionBudget(budget=1.0)
    candidates = [
        AttentionCandidate(name="unknown", uncertainty=float("inf"), cost=1.0),
        AttentionCandidate(name="known", uncertainty=1000.0, cost=1.0),
    ]

    allocations = budget.allocate(candidates)

    assert allocations[0].name == "unknown"


def test_ties_break_deterministically_by_name():
    budget = AttentionBudget(budget=1.0)
    candidates = [
        AttentionCandidate(name="b", uncertainty=1.0, cost=1.0),
        AttentionCandidate(name="a", uncertainty=1.0, cost=1.0),
    ]

    allocations = budget.allocate(candidates)

    assert allocations[0].name == "a"


def test_nothing_selected_when_cheapest_candidate_exceeds_budget():
    budget = AttentionBudget(budget=0.5)
    candidates = [AttentionCandidate(name="a", uncertainty=1.0, cost=1.0)]

    assert budget.allocate(candidates) == ()


def test_uncertainty_from_missing_baseline_is_infinite():
    assert uncertainty_from_baseline(None) == float("inf")


def test_uncertainty_from_baseline_is_coefficient_of_variation():
    baseline = CapabilityBaseline(count=5, mean=2.0, variance=4.0)
    assert uncertainty_from_baseline(baseline) == pytest.approx(1.0)  # stdev=2.0, mean=2.0


def test_uncertainty_from_zero_mean_baseline_falls_back_to_stdev():
    baseline = CapabilityBaseline(count=5, mean=0.0, variance=9.0)
    assert uncertainty_from_baseline(baseline) == pytest.approx(3.0)


def test_attend_to_host_prioritizes_unacclimated_capability():
    acclimation = HostAcclimation(min_samples=5)
    acclimation.observe([_reading("stable", v) for v in [1.0, 1.0, 1.0, 1.0, 1.0]])
    acclimation.observe([_reading("new", 1.0)])  # only one sample, never acclimates

    allocations = attend_to_host(acclimation, budget=1.0)

    assert allocations[0].name == "new"
    assert allocations[0].uncertainty == float("inf")


def test_attend_to_host_respects_custom_costs():
    acclimation = HostAcclimation(min_samples=1)
    acclimation.observe([_reading("cheap", 1.0), _reading("costly", 1.0)])

    allocations = attend_to_host(acclimation, budget=1.0, costs={"cheap": 1.0, "costly": 5.0})

    assert {a.name for a in allocations} == {"cheap"}


def test_attend_to_host_never_produces_a_threat_or_classification_field():
    """Same discipline as everything else in symbiont.host: a selection
    mechanism, not a threat/classification judgment (ADR-0003)."""
    acclimation = HostAcclimation(min_samples=1)
    acclimation.observe([_reading("cpu", 1.0)])

    allocations = attend_to_host(acclimation, budget=1.0)

    for allocation in allocations:
        public_attrs = {name for name in dir(allocation) if not name.startswith("_")}
        assert public_attrs <= {"name", "uncertainty", "cost"}


# --- A05: a permanently-known-but-removed capability must not starve real ones ---


def test_eligible_filter_excludes_a_historically_known_capability():
    acclimation = HostAcclimation()  # default min_samples: one reading never establishes a-removed
    acclimation.observe([_reading("a-removed", 7.0)])
    acclimation.restore("z-live", CapabilityBaseline(count=10, mean=10.0, variance=1.0))

    unfiltered = attend_to_host(acclimation)
    assert unfiltered[0].name == "a-removed"  # default: no eligibility concept, old behavior

    filtered = attend_to_host(acclimation, eligible_capability_ids={"z-live"})
    assert filtered[0].name == "z-live"
    assert all(allocation.name != "a-removed" for allocation in filtered)


def test_eligible_filter_with_empty_set_yields_no_allocations():
    acclimation = HostAcclimation(min_samples=1)
    acclimation.observe([_reading("cpu", 1.0)])

    allocations = attend_to_host(acclimation, eligible_capability_ids=set())
    assert allocations == ()


# --- v0.53: rank_cost is ranking-only, never affects budget consumption ---


def test_rank_cost_defaults_to_one_and_does_not_change_existing_behavior():
    candidates = [
        AttentionCandidate(name="a", uncertainty=1.0, cost=1.0),
        AttentionCandidate(name="b", uncertainty=1.0, cost=1.0),
    ]
    allocations = AttentionBudget(budget=1.0).allocate(candidates)
    assert len(allocations) == 1
    assert allocations[0].name == "a"


def test_rank_cost_reorders_ranking_without_changing_budget_consumption():
    candidates = [
        AttentionCandidate(
            name="expensive-but-uncertain", uncertainty=10.0, cost=1.0, rank_cost=4.0
        ),
        AttentionCandidate(name="cheap-and-uncertain", uncertainty=10.0, cost=1.0, rank_cost=1.0),
    ]
    allocations = AttentionBudget(budget=1.0).allocate(candidates)
    assert allocations[0].name == "cheap-and-uncertain"
    assert allocations[0].cost == 1.0


def test_candidate_rejects_non_positive_rank_cost():
    with pytest.raises(ValueError):
        AttentionCandidate(name="a", uncertainty=1.0, cost=1.0, rank_cost=0.0)


def test_attend_to_host_with_no_rank_costs_matches_baseline():
    acclimation = HostAcclimation(min_samples=1)
    acclimation.observe([_reading("cheap", 1.0), _reading("costly", 1.0)])

    baseline_allocations = attend_to_host(acclimation, budget=1.0)
    same_allocations = attend_to_host(acclimation, budget=1.0, rank_costs=None)
    assert baseline_allocations == same_allocations


def test_attend_to_host_applies_rank_costs_per_capability():
    acclimation = HostAcclimation(min_samples=1)
    acclimation.restore("capability-a", CapabilityBaseline(count=10, mean=1.0, variance=1.0))
    acclimation.restore("capability-b", CapabilityBaseline(count=10, mean=1.0, variance=1.0))

    allocations = attend_to_host(
        acclimation,
        budget=1.0,
        rank_costs={"capability-a": 4.0, "capability-b": 1.0},
    )
    assert allocations[0].name == "capability-b"
