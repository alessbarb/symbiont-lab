"""Durable world persistence and atomic checkpointing (docs/design/symbiont-world-v3.md §6, §7, §8, §37).

Guarantees:
1. Complete universe state is captured in PersistentWorldCheckpoint.
2. Atomic checkpoint writes on disk (temporary file, fsync, checksum, atomic rename, update HEAD).
3. Checkpoint/replay equivalence:
   future(continuous_run) == future(checkpoint -> restore -> continue)
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import random
from typing import Any, Mapping
import uuid

from symbiont.core.ecology import SharedHabitat
from symbiont.modeling.runtime import ModeledOrganismRuntime
from symbiont_world.constitution import WorldConstitution
from symbiont_world.events import EventJournal, WorldEvent
from symbiont_world.genesis import GroundTruth
from symbiont_world.state import WorldState
from symbiont_world.topology import HexCoord, HexTopology, OccupancyGrid, WorldBody

from .adapter import _OrganismRig, _construct_organism
from .deferred import DeferredEffect, DeferredEffectQueue
from .population import PopulationGenesisRuntime

PERSISTENCE_SCHEMA_VERSION = 2


def _restore_rng_state(state_data: Any) -> tuple:
    """Restore a Python random.getstate() tuple that was JSON-deserialized."""
    if isinstance(state_data, (list, tuple)) and len(state_data) == 3:
        return (state_data[0], tuple(state_data[1]), state_data[2])
    return tuple(state_data)


@dataclass(frozen=True, slots=True)
class PersistentWorldCheckpoint:
    schema_version: int
    world_id: str
    world_fingerprint: str
    world_seed: int
    epoch: int
    tick: int
    topology: dict[str, int]
    occupancy: dict[str, str]
    bodies: dict[str, dict[str, int]]
    environment: dict[str, Any]
    organisms: dict[str, dict[str, Any]]
    deferred_effects: list[dict[str, Any]]
    journal_event_count: int
    last_event_id: str | None
    journal: list[dict[str, Any]]

    def to_dict(self, *, include_journal: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "world_id": self.world_id,
            "world_fingerprint": self.world_fingerprint,
            "world_seed": self.world_seed,
            "epoch": self.epoch,
            "tick": self.tick,
            "topology": dict(self.topology),
            "occupancy": dict(self.occupancy),
            "bodies": dict(self.bodies),
            "environment": self.environment,
            "organisms": self.organisms,
            "deferred_effects": self.deferred_effects,
            "journal_event_count": self.journal_event_count,
            "last_event_id": self.last_event_id,
        }
        if include_journal:
            payload["journal"] = self.journal
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersistentWorldCheckpoint":
        return cls(
            schema_version=int(data["schema_version"]),
            world_id=str(data["world_id"]),
            world_fingerprint=str(data["world_fingerprint"]),
            world_seed=int(data["world_seed"]),
            epoch=int(data.get("epoch", 0)),
            tick=int(data["tick"]),
            topology=dict(data["topology"]),
            occupancy=dict(data["occupancy"]),
            bodies=dict(data["bodies"]),
            environment=dict(data["environment"]),
            organisms=dict(data["organisms"]),
            deferred_effects=list(data.get("deferred_effects", ())),
            journal_event_count=int(data.get("journal_event_count", len(data.get("journal", ())))),
            last_event_id=(
                str(data["last_event_id"])
                if data.get("last_event_id") is not None
                else (
                    str(data.get("journal", ())[-1]["event_id"])
                    if data.get("journal")
                    else None
                )
            ),
            journal=list(data.get("journal", ())),
        )


def capture_checkpoint(
    pop: PopulationGenesisRuntime,
    *,
    world_fingerprint: str,
    epoch: int = 0,
) -> PersistentWorldCheckpoint:
    """Extract a complete PersistentWorldCheckpoint from a live PopulationGenesisRuntime."""
    # Occupancy: "q,r" -> organism_id
    occupancy = {
        f"{cell.q},{cell.r}": organism_id
        for cell, organism_id in pop.state.occupancy.snapshot().items()
    }
    # Bodies: organism_id -> {"q": cell.q, "r": cell.r}
    bodies = {
        oid: {"q": body.occupied_cell.q, "r": body.occupied_cell.r}
        for oid, body in pop.state.bodies.items()
    }
    # Environment
    env_data = {
        "field_values": dict(pop.environment.field_values()),
        "resource_pools": {
            f"{cell.q},{cell.r}": dict(pool)
            for cell, pool in pop.environment._resource_pools.items()
        },
    }
    # Organisms
    organisms = {}
    for oid in pop.organism_ids:
        rig = pop._rigs[oid]
        organisms[oid] = {
            "checkpoint": rig.runtime.checkpoint(),
            "resource_habitats": {
                hid: hab.checkpoint() for hid, hab in rig.resource_habitats.items()
            },
            "policy": rig.policy,
            "policy_rng_state": rig.policy_rng.getstate(),
            "alive": pop.is_alive(oid),
        }

    journal_snapshot = pop.journal.snapshot()
    return PersistentWorldCheckpoint(
        schema_version=PERSISTENCE_SCHEMA_VERSION,
        world_id=pop.state.world_id,
        world_fingerprint=world_fingerprint,
        world_seed=pop.world_seed,
        epoch=epoch,
        tick=pop.state.tick,
        topology={"width": pop.topology.width, "height": pop.topology.height},
        occupancy=occupancy,
        bodies=bodies,
        environment=env_data,
        organisms=organisms,
        deferred_effects=pop.deferred_queue.snapshot(),
        journal_event_count=len(journal_snapshot),
        last_event_id=journal_snapshot[-1]["event_id"] if journal_snapshot else None,
        journal=journal_snapshot,
    )


def restore_population_from_checkpoint(
    checkpoint: PersistentWorldCheckpoint,
    ground_truth: GroundTruth,
    *,
    sensory_plasticity: bool = False,
    discover_senses: bool = False,
) -> PopulationGenesisRuntime:
    """Instantiate a PopulationGenesisRuntime from a PersistentWorldCheckpoint."""
    topo = HexTopology(
        width=checkpoint.topology["width"],
        height=checkpoint.topology["height"],
    )
    organism_ids = tuple(sorted(checkpoint.organisms.keys()))
    start_cells = tuple(
        HexCoord(checkpoint.bodies[oid]["q"], checkpoint.bodies[oid]["r"])
        for oid in organism_ids
    )

    pop = PopulationGenesisRuntime(
        organism_ids=organism_ids,
        world_seed=checkpoint.world_seed,
        ground_truth=ground_truth,
        topology=topo,
        start_cells=start_cells,
        world_id=checkpoint.world_id,
        sensory_plasticity=sensory_plasticity,
        discover_senses=discover_senses,
        journal=EventJournal.from_snapshot(checkpoint.journal),
    )

    # 1. Restore state
    grid = OccupancyGrid()
    for cell_key, oid in checkpoint.occupancy.items():
        q_str, r_str = cell_key.split(",")
        grid.occupy(HexCoord(int(q_str), int(r_str)), oid)
    pop.state.occupancy = grid

    bodies = {}
    for oid, bdata in checkpoint.bodies.items():
        cell = HexCoord(bdata["q"], bdata["r"])
        bodies[oid] = WorldBody(organism_id=oid, occupied_cell=cell)
    pop.state.bodies = bodies
    pop.state.tick = checkpoint.tick

    # 2. Restore environment
    env_snap = {
        "field_values": checkpoint.environment["field_values"],
        "resource_pools": {
            HexCoord(int(k.split(",")[0]), int(k.split(",")[1])): dict(pool)
            for k, pool in checkpoint.environment["resource_pools"].items()
        },
    }
    pop.environment.restore(env_snap)

    # 3. Restore deferred queue
    pop.deferred_queue.restore(checkpoint.deferred_effects)

    # 4. Restore each organism rig
    for oid, odata in checkpoint.organisms.items():
        rig = pop._rigs[oid]
        # Restore habitats
        for hid, hdata in odata["resource_habitats"].items():
            rig.resource_habitats[hid] = SharedHabitat.from_checkpoint(hdata)

        # Restore runtime with wired lifecycle and habitats
        rig.runtime = ModeledOrganismRuntime.from_checkpoint(
            odata["checkpoint"],
            host_lifecycle=rig.runtime._lifecycle,
            resource_habitats=rig.resource_habitats,
        )
        rig.policy = str(odata["policy"])
        rig.policy_rng.setstate(_restore_rng_state(odata["policy_rng_state"]))

    return pop


class WorldStorage:
    """Manages physical disk persistence in <world_dir> (docs/design/symbiont-world-v3.md §8).

    Guarantees:
    - Atomic writes using temporary file, fsync, checksum, and atomic replace.
    - HEAD pointer updating.
    - Corrupt checkpoint detection via SHA-256 verification.
    """

    def __init__(self, world_dir: Path | str) -> None:
        self.world_dir = Path(world_dir)
        self.checkpoints_dir = self.world_dir / "checkpoints"
        self.events_dir = self.world_dir / "events"
        self.head_file = self.world_dir / "HEAD"
        self.manifest_file = self.world_dir / "manifest.json"
        self.constitution_file = self.world_dir / "constitution.json"

    def ensure_dirs(self) -> None:
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        pop: PopulationGenesisRuntime,
        *,
        world_fingerprint: str,
        epoch: int = 0,
        constitution: WorldConstitution | None = None,
    ) -> Path:
        """Atomically persist a checkpoint to disk and update HEAD."""
        self.ensure_dirs()
        checkpoint = capture_checkpoint(pop, world_fingerprint=world_fingerprint, epoch=epoch)
        payload_bytes = json.dumps(checkpoint.to_dict(), indent=2, sort_keys=True).encode("utf-8")
        checksum = hashlib.sha256(payload_bytes).hexdigest()

        envelope = {
            "checksum": checksum,
            "schema_version": PERSISTENCE_SCHEMA_VERSION,
            "payload": checkpoint.to_dict(),
        }
        envelope_bytes = json.dumps(envelope, indent=2, sort_keys=True).encode("utf-8")

        target_name = f"{checkpoint.tick:012d}.chk"
        target_path = self.checkpoints_dir / target_name
        tmp_name = f".tmp_{checkpoint.tick:012d}_{uuid.uuid4().hex[:8]}.chk"
        tmp_path = self.checkpoints_dir / tmp_name

        # 1. Write tmp and fsync
        with open(tmp_path, "wb") as f:
            f.write(envelope_bytes)
            f.flush()
            os.fsync(f.fileno())

        # 2. Verify checksum before rename
        with open(tmp_path, "rb") as f:
            readback = json.loads(f.read().decode("utf-8"))
            recomputed = hashlib.sha256(
                json.dumps(readback["payload"], indent=2, sort_keys=True).encode("utf-8")
            ).hexdigest()
            if recomputed != readback["checksum"]:
                tmp_path.unlink(missing_ok=True)
                raise IOError("checkpoint write failed checksum verification")

        # 3. Atomic rename to final target
        os.replace(tmp_path, target_path)

        # 4. Atomic update HEAD
        head_tmp = self.world_dir / f".HEAD.tmp.{uuid.uuid4().hex[:8]}"
        with open(head_tmp, "w", encoding="utf-8") as f:
            f.write(f"{target_name}\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(head_tmp, self.head_file)

        # 5. Atomic update manifest
        manifest_data = {
            "world_id": checkpoint.world_id,
            "world_fingerprint": world_fingerprint,
            "world_seed": checkpoint.world_seed,
            "last_tick": checkpoint.tick,
            "last_checkpoint": target_name,
        }
        manifest_tmp = self.world_dir / f".manifest.tmp.{uuid.uuid4().hex[:8]}"
        with open(manifest_tmp, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(manifest_tmp, self.manifest_file)

        # 6. Save constitution if provided and not yet present
        if constitution is not None and not self.constitution_file.exists():
            const_tmp = self.world_dir / f".constitution.tmp.{uuid.uuid4().hex[:8]}"
            with open(const_tmp, "w", encoding="utf-8") as f:
                f.write(constitution.canonical())
                f.flush()
                os.fsync(f.fileno())
            os.replace(const_tmp, self.constitution_file)

        return target_path

    def load_latest_checkpoint(self) -> PersistentWorldCheckpoint:
        """Load and verify the checkpoint pointed to by HEAD."""
        if not self.head_file.exists():
            raise FileNotFoundError(f"no HEAD file found in {self.world_dir}")
        target_name = self.head_file.read_text(encoding="utf-8").strip()
        target_path = self.checkpoints_dir / target_name
        if not target_path.exists():
            raise FileNotFoundError(f"checkpoint {target_path} referenced by HEAD does not exist")

        with open(target_path, "rb") as f:
            envelope = json.loads(f.read().decode("utf-8"))

        checksum = envelope.get("checksum")
        payload = envelope.get("payload")
        if not checksum or not payload:
            raise ValueError(f"checkpoint {target_path} has missing or invalid envelope")

        recomputed = hashlib.sha256(
            json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if recomputed != checksum:
            raise ValueError(f"checkpoint {target_path} checksum mismatch: corrupt file")

        return PersistentWorldCheckpoint.from_dict(payload)

    def restore(
        self,
        ground_truth: GroundTruth,
        *,
        expected_constitution: WorldConstitution | None = None,
        sensory_plasticity: bool = False,
        discover_senses: bool = False,
    ) -> PopulationGenesisRuntime:
        """Restore world from latest confirmed checkpoint on disk."""
        chk = self.load_latest_checkpoint()
        if expected_constitution is not None:
            expected_fp = expected_constitution.fingerprint()
            if chk.world_fingerprint != expected_fp:
                raise ValueError(
                    f"constitution fingerprint mismatch: expected {expected_fp[:16]}..., "
                    f"checkpoint has {chk.world_fingerprint[:16]}..."
                )

        return restore_population_from_checkpoint(
            chk,
            ground_truth,
            sensory_plasticity=sensory_plasticity,
            discover_senses=discover_senses,
        )
