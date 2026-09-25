from __future__ import annotations

import pytest

from symbiont.core.body import create_standard_body
from symbiont.core.embodiment import EmbodimentState
from symbiont.core.individual import create_individual


def test_clean_individual_session_and_episode_share_identity() -> None:
    ind = create_individual(
        "sym.clean",
        "body.clean",
        num_receptors=2,
        num_effectors=2,
    )
    assert ind.embodiment_id == ind.session.embodiment_id
    assert ind.embodiment.body_id == ind.body_id
    assert ind.embodiment.symbiont_id == ind.symbiont_id
    assert ind.embodiment.epoch == 1
    assert ind.embodiment_tick == 0


def test_clean_individual_has_three_explicit_temporal_domains() -> None:
    ind = create_individual(
        "sym.time",
        "body.time",
        num_receptors=2,
        num_effectors=1,
        started_at=40,
    )
    assert ind.current_tick == 40
    assert ind.symbiont.total_ticks == 0
    assert ind.body.age_ticks == 0
    assert ind.embodiment_tick == 0

    ind.step()
    assert ind.current_tick == 41
    assert ind.symbiont.total_ticks == 1
    assert ind.body.age_ticks == 1
    assert ind.embodiment_tick == 1

    # Equal numerical increments do not imply shared ownership or derivation.
    ind.body.physiology.age_ticks = 17
    assert ind.embodiment_tick == 1
    assert ind.symbiont.total_ticks == 1


def test_transplant_closes_archives_and_replaces_embodiment_only() -> None:
    ind = create_individual(
        "sym.traveler",
        "body.a",
        num_receptors=2,
        num_effectors=2,
    )
    for _ in range(12):
        ind.step()

    old_episode = ind.embodiment
    old_session = ind.session
    old_id = ind.embodiment_id
    old_total_ticks = ind.symbiont.total_ticks
    old_relation_count = ind.symbiont.sensorimotor_model.relation_count

    new_body = create_standard_body(
        "body.b",
        num_receptors=3,
        num_effectors=3,
    )
    ind.transplant_to(new_body)

    assert old_episode.state is EmbodimentState.CLOSED
    assert not old_session.is_active
    assert ind.symbiont_id == "sym.traveler"
    assert ind.symbiont.total_ticks == old_total_ticks
    assert ind.body_id == "body.b"
    assert ind.embodiment_id != old_id
    assert ind.session.embodiment_id == ind.embodiment_id
    assert ind.embodiment.epoch == old_episode.epoch + 1
    assert ind.embodiment_tick == 0

    # Old-body factual state is archived but has no current authority.
    archived = ind.embodiment_archive.for_body("body.a")
    assert archived is not None
    assert archived.last_embodiment_id == old_id
    assert ind.symbiont.sensorimotor_model.relation_count == 0
    assert ind.symbiont.causal_evidence.evidence == ()
    assert ind.symbiont.agency_model.estimates == ()
    assert ind.symbiont.body_schema.boundary_confidence == 0.0
    assert len(ind.embodiment_archive.summaries) == 1
    assert old_relation_count >= 0


def test_clean_body_death_closes_episode_and_prevents_further_steps() -> None:
    ind = create_individual(
        "sym.mortal",
        "body.mortal",
        num_receptors=1,
        num_effectors=1,
    )
    # Force a physically tiny reserve so the next basal tick ends the Body.
    ind.body.physiology.energy_reserve = min(
        ind.body.basal_metabolic_rate / 2.0,
        ind.body.physiology.max_energy,
    )

    record = ind.step()
    assert not record.body_viable
    assert ind.embodiment.state is EmbodimentState.CLOSED
    assert not ind.session.is_active
    assert ind.embodiment_archive.for_body("body.mortal") is not None

    with pytest.raises(RuntimeError, match="active embodiment"):
        ind.step()


def test_suspended_clean_episode_cannot_execute_physics_or_cognition() -> None:
    ind = create_individual("sym.pause", "body.pause")
    ind.embodiment.suspend()
    sym_tick = ind.symbiont.total_ticks
    body_tick = ind.body.age_ticks
    embodiment_tick = ind.embodiment_tick

    with pytest.raises(RuntimeError, match="active embodiment"):
        ind.step()

    assert ind.symbiont.total_ticks == sym_tick
    assert ind.body.age_ticks == body_tick
    assert ind.embodiment_tick == embodiment_tick
