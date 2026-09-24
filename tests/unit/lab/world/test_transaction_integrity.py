"""Tests for Phase P0: IntegratedWorldTickTransaction and state integrity.

Verifies the Phase P0 technical gate from docs/design/symbiont-world-v3.md §39:
"forced failure at every phase -> exact state restoration (failed_tick(state_n) == state_n)"
"""
from __future__ import annotations

from unittest.mock import patch
import pytest

from symbiont_lab.world.deferred import DeferredEffect
from symbiont_lab.world.genesis_v1 import build_ground_truth
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
from symbiont_world.state import TickAborted
from symbiont_world.topology import HexTopology


def _make_pop(seed: int = 101, count: int = 4) -> PopulationGenesisRuntime:
    topo = HexTopology(width=8, height=8)
    gt = build_ground_truth()
    cells = founder_placement(seed, topo, count)
    return PopulationGenesisRuntime(
        organism_ids=tuple(f"org-{i}" for i in range(count)),
        world_seed=seed,
        ground_truth=gt,
        topology=topo,
        start_cells=cells,
    )


def _capture_world_full_state(pop: PopulationGenesisRuntime) -> dict[str, object]:
    """Capture comprehensive semantic snapshot of the entire runtime."""
    rig_checkpoints = {}
    rig_habitats = {}
    for oid, rig in pop._rigs.items():
        original_hash = rig.runtime._last_checkpoint_hash
        rig_checkpoints[oid] = rig.runtime.checkpoint()
        rig.runtime._last_checkpoint_hash = original_hash
        rig_habitats[oid] = {r_id: h.checkpoint() for r_id, h in rig.resource_habitats.items()}

    return {
        "tick": pop.state.tick,
        "state_snapshot": pop.state.snapshot(),
        "env_snapshot": pop.environment.snapshot(),
        "rig_checkpoints": rig_checkpoints,
        "rig_habitats": rig_habitats,
        "deferred_snapshot": pop.deferred_queue.snapshot(),
        "journal_len": len(pop.journal),
        "history_len": len(pop.history),
    }


def test_failed_tick_restores_exact_state_phase_environment():
    """Phase 1 failure: failure during environment propagation leaves zero side effects."""
    pop = _make_pop()
    pop.run(5)
    pre = _capture_world_full_state(pop)

    with patch.object(pop.environment, "propagate_fields", side_effect=RuntimeError("simulated env failure")):
        with pytest.raises(RuntimeError, match="simulated env failure"):
            pop.run_tick()

    post = _capture_world_full_state(pop)
    assert post == pre


def test_failed_tick_restores_exact_state_phase_organism_cognition():
    """Phase 2 failure: failure during organism cognition mid-iteration rolls back
    both the failed organism AND previously processed organisms."""
    pop = _make_pop()
    pop.run(5)
    pre = _capture_world_full_state(pop)

    # Fail on the 3rd organism (org-2), so org-0 and org-1 have already stepped their runtime
    original_tick = pop._rigs["org-2"].runtime.tick

    def failing_tick():
        raise RuntimeError("simulated brain fault in org-2")

    pop._rigs["org-2"].runtime.tick = failing_tick
    try:
        with pytest.raises(RuntimeError, match="simulated brain fault in org-2"):
            pop.run_tick()
    finally:
        pop._rigs["org-2"].runtime.tick = original_tick

    post = _capture_world_full_state(pop)
    assert post == pre


def test_failed_tick_restores_exact_state_phase_action_execution():
    """Phase 3 failure: failure during action execution rolls back resource consumption
    and physiology."""
    pop = _make_pop()
    pop.run(5)
    pre = _capture_world_full_state(pop)

    with patch("symbiont_lab.world.population._act", side_effect=RuntimeError("action execution failed")):
        with pytest.raises(RuntimeError, match="action execution failed"):
            pop.run_tick()

    post = _capture_world_full_state(pop)
    assert post == pre


def test_failed_tick_restores_exact_state_phase_hazard_resolution():
    """Phase 4 failure: failure during hazard resolution rolls back damage and events."""
    pop = _make_pop()
    pop.run(5)
    pre = _capture_world_full_state(pop)

    with patch.object(pop.environment, "hazard_exposures_at", side_effect=RuntimeError("hazard engine failure")):
        with pytest.raises(RuntimeError, match="hazard engine failure"):
            pop.run_tick()

    post = _capture_world_full_state(pop)
    assert post == pre


def test_tick_aborted_suppresses_and_rolls_back():
    """TickAborted is treated as a modeled kernel abort: suppressed and clean rollback."""
    pop = _make_pop()
    pop.run(3)
    pre = _capture_world_full_state(pop)

    def aborting_renew(*args, **kwargs):
        raise TickAborted("resource equilibrium condition violated")

    with patch.object(pop.environment, "renew_resources", side_effect=aborting_renew):
        # TickAborted is caught and suppressed by the transaction
        pop.run_tick()

    post = _capture_world_full_state(pop)
    assert post == pre


