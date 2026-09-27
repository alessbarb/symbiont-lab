"""Bounded Generative Cognition agenda under sustained prospective demand (GC §38)."""

from __future__ import annotations

from symbiont.cognition.generative import ResidentGenerativeCognition, TargetStatus


def _flood(resident: ResidentGenerativeCognition, count: int, *, tick: int) -> None:
    resident.step(
        tick=tick,
        cognition=None,
        prospective_candidate_ids=tuple(f"competence.{index}" for index in range(count)),
        known_action_ids=tuple(f"competence.{index}" for index in range(count)),
    )


def test_prospective_targets_of_vanished_sources_are_retired():
    resident = ResidentGenerativeCognition(organism_id="organism.agenda")
    _flood(resident, 4, tick=1)
    resident.step(
        tick=2,
        cognition=None,
        prospective_candidate_ids=("competence.0",),
        known_action_ids=("competence.0", "competence.1"),
    )
    status = {target.target_id: target.status for target in resident.agenda.targets}
    assert status["gc.prospective.competence.2"] is TargetStatus.RETIRED
    assert status["gc.prospective.competence.3"] is TargetStatus.RETIRED
    assert status["gc.prospective.competence.1"] is not TargetStatus.RETIRED


def test_demand_beyond_capacity_is_dropped_not_fatal():
    resident = ResidentGenerativeCognition(organism_id="organism.agenda")
    capacity = resident.agenda.max_targets
    _flood(resident, capacity + 5, tick=1)
    assert len(resident.agenda.targets) == capacity
    assert resident.agenda_overflow_count >= 5
