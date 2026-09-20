"""Canonical Symbiont runtime embodied in a PyBullet body.

PyBullet is an apparatus: it supplies physical senses and executes delivered
opaque motor actuation. Cognition, BodySchema, physiology, metabolism, private
experience and SLM state remain inside the canonical organism runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
import secrets
from typing import Mapping, Any

from symbiont.core.physiology import VitalState
from symbiont.cognition.types import NodeKind
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime

from .apparatus import (
    PhysicsDiscoveryProvider,
    PhysicsReadingProvider,
    actuator_to_effector_map,
    body_schema_summary,
    physics3d_cognition,
    physics3d_sensory_system,
)
from .humanoid import HumanoidPhysics


class PhysicsServerDisconnected(RuntimeError):
    """Raised when the user closes the PyBullet GUI/server."""


@dataclass(frozen=True, slots=True)
class Tick3D:
    tick: int
    alive: bool
    base_position: tuple[float, float, float]
    base_orientation: tuple[float, float, float, float]
    schema_confidence: float
    schema_parts: int
    schema_sensory_parts: int
    schema_cognitive_regions: int
    schema_dependency_evidence: int
    schema_dependencies: int
    predictor_count: int
    shadow_prediction_count: int
    promotable_shadow_count: int
    prediction_error: float | None
    active_effectors: int
    joint_motion: float
    contact_count: int
    mechanical_work_joules: float
    metabolic_work_cost: float
    slm_records: int
    slm_transition_records: int
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
        physics_substeps_per_tick: int = 8,
        mechanical_work_cost_per_joule: float = 0.001,
        runtime_checkpoint: Mapping[str, Any] | None = None,
        physical_state: Mapping[str, object] | None = None,
        organism_id: str | None = None,
    ) -> None:
        try:
            import pybullet as p
        except ImportError as exc:
            raise RuntimeError(
                "PyBullet is optional. Install with: pip install 'symbiont-lab[physics3d]'"
            ) from exc

        self.p = p
        self.time_step = float(time_step)
        if physics_substeps_per_tick < 1:
            raise ValueError("physics_substeps_per_tick must be >= 1")
        self.physics_substeps_per_tick = int(physics_substeps_per_tick)
        if (
            isinstance(mechanical_work_cost_per_joule, bool)
            or not isinstance(mechanical_work_cost_per_joule, (int, float))
            or not 0.0 <= float(mechanical_work_cost_per_joule) <= 0.1
        ):
            raise ValueError("mechanical_work_cost_per_joule must be within [0, 0.1]")
        self.mechanical_work_cost_per_joule = float(mechanical_work_cost_per_joule)
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

        self._last_physical_state = self.apparatus.export_physical_state()
        self._last_physical_tick = 0

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
            if organism_id is None:
                organism_id = f"symbiont:3d:{secrets.token_hex(8)}"
            self.organism = PrivateModelOrganismRuntime(
                organism_id=organism_id,
                host_lifecycle=host_lifecycle,
                host_reading_providers=(reading_provider,),
                genome=genome,
                cognitive_graph=graph,
                kernel_limits=kernel_limits,
                mutation_seed=seed,
                bootstrap_semantic_senses=False,
                discover_senses=True,
                sensory_system=physics3d_sensory_system(),
                sensory_plasticity=True,
                interoception_mode="absent",
                min_samples=1,
                auto_promote_predictors=True,
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
                auto_promote_predictors=True,
            )

        self._last_physical_tick = self.tick_count

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

    def physics_connected(self) -> bool:
        if self.client_id < 0:
            return False
        try:
            return bool(self.p.isConnected(physicsClientId=self.client_id))
        except Exception:
            return False

    def physical_checkpoint(self) -> tuple[dict[str, object], int]:
        """Return the newest completed physical state and its organism tick."""
        if self.physics_connected():
            try:
                state = self.apparatus.export_physical_state()
                self._last_physical_state = state
                self._last_physical_tick = self.tick_count
            except Exception:
                if self.physics_connected():
                    raise
        return dict(self._last_physical_state), int(self._last_physical_tick)

    def checkpoint(self) -> dict[str, Any]:
        """Portable organism state; contains no PyBullet pose or anatomy."""
        return self.organism.checkpoint()

    def passive_physical_state(self) -> dict[str, object]:
        """Return the last completed pose without querying/rendering PyBullet."""
        return dict(self._last_physical_state)

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
    def _prediction_error(result, *, predictor_count: int) -> float | None:
        if predictor_count <= 0:
            return None
        cognition = result.cognition
        if cognition is None:
            return None
        errors = getattr(cognition, "prediction_errors", ())
        losses = [
            float(getattr(item, "loss", 0.0))
            for item in errors
        ]
        return sum(losses) / len(losses) if losses else None

    def _predictor_count(self) -> int:
        bridge = self.organism.cognitive_bridge
        if bridge is None or bridge.graph is None:
            return 0
        return sum(
            1 for node in bridge.graph.nodes
            if node.kind is NodeKind.PREDICTOR
        )

    def step(self) -> Tick3D:
        if not self.physics_connected():
            raise PhysicsServerDisconnected("PyBullet physics server was closed")
        result = self.organism.tick()
        try:
            active_effectors = self._apply_runtime_actuation()
        except Exception as exc:
            if not self.physics_connected():
                raise PhysicsServerDisconnected(
                    "PyBullet physics server was closed during actuation"
                ) from exc
            raise
        # Hold the organism's motor command while the physical body evolves at
        # its higher-frequency integration rate. Cognition does not need to run
        # at the physics solver frequency.
        mechanical_work_joules = 0.0
        try:
            for _ in range(self.physics_substeps_per_tick):
                self.p.stepSimulation(physicsClientId=self.client_id)
                mechanical_work_joules += self.apparatus.mechanical_work_step(self.time_step)
        except Exception as exc:
            if not self.physics_connected():
                raise PhysicsServerDisconnected(
                    "PyBullet physics server was closed during integration"
                ) from exc
            raise

        metabolic_work_cost = min(
            0.05,
            mechanical_work_joules * self.mechanical_work_cost_per_joule,
        )
        if metabolic_work_cost > 0.0:
            self.organism.register_embodied_work(metabolic_work_cost)

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
        schema = body_schema_summary(self.organism)
        registry = self.organism.model_registry
        predictor_count = self._predictor_count()
        shadow_predictions = self.organism.shadow_predictions
        shadow_prediction_count = len(shadow_predictions)
        promotable_shadow_count = sum(
            1 for candidate in shadow_predictions
            if bool(getattr(candidate, "promotable", False))
        )
        ledger_records = self.organism.experience_ledger.records
        transition_records = sum(
            1 for record in ledger_records
            if record.record_id.startswith("transition.")
        )

        self._last_physical_state = self.apparatus.export_physical_state()
        self._last_physical_tick = self.tick_count

        return Tick3D(
            tick=self.tick_count,
            alive=(
                result.physiology is None
                or result.physiology.state is not VitalState.DEAD
            ),
            base_position=tuple(float(x) for x in position),
            base_orientation=tuple(float(x) for x in orientation),
            schema_confidence=float(schema["confidence"]),
            schema_parts=int(schema["parts"]),
            schema_sensory_parts=int(schema["sensory_parts"]),
            schema_cognitive_regions=int(schema["cognitive_regions"]),
            schema_dependency_evidence=int(schema["dependency_evidence"]),
            schema_dependencies=int(schema["dependencies"]),
            predictor_count=predictor_count,
            shadow_prediction_count=shadow_prediction_count,
            promotable_shadow_count=promotable_shadow_count,
            prediction_error=self._prediction_error(
                result,
                predictor_count=predictor_count,
            ),
            active_effectors=active_effectors,
            joint_motion=float(joint_motion),
            contact_count=contact_count,
            mechanical_work_joules=float(mechanical_work_joules),
            metabolic_work_cost=float(metabolic_work_cost),
            slm_records=len(ledger_records),
            slm_transition_records=transition_records,
            slm_models=len(registry.records),
            slm_active=registry.active is not None,
        )

    def render_camera_frame(
        self,
        *,
        width: int = 900,
        height: int = 600,
        yaw: float = 38.0,
        pitch: float = -20.0,
        distance: float = 3.1,
        target_z: float = 0.85,
    ) -> bytes:
        """Render passive RGB observation from the physical world.

        This is evaluator-only. Camera state never enters cognition or body
        sensing and therefore cannot affect the organism's learned world.
        """
        if not self.physics_connected():
            raise PhysicsServerDisconnected("PyBullet physics server was closed")
        if width < 160 or height < 120:
            raise ValueError("camera frame must be at least 160x120")

        import numpy as np

        base_position, _ = self.p.getBasePositionAndOrientation(
            self.apparatus.body_id,
            physicsClientId=self.client_id,
        )
        target = (
            float(base_position[0]),
            float(base_position[1]),
            float(target_z),
        )
        view = self.p.computeViewMatrixFromYawPitchRoll(
            cameraTargetPosition=target,
            distance=max(1.1, min(8.0, float(distance))),
            yaw=float(yaw),
            pitch=max(-85.0, min(35.0, float(pitch))),
            roll=0.0,
            upAxisIndex=2,
        )
        projection = self.p.computeProjectionMatrixFOV(
            fov=55.0,
            aspect=float(width) / float(height),
            nearVal=0.05,
            farVal=25.0,
        )
        image = self.p.getCameraImage(
            width=int(width),
            height=int(height),
            viewMatrix=view,
            projectionMatrix=projection,
            renderer=self.p.ER_TINY_RENDERER,
            flags=self.p.ER_NO_SEGMENTATION_MASK,
            physicsClientId=self.client_id,
        )
        rgba = np.asarray(image[2], dtype=np.uint8).reshape(
            int(height), int(width), 4
        )
        return rgba[:, :, :3].tobytes()

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
        client_id = self.client_id
        self.client_id = -1
        if client_id < 0:
            return
        try:
            if self.p.isConnected(physicsClientId=client_id):
                self.p.disconnect(physicsClientId=client_id)
        except Exception:
            # Closing the native GUI can tear down the physics server before
            # Python receives control. Shutdown must remain idempotent.
            pass

    def __enter__(self) -> "PyBulletEmbodimentRuntime":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


__all__ = ["PhysicsServerDisconnected", "PyBulletEmbodimentRuntime", "Tick3D"]