def test_determinism_preserved_after_aborted_tick():
    """If tick N fails and is rolled back, re-running tick N without fault matches
    the exact trajectory of an unperturbed run."""
    pop_clean = _make_pop(seed=202)
    pop_perturbed = _make_pop(seed=202)

    pop_clean.run(5)
    pop_perturbed.run(5)

    # Induce failure in perturbed at tick 6
    with patch.object(pop_perturbed.environment, "propagate_fields", side_effect=RuntimeError("transient error")):
        with pytest.raises(RuntimeError):
            pop_perturbed.run_tick()

    # Now let both proceed for 10 more ticks
    clean_records = pop_clean.run(10)
    perturbed_records = pop_perturbed.run(10)

    assert len(clean_records) == len(perturbed_records)
    for c_rec, p_rec in zip(clean_records, perturbed_records):
        assert c_rec.tick == p_rec.tick
        for oid in pop_clean.organism_ids:
            assert c_rec.per_organism[oid].action.action_id == p_rec.per_organism[oid].action.action_id
            assert c_rec.per_organism[oid].hazard_hits == p_rec.per_organism[oid].hazard_hits
            assert c_rec.per_organism[oid].alive == p_rec.per_organism[oid].alive


def test_staged_events_only_commit_to_journal_on_success():
    """No partial or aborted events leak into EventJournal."""
    pop = _make_pop()
    initial_events = len(pop.journal)

    # Normal tick commits events
    pop.run_tick()
    assert len(pop.journal) > initial_events
    events_after_tick_1 = len(pop.journal)

    # Aborted tick does not commit ANY events
    with patch.object(pop.environment, "hazard_exposures_at", side_effect=RuntimeError("abort")):
        with pytest.raises(RuntimeError):
            pop.run_tick()

    assert len(pop.journal) == events_after_tick_1


def test_rollback_preserves_internal_rig_reference_graph():
    """Rollback must restore aliases, not merely equal independent copies.

    The runtime lifecycle must sample through the rig's reading provider and
    the runtime resource habitats must reference the exact same habitat
    instances exposed by the rig.
    """
    pop = _make_pop(seed=303, count=2)
    pop.run(2)

    with patch.object(pop.environment, "hazard_exposures_at", side_effect=RuntimeError("force rollback")):
        with pytest.raises(RuntimeError, match="force rollback"):
            pop.run_tick()

    for rig in pop._rigs.values():
        lifecycle_providers = rig.runtime._lifecycle._reading_providers
        assert any(provider is rig.reading_provider for provider in lifecycle_providers)
        for resource_id, habitat in rig.resource_habitats.items():
            assert rig.runtime._resource_habitats[resource_id] is habitat


def test_multiple_deferred_damage_events_same_tick_have_unique_ids():
    pop = _make_pop(seed=404, count=1)
    organism_id = pop.organism_ids[0]
    due_tick = pop.state.tick
    assert pop.deferred_queue.schedule(DeferredEffect(organism_id, due_tick, 0.01))
    assert pop.deferred_queue.schedule(DeferredEffect(organism_id, due_tick, 0.02))

    pop.run_tick()
    events = [
        event for event in pop.journal.replay()
        if event.kind == "PHYSIOLOGICAL_DAMAGE"
        and event.actor == organism_id
        and event.payload.get("source") == "deferred_effect"
    ]
    assert len(events) == 2
    assert len({event.event_id for event in events}) == 2
    assert [event.payload["effect_index"] for event in events] == [0, 1]


def test_experimental_clean_rollback_restores_individual_state():
    topo = HexTopology(width=8, height=8)
    gt = build_ground_truth()
    cells = founder_placement(505, topo, 2)
    pop = PopulationGenesisRuntime(
        organism_ids=("org-0", "org-1"),
        world_seed=505,
        ground_truth=gt,
        topology=topo,
        start_cells=cells,
        movement_enabled=True,
        experimental_clean=True,
    )
    pop.run(3)
    pre_hist_len = len(pop._rigs["org-0"].individual.history)
    pre_energy = pop._rigs["org-0"].individual.body.physiology.energy_reserve

    with patch.object(pop.environment, "hazard_exposures_at", side_effect=RuntimeError("simulated clean fault")):
        with pytest.raises(RuntimeError, match="simulated clean fault"):
            pop.run_tick()

    assert len(pop._rigs["org-0"].individual.history) == pre_hist_len
    assert pop._rigs["org-0"].individual.body.physiology.energy_reserve == pre_energy
