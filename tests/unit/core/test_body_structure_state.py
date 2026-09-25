"""L5.5.1 v1 — per-structure damage (BodyStructureState)."""

from __future__ import annotations

import pytest
from symbiont.core.physiology import BodyStructureState, LivingBodyState


def _uniform_body(n: int = 3) -> LivingBodyState:
    return LivingBodyState(
        structure_states={f"s{i}": BodyStructureState(structure_id=f"s{i}") for i in range(n)}
    )


def test_scalar_only_body_behaves_exactly_as_before():
    body = LivingBodyState()
    body.apply_wear(0.3)
    assert body.structural_integrity == pytest.approx(0.7)
    assert body.structure_states == {}


def test_uniform_structures_aggregate_matches_scalar_behavior():
    body = _uniform_body()
    body.apply_wear(0.25)
    assert body.structural_integrity == pytest.approx(0.75)
    assert all(s.integrity == pytest.approx(0.75) for s in body.structure_states.values())


def test_repair_and_damage_stay_in_sync_via_homeostasis_setter():
    from symbiont.core.homeostasis import HomeostaticController

    body = _uniform_body()
    controller = HomeostaticController(body_state=body)
    controller.integrity = 0.4

    assert body.structural_integrity == pytest.approx(0.4)
    assert all(s.integrity == pytest.approx(0.4) for s in body.structure_states.values())

    controller.integrity = 0.9
    assert body.structural_integrity == pytest.approx(0.9)
    assert all(s.integrity == pytest.approx(0.9) for s in body.structure_states.values())


def test_structure_states_checkpoint_round_trip():
    body = _uniform_body()
    body.apply_wear(0.15)
    restored = LivingBodyState.from_checkpoint(body.checkpoint())

    assert restored.structural_integrity == pytest.approx(body.structural_integrity)
    for structure_id, structure in body.structure_states.items():
        assert restored.structure_states[structure_id].checkpoint() == structure.checkpoint()


def test_v2_checkpoint_without_structures_restores_with_none():
    body = LivingBodyState(structural_integrity=0.6)
    payload = body.checkpoint()
    payload["schema_version"] = 2
    del payload["structure_states"]

    restored = LivingBodyState.from_checkpoint(payload)

    assert restored.structure_states == {}
    assert restored.structural_integrity == pytest.approx(0.6)


def test_structure_states_key_must_match_own_structure_id():
    with pytest.raises(ValueError):
        LivingBodyState(structure_states={"a": BodyStructureState(structure_id="b")})


def test_checkpoint_rejects_mismatched_structure_id_key():
    body = _uniform_body(1)
    payload = body.checkpoint()
    only_key = next(iter(payload["structure_states"]))
    payload["structure_states"] = {"wrong-key": payload["structure_states"][only_key]}

    with pytest.raises(ValueError):
        LivingBodyState.from_checkpoint(payload)


def test_body_structure_state_rejects_out_of_bounds_fields():
    with pytest.raises(ValueError):
        BodyStructureState(structure_id="x", integrity=1.5)
    with pytest.raises(ValueError):
        BodyStructureState(structure_id="")


def test_apply_wear_kills_body_when_all_structures_destroyed():
    body = _uniform_body(2)
    body.apply_wear(1.0)
    assert body.structural_integrity == 0.0
    assert not body.alive


def test_organism_runtime_populates_structures_from_actuator_slots():
    from symbiont.core.runtime import OrganismRuntime

    from symbiont.actuation.constitution import ActuatorConstitution, MotorSlot

    constitution = ActuatorConstitution(
        slots=(
            MotorSlot(
                slot_id="slot.0",
                actuator_id="act.0",
                basal_cost=0.05,
                initial_health=1.0,
                execution_threshold=0.5,
            ),
            MotorSlot(
                slot_id="slot.1",
                actuator_id="act.1",
                basal_cost=0.05,
                initial_health=1.0,
                execution_threshold=0.5,
            ),
        )
    )
    runtime = OrganismRuntime(
        actuation_enabled=True,
        actuator_constitution=constitution,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    assert set(runtime.living_body_state.structure_states) == {"slot.0", "slot.1"}
