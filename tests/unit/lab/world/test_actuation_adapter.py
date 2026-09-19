from __future__ import annotations

import pytest

from symbiont.actuation.constitution import derive_actuator_constitution
from symbiont.actuation.types import Actuation
from symbiont.cognition.genome import MotorGenes
from symbiont_lab.world.adapter import (
    ActuationAdapter,
    ActuationBinding,
    ActuationBindingConstitution,
)


def _constitution():
    return derive_actuator_constitution(MotorGenes(slot_count=3, execution_threshold=0.5))


def _actuation(actuator_id: str, delivered: float) -> Actuation:
    return Actuation(
        actuator_id=actuator_id,
        requested=1.0,
        delivered=delivered,
        cost=0.05,
        health_at_execution=1.0,
    )


def test_binding_fingerprint_is_deterministic_and_mapping_sensitive():
    ids = _constitution().actuator_ids
    first = ActuationBindingConstitution((
        ActuationBinding(ids[0], "move", "0"),
        ActuationBinding(ids[1], "acquire", "local"),
    ))
    same = ActuationBindingConstitution((
        ActuationBinding(ids[0], "move", "0"),
        ActuationBinding(ids[1], "acquire", "local"),
    ))
    permuted = ActuationBindingConstitution((
        ActuationBinding(ids[0], "move", "4"),
        ActuationBinding(ids[1], "acquire", "local"),
    ))
    assert first.fingerprint == same.fingerprint
    assert first.fingerprint != permuted.fingerprint


def test_adapter_applies_body_execution_threshold_without_world_queries():
    constitution = _constitution()
    aid = constitution.actuator_ids[0]
    adapter = ActuationAdapter(
        constitution,
        ActuationBindingConstitution((ActuationBinding(aid, "move", "3"),)),
    )
    assert adapter.translate(_actuation(aid, 0.49)) is None
    translated = adapter.translate(_actuation(aid, 0.5))
    assert translated is not None
    assert translated.move == "3"


def test_adapter_supports_opaque_local_interaction_and_emission():
    constitution = _constitution()
    acquire_id, emit_id = constitution.actuator_ids[:2]
    adapter = ActuationAdapter(
        constitution,
        ActuationBindingConstitution((
            ActuationBinding(acquire_id, "acquire", "local"),
            ActuationBinding(emit_id, "emit", "17"),
        )),
    )
    assert adapter.translate(_actuation(acquire_id, 1.0)).acquire == "local"
    assert adapter.translate(_actuation(emit_id, 1.0)).emit == (17,)


@pytest.mark.parametrize(
    "binding",
    [
        ActuationBinding("actuator.a", "move", "6"),
        ActuationBinding("actuator.a", "acquire", "resource.secret"),
        ActuationBinding("actuator.a", "emit", "999"),
    ],
)
def test_binding_rejects_invalid_world_arguments(binding):
    with pytest.raises(ValueError):
        ActuationBindingConstitution((binding,))
