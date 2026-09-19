from symbiont_lab.world.cli_view import render_world, world_snapshot
from symbiont_lab.world.genesis_v1 import GENESIS_V1_METADATA, build_ground_truth
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
from symbiont_world.events import WorldEvent
from symbiont_world.topology import HexTopology


def _population(count: int = 3):
    topo = HexTopology(width=8, height=8)
    truth = build_ground_truth()
    cells = founder_placement(101, topo, count)
    pop = PopulationGenesisRuntime(
        organism_ids=tuple(f"org-{i}" for i in range(count)),
        world_seed=101,
        ground_truth=truth,
        topology=topo,
        start_cells=cells,
    )
    return pop, truth, topo


def test_render_world_is_pure_and_returns_a_string():
    pop, truth, topo = _population()
    text = render_world(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    assert isinstance(text, str)
    assert "World" in text


def test_render_world_shows_real_semantic_labels_not_opaque_ids():
    pop, truth, topo = _population()
    pop.run(5)
    text = render_world(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    assert "field-cycle-a" in text
    assert "resource-abundant-cheap" in text
    assert "hazard-density-coupled" in text


def test_render_world_lists_every_occupied_organism():
    pop, truth, topo = _population(count=5)
    text = render_world(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    for organism_id in pop.organism_ids:
        assert organism_id in text


def test_render_world_has_no_control_surface():
    """The public contract exposes exactly one callable; nothing here can
    call WorldAction or advance a tick."""
    import symbiont_lab.world.cli_view as module

    public_names = [name for name in dir(module) if not name.startswith("_")]
    assert "render_world" in public_names
    forbidden = {"step", "act", "advance_tick", "apply_action"}
    assert forbidden.isdisjoint(public_names)


def test_render_world_without_journal_says_so_honestly():
    pop, truth, topo = _population()
    text = render_world(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    assert "no journal attached" in text


def test_world_snapshot_is_json_serializable_and_matches_organisms():
    import json

    pop, truth, topo = _population(count=4)
    pop.run(5)
    snapshot = world_snapshot(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    json.dumps(snapshot)  # must not raise

    assert snapshot["width"] == 8
    assert snapshot["height"] == 8
    assert {org["id"] for org in snapshot["organisms"]} == set(pop.organism_ids)
    for org in snapshot["organisms"]:
        cell_key = f"{org['q']},{org['r']}"
        assert cell_key in snapshot["cells"]


def test_world_snapshot_uses_real_labels_not_opaque_ids():
    pop, truth, topo = _population(count=2)
    pop.run(3)
    snapshot = world_snapshot(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    assert "field-cycle-a" in snapshot["fields"]
    any_cell = next(iter(snapshot["cells"].values()))
    assert "resource-abundant-cheap" in any_cell["resources"]


def test_world_snapshot_does_not_mutate_state():
    pop, truth, topo = _population()
    before_tick = pop.state.tick
    world_snapshot(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    assert pop.state.tick == before_tick


def test_render_world_does_not_mutate_state():
    pop, truth, topo = _population()
    before_tick = pop.state.tick
    before_occupancy = pop.state.occupancy.snapshot()
    render_world(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    assert pop.state.tick == before_tick
    assert pop.state.occupancy.snapshot() == before_occupancy


def test_world_snapshot_reports_unknown_cognition_as_null_not_plausible_defaults():
    pop, truth, topo = _population(count=2)
    pop.run(2)
    snapshot = world_snapshot(
        pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo,
        population=pop,
    )
    for org in snapshot["organisms"]:
        cognition = org["cognition"]
        assert cognition["prediction_confidence"] is None
        assert isinstance(cognition["private_model_bridge_active"], bool)
        assert cognition["interoception_mode"] in {"enabled", "sham", "absent"}
        assert org["metabolic_pressure"] in {
            "normal", "elevated", "severe", "unrecoverable"
        }


def test_perception_projection_keeps_opaque_signal_ids():
    pop, truth, topo = _population(count=1)
    pop.run(1)
    snapshot = world_snapshot(
        pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo,
        population=pop,
    )
    perception = snapshot["organisms"][0]["perception"]
    assert perception
    semantic_labels = set(GENESIS_V1_METADATA)
    assert semantic_labels.isdisjoint(perception)


def test_recent_damage_is_summed_from_committed_damage_events():
    pop, truth, topo = _population(count=1)
    pop.run(1)
    organism_id = pop.organism_ids[0]
    tick = pop.history[-1].tick
    existing = sum(
        float(event.payload.get("damage", 0.0))
        for event in pop.journal.replay()
        if event.tick == tick
        and event.actor == organism_id
        and event.kind == "PHYSIOLOGICAL_DAMAGE"
    )
    pop.journal.append(WorldEvent(
        event_id="evt-test-observatory-damage",
        world_id=pop.state.world_id,
        tick=tick,
        kind="PHYSIOLOGICAL_DAMAGE",
        actor=organism_id,
        position=None,
        payload={"damage": 0.13, "source": "test"},
    ))

    snapshot = world_snapshot(
        pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo,
        population=pop,
    )
    org = next(item for item in snapshot["organisms"] if item["id"] == organism_id)
    assert org["recent_damage"] == round(existing + 0.13, 4)


def test_text_view_uses_real_local_density_for_hazard_exposure():
    topo = HexTopology(width=2, height=2)
    truth = build_ground_truth()
    cells = founder_placement(101, topo, 4)
    pop = PopulationGenesisRuntime(
        organism_ids=tuple(f"dense-{i}" for i in range(4)),
        world_seed=101,
        ground_truth=truth,
        topology=topo,
        start_cells=cells,
    )
    text = render_world(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    assert "exposure(density=0.000)" not in text
