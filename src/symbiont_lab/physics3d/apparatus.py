"""PyBullet apparatus adapters for the canonical Symbiont runtime.

PyBullet owns anatomy and physical truth. OrganismRuntime sees only bounded,
opaque sensory capabilities and its inherited opaque actuator surface.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
import time

from symbiont import __version__ as symbiont_version
from symbiont.actuation.constitution import ActuatorConstitution
from symbiont.cognition.birth import load_actuator_constitution, load_base_cognition
from symbiont.cognition.genome import MotorGenes
from symbiont.core.physiology import LivingBodyState
from symbiont.cognition.limits import KernelLimits
from symbiont.host.contracts import (
    AccessMode,
    Capability,
    CapabilityKind,
    CapabilityScope,
)
from symbiont.sensory.limits import SensoryLimits
from symbiont.sensory.system import SensorySystem
from symbiont.host.readings import (
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
)

from .humanoid import (
    HumanoidPhysics,
    effector_contract_ids,
    interoceptive_receptor_contract_ids,
    receptor_contract_ids,
)


def _running_version() -> tuple[int, int, int]:
    parts = (symbiont_version.split(".") + ["0", "0"])[:3]
    return tuple(int(part) for part in parts)


def physics3d_sensory_system() -> SensorySystem:
    """Body-sized sensory substrate with an explicit bounded checkpoint budget.

    Anthropomorphic-v2 exposes a 107-channel opaque body surface. The apparatus
    therefore grants enough active-sensor and checkpoint capacity for every
    physical/interoceptive channel to remain discoverable without semantic
    prioritization by the lab.
    """
    limits = SensoryLimits(
        max_active_sensors=128,
        max_sensor_checkpoint_bytes=1024 * 1024,
    )
    return SensorySystem(
        limits=limits,
        plasticity_enabled=True,
    )


def physics3d_cognition(*, motor_slots: int | None = None):
    """Canonical germinal cognition with a body-compatible opaque motor surface."""
    if motor_slots is None:
        motor_slots = len(effector_contract_ids())
    if motor_slots < 1 or motor_slots > 64:
        raise ValueError("motor_slots must be within [1, 64]")
    limits = KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=_running_version(),
    )
    genome = replace(
        genome,
        genome_id="genome_symbiont_physics3d_v8",
        parent_ids=(genome.genome_id,),
        development=replace(
            genome.development,
            soft_node_budget=192,
            soft_edge_budget=1536,
            sense_node_budget=128,
        ),
        motor=MotorGenes(
            slot_count=motor_slots,
            basal_cost=0.002,
            initial_health=1.0,
            execution_threshold=0.05,
        ),
    )
    return genome, graph, limits


class OpaqueBodyInteroception:
    """Apparatus-side transducer from LivingBodyState to anonymous receptor slots.

    Source order is apparatus truth only:
    reserve ratio, structural integrity, temperature and fatigue.  The organism
    receives only the receptor ids and bounded values after an optional slot
    permutation.  No source names, setpoints, valence or action hints cross the
    reading boundary.
    """

    SOURCE_COUNT = 4

    def __init__(
        self,
        *,
        receptor_ids: Sequence[str] | None = None,
        source_ordinals_by_slot: Sequence[int] | None = None,
    ) -> None:
        ids = tuple(
            interoceptive_receptor_contract_ids()
            if receptor_ids is None
            else (str(item) for item in receptor_ids)
        )
        if len(ids) != self.SOURCE_COUNT or len(set(ids)) != self.SOURCE_COUNT:
            raise ValueError("body interoception requires four unique opaque receptor ids")
        permutation = (
            tuple(range(self.SOURCE_COUNT))
            if source_ordinals_by_slot is None
            else tuple(int(item) for item in source_ordinals_by_slot)
        )
        if sorted(permutation) != list(range(self.SOURCE_COUNT)):
            raise ValueError("interoception mapping must be a permutation of source ordinals")
        self.receptor_ids = ids
        self._source_ordinals_by_slot = permutation

    @property
    def source_ordinals_by_slot(self) -> tuple[int, ...]:
        return self._source_ordinals_by_slot

    def sample(self, state: LivingBodyState) -> dict[str, float]:
        source_values = (
            max(0.0, min(1.0, state.energy_reserve / max(state.max_energy, 1e-12))),
            max(0.0, min(1.0, state.structural_integrity)),
            max(0.0, min(1.0, state.temperature)),
            max(0.0, min(1.0, state.fatigue)),
        )
        return {
            receptor_id: float(source_values[source_ordinal])
            for receptor_id, source_ordinal in zip(
                self.receptor_ids, self._source_ordinals_by_slot
            )
        }

    def checkpoint(self) -> dict[str, object]:
        # Deliberately ordinal-only: serialized state preserves identity without
        # embedding physiology labels.
        return {
            "schema_version": 1,
            "source_ordinals_by_slot": list(self._source_ordinals_by_slot),
        }

    @classmethod
    def from_checkpoint(
        cls,
        payload: Mapping[str, object],
        *,
        receptor_ids: Sequence[str] | None = None,
    ) -> "OpaqueBodyInteroception":
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported opaque body interoception checkpoint")
        raw = payload.get("source_ordinals_by_slot")
        if not isinstance(raw, (list, tuple)):
            raise ValueError("opaque body interoception mapping is missing")
        return cls(receptor_ids=receptor_ids, source_ordinals_by_slot=raw)


class PhysicsDiscoveryProvider:
    """Expose physical receptors as opaque local read-only capabilities."""

    provider_id = "physics3d-body"

    def __init__(self, receptor_ids: Sequence[str]) -> None:
        self.receptor_ids = tuple(str(item) for item in receptor_ids)

    def discover(self) -> tuple[Capability, ...]:
        return tuple(
            Capability(
                capability_id=receptor_id,
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                access=AccessMode.READ_ONLY,
                scope=CapabilityScope.LOCAL,
            )
            for receptor_id in self.receptor_ids
        )


class PhysicsReadingProvider:
    """Sample one consistent PyBullet body state for the current runtime tick."""

    provider_id = "physics3d-body"

    def __init__(
        self,
        apparatus: HumanoidPhysics,
        *,
        body_state_getter: Callable[[], LivingBodyState] | None = None,
        interoception: OpaqueBodyInteroception | None = None,
    ) -> None:
        self.apparatus = apparatus
        self._body_state_getter = body_state_getter
        self.interoception = (
            interoception
            if interoception is not None
            else (OpaqueBodyInteroception() if body_state_getter is not None else None)
        )
        self.receptor_ids = (
            tuple(apparatus.receptor_ids)
            + (() if self.interoception is None else self.interoception.receptor_ids)
        )
        if body_state_getter is not None and self.receptor_ids != receptor_contract_ids():
            raise ValueError("Physics3D receptor surface does not match canonical contract")
        self.last_values: dict[str, float] = {}
        self.last_monotonic_timestamp_ns: int | None = None

    def sample(
        self,
        capabilities: tuple[Capability, ...],
    ) -> tuple[SensorReading, ...]:
        values = dict(self.apparatus.sample_receptors())
        if self.interoception is not None:
            if self._body_state_getter is None:
                raise RuntimeError("body-state getter missing for interoceptive surface")
            values.update(self.interoception.sample(self._body_state_getter()))
        now = time.monotonic_ns()
        requested = {capability.capability_id for capability in capabilities}
        self.last_values = {
            receptor_id: float(value)
            for receptor_id, value in sorted(values.items())
            if receptor_id in requested
        }
        self.last_monotonic_timestamp_ns = now
        return tuple(
            SensorReading(
                capability_id=receptor_id,
                source=self.provider_id,
                value=float(value),
                unit=Unit.RATIO,
                monotonic_timestamp_ns=now,
                quality=ReadingQuality.NOMINAL,
                privacy_class=ReadingPrivacyClass.NON_IDENTIFYING,
            )
            for receptor_id, value in sorted(values.items())
            if receptor_id in requested
        )


def actuator_to_effector_map(
    constitution: ActuatorConstitution,
    apparatus: HumanoidPhysics,
) -> dict[str, str]:
    """Bind opaque inherited actuator ordinals to opaque physical ports."""
    actuator_ids = constitution.actuator_ids
    effector_ids = apparatus.effector_ids
    if len(actuator_ids) != len(effector_ids):
        raise ValueError(
            "physical body effector surface must exactly match motor constitution"
        )
    return {
        actuator_id: effector_ids[index]
        for index, actuator_id in enumerate(actuator_ids)
    }


def body_schema_summary(runtime) -> dict[str, float | int]:
    """Return evaluator-only BodySchema structure without exposing opaque IDs."""
    representation = runtime.body_schema.export_representation(
        current_tick=runtime.tick_count
    )
    parts = representation.get("parts", ())
    dependencies = representation.get("dependencies", ())
    confidence_classes = [
        int(part.get("existence_confidence_class", 0))
        for part in parts
        if isinstance(part, dict)
    ]
    confidence = (
        sum(confidence_classes) / (15.0 * len(confidence_classes))
        if confidence_classes
        else 0.0
    )
    return {
        "confidence": float(confidence),
        "parts": len(parts),
        "sensory_parts": runtime.body_schema.sensory_part_count,
        "cognitive_regions": runtime.body_schema.cognitive_region_count,
        "dependency_evidence": runtime.body_schema.dependency_evidence_count,
        "dependencies": len(dependencies),
    }


__all__ = [
    "OpaqueBodyInteroception",
    "PhysicsDiscoveryProvider",
    "PhysicsReadingProvider",
    "actuator_to_effector_map",
    "body_schema_summary",
    "physics3d_cognition",
    "physics3d_sensory_system",
]
