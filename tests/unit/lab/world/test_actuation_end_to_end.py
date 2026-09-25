from __future__ import annotations

from symbiont.actuation.surface import derive_actuator_constitution
from symbiont_lab.world.adapter import (
    ActuationBinding,
    ActuationBindingConstitution,
    _load_base_genome,
)
from symbiont_lab.world.genesis_v1 import build_ground_truth
from symbiont_lab.world.population import PopulationGenesisRuntime
from symbiont_world.topology import HexCoord, HexTopology


def _binding(effect: str, argument: str) -> ActuationBindingConstitution:
    _load_base_genome()  # assert canonical Genome v2 remains loadable
    constitution = derive_actuator_constitution(8, physical_contract="genesis-world-body-v2")
    return ActuationBindingConstitution(
        tuple(
            ActuationBinding(actuator_id, effect, argument)
            for actuator_id in constitution.actuator_ids
        )
    )


def test_blocked_move_is_attempted_and_journaled_not_prefiltered_by_lab():
    pop = PopulationGenesisRuntime(
        organism_ids=("org-a",),
        world_seed=1201,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(0, 2),),
        movement_enabled=True,
        # Direction 3 is q-1: every motor channel points across the west
        # boundary from q=0. If Lab still filtered valid directions, these
        # organism-owned attempts would disappear instead of being resolved.
        actuation_binding=_binding("move", "3"),
    )
    pop.run(80)
    resolutions = [
        event
        for event in pop.journal.replay()
        if event.kind == "ACTUATION_RESOLVED"
        and event.actor == "org-a"
        and event.payload.get("effect") == "move"
    ]
    assert resolutions
    assert any(event.payload.get("outcome") == "boundary" for event in resolutions)
    assert not [event for event in pop.journal.replay() if event.kind == "MOVE"]


def test_local_interaction_actuator_reaches_world_without_resource_semantics_in_command():
    pop = PopulationGenesisRuntime(
        organism_ids=("org-a",),
        world_seed=1202,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(2, 2),),
        actuation_binding=_binding("acquire", "local"),
    )
    records = pop.run(80)
    assert all(
        not record.per_organism["org-a"].action.action_id.startswith("intake") for record in records
    )
    resolutions = [
        event
        for event in pop.journal.replay()
        if event.kind == "ACTUATION_RESOLVED"
        and event.actor == "org-a"
        and event.payload.get("effect") == "acquire"
    ]
    assert resolutions
    # World truth may know which resource pool physically supplied intake,
    # but the motor command itself is only the opaque local interaction.
    assert all("resource_id" not in event.payload for event in resolutions)


def test_emission_is_received_on_next_tick_without_sender_identity():
    pop = PopulationGenesisRuntime(
        organism_ids=("org-a", "org-b"),
        world_seed=1203,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1), HexCoord(2, 1)),
        actuation_binding=_binding("emit", "17"),
    )
    records = pop.run(100)
    assert any(event.kind == "ORGANISM_EMITTED" for event in pop.journal.replay())

    receptions = [
        received
        for record in records
        for oid in pop.organism_ids
        for received in record.per_organism[oid].observation.reception
    ]
    assert receptions
    assert all(received.sequence == (17,) for received in receptions)
    # ReceivedEmission deliberately has no sender/actor field.
    assert all(not hasattr(received, "sender_id") for received in receptions)
