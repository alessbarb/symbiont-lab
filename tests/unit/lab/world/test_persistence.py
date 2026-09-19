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
    build_constitution,
    build_genesis_smoke_v1,
    build_genesis_v1,
    build_ground_truth,
)
from symbiont_lab.world.persistence import (
    WorldStorage,
    capture_checkpoint,
    restore_population_from_checkpoint,
)
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
from symbiont_world.topology import HexTopology


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

    # Verify final state equivalence
    assert pop_a.state.occupancy == pop_b.state.occupancy
    assert pop_a.environment.field_values() == pop_b.environment.field_values()
    assert len(pop_a.journal) == len(pop_b.journal)


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

    with pytest.raises(ValueError, match="checksum mismatch"):
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
