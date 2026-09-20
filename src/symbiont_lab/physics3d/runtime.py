"""Canonical Symbiont runtime embodied in a PyBullet body.

PyBullet is an apparatus: it supplies physical senses and executes delivered
opaque motor actuation. Cognition, BodySchema, physiology, metabolism, private
experience and SLM state remain inside the canonical organism runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from symbiont.core.physiology import VitalState
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime

from .apparatus import (
    PhysicsDiscoveryProvider,
    PhysicsReadingProvider,
    actuator_to_effector_map,
    body_schema_summary,
    physics3d_cognition,
)
from .humanoid import HumanoidPhysics


@dataclass(frozen=True, slots=True)
class Tick3D:
    tick: int
    alive: bool
    base_position: tuple[float, float, float]
    base_orientation: tuple[float, float, float, float]
    schema_confidence: float
    schema_parts: int
    schema_dependencies: int
    prediction_error: float
    active_effectors: int
    joint_motion: float
    contact_count: int
    slm_records: int
    slm_models: int
    slm_active: bool


class PyBulletEmbodimentRuntime:
    """One canonical organism runtime coupled to one physical PyBullet body."""

    def __init__(
        self,
        *,
        gui: bool = True,
        seed: int = 42,
        time_step: float = 1.0 / 240.0,
        runtime_checkpoint: Mapping[str, Any] | None = None,
        physical_state: Mapping[str, object] | None = None,
    ) -> None:
        try:
            import pybullet as p
        except ImportError as exc:
            raise RuntimeError(
                "PyBullet is optional. Install with: pip install 'symbiont-lab[physics3d]'"
            ) from exc

        self.p = p
        self.time_step = float(time_step)
        mode = p.GUI if gui else p.DIRECT
        self.client_id = p.connect(mode)
        if self.client_id < 0:
            raise RuntimeError("failed to connect to PyBullet")

        p.setGravity(0.0, 0.0, -9.81, physicsClientId=self.client_id)
        p.setTimeStep(self.time_step, physicsClientId=self.client_id)
        p.setPhysicsEngineParameter(
            numSolverIterations=30,
            fixedTimeStep=self.time_step,
            physicsClientId=self.client_id,
        )

        plane_shape = p.createCollisionShape(
            p.GEOM_PLANE,
            planeNormal=(0.0, 0.0, 1.0),
            physicsClientId=self.client_id,
        )
        self.plane_id = p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=plane_shape,
            physicsClientId=self.client_id,
        )
        p.changeDynamics(
            self.plane_id,
            -1,
            lateralFriction=0.95,
            restitution=0.0,
            physicsClientId=self.client_id,
        )

        self.apparatus = HumanoidPhysics(p, self.client_id)
        if physical_state is not None:
            self.apparatus.restore_physical_state(physical_state)

        discovery_provider = PhysicsDiscoveryProvider(self.apparatus)
        reading_provider = PhysicsReadingProvider(self.apparatus)
        host_lifecycle = HostLifecycle(
            discovery=HostDiscovery(providers=(discovery_provider,)),
            reading_providers=(reading_provider,),
        )

        if runtime_checkpoint is None:
            genome, graph, kernel_limits = physics3d_cognition(
                motor_slots=len(self.apparatus.effector_ids)
            )
            self.organism = PrivateModelOrganismRuntime(
                organism_id="symbiont:3d-subject",
                host_lifecycle=host_lifecycle,
                host_reading_providers=(reading_provider,),
                genome=genome,
                cognitive_graph=graph,
                kernel_limits=kernel_limits,
                mutation_seed=seed,
                bootstrap_semantic_senses=False,
                discover_senses=True,
                sensory_plasticity=True,
                interoception_mode="absent",
                min_samples=1,
                actuation_enabled=True,
                motor_exploration_mode="spontaneous",
            )
        else:
            self.organism = PrivateModelOrganismRuntime.from_checkpoint(
                dict(runtime_checkpoint),
                host_lifecycle=host_lifecycle,
                host_reading_providers=(reading_provider,),
                bootstrap_semantic_senses=False,
                discover_senses=True,
                sensory_plasticity=True,
                interoception_mode="absent",
                min_samples=1,
            )

        constitution = self.organism.actuator_constitution
        if constitution is None:
            raise RuntimeError("canonical runtime restored without motor constitution")
        self._actuator_to_effector = actuator_to_effector_map(
            constitution, self.apparatus
        )

        if gui:
            p.resetDebugVisualizerCamera(
                cameraDistance=3.1,
                cameraYaw=38.0,
                cameraPitch=-20.0,
                cameraTargetPosition=(0.0, 0.0, 0.9),
                physicsClientId=self.client_id,
            )
            p.configureDebugVisualizer(
                p.COV_ENABLE_GUI,
                0,
                physicsClientId=self.client_id,
            )

    @property
    def tick_count(self) -> int:
        return int(self.organism.tick_count)

    @property
    def organism_id(self) -> str:
        return self.organism.organism_id

    def checkpoint(self) -> dict[str, Any]:
        """Portable organism state; contains no PyBullet pose or anatomy."""
        return self.organism.checkpoint()

    def _apply_runtime_actuation(self) -> int:
        actuation = self.organism.last_actuation
        physical: dict[str, float] = {}
        active = 0
        if actuation is not None:
            effector_id = self._actuator_to_effector.get(actuation.actuator_id)
            if effector_id is not None:
                physical[effector_id] = float(actuation.delivered)
                if actuation.delivered > 0.05:
                    active = 1
        # Explicitly zero every other physical motor each tick so a previous
        # torque can never persist after the organism stops commanding it.
        self.apparatus.apply_effectors(physical)
        return active

    @staticmethod
    def _prediction_error(result) -> float:
        cognition = result.cognition
        if cognition is None:
            return 0.0
        errors = getattr(cognition, "prediction_errors", ())
        losses = [
            float(getattr(item, "loss", 0.0))
            for item in errors
        ]
        return sum(losses) / len(losses) if losses else 0.0

    def step(self) -> Tick3D:
        result = self.organism.tick()
        active_effectors = self._apply_runtime_actuation()
        self.p.stepSimulation(physicsClientId=self.client_id)

        position, orientation = self.p.getBasePositionAndOrientation(
            self.apparatus.body_id,
            physicsClientId=self.client_id,
        )
        joint_motion = 0.0
        for joint_index in self.apparatus.motor_joint_indices:
            _, velocity, *_ = self.p.getJointState(
                self.apparatus.body_id,
                joint_index,
                physicsClientId=self.client_id,
            )
            joint_motion += abs(float(velocity))

        contact_count = len(
            self.p.getContactPoints(
                bodyA=self.apparatus.body_id,
                physicsClientId=self.client_id,
            )
        )
        schema_confidence, schema_parts, schema_dependencies = body_schema_summary(
            self.organism
        )
        registry = self.organism.model_registry

        return Tick3D(
            tick=self.tick_count,
            alive=(
                result.physiology is None
                or result.physiology.state is not VitalState.DEAD
            ),
            base_position=tuple(float(x) for x in position),
            base_orientation=tuple(float(x) for x in orientation),
            schema_confidence=schema_confidence,
            schema_parts=schema_parts,
            schema_dependencies=schema_dependencies,
            prediction_error=self._prediction_error(result),
            active_effectors=active_effectors,
            joint_motion=float(joint_motion),
            contact_count=contact_count,
            slm_records=len(self.organism.experience_ledger.records),
            slm_models=len(registry.records),
            slm_active=registry.active is not None,
        )

    def motor_activity(self) -> dict[str, float]:
        actuation = self.organism.last_actuation
        if actuation is None:
            return {}
        constitution = self.organism.actuator_constitution
        if constitution is None:
            return {}
        index_by_id = {
            actuator_id: index
            for index, actuator_id in enumerate(constitution.actuator_ids)
        }
        index = index_by_id.get(actuation.actuator_id)
        if index is None:
            return {}
        return {f"motor.{index}": float(actuation.delivered)}

    def close(self) -> None:
        if self.client_id >= 0:
            self.p.disconnect(physicsClientId=self.client_id)
            self.client_id = -1

    def __enter__(self) -> "PyBulletEmbodimentRuntime":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
