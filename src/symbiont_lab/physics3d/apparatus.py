"""PyBullet apparatus adapters for the canonical Symbiont runtime.

PyBullet owns anatomy and physical truth. OrganismRuntime sees only bounded,
opaque sensory capabilities and its inherited opaque actuator surface.
"""
from __future__ import annotations

from dataclasses import replace
import time

from symbiont import __version__ as symbiont_version
from symbiont.actuation.constitution import ActuatorConstitution
from symbiont.cognition.birth import load_actuator_constitution, load_base_cognition
from symbiont.cognition.genome import MotorGenes
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

from .humanoid import HumanoidPhysics


def _running_version() -> tuple[int, int, int]:
    parts = (symbiont_version.split(".") + ["0", "0"])[:3]
    return tuple(int(part) for part in parts)


def physics3d_sensory_system() -> SensorySystem:
    """Body-sized sensory substrate with an explicit bounded checkpoint budget.

    The canonical default (128 KiB) is intentionally conservative for small
    hosts, but a 33-receptor plastic body can legitimately reach 64 active
    sensors plus bounded mutation/selection state. Physics3D therefore grants
    this apparatus 512 KiB while keeping every other sensory bound unchanged.
    """
    limits = SensoryLimits(max_sensor_checkpoint_bytes=512 * 1024)
    return SensorySystem(
        limits=limits,
        plasticity_enabled=True,
    )


def physics3d_cognition(*, motor_slots: int = 28):
    """Canonical germinal cognition with a body-compatible opaque motor surface."""
    if motor_slots < 1 or motor_slots > 64:
        raise ValueError("motor_slots must be within [1, 64]")
    limits = KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=_running_version(),
    )
    genome = replace(
        genome,
        genome_id="genome_symbiont_physics3d_v3",
        parent_ids=(genome.genome_id,),
        development=replace(
            genome.development,
            soft_node_budget=128,
            soft_edge_budget=768,
            sense_node_budget=48,
        ),
        motor=MotorGenes(
            slot_count=motor_slots,
            basal_cost=0.002,
            initial_health=1.0,
            execution_threshold=0.05,
        ),
    )
    return genome, graph, limits


class PhysicsDiscoveryProvider:
    """Expose physical receptors as opaque local read-only capabilities."""

    provider_id = "physics3d-body"

    def __init__(self, apparatus: HumanoidPhysics) -> None:
        self.apparatus = apparatus

    def discover(self) -> tuple[Capability, ...]:
        return tuple(
            Capability(
                capability_id=receptor_id,
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                access=AccessMode.READ_ONLY,
                scope=CapabilityScope.LOCAL,
            )
            for receptor_id in self.apparatus.receptor_ids
        )


class PhysicsReadingProvider:
    """Sample one consistent PyBullet body state for the current runtime tick."""

    provider_id = "physics3d-body"

    def __init__(self, apparatus: HumanoidPhysics) -> None:
        self.apparatus = apparatus
        self.last_values: dict[str, float] = {}
        self.last_monotonic_timestamp_ns: int | None = None

    def sample(
        self,
        capabilities: tuple[Capability, ...],
    ) -> tuple[SensorReading, ...]:
        values = self.apparatus.sample_receptors()
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
    "PhysicsDiscoveryProvider",
    "PhysicsReadingProvider",
    "actuator_to_effector_map",
    "body_schema_summary",
    "physics3d_cognition",
    "physics3d_sensory_system",
]
