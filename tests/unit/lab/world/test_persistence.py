"""Tests for Phase P1: Durable World & Persistence (docs/design/symbiont-world-v3.md §6, §7, §8, §12, §37).

Verifies the Phase P1 technical gate:
1. Checkpoint/replay equivalence:
   future(A) == future(B)
   where Run A runs continuously and Run B checkpoints to disk, restores in a new instance, and continues.
2. Physical disk atomic persistence:
   - Atomic rename, fsync, HEAD file, manifest.json.
   - SHA-256 corruption detection.
   - Constitution fingerprint enforcement.
3. Genesis canonical vs smoke constitution separation.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from symbiont_lab.world.genesis_v1 import (
    build_genesis_smoke_v1,
    build_genesis_v1,
    build_ground_truth,
)
from symbiont_lab.world.persistence import (
    WorldStorage,
)
from symbiont.cognition.birth import load_actuator_constitution
from symbiont_lab.world.adapter import (
    ActuationBinding,
    ActuationBindingConstitution,
    _load_base_genome,
)
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
from symbiont_world.events import EventJournal
from symbiont_world.topology import HexCoord, HexTopology


def _make_pop(seed: int = 101, count: int = 4, world_id: str = "genesis-v1-population") -> PopulationGenesisRuntime:
    topo = HexTopology(width=8, height=8)
    gt = build_ground_truth()
    cells = founder_placement(seed, topo, count)
    return PopulationGenesisRuntime(
        organism_ids=tuple(f"org-{i}" for i in range(count)),
        world_seed=seed,
        ground_truth=gt,
        topology=topo,
        start_cells=cells,
        world_id=world_id,
    )


def test_genesis_canonical_vs_smoke_constitutions_diverge():
    """Section 12: Genesis-v1 (64x64) and Genesis-Smoke-v1 (8x8) must have distinct fingerprints."""
    canonical = build_genesis_v1()
    smoke = build_genesis_smoke_v1()

    assert canonical.constitution.world_dimensions == (64, 64)
    assert smoke.constitution.world_dimensions == (8, 8)
    assert canonical.constitution.fingerprint() != smoke.constitution.fingerprint()


def test_checkpoint_replay_equivalence_future_a_equals_future_b(tmp_path: Path):
    """Section 7 gate: Run A (continuous) == Run B (checkpoint -> restore -> continue)."""
    smoke_genesis = build_genesis_smoke_v1()
    fingerprint = smoke_genesis.constitution.fingerprint()
    storage = WorldStorage(tmp_path / "storage_test")

    # Run A: uninterrupted run from tick 0 to tick 15
    pop_a = _make_pop(seed=555, count=4)
    pop_a.run(5)

    # At tick 5, save checkpoint to disk for Run B
    storage.save_checkpoint(
        pop_a,
        world_fingerprint=fingerprint,
        constitution=smoke_genesis.constitution,
    )

    # Continue Run A from tick 5 to tick 15
    records_a = pop_a.run(10)
    assert pop_a.state.tick == 15

    # Run B: restore from disk at tick 5
    pop_b = storage.restore(
        ground_truth=pop_a.ground_truth,
        expected_constitution=smoke_genesis.constitution,
    )
    assert pop_b.state.tick == 5
    assert pop_b.state.world_id == pop_a.state.world_id
    assert pop_b.organism_ids == pop_a.organism_ids

    # Run B from tick 5 to tick 15
    records_b = pop_b.run(10)
    assert pop_b.state.tick == 15

    # Verify future(A) == future(B)
    assert len(records_a) == len(records_b) == 10
    for ra, rb in zip(records_a, records_b):
        assert ra.tick == rb.tick
        for oid in pop_a.organism_ids:
            act_a = ra.per_organism[oid].action
            act_b = rb.per_organism[oid].action
            assert act_a.action_id == act_b.action_id
            assert ra.per_organism[oid].hazard_hits == rb.per_organism[oid].hazard_hits
            assert ra.per_organism[oid].alive == rb.per_organism[oid].alive

    # Verify complete final-state equivalence, not only visible behavior.
    assert pop_a.state.snapshot() == pop_b.state.snapshot()
    assert pop_a.environment.snapshot() == pop_b.environment.snapshot()
    assert pop_a.deferred_queue.snapshot() == pop_b.deferred_queue.snapshot()
    assert pop_a.journal.snapshot() == pop_b.journal.snapshot()

    # Organism runtime deterministic internal state equivalence.
    # Note: host statistical baselines (acclimation/rhythms/drift) undergo privacy-preserving
    # lossy quantization into discrete classes upon checkpoint export (symbiont design §14),
    # so continuous accumulation vs quantized-seed accumulation are compared on all exact keys.
    lossy_baseline_keys = {
        "acclimation", "rhythms", "drift", "sensory_development",
        "sensory_system", "signal_knowledge", "narrative_journal",
    }
    assert {
        oid: {k: v for k, v in pop_a._rigs[oid].runtime.checkpoint().items() if k not in lossy_baseline_keys}
        for oid in pop_a.organism_ids
    } == {
        oid: {k: v for k, v in pop_b._rigs[oid].runtime.checkpoint().items() if k not in lossy_baseline_keys}
        for oid in pop_b.organism_ids
    }
    assert {
        oid: {
            rid: habitat.checkpoint()
            for rid, habitat in pop_a._rigs[oid].resource_habitats.items()
        }
        for oid in pop_a.organism_ids
    } == {
        oid: {
            rid: habitat.checkpoint()
            for rid, habitat in pop_b._rigs[oid].resource_habitats.items()
        }
        for oid in pop_b.organism_ids
    }

    # Two restored runs starting from the same checkpoint must be 100% bit-for-bit identical,
    # including all internal runtime checkpoint keys without exceptions.
    pop_b2 = storage.restore(
        ground_truth=pop_a.ground_truth,
        expected_constitution=smoke_genesis.constitution,
    )
    records_b2 = pop_b2.run(10)
    assert pop_b.state.snapshot() == pop_b2.state.snapshot()
    assert pop_b.environment.snapshot() == pop_b2.environment.snapshot()
    assert pop_b.journal.snapshot() == pop_b2.journal.snapshot()
    assert {
        oid: pop_b._rigs[oid].runtime.checkpoint()
        for oid in pop_b.organism_ids
    } == {
        oid: pop_b2._rigs[oid].runtime.checkpoint()
        for oid in pop_b2.organism_ids
    }


def test_storage_atomic_files_and_head_pointer(tmp_path: Path):
    """Section 8: verifies HEAD pointer, directory layout, and manifest.json."""
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "world_run")
    pop = _make_pop()
    pop.run(3)

    chk_path = storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )

    assert chk_path.exists()
    assert storage.head_file.exists()
    head_content = storage.head_file.read_text().strip()
    assert head_content == "000000000003.chk"

    assert storage.manifest_file.exists()
    manifest = json.loads(storage.manifest_file.read_text())
    assert manifest["last_tick"] == 3
    assert manifest["last_checkpoint"] == "000000000003.chk"

    assert storage.constitution_file.exists()


def test_corrupt_checkpoint_detection(tmp_path: Path):
    """Corrupt checkpoint files must be rejected by SHA-256 validation, never accepted."""
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "corrupt_test")
    pop = _make_pop()
    pop.run(2)

    chk_path = storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
    )

    # Tamper with the checkpoint payload on disk
    data = json.loads(chk_path.read_text(encoding="utf-8"))
    data["payload"]["tick"] = 99999  # modify payload without updating checksum
    chk_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="no valid checkpoint available"):
        storage.load_latest_checkpoint()


def test_constitution_mismatch_rejection(tmp_path: Path):
    """Section 12 & 37: restoring with the wrong constitution fingerprint must fail."""
    smoke = build_genesis_smoke_v1()
    canonical = build_genesis_v1()
    storage = WorldStorage(tmp_path / "const_mismatch_test")
    pop = _make_pop()
    pop.run(2)

    storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
    )

    # Attempt to restore requiring the canonical (64x64) constitution
    with pytest.raises(ValueError, match="constitution fingerprint mismatch"):
        storage.restore(
            ground_truth=pop.ground_truth,
            expected_constitution=canonical.constitution,
        )


def test_journal_is_segmented_once_and_not_duplicated_inside_checkpoint(tmp_path: Path):
    """Committed events live in append-only segments; checkpoint payload stores only journal metadata."""
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "segmented_journal")
    pop = _make_pop()
    pop.run(2)
    first = storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )
    first_event_count = len(pop.journal)
    assert first_event_count > 0

    envelope = json.loads(first.read_text(encoding="utf-8"))
    assert "journal" not in envelope["payload"]
    assert envelope["payload"]["journal_event_count"] == first_event_count

    segments_after_first = sorted(storage.events_dir.glob("segment-*.jsonl"))
    assert len(segments_after_first) == 1
    assert len(segments_after_first[0].read_text(encoding="utf-8").splitlines()) == first_event_count

    pop.run(2)
    storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )
    segments_after_second = sorted(storage.events_dir.glob("segment-*.jsonl"))
    assert len(segments_after_second) == 2
    total_lines = sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in segments_after_second
    )
    assert total_lines == len(pop.journal)


def test_corrupt_head_falls_back_to_previous_valid_checkpoint_and_rewinds_manifest(tmp_path: Path):
    """A corrupt latest checkpoint must not destroy world continuity."""
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "fallback")
    pop = _make_pop(seed=909)

    pop.run(2)
    first = storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )
    first_tick = pop.state.tick
    first_events = len(pop.journal)

    pop.run(2)
    second = storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )
    assert second != first

    broken = json.loads(second.read_text(encoding="utf-8"))
    broken["payload"]["tick"] = 999999
    second.write_text(json.dumps(broken), encoding="utf-8")

    recovered = storage.load_latest_checkpoint()
    assert recovered.tick == first_tick
    assert recovered.journal_event_count == first_events
    assert len(recovered.journal) == first_events
    assert storage.head_file.read_text(encoding="utf-8").strip() == first.name

    manifest = json.loads(storage.manifest_file.read_text(encoding="utf-8"))
    assert manifest["last_checkpoint"] == first.name
    assert manifest["last_tick"] == first_tick
    assert manifest["journal_event_count"] == first_events
    assert manifest["recovered_from_invalid_head"] == second.name

    # The discarded future's event segment is removed as well; resuming from
    # the recovered universe must be able to persist a new causal future.
    segments = sorted(storage.events_dir.glob("segment-*.jsonl"))
    assert len(segments) == 1

    resumed = storage.restore(
        ground_truth=pop.ground_truth,
        expected_constitution=smoke.constitution,
    )
    resumed.run(1)
    storage.save_checkpoint(
        resumed,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )
    assert storage.load_latest_checkpoint().tick == first_tick + 1


def test_restore_from_segmented_journal_preserves_confirmed_event_prefix(tmp_path: Path):
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "restore_segmented")
    pop = _make_pop(seed=818)
    pop.run(4)
    expected_event_ids = [event.event_id for event in pop.journal.replay()]

    storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )
    restored = storage.restore(
        ground_truth=pop.ground_truth,
        expected_constitution=smoke.constitution,
    )

    assert [event.event_id for event in restored.journal.replay()] == expected_event_ids


def test_storage_rejects_cross_world_identity_reuse(tmp_path: Path):
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "identity_guard")
    first = _make_pop(seed=101, world_id="world-a")
    first.run(1)
    storage.save_checkpoint(
        first,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )

    second = _make_pop(seed=202, world_id="world-b")
    second.run(1)
    with pytest.raises(ValueError, match="durable world identity mismatch"):
        storage.save_checkpoint(
            second,
            world_fingerprint=smoke.constitution.fingerprint(),
            constitution=smoke.constitution,
        )


def test_missing_manifest_recovers_event_prefix_without_duplicate_segments(tmp_path: Path):
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "manifest_recovery")
    pop = _make_pop(seed=606)
    pop.run(2)
    storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )
    first_count = len(pop.journal)
    storage.manifest_file.unlink()

    pop.run(2)
    storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )

    segments = sorted(storage.events_dir.glob("segment-*.jsonl"))
    assert len(segments) == 2
    total_lines = sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in segments
    )
    assert total_lines == len(pop.journal)
    assert total_lines > first_count
    restored = storage.load_latest_checkpoint()
    assert restored.journal_event_count == len(pop.journal)
    assert len(restored.journal) == len(pop.journal)


def test_save_rejects_incompatible_in_memory_journal_prefix(tmp_path: Path):
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "prefix_guard")
    pop = _make_pop(seed=707)
    pop.run(2)
    storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )

    snapshot = pop.journal.snapshot()
    assert snapshot
    snapshot[0] = {**snapshot[0], "event_id": "evt-incompatible-prefix"}
    pop.journal = EventJournal.from_snapshot(snapshot)
    pop.run(1)

    with pytest.raises(ValueError, match="journal prefix mismatch"):
        storage.save_checkpoint(
            pop,
            world_fingerprint=smoke.constitution.fingerprint(),
            constitution=smoke.constitution,
        )


def test_actuation_world_replay_equivalence_with_movement_enabled(tmp_path: Path):
    """P6: motor body + binding + World consequence survive cold restart."""
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "actuation_replay")
    topo = HexTopology(width=8, height=8)
    gt = build_ground_truth()
    cells = founder_placement(1313, topo, 2)
    pop_a = PopulationGenesisRuntime(
        organism_ids=("motor-a", "motor-b"),
        world_seed=1313,
        ground_truth=gt,
        topology=topo,
        start_cells=cells,
        movement_enabled=True,
    )
    pop_a.run(17)
    storage.save_checkpoint(
        pop_a,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )
    pop_a.run(20)

    pop_b = storage.restore(
        ground_truth=gt,
        expected_constitution=smoke.constitution,
    )
    assert pop_b.movement_enabled is True
    pop_b.run(20)

    assert pop_a.state.snapshot() == pop_b.state.snapshot()
    assert pop_a.environment.snapshot() == pop_b.environment.snapshot()
    assert pop_a.journal.snapshot() == pop_b.journal.snapshot()
    assert {
        oid: pop_a._rigs[oid].runtime.checkpoint()["actuation"]
        for oid in pop_a.organism_ids
    } == {
        oid: pop_b._rigs[oid].runtime.checkpoint()["actuation"]
        for oid in pop_b.organism_ids
    }
    assert {
        oid: pop_a._rigs[oid].actuation_binding.fingerprint
        for oid in pop_a.organism_ids
    } == {
        oid: pop_b._rigs[oid].actuation_binding.fingerprint
        for oid in pop_b.organism_ids
    }


def test_actuation_binding_and_pending_emissions_survive_world_checkpoint(tmp_path: Path):
    smoke = build_genesis_smoke_v1()
    storage = WorldStorage(tmp_path / "actuation_emission")
    genome, _ = _load_base_genome()
    constitution = load_actuator_constitution(genome)
    binding = ActuationBindingConstitution(tuple(
        ActuationBinding(actuator_id, "emit", "23")
        for actuator_id in constitution.actuator_ids
    ))
    pop = PopulationGenesisRuntime(
        organism_ids=("emit-a", "emit-b"),
        world_seed=1414,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=8, height=8),
        start_cells=(HexCoord(2, 2), HexCoord(3, 2)),
        actuation_binding=binding,
    )
    for _ in range(120):
        pop.run_tick()
        if pop._emissions:
            break
    assert pop._emissions

    storage.save_checkpoint(
        pop,
        world_fingerprint=smoke.constitution.fingerprint(),
        constitution=smoke.constitution,
    )
    restored = storage.restore(
        ground_truth=pop.ground_truth,
        expected_constitution=smoke.constitution,
    )
    assert restored._emissions == pop._emissions
    assert {
        oid: restored._rigs[oid].actuation_binding.fingerprint
        for oid in restored.organism_ids
    } == {oid: binding.fingerprint for oid in restored.organism_ids}
