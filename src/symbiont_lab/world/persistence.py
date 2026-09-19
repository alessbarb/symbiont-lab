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
from typing import Any
import uuid

from symbiont.core.ecology import SharedHabitat
from symbiont.modeling.runtime import ModeledOrganismRuntime
from symbiont_world.constitution import WorldConstitution
from symbiont_world.events import EventJournal
from symbiont_world.genesis import GroundTruth
from symbiont_world.topology import HexCoord, HexTopology, OccupancyGrid, WorldBody

from .adapter import ActuationAdapter, ActuationBinding, ActuationBindingConstitution
from .population import PopulationGenesisRuntime
from .terrain import DynamicGeography

PERSISTENCE_SCHEMA_VERSION = 3


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
    geography: dict[str, Any] | None = None
    movement_enabled: bool = False
    emissions: dict[str, list[int]] | None = None

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
            "movement_enabled": self.movement_enabled,
            "emissions": dict(self.emissions or {}),
        }
        if self.geography is not None:
            payload["geography"] = self.geography
        if include_journal:
            payload["journal"] = self.journal
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersistentWorldCheckpoint":
        journal_data = data.get("journal")
        last_event_id: str | None = None
        if data.get("last_event_id") is not None:
            last_event_id = str(data["last_event_id"])
        elif isinstance(journal_data, (list, tuple)) and len(journal_data) > 0:
            last_event_id = str(journal_data[-1]["event_id"])

        journal_count = (
            int(data["journal_event_count"])
            if data.get("journal_event_count") is not None
            else (len(journal_data) if isinstance(journal_data, (list, tuple)) else 0)
        )

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
            journal_event_count=journal_count,
            last_event_id=last_event_id,
            journal=list(journal_data) if isinstance(journal_data, (list, tuple)) else [],
            geography=dict(data["geography"]) if data.get("geography") is not None else None,
            movement_enabled=bool(data.get("movement_enabled", False)),
            emissions={
                str(oid): [int(value) for value in sequence]
                for oid, sequence in dict(data.get("emissions", {})).items()
            },
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
            "actuation_binding": [
                {
                    "actuator_id": item.actuator_id,
                    "effect": item.effect,
                    "argument": item.argument,
                }
                for item in rig.actuation_binding.bindings
            ],
            "actuation_binding_fingerprint": rig.actuation_binding.fingerprint,
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
        geography=pop.geography.to_dict() if hasattr(pop, "geography") and pop.geography is not None else None,
        movement_enabled=bool(pop.movement_enabled),
        emissions={oid: list(sequence) for oid, sequence in sorted(pop._emissions.items())},
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

    geography = (
        DynamicGeography.from_dict(checkpoint.geography)
        if checkpoint.geography is not None
        else None
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
        geography=geography,
        movement_enabled=checkpoint.movement_enabled,
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
            min_samples=1,
        )
        rig.policy = str(odata["policy"])
        rig.policy_rng.setstate(_restore_rng_state(odata["policy_rng_state"]))
        raw_binding = odata.get("actuation_binding")
        if raw_binding is not None:
            if not isinstance(raw_binding, list):
                raise ValueError("invalid persisted actuation binding")
            binding = ActuationBindingConstitution(
                bindings=tuple(
                    ActuationBinding(
                        actuator_id=str(item["actuator_id"]),
                        effect=str(item["effect"]),
                        argument=str(item["argument"]),
                    )
                    for item in raw_binding
                )
            )
            expected_fingerprint = odata.get("actuation_binding_fingerprint")
            if expected_fingerprint is not None and binding.fingerprint != expected_fingerprint:
                raise ValueError("persisted actuation binding fingerprint mismatch")
            if rig.runtime.actuator_constitution is None:
                raise ValueError("persisted binding requires restored actuator constitution")
            rig.actuation_binding = binding
            rig.actuation_adapter = ActuationAdapter(rig.runtime.actuator_constitution, binding)

    pop._emissions = {
        oid: tuple(int(value) for value in sequence)
        for oid, sequence in (checkpoint.emissions or {}).items()
        if oid in pop._rigs
    }
    return pop


