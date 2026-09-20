"""Canonical Symbiont runtime embodied in a PyBullet body.

PyBullet is an apparatus: it supplies physical senses and executes delivered
opaque motor actuation. Cognition, BodySchema, physiology, metabolism, private
experience and SLM state remain inside the canonical organism runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
import secrets
import time
from typing import Mapping, Any

from symbiont.core.metabolism import MetabolicLedger
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
from .humanoid import GROUND_MATERIAL, HumanoidPhysics, apply_surface_material
from .resource import PhysicalResource


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
    organism_ms: float
    physics_ms: float
    diagnostics_ms: float
    resource_distance: float
    resource_field: float
    resource_remaining: float
    absorbed_energy: float
    metabolic_reserve_ratio: float
    displacement_from_origin: float
    motor_origin: str
    initial_resource_distance: float
    minimum_resource_distance: float
    resource_progress: float
    motor_origin_cognition: int
    motor_origin_babbling: int
    motor_origin_primitive: int
    motor_origin_mixed: int
    motor_origin_spontaneous: int
    motor_origin_probe: int
    motor_origin_none: int
    motor_repertoire_size: int
    sensorimotor_coverage: float
    sensorimotor_patterns: int
    motor_primitives: int
    cognitive_motor_primitives: int
    best_motor_controllability: float
    best_motor_directional_consistency: float
    primitive_replay_active: bool
    sensorimotor_h1_samples: int
    sensorimotor_h4_samples: int
    sensorimotor_h16_samples: int
    sensorimotor_h64_samples: int
    passive_baseline_samples: int


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
        apply_surface_material(
            p,
            self.plane_id,
            -1,
            GROUND_MATERIAL,
            client_id=self.client_id,
        )

        self.apparatus = HumanoidPhysics(p, self.client_id)
        if physical_state is not None:
            self.apparatus.restore_physical_state(physical_state)
        else:
            self._settle_new_body()

        resource_state = None
        if isinstance(physical_state, Mapping):
            raw_resource = physical_state.get("locomotion_resource")
            if isinstance(raw_resource, Mapping):
                resource_state = raw_resource
        self.resource = PhysicalResource.from_state(
            p,
            self.client_id,
            resource_state,
        )
        base_position, _ = p.getBasePositionAndOrientation(
            self.apparatus.body_id,
            physicsClientId=self.client_id,
        )
        restored_origin = (
            physical_state.get("origin_xy")
            if isinstance(physical_state, Mapping)
            else None
        )
        if (
            isinstance(restored_origin, (list, tuple))
            and len(restored_origin) == 2
        ):
            self._origin_xy = (
                float(restored_origin[0]),
                float(restored_origin[1]),
            )
        else:
            self._origin_xy = (float(base_position[0]), float(base_position[1]))

        current_distance = self.resource.distance_to(
            tuple(float(value) for value in base_position)
        )
        evaluator_state = (
            physical_state.get("locomotion_evaluator")
            if isinstance(physical_state, Mapping)
            else None
        )
        if isinstance(evaluator_state, Mapping):
            self._initial_resource_distance = float(
                evaluator_state.get("initial_resource_distance", current_distance)
            )
            self._minimum_resource_distance = float(
                evaluator_state.get("minimum_resource_distance", current_distance)
            )
            raw_counts = evaluator_state.get("motor_origin_counts", {})
            if not isinstance(raw_counts, Mapping):
                raw_counts = {}
            self._motor_origin_counts = {
                key: int(raw_counts.get(key, 0))
                for key in (
                    "cognition", "babbling", "primitive", "mixed",
                    "spontaneous", "probe", "none"
                )
            }
        else:
            self._initial_resource_distance = current_distance
            self._minimum_resource_distance = current_distance
            self._motor_origin_counts = {
                "cognition": 0,
                "babbling": 0,
                "primitive": 0,
                "mixed": 0,
                "spontaneous": 0,
                "probe": 0,
                "none": 0,
            }

        self._last_physical_state = self._physical_state_payload()
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
            metabolic_capacity = {
                kind: 400.0
                for kind in ("observation", "cognition", "persistence", "maintenance")
            }
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
                metabolism=MetabolicLedger(
                    capacity=metabolic_capacity,
                    replenishment={kind: 0.0 for kind in metabolic_capacity},
                ),
                explicit_metabolism=True,
                interoception_mode="absent",
                min_samples=1,
                auto_promote_predictors=True,
                actuation_enabled=True,
                motor_exploration_mode="babbling",
            )
        else:
            effective = runtime_checkpoint.get("effective_config", {})
            if not isinstance(effective, Mapping) or not bool(
                effective.get("explicit_metabolism", False)
            ):
                raise RuntimeError(
                    "Physics3D locomotion constitution requires a fresh subject; "
                    "start once with --new-symbiont"
                )
            if effective.get("motor_exploration_mode") != "babbling":
                raise RuntimeError(
                    "Physics3D sensorimotor-development constitution requires "
                    "a fresh subject; start once with --new-symbiont"
                )
            raw_genome = runtime_checkpoint.get("genome")
            if (
                not isinstance(raw_genome, Mapping)
                or raw_genome.get("genome_id")
                != "genome_symbiont_physics3d_v2"
            ):
                raise RuntimeError(
                    "Physics3D sensorimotor v2 cognition requires a fresh "
                    "subject; start once with --new-symbiont"
                )
            self.organism = PrivateModelOrganismRuntime.from_checkpoint(
                dict(runtime_checkpoint),
                host_lifecycle=host_lifecycle,
                host_reading_providers=(reading_provider,),
                bootstrap_semantic_senses=False,
                discover_senses=True,
                sensory_plasticity=True,
                explicit_metabolism=True,
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

    def _settle_new_body(
        self,
        *,
        max_steps: int = 1440,
        stable_samples: int = 48,
        linear_threshold: float = 0.025,
        angular_threshold: float = 0.05,
        joint_threshold: float = 0.08,
    ) -> int:
        """Let a newborn body reach passive mechanical equilibrium before tick 0."""
        self.apparatus.apply_effectors({})
        stable = 0
        for step in range(1, max_steps + 1):
            self.apparatus.prepare_physics_substep()
            self.p.stepSimulation(physicsClientId=self.client_id)

            linear_velocity, angular_velocity = self.p.getBaseVelocity(
                self.apparatus.body_id,
                physicsClientId=self.client_id,
            )
            max_linear = max(abs(float(value)) for value in linear_velocity)
            max_angular = max(abs(float(value)) for value in angular_velocity)
            max_joint = 0.0
            for joint_index in self.apparatus.motor_joint_indices:
                _, velocity, *_ = self.p.getJointState(
                    self.apparatus.body_id,
                    joint_index,
                    physicsClientId=self.client_id,
                )
                max_joint = max(max_joint, abs(float(velocity)))

            if (
                max_linear <= linear_threshold
                and max_angular <= angular_threshold
                and max_joint <= joint_threshold
            ):
                stable += 1
                if stable >= stable_samples:
                    return step
            else:
                stable = 0
        return max_steps

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

    def _physical_state_payload(self) -> dict[str, object]:
        state = dict(self.apparatus.export_physical_state())
        state["locomotion_resource"] = self.resource.checkpoint()
        state["origin_xy"] = [float(self._origin_xy[0]), float(self._origin_xy[1])]
        state["locomotion_evaluator"] = {
            "initial_resource_distance": float(self._initial_resource_distance),
            "minimum_resource_distance": float(self._minimum_resource_distance),
            "motor_origin_counts": dict(self._motor_origin_counts),
        }
        return state

    def physical_checkpoint(self) -> tuple[dict[str, object], int]:
        """Return the newest completed physical state and its organism tick."""
        if self.physics_connected():
            try:
                state = self._physical_state_payload()
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
        physical: dict[str, float] = {}
        active = 0
        for actuation in self.organism.last_actuations:
            effector_id = self._actuator_to_effector.get(actuation.actuator_id)
            if effector_id is None:
                continue
            physical[effector_id] = float(actuation.delivered)
            if actuation.delivered > 0.05:
                active += 1
        # Explicitly zero every physical motor not present in the current
        # concurrent vector so stale torque can never leak between ticks.
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

        pre_position, _ = self.p.getBasePositionAndOrientation(
            self.apparatus.body_id,
            physicsClientId=self.client_id,
        )
        metabolic_snapshot = self.organism.metabolism.snapshot()
        reserve_ratio = min(
            metabolic_snapshot.reserve[kind] / max(1e-12, metabolic_snapshot.capacity[kind])
            for kind in metabolic_snapshot.capacity
        )
        resource_field = self.resource.field_at(
            tuple(float(value) for value in pre_position)
        )
        self.apparatus.set_opaque_environment_state(
            external_field=resource_field,
            internal_state=max(0.0, min(1.0, reserve_ratio)),
        )

        phase_started = time.perf_counter()
        result = self.organism.tick()
        organism_ms = (time.perf_counter() - phase_started) * 1000.0

        physics_started = time.perf_counter()
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
        resource_contacted = False
        try:
            for _ in range(self.physics_substeps_per_tick):
                self.apparatus.prepare_physics_substep()
                self.p.stepSimulation(physicsClientId=self.client_id)
                mechanical_work_joules += self.apparatus.mechanical_work_step(self.time_step)
                if not resource_contacted and self.resource.touching(self.apparatus.body_id):
                    resource_contacted = True
        except Exception as exc:
            if not self.physics_connected():
                raise PhysicsServerDisconnected(
                    "PyBullet physics server was closed during integration"
                ) from exc
            raise

        absorbed_energy = 0.0
        if resource_contacted:
            offered = self.resource.offered_material()
            if offered > 0.0:
                absorbed_energy = self.organism.absorb_metabolic_energy(offered)
                if absorbed_energy > 0.0:
                    self.resource.consume_absorbed(absorbed_energy)

        physics_ms = (time.perf_counter() - physics_started) * 1000.0
        diagnostics_started = time.perf_counter()

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

        resource_distance = self.resource.distance_to(
            tuple(float(value) for value in position)
        )
        self._minimum_resource_distance = min(
            self._minimum_resource_distance,
            resource_distance,
        )
        motor_origin = str(self.organism.last_motor_origin)
        if motor_origin not in self._motor_origin_counts:
            motor_origin = "none"
        self._motor_origin_counts[motor_origin] += 1
        reserve_snapshot = self.organism.metabolism.snapshot()
        reserve_ratio_after = min(
            reserve_snapshot.reserve[kind] / max(1e-12, reserve_snapshot.capacity[kind])
            for kind in reserve_snapshot.capacity
        )
        displacement = (
            (float(position[0]) - self._origin_xy[0]) ** 2
            + (float(position[1]) - self._origin_xy[1]) ** 2
        ) ** 0.5

        sensorimotor = self.organism.sensorimotor_snapshot
        horizon_counts = (
            dict(sensorimotor.horizon_samples)
            if sensorimotor is not None
            else {}
        )

        self._last_physical_state = self._physical_state_payload()
        self._last_physical_tick = self.tick_count

        diagnostics_ms = (time.perf_counter() - diagnostics_started) * 1000.0

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
            organism_ms=float(organism_ms),
            physics_ms=float(physics_ms),
            diagnostics_ms=float(diagnostics_ms),
            resource_distance=float(resource_distance),
            resource_field=float(resource_field),
            resource_remaining=float(self.resource.remaining),
            absorbed_energy=float(absorbed_energy),
            metabolic_reserve_ratio=float(reserve_ratio_after),
            displacement_from_origin=float(displacement),
            motor_origin=motor_origin,
            initial_resource_distance=float(self._initial_resource_distance),
            minimum_resource_distance=float(self._minimum_resource_distance),
            resource_progress=float(
                self._initial_resource_distance - resource_distance
            ),
            motor_origin_cognition=int(self._motor_origin_counts["cognition"]),
            motor_origin_babbling=int(self._motor_origin_counts["babbling"]),
            motor_origin_primitive=int(self._motor_origin_counts["primitive"]),
            motor_origin_mixed=int(self._motor_origin_counts["mixed"]),
            motor_origin_spontaneous=int(self._motor_origin_counts["spontaneous"]),
            motor_origin_probe=int(self._motor_origin_counts["probe"]),
            motor_origin_none=int(self._motor_origin_counts["none"]),
            motor_repertoire_size=int(
                len(self.organism.active_motor_repertoire)
            ),
            sensorimotor_coverage=float(
                sensorimotor.babbling_coverage if sensorimotor is not None else 0.0
            ),
            sensorimotor_patterns=int(
                sensorimotor.known_patterns if sensorimotor is not None else 0
            ),
            motor_primitives=int(
                sensorimotor.primitives if sensorimotor is not None else 0
            ),
            cognitive_motor_primitives=int(
                sensorimotor.cognitive_primitives
                if sensorimotor is not None
                else 0
            ),
            best_motor_controllability=float(
                sensorimotor.best_controllability if sensorimotor is not None else 0.0
            ),
            best_motor_directional_consistency=float(
                sensorimotor.best_directional_consistency
                if sensorimotor is not None
                else 0.0
            ),
            primitive_replay_active=bool(
                sensorimotor.replay_active if sensorimotor is not None else False
            ),
            sensorimotor_h1_samples=int(horizon_counts.get(1, 0)),
            sensorimotor_h4_samples=int(horizon_counts.get(4, 0)),
            sensorimotor_h16_samples=int(horizon_counts.get(16, 0)),
            sensorimotor_h64_samples=int(horizon_counts.get(64, 0)),
            passive_baseline_samples=int(
                sensorimotor.passive_baseline_samples
                if sensorimotor is not None
                else 0
            ),
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
        constitution = self.organism.actuator_constitution
        if constitution is None:
            return {}
        index_by_id = {
            actuator_id: index
            for index, actuator_id in enumerate(constitution.actuator_ids)
        }
        activity: dict[str, float] = {}
        for actuation in self.organism.last_actuations:
            index = index_by_id.get(actuation.actuator_id)
            if index is not None:
                activity[f"motor.{index}"] = float(actuation.delivered)
        return activity

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
