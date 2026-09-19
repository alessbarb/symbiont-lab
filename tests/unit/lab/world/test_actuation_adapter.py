from __future__ import annotations

import pytest

from symbiont.actuation.constitution import derive_actuator_constitution
from symbiont.actuation.types import Actuation
from symbiont.cognition.genome import MotorGenes
from symbiont_lab.world.adapter import (
    ActuationAdapter,
    ActuationBinding,
    ActuationBindingConstitution,
    local_substrate_signals,
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



def test_local_substrate_signals_are_opaque_and_causally_change_after_impulse():
    from symbiont_lab.world.terrain import DynamicGeography
    from symbiont_world.topology import HexCoord, HexTopology

    topo = HexTopology(width=4, height=4)
    geo = DynamicGeography(topo, 1201)
    origin = HexCoord(1, 1)
    target = origin.neighbor(0)
    geo._surface_water[origin] = 0.6
    geo._detritus[origin] = 0.5

    before = local_substrate_signals(geo, origin)
    geo.apply_directional_impulse(origin, target, 1.0)
    after = local_substrate_signals(geo, origin)

    assert set(before) == set(after)
    assert len(before) == 3
    assert any(before[key] != after[key] for key in before)
    assert all(len(key) == 16 for key in before)
    assert all(all(ch in "0123456789abcdef" for ch in key) for key in before)
    assert not any(
        word in key
        for key in before
        for word in ("water", "detritus", "fertility", "disturbance", "pressure")
    )