class WorldStorage:
    """Durable storage for checkpoints plus an append-only segmented event log.

    Checkpoints contain the current universe state and only journal metadata;
    committed events live once in events/ segments. HEAD is a convenience
    pointer, not a single point of failure: loading falls back to the newest
    valid older checkpoint when the pointed file is missing or corrupt.
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

    def _atomic_write_text(self, path: Path, content: str) -> None:
        tmp = path.parent / f".{path.name}.tmp.{uuid.uuid4().hex[:8]}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    def _read_manifest(self) -> dict[str, Any]:
        if not self.manifest_file.exists():
            return {}
        try:
            data = json.loads(self.manifest_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _persist_event_delta(self, events: list[dict[str, Any]], previous_count: int) -> None:
        if previous_count < 0 or previous_count > len(events):
            raise ValueError("journal event count regressed relative to durable manifest")
        if previous_count == len(events):
            return
        start = previous_count
        end = len(events)
        target = self.events_dir / f"segment-{start:012d}-{end:012d}.jsonl"
        tmp = self.events_dir / f".tmp-events-{uuid.uuid4().hex[:8]}.jsonl"
        with open(tmp, "w", encoding="utf-8") as f:
            for event in events[start:end]:
                f.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)

    def _load_event_prefix(self, count: int) -> list[dict[str, Any]]:
        if count <= 0:
            return []
        events: list[dict[str, Any]] = []
        expected_start = 0
        segments = sorted(self.events_dir.glob("segment-*.jsonl"))
        for segment in segments:
            parts = segment.stem.split("-")
            if len(parts) != 3:
                continue
            try:
                start, end = int(parts[1]), int(parts[2])
            except ValueError:
                continue
            # Ignore orphan/superseded segments that do not extend the
            # contiguous committed prefix we are reconstructing.
            if start != expected_start:
                continue
            lines = segment.read_text(encoding="utf-8").splitlines()
            decoded = [json.loads(line) for line in lines if line.strip()]
            if len(decoded) != end - start:
                raise ValueError(f"event segment {segment} length mismatch")
            events.extend(decoded)
            expected_start = end
            if len(events) >= count:
                return events[:count]
        if len(events) < count:
            raise ValueError(
                f"event journal incomplete: checkpoint requires {count} events, "
                f"only {len(events)} are durable"
            )
        return events[:count]

    def _prune_event_suffix(self, committed_count: int) -> None:
        """Remove durable event segments that belong to a discarded future.

        Checkpoints are written only after their journal delta, so every
        checkpoint boundary is also a segment boundary. When recovery falls
        back to an older complete universe state, later descriptive events
        cannot be replayed into organism internals and must be discarded.
        """
        for segment in self.events_dir.glob("segment-*.jsonl"):
            parts = segment.stem.split("-")
            if len(parts) != 3:
                continue
            try:
                start = int(parts[1])
            except ValueError:
                continue
            if start >= committed_count:
                segment.unlink(missing_ok=True)

    def save_checkpoint(
        self,
        pop: PopulationGenesisRuntime,
        *,
        world_fingerprint: str,
        epoch: int = 0,
        constitution: WorldConstitution | None = None,
    ) -> Path:
        """Atomically persist a universe checkpoint and journal delta."""
        self.ensure_dirs()
        checkpoint = capture_checkpoint(pop, world_fingerprint=world_fingerprint, epoch=epoch)

        manifest_before = self._read_manifest()
        # manifest.json is descriptive metadata, not the authority for causal
        # continuity. If it is missing/corrupt but HEAD exists, recover the
        # durable identity/event prefix from the latest valid checkpoint.
        if not manifest_before and self.head_file.exists():
            durable = self.load_latest_checkpoint()
            manifest_before = {
                "world_id": durable.world_id,
                "world_fingerprint": durable.world_fingerprint,
                "world_seed": durable.world_seed,
                "last_tick": durable.tick,
                "last_checkpoint": self.head_file.read_text(encoding="utf-8").strip(),
                "journal_event_count": durable.journal_event_count,
                "last_event_id": durable.last_event_id,
            }
            self._atomic_write_text(
                self.manifest_file,
                json.dumps(manifest_before, indent=2),
            )

        if manifest_before:
            identity_checks = {
                "world_id": checkpoint.world_id,
                "world_fingerprint": world_fingerprint,
                "world_seed": checkpoint.world_seed,
            }
            for key, expected in identity_checks.items():
                existing = manifest_before.get(key)
                if existing is not None and existing != expected:
                    raise ValueError(
                        f"durable world identity mismatch for {key}: "
                        f"existing={existing!r}, attempted={expected!r}"
                    )

        if constitution is not None and self.constitution_file.exists():
            existing_constitution = self.constitution_file.read_text(encoding="utf-8")
            if existing_constitution != constitution.canonical():
                raise ValueError("durable world constitution mismatch")

        previous_event_count = int(manifest_before.get("journal_event_count", 0))
        durable_last_event_id = manifest_before.get("last_event_id")
        if previous_event_count:
            if previous_event_count > len(checkpoint.journal):
                raise ValueError("journal event count regressed relative to durable manifest")
            in_memory_tail = checkpoint.journal[previous_event_count - 1].get("event_id")
            if durable_last_event_id is not None and in_memory_tail != durable_last_event_id:
                raise ValueError(
                    "journal prefix mismatch: in-memory history does not extend "
                    "the durable causal prefix"
                )
            durable_events = self._load_event_prefix(previous_event_count)
            for idx in range(min(previous_event_count, len(durable_events))):
                if checkpoint.journal[idx].get("event_id") != durable_events[idx].get("event_id"):
                    raise ValueError(
                        f"journal prefix mismatch: event {idx} differs from durable history"
                    )
        self._persist_event_delta(checkpoint.journal, previous_event_count)

        # Journal entries themselves are stored once in events/. The checkpoint
        # records the exact prefix required for recovery.
        payload = checkpoint.to_dict(include_journal=False)
        payload_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        checksum = hashlib.sha256(payload_bytes).hexdigest()
        envelope = {
            "checksum": checksum,
            "schema_version": PERSISTENCE_SCHEMA_VERSION,
            "payload": payload,
        }
        envelope_bytes = json.dumps(envelope, indent=2, sort_keys=True).encode("utf-8")

        target_name = f"{checkpoint.tick:012d}.chk"
        target_path = self.checkpoints_dir / target_name
        tmp_path = self.checkpoints_dir / f".tmp_{checkpoint.tick:012d}_{uuid.uuid4().hex[:8]}.chk"

        with open(tmp_path, "wb") as f:
            f.write(envelope_bytes)
            f.flush()
            os.fsync(f.fileno())

        readback = json.loads(tmp_path.read_text(encoding="utf-8"))
        recomputed = hashlib.sha256(
            json.dumps(readback["payload"], indent=2, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if recomputed != readback["checksum"]:
            tmp_path.unlink(missing_ok=True)
            raise IOError("checkpoint write failed checksum verification")

        os.replace(tmp_path, target_path)

        self._atomic_write_text(self.head_file, f"{target_name}\n")
        manifest_data = {
            "world_id": checkpoint.world_id,
            "world_fingerprint": world_fingerprint,
            "world_seed": checkpoint.world_seed,
            "last_tick": checkpoint.tick,
            "last_checkpoint": target_name,
            "journal_event_count": checkpoint.journal_event_count,
            "last_event_id": checkpoint.last_event_id,
        }
        self._atomic_write_text(self.manifest_file, json.dumps(manifest_data, indent=2))

        if constitution is not None and not self.constitution_file.exists():
            self._atomic_write_text(self.constitution_file, constitution.canonical())

        return target_path

    def _load_checkpoint_path(self, target_path: Path) -> PersistentWorldCheckpoint:
        envelope = json.loads(target_path.read_text(encoding="utf-8"))
        checksum = envelope.get("checksum")
        payload = envelope.get("payload")
        if not checksum or not isinstance(payload, dict):
            raise ValueError(f"checkpoint {target_path} has missing or invalid envelope")
        recomputed = hashlib.sha256(
            json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if recomputed != checksum:
            raise ValueError(f"checkpoint {target_path} checksum mismatch: corrupt file")

        checkpoint = PersistentWorldCheckpoint.from_dict(payload)
        # Schema v1 checkpoints embedded their entire journal. Schema v2+
        # reconstructs the exact committed prefix from durable event segments.
        if checkpoint.journal_event_count and not checkpoint.journal:
            events = self._load_event_prefix(checkpoint.journal_event_count)
            if checkpoint.last_event_id is not None:
                if not events or events[-1].get("event_id") != checkpoint.last_event_id:
                    raise ValueError("event journal tail does not match checkpoint metadata")
            checkpoint = replace(checkpoint, journal=events)
        return checkpoint

    def load_latest_checkpoint(self) -> PersistentWorldCheckpoint:
        """Load HEAD, falling back to the newest older valid checkpoint.

        Recovery deliberately does not pretend that descriptive WorldEvents can
        reconstruct arbitrary organism internals. If HEAD is corrupt, the world
        resumes from the latest complete valid universe checkpoint.
        """
        self.ensure_dirs()
        if not self.head_file.exists():
            raise FileNotFoundError(f"no HEAD file found in {self.world_dir}")

        head_name = self.head_file.read_text(encoding="utf-8").strip()
        candidates: list[Path] = []
        head_path = self.checkpoints_dir / head_name
        candidates.append(head_path)
        candidates.extend(
            p for p in sorted(self.checkpoints_dir.glob("*.chk"), reverse=True)
            if p != head_path
        )

        failures: list[str] = []
        for path in candidates:
            if not path.exists():
                failures.append(f"{path.name}: missing")
                continue
            try:
                checkpoint = self._load_checkpoint_path(path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                failures.append(f"{path.name}: {exc}")
                continue
            if path.name != head_name:
                self._prune_event_suffix(checkpoint.journal_event_count)
                self._atomic_write_text(self.head_file, f"{path.name}\n")
                recovered_manifest = {
                    "world_id": checkpoint.world_id,
                    "world_fingerprint": checkpoint.world_fingerprint,
                    "world_seed": checkpoint.world_seed,
                    "last_tick": checkpoint.tick,
                    "last_checkpoint": path.name,
                    "journal_event_count": checkpoint.journal_event_count,
                    "last_event_id": checkpoint.last_event_id,
                    "recovered_from_invalid_head": head_name,
                }
                self._atomic_write_text(
                    self.manifest_file,
                    json.dumps(recovered_manifest, indent=2),
                )
            return checkpoint

        detail = "; ".join(failures) if failures else "no checkpoint files"
        raise ValueError(f"no valid checkpoint available: {detail}")

    def restore(
        self,
        ground_truth: GroundTruth,
        *,
        expected_constitution: WorldConstitution | None = None,
        sensory_plasticity: bool = False,
        discover_senses: bool = False,
    ) -> PopulationGenesisRuntime:
        """Restore world from the newest valid confirmed checkpoint on disk."""
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
