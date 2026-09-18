from symbiont_lab.world.cli_view import render_world
from symbiont_lab.world.genesis_v1 import GENESIS_V1_METADATA, build_ground_truth
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
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


def test_render_world_does_not_mutate_state():
    pop, truth, topo = _population()
    before_tick = pop.state.tick
    before_occupancy = pop.state.occupancy.snapshot()
    render_world(pop.state, pop.environment, truth, GENESIS_V1_METADATA, topo)
    assert pop.state.tick == before_tick
    assert pop.state.occupancy.snapshot() == before_occupancy
