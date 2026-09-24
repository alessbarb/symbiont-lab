"""Canonical Symbiont runtime embodied in a PyBullet body.

PyBullet is an apparatus: it supplies physical senses and executes delivered
opaque motor actuation. Cognition, BodySchema, physiology, metabolism, private
experience and SLM state remain inside the canonical organism runtime.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import math
import secrets
import time
from typing import Mapping, Any

from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.physiology import LivingBodyState, VitalState
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime

from .apparatus import (
    OpaqueBodyInteroception,
    PhysicsDiscoveryProvider,
    PhysicsReadingProvider,
    actuator_to_effector_map,
    body_schema_summary,
    physics3d_cognition,
    physics3d_sensory_system,
)
from .observer_semantics import motor_semantics, sensory_semantics
from .bodies import DEFAULT_BODY_REGISTRY
from .humanoid import apply_surface_material, configure_physics_solver
from .resource import PhysicalResource
from .reembodiment import (
    EmbodimentContract,
    migrate_temporal_domains,
    prepare_fresh_embodiment_checkpoint,
    update_lifecycle_for_checkpoint,
)


class PhysicsServerDisconnected(RuntimeError):
    """Raised when the user closes the PyBullet GUI/server."""


@dataclass(frozen=True, slots=True)
class Tick3D:
    tick: int
    symbiont_tick: int
    alive: bool
    base_position: tuple[float, float, float]
    base_orientation: tuple[float, float, float, float]
    schema_confidence: float
    schema_parts: int
    schema_sensory_parts: int
    schema_cognitive_regions: int
    schema_dependency_evidence: int
    schema_dependencies: int
    embodiment_epoch: int
    body_age_ticks: int
    body_senescence: float
    reacclimation_remaining: int
    reacclimating: bool
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
    motor_origin_detail: str
    initial_resource_distance: float
    minimum_resource_distance: float
    resource_progress: float
    motor_origin_cognition: int
    motor_origin_babbling: int
    motor_origin_primitive: int
    motor_origin_primitive_cognition: int
    motor_origin_primitive_verification: int
    motor_origin_primitive_prospective: int
    prospective_reason: str | None
    prospective_candidates: int
    prospective_selected: bool
    prospective_action_id: str | None
    prospective_predicted_outcome: str | None
    prospective_expected_value: float | None
    prospective_model_confidence: float | None
    prospective_value_confidence: float | None
    prospective_value_samples: int
    prospective_decision_margin: float | None
    prospective_cost: float
    motor_origin_mixed: int
    motor_origin_spontaneous: int
    motor_origin_probe: int
    motor_origin_none: int
    motor_repertoire_size: int
    sensorimotor_coverage: float
    sensorimotor_patterns: int
    motor_primitives: int
    cognitive_motor_primitives: int
    primitive_candidates: int
    recurrent_primitive_candidates: int
    max_primitive_samples: int
    sample_gate_candidates: int
    controllability_gate_candidates: int
    variance_gate_candidates: int
    direction_gate_candidates: int
    full_competence_gate_candidates: int
    best_candidate_controllability: float
    best_candidate_directional_consistency: float
    lowest_recurrent_effect_variance: float | None
    best_motor_controllability: float
    best_motor_directional_consistency: float
    primitive_replay_active: bool
    sensorimotor_h1_samples: int
    sensorimotor_h4_samples: int
    sensorimotor_h16_samples: int
    sensorimotor_h64_samples: int
    passive_baseline_samples: int
    cognitive_concepts: int
    cognitive_readouts: int
    motor_readout_nodes: int
    primitive_readout_nodes: int
    cognitive_motor_output_edges: int
    structural_candidates: int
    structural_producers: int
    oldest_structural_wait_ticks: int
    maturity_nascent: int
    maturity_provisional: int
    maturity_mature: int
    maturity_stable: int
    maturity_weakening: int
    maturity_retiring: int
    joints: tuple[dict[str, float], ...] = ()
    contact_links: tuple[int, ...] = ()


class PyBulletEmbodimentRuntime:
    """One canonical organism runtime coupled to one physical PyBullet body."""

    def __init__(
        self,
        *,
        gui: bool = True,
        seed: int = 42,
        time_step: float = 1.0 / 240.0,
        physics_substeps_per_tick: int = 10,
        mechanical_work_cost_per_joule: float = 0.001,
        capture_physics_trace: bool = False,
        body_kind: str = "anthropomorphic-v4",
        runtime_checkpoint: Mapping[str, Any] | None = None,
        physical_state: Mapping[str, object] | None = None,
        organism_id: str | None = None,
        kernel_limits: KernelLimits | None = None,
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
        self.capture_physics_trace = bool(capture_physics_trace)
        self.body_descriptor = DEFAULT_BODY_REGISTRY.get(body_kind)
        mode = p.GUI if gui else p.DIRECT
        self.client_id = p.connect(mode)
        if self.client_id < 0:
            raise RuntimeError("failed to connect to PyBullet")

        p.setGravity(0.0, 0.0, -9.81, physicsClientId=self.client_id)
        p.setTimeStep(self.time_step, physicsClientId=self.client_id)
        configure_physics_solver(p, self.client_id, self.time_step)

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
            self.body_descriptor.ground_material,
            client_id=self.client_id,
        )

        self.apparatus = self.body_descriptor.apparatus_factory(p, self.client_id)
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

        if physical_state is None:
            body_interoception = OpaqueBodyInteroception(
                receptor_ids=self.body_descriptor.interoceptive_receptor_ids
            )
        else:
            raw_interoception = physical_state.get("body_interoception")
            if not isinstance(raw_interoception, Mapping):
                raise RuntimeError(
                    "Physics3D Living Body L3 requires a fresh subject; "
                    "opaque interoception mapping is missing"
                )
            body_interoception = OpaqueBodyInteroception.from_checkpoint(
                raw_interoception,
                receptor_ids=self.body_descriptor.interoceptive_receptor_ids,
            )
        self._body_interoception = body_interoception

        self._last_physical_state = self._physical_state_payload()
        self._last_physical_tick = 0

        # Passive presentation sampling is deliberately outside organism state.
        # At the default 240 Hz solver rate, every 4th substep yields a 60 Hz
        # physical-pose stream for observers without adding cognition ticks.
        self._presentation_substep = 0
        self._presentation_pose_frames: list[dict[str, object]] = []
        reading_provider = PhysicsReadingProvider(
            self.apparatus,
            body_state_getter=lambda: self.organism.living_body_state,
            interoception=body_interoception,
            expected_receptor_ids=self.body_descriptor.receptor_ids,
        )
        discovery_provider = PhysicsDiscoveryProvider(reading_provider.receptor_ids)
        self._reading_provider = reading_provider
        self._last_telemetry_state: dict[str, object] = {}
        host_lifecycle = HostLifecycle(
            discovery=HostDiscovery(providers=(discovery_provider,)),
            reading_providers=(reading_provider,),
        )

        contract = EmbodimentContract(
            body_kind=self.body_descriptor.body_kind,
            receptor_count=self.body_descriptor.receptor_count,
            effector_count=self.body_descriptor.effector_count,
        )

        def _fresh_organism(subject_id: str) -> PrivateModelOrganismRuntime:
            genome, graph, resolved_limits = physics3d_cognition(
                motor_slots=len(self.apparatus.effector_ids),
                kernel_limits=kernel_limits,
            )
            metabolic_capacity = {
                kind: 400.0
                for kind in ("observation", "cognition", "persistence", "maintenance")
            }
            physical_energy_capacity = sum(metabolic_capacity.values())
            living_body_state = LivingBodyState(
                energy_reserve=physical_energy_capacity,
                max_energy=physical_energy_capacity,
            )
            return PrivateModelOrganismRuntime(
                organism_id=subject_id,
                host_lifecycle=host_lifecycle,
                host_reading_providers=(reading_provider,),
                genome=genome,
                cognitive_graph=graph,
                kernel_limits=resolved_limits,
                mutation_seed=seed,
                bootstrap_semantic_senses=False,
                discover_senses=True,
                sensory_system=physics3d_sensory_system(),
                sensory_plasticity=True,
                metabolism=MetabolicLedger(
                    capacity=metabolic_capacity,
                    replenishment={kind: 0.0 for kind in metabolic_capacity},
                    body_state=living_body_state,
                ),
                living_body_state=living_body_state,
                explicit_metabolism=True,
                interoception_mode="absent",
                min_samples=1,
                auto_promote_predictors=True,
                actuation_enabled=True,
                motor_exploration_mode="babbling",
            )

        if runtime_checkpoint is None:
            if organism_id is None:
                organism_id = f"symbiont:3d:{secrets.token_hex(8)}"
            self.organism = _fresh_organism(organism_id)
            self._embodiment_contract = contract
            self._embodiment_lifecycle: dict[str, Any] | None = None
            self._reembodied = False
        else:
            runtime_checkpoint = migrate_temporal_domains(runtime_checkpoint)
            effective = runtime_checkpoint.get("effective_config", {})
            if not isinstance(effective, Mapping) or not bool(
                effective.get("explicit_metabolism", False)
            ):
                raise RuntimeError(
                    "Physics3D locomotion constitution requires a canonical "
                    "Physics3D Symbiont checkpoint"
                )
            if effective.get("motor_exploration_mode") != "babbling":
                raise RuntimeError(
                    "Physics3D sensorimotor-development constitution requires "
                    "babbling-capable checkpoint state"
                )
            raw_genome = runtime_checkpoint.get("genome")
            if (
                not isinstance(raw_genome, Mapping)
                or raw_genome.get("genome_id")
                != "genome_symbiont_physics3d_v9"
            ):
                raise RuntimeError(
                    "checkpoint is not from the canonical Physics3D Symbiont lineage"
                )

            restored_payload = dict(runtime_checkpoint)
            self._reembodied = physical_state is None
            if self._reembodied:
                subject_id = str(
                    runtime_checkpoint.get("organism_id")
                    or organism_id
                    or f"symbiont:3d:{secrets.token_hex(8)}"
                )
                fresh_template = _fresh_organism(subject_id).checkpoint()
                restored_payload = prepare_fresh_embodiment_checkpoint(
                    runtime_checkpoint,
                    fresh_template,
                    contract=contract,
                )

            raw_lifecycle = restored_payload.get("embodiment_lifecycle")
            self._embodiment_lifecycle = (
                deepcopy(raw_lifecycle)
                if isinstance(raw_lifecycle, dict)
                else None
            )
            self.organism = PrivateModelOrganismRuntime.from_checkpoint(
                restored_payload,
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
            self._embodiment_contract = contract

        current_lifecycle = (
            self._embodiment_lifecycle.get("current")
            if isinstance(self._embodiment_lifecycle, Mapping)
            else None
        )
        raw_epoch_metrics = (
            current_lifecycle.get("metrics")
            if isinstance(current_lifecycle, Mapping)
            else None
        )
        raw_epoch_metrics = raw_epoch_metrics if isinstance(raw_epoch_metrics, Mapping) else {}
        self._epoch_metrics: dict[str, Any] = {
            "absorbed_material_total": float(raw_epoch_metrics.get("absorbed_material_total") or 0.0),
            "mechanical_work_total": float(raw_epoch_metrics.get("mechanical_work_total") or 0.0),
            "physiological_cost_total": float(raw_epoch_metrics.get("physiological_cost_total") or 0.0),
            "reacclimation_ticks_consumed": int(raw_epoch_metrics.get("reacclimation_ticks_consumed") or 0),
            "reacclimation_completed": bool(raw_epoch_metrics.get("reacclimation_completed", False)),
            "vital_state_ticks": dict(raw_epoch_metrics.get("vital_state_ticks") or {}),
        }
        self._last_physical_tick = self.tick_count
        self._telemetry_seen_experience_ids = {
            str(record.record_id)
            for record in self.organism.experience_ledger.records
        }
        self._telemetry_last_ledger_index = len(self.organism.experience_ledger.records)
        self._telemetry_transition_records_count = sum(
            1 for record in self.organism.experience_ledger.records
            if record.record_id.startswith("transition.")
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
            if hasattr(self.p, "getJointStates"):
                raw_joint_states = self.p.getJointStates(
                    self.apparatus.body_id,
                    self.apparatus.motor_joint_indices,
                    physicsClientId=self.client_id,
                )
            else:
                raw_joint_states = [
                    self.p.getJointState(self.apparatus.body_id, j, physicsClientId=self.client_id)
                    for j in self.apparatus.motor_joint_indices
                ]
            max_joint = max((abs(float(state[1])) for state in raw_joint_states), default=0.0)

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

    @property
    def embodiment_epoch(self) -> int:
        lifecycle = self._embodiment_lifecycle
        if isinstance(lifecycle, Mapping):
            try:
                return max(1, int(lifecycle.get("epoch") or 1))
            except (TypeError, ValueError):
                pass
        return 1

    @property
    def historical_private_model_candidates(self) -> tuple[str, ...]:
        lifecycle = self._embodiment_lifecycle
        current = lifecycle.get("current") if isinstance(lifecycle, Mapping) else None
        raw = current.get("candidate_private_model_ids") if isinstance(current, Mapping) else None
        if not isinstance(raw, list):
            return ()
        return tuple(
            str(value)
            for value in raw
            if isinstance(value, str) and value
        )
    def physics_connected(self) -> bool:
        if self.client_id < 0:
            return False
        try:
            return bool(self.p.isConnected(physicsClientId=self.client_id))
        except Exception:
            return False

    def _physical_state_payload(
        self, physical_state: dict[str, object] | None = None
    ) -> dict[str, object]:
        state = dict(
            self.apparatus.export_physical_state()
            if physical_state is None
            else physical_state
        )
        state["locomotion_resource"] = self.resource.checkpoint()
        state["body_interoception"] = self._body_interoception.checkpoint()
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

    def checkpoint(self, *, lifecycle_state: str = "active") -> dict[str, Any]:
        """Portable Symbiont state plus body-independent embodiment history."""
        payload = self.organism.checkpoint()
        if self._embodiment_lifecycle is not None:
            payload["embodiment_lifecycle"] = deepcopy(self._embodiment_lifecycle)
        payload = update_lifecycle_for_checkpoint(
            payload,
            contract=self._embodiment_contract,
            state=lifecycle_state,
            metrics=self._epoch_metrics,
        )
        self._embodiment_lifecycle = deepcopy(payload["embodiment_lifecycle"])
        return payload

    def passive_physical_state(self) -> dict[str, object]:
        """Return the last completed pose without querying/rendering PyBullet."""
        return dict(self._last_physical_state)

    def drain_presentation_pose_frames(self) -> list[dict[str, object]]:
        """Drain passive 60 Hz pose samples captured during physics integration.

        These frames are observer-only. They are not checkpointed, sensed,
        learned from, or exposed to the organism.
        """
        frames = self._presentation_pose_frames
        self._presentation_pose_frames = []
        return frames

    def passive_telemetry_state(self) -> dict[str, object]:
        """Return the last completed rich evaluator snapshot.

        This surface is write-only from the experiment's perspective: callers may
        persist or analyze it, but it never feeds back into cognition.
        """
        return dict(self._last_telemetry_state)

    @classmethod
    def _telemetry_value(cls, value):
        t = type(value)
        if t in (str, int, bool) or value is None:
            return value
        if t is float:
            return value if math.isfinite(value) else None
        if t is dict:
            return {
                (k if type(k) is str else str(k)): cls._telemetry_value(v)
                for k, v in value.items()
            }
        if t in (list, tuple, set):
            return [cls._telemetry_value(item) for item in value]
        if isinstance(value, Enum):
            return cls._telemetry_value(value.value)
        if hasattr(value, "__dataclass_fields__"):
            return {
                f_name: cls._telemetry_value(getattr(value, f_name))
                for f_name in value.__dataclass_fields__
            }
        if isinstance(value, Mapping):
            return {
                str(key): cls._telemetry_value(item)
                for key, item in value.items()
            }
        return str(value)

    @staticmethod
    def _metabolism_payload(snapshot) -> dict[str, object]:
        reserve = {
            str(key): float(value)
            for key, value in dict(getattr(snapshot, "reserve", {}) or {}).items()
        }
        capacity = {
            str(key): float(value)
            for key, value in dict(getattr(snapshot, "capacity", {}) or {}).items()
        }
        return {
            "reserve": reserve,
            "capacity": capacity,
            "pressure": str(getattr(getattr(snapshot, "pressure", None), "value", getattr(snapshot, "pressure", "unknown"))),
        }

    @staticmethod
    def _cognitive_topology_payload(bridge) -> dict[str, object] | None:
        """Bounded evaluator-only structural projection of the live graph."""
        if bridge is None:
            return None
        graph = getattr(bridge, "graph", None)
        if graph is None:
            return None

        nodes = []
        for node in tuple(getattr(graph, "nodes", ())):
            kind = getattr(getattr(node, "kind", None), "value", getattr(node, "kind", "concept"))
            nodes.append({
                "node_id": str(getattr(node, "node_id", ""))[:128],
                "kind": str(kind),
                "predicts_node_id": (
                    str(getattr(node, "predicts_node_id"))[:128]
                    if getattr(node, "predicts_node_id", None) is not None
                    else None
                ),
                "bias": float(getattr(node, "bias", 0.0)),
                "tau": float(getattr(node, "tau", 1.0)),
            })

        edges = []
        for edge in tuple(getattr(graph, "edges", ())):
            kind = getattr(getattr(edge, "kind", None), "value", getattr(edge, "kind", "excitatory"))
            edges.append({
                "source_id": str(getattr(edge, "source_id", ""))[:128],
                "target_id": str(getattr(edge, "target_id", ""))[:128],
                "kind": str(kind),
                "weight": float(getattr(edge, "weight", 0.0)),
                "plasticity": float(getattr(edge, "plasticity", 0.0)),
                "delay_ticks": int(getattr(edge, "delay_ticks", 0)),
                "support": int(getattr(edge, "support", 0)),
                "age_ticks": int(getattr(edge, "age_ticks", 0)),
                "stable_ticks": int(getattr(edge, "stable_ticks", 0)),
                "last_use_tick": int(getattr(edge, "last_use_tick", 0)),
            })

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _cognition_payload(cognition) -> dict[str, object]:
        if cognition is None:
            return {}
        prediction_errors = []
        for item in tuple(getattr(cognition, "prediction_errors", ())):
            prediction_errors.append(
                {
                    "predictor_id": str(getattr(item, "predictor_id", "")),
                    "target_id": str(getattr(item, "target_id", "")),
                    "error": float(getattr(item, "error", 0.0)),
                    "loss": float(getattr(item, "loss", 0.0)),
                }
            )
        mutations = []
        for mutation in tuple(getattr(cognition, "mutations", ())):
            mutations.append(
                {
                    "kind": str(getattr(mutation, "kind", "")),
                    "payload": PyBulletEmbodimentRuntime._telemetry_value(
                        dict(getattr(mutation, "payload", {}) or {})
                    ),
                }
            )
        health = getattr(cognition, "topology_health", "germinal")
        return {
            "activations": {
                str(key): float(value)
                for key, value in dict(getattr(cognition, "activations", {}) or {}).items()
            },
            "readouts": {
                str(key): float(value)
                for key, value in dict(getattr(cognition, "readouts", {}) or {}).items()
            },
            "motor_readouts": {
                str(key): float(value)
                for key, value in dict(getattr(cognition, "motor_readouts", {}) or {}).items()
            },
            "primitive_readouts": {
                str(key): float(value)
                for key, value in dict(getattr(cognition, "primitive_readouts", {}) or {}).items()
            },
            "prediction_errors": prediction_errors,
            "mutations": mutations,
            "structural_mutations_applied": int(getattr(cognition, "structural_mutations_applied", 0)),
            "frozen": bool(getattr(cognition, "frozen", False)),
            "topology_revision": int(getattr(cognition, "topology_revision", 0)),
            "topology_health": str(getattr(health, "value", health)),
            "recovering": bool(getattr(cognition, "recovering", False)),
            "consecutive_failures": int(getattr(cognition, "consecutive_failures", 0)),
            "recycling_events": [
                dict(item) for item in tuple(getattr(cognition, "recycling_events", ()))
                if isinstance(item, Mapping)
            ],
            "stranded_concepts": list(getattr(cognition, "stranded_concepts", ()) or ()),
            "predictive_gain": float(getattr(cognition, "predictive_gain", 0.0)),
            "active_concept_ids": list(getattr(cognition, "active_concept_ids", ()) or ()),
            "retiring_predictors": list(getattr(cognition, "retiring_predictors", ()) or ()),
            "retirement_edges": int(getattr(cognition, "retirement_edges", 0)),
            "structural_candidates": int(getattr(cognition, "structural_candidates", 0)),
            "structural_producers": int(getattr(cognition, "structural_producers", 0)),
            "oldest_structural_wait_ticks": int(getattr(cognition, "oldest_structural_wait_ticks", 0)),
            "representation_maturity": dict(getattr(cognition, "representation_maturity", {}) or {}),
            "max_contention_losses": int(getattr(cognition, "max_contention_losses", 0)),
        }

    def _action_payload(self) -> dict[str, object]:
        actuations = []
        for actuation in self.organism.last_actuations:
            actuations.append(
                {
                    "actuator_id": str(actuation.actuator_id),
                    "effector_id": self._actuator_to_effector.get(actuation.actuator_id),
                    "requested": float(actuation.requested),
                    "delivered": float(actuation.delivered),
                    "cost": float(actuation.cost),
                    "health_at_execution": float(actuation.health_at_execution),
                }
            )
        return {
            "origin": str(self.organism.last_motor_origin),
            "origin_detail": str(self.organism.last_motor_origin_detail),
            "actuations": actuations,
        }

    def _contact_payload(self) -> list[dict[str, object]]:
        contacts = self.p.getContactPoints(
            bodyA=self.apparatus.body_id,
            physicsClientId=self.client_id,
        )
        payload: list[dict[str, object]] = []
        for item in contacts:
            payload.append(
                {
                    "body_a": int(item[1]),
                    "body_b": int(item[2]),
                    "link_a": int(item[3]),
                    "link_b": int(item[4]),
                    "position_a": [float(value) for value in item[5]],
                    "position_b": [float(value) for value in item[6]],
                    "normal_on_b": [float(value) for value in item[7]],
                    "distance": float(item[8]),
                    "normal_force": float(item[9]),
                    "lateral_friction_1": float(item[10]) if len(item) > 10 else 0.0,
                    "lateral_friction_2": float(item[12]) if len(item) > 12 else 0.0,
                }
            )
        return payload

    def _physics_trace_sample(self, substep: int) -> dict[str, object]:
        base_position, base_orientation = self.p.getBasePositionAndOrientation(
            self.apparatus.body_id,
            physicsClientId=self.client_id,
        )
        linear_velocity, angular_velocity = self.p.getBaseVelocity(
            self.apparatus.body_id,
            physicsClientId=self.client_id,
        )
        if hasattr(self.p, "getJointStates"):
            raw_joint_states = self.p.getJointStates(
                self.apparatus.body_id,
                self.apparatus.motor_joint_indices,
                physicsClientId=self.client_id,
            )
        else:
            raw_joint_states = [
                self.p.getJointState(self.apparatus.body_id, j, physicsClientId=self.client_id)
                for j in self.apparatus.motor_joint_indices
            ]
        for joint_index, state in zip(self.apparatus.motor_joint_indices, raw_joint_states):
            joints.append(
                {
                    "joint_index": int(joint_index),
                    "position": float(state[0]),
                    "velocity": float(state[1]),
                    "commanded_torque": float(
                        self.apparatus._applied_torque_by_joint.get(joint_index, 0.0)
                    ),
                }
            )
        return {
            "substep": int(substep),
            "base_position": [float(value) for value in base_position],
            "base_orientation": [float(value) for value in base_orientation],
            "linear_velocity": [float(value) for value in linear_velocity],
            "angular_velocity": [float(value) for value in angular_velocity],
            "joints": joints,
            "contacts": self._contact_payload(),
        }

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

    def _cognitive_node_counts(self) -> tuple[int, int, int, int]:
        bridge = self.organism.cognitive_bridge
        if bridge is None or bridge.graph is None:
            return 0, 0, 0, 0
        concepts = sum(
            1 for node in bridge.graph.nodes
            if node.kind is NodeKind.CONCEPT
        )
        core_readouts = sum(
            1
            for node in bridge.graph.nodes
            if (
                node.kind is NodeKind.READOUT
                and not node.node_id.startswith("readout_motor:")
                and not node.node_id.startswith("readout_primitive:")
            )
        )
        motor_readouts = sum(
            1
            for node in bridge.graph.nodes
            if node.kind is NodeKind.READOUT
            and node.node_id.startswith("readout_motor:")
        )
        primitive_readouts = sum(
            1
            for node in bridge.graph.nodes
            if node.kind is NodeKind.READOUT
            and node.node_id.startswith("readout_primitive:")
        )
        return concepts, core_readouts, motor_readouts, primitive_readouts


    def _cognitive_motor_output_edge_count(self) -> int:
        bridge = self.organism.cognitive_bridge
        if bridge is None or bridge.graph is None:
            return 0
        return sum(
            1
            for edge in bridge.graph.edges
            if (
                edge.target_id.startswith("readout_motor:")
                or edge.target_id.startswith("readout_primitive:")
            )
        )

    def step(self) -> Tick3D:
        if not self.physics_connected():
            raise PhysicsServerDisconnected("PyBullet physics server was closed")

        pre_physical_state = self.apparatus.export_physical_state()
        pre_position = tuple(float(value) for value in pre_physical_state["base_position"])
        metabolic_snapshot = self.organism.metabolism.snapshot()
        resource_field = self.resource.field_at(
            tuple(float(value) for value in pre_position)
        )
        self.apparatus.set_opaque_environment_state(
            external_field=resource_field,
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
        physics_trace: list[dict[str, object]] = []
        base_path_length = 0.0
        max_contact_force = 0.0
        contact_normal_impulse = 0.0
        previous_substep_position = tuple(float(value) for value in pre_position)
        try:
            for substep in range(self.physics_substeps_per_tick):
                self.apparatus.prepare_physics_substep()
                self.p.stepSimulation(physicsClientId=self.client_id)
                mechanical_work_joules += self.apparatus.mechanical_work_step(self.time_step)

                self._presentation_substep += 1
                if self._presentation_substep % 4 == 0:
                    pose = self.apparatus.export_physical_state()
                    self._presentation_pose_frames.append(
                        {
                            "tick": int(self.tick_count),
                            "substep_index": int(substep),
                            "physics_step": int(self._presentation_substep),
                            "simulation_time_s": float(
                                self._presentation_substep * self.time_step
                            ),
                            "tick_simulation_span_s": float(
                                self.physics_substeps_per_tick * self.time_step
                            ),
                            "physical_state": pose,
                        }
                    )
                    if len(self._presentation_pose_frames) > 8:
                        del self._presentation_pose_frames[:-8]

                current_position, _ = self.p.getBasePositionAndOrientation(
                    self.apparatus.body_id,
                    physicsClientId=self.client_id,
                )
                current_position = (float(current_position[0]), float(current_position[1]), float(current_position[2]))
                dx = current_position[0] - previous_substep_position[0]
                dy = current_position[1] - previous_substep_position[1]
                dz = current_position[2] - previous_substep_position[2]
                base_path_length += math.sqrt(dx * dx + dy * dy + dz * dz)
                previous_substep_position = current_position

                contacts_now = self.p.getContactPoints(
                    bodyA=self.apparatus.body_id,
                    physicsClientId=self.client_id,
                )
                for contact in contacts_now:
                    normal_force = max(0.0, float(contact[9]))
                    max_contact_force = max(max_contact_force, normal_force)
                    contact_normal_impulse += normal_force * self.time_step
                    if not resource_contacted and (
                        contact[2] == self.resource.body_id or contact[1] == self.resource.body_id
                    ):
                        resource_contacted = True

                if self.capture_physics_trace:
                    physics_trace.append(self._physics_trace_sample(substep))

                if (
                    not resource_contacted
                    and self.resource.distance_to(current_position) < 1.8
                    and self.resource.touching(self.apparatus.body_id)
                ):
                    resource_contacted = True
        except Exception as exc:
            if not self.physics_connected():
                raise PhysicsServerDisconnected(
                    "PyBullet physics server was closed during integration"
                ) from exc
            raise

        absorbed_energy = 0.0
        if resource_contacted and self.organism.living_body_state.alive:
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

        raw_physical_state = self.apparatus.export_physical_state()
        position = tuple(float(value) for value in raw_physical_state["base_position"])
        orientation = tuple(float(value) for value in raw_physical_state["base_orientation"])
        joint_motion = sum(
            abs(float(j["velocity"]))
            for j in raw_physical_state.get("joints", ())
            if isinstance(j, dict)
        )
        contact_count = int(
            raw_physical_state.get(
                "contact_count",
                len(raw_physical_state.get("contact_links", ())),
            )
        )
        schema = body_schema_summary(self.organism)
        registry = self.organism.model_registry
        predictor_count = self._predictor_count()
        (
            concept_count,
            readout_count,
            motor_readout_nodes,
            primitive_readout_nodes,
        ) = self._cognitive_node_counts()
        cognition = result.cognition
        maturity = (
            dict(getattr(cognition, "representation_maturity", {}) or {})
            if cognition is not None
            else {}
        )
        shadow_predictions = self.organism.shadow_predictions
        shadow_prediction_count = len(shadow_predictions)
        promotable_shadow_count = sum(
            1 for candidate in shadow_predictions
            if bool(getattr(candidate, "promotable", False))
        )
        ledger_records = self.organism.experience_ledger.records
        if self._telemetry_last_ledger_index > len(ledger_records):
            self._telemetry_last_ledger_index = 0
            self._telemetry_seen_experience_ids.clear()
            self._telemetry_transition_records_count = 0

        new_slice = ledger_records[self._telemetry_last_ledger_index:]
        self._telemetry_last_ledger_index = len(ledger_records)

        new_experience_records = []
        for record in new_slice:
            rec_id = str(record.record_id)
            if rec_id not in self._telemetry_seen_experience_ids:
                self._telemetry_seen_experience_ids.add(rec_id)
                new_experience_records.append(record.canonical_payload())
            if rec_id.startswith("transition."):
                self._telemetry_transition_records_count += 1
        transition_records = self._telemetry_transition_records_count

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
        motor_origin_detail = str(self.organism.last_motor_origin_detail)
        if not hasattr(self, "_motor_origin_detail_counts"):
            self._motor_origin_detail_counts = {
                "primitive_cognition": 0,
                "primitive_verification": 0,
                "primitive_prospective": 0,
            }
        if motor_origin_detail in self._motor_origin_detail_counts:
            self._motor_origin_detail_counts[motor_origin_detail] += 1
        reserve_snapshot = self.organism.metabolism.snapshot()
        body_energy = self.organism.living_body_state
        reserve_ratio_after = body_energy.energy_reserve / max(
            1e-12,
            body_energy.max_energy,
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

        self._last_physical_state = self._physical_state_payload(raw_physical_state)
        self._last_physical_tick = self.tick_count

        body_schema_representation = self.organism.body_schema.export_representation(
            current_tick=self.tick_count
        )
        sensorimotor_payload = {}
        if sensorimotor is not None:
            motor_primitives = [
                {
                    **primitive.checkpoint(),
                    "cognitive": bool(primitive.is_competence),
                }
                for primitive in self.organism.sensorimotor_primitives
            ]
            actuator_evidence = []
            for state in self.organism.actuator_causal_states:
                relations = []
                for percept_id, relation in sorted(state.effect_relations.items()):
                    correlation = relation.correlation
                    if correlation is None:
                        continue
                    relations.append({
                        "percept_id": str(percept_id),
                        "samples": int(relation.count),
                        "correlation": float(correlation),
                    })
                actuator_evidence.append({
                    "actuator_id": str(state.actuator_id),
                    "state": str(state.probing_state),
                    "activations": int(state.activations),
                    "effect_strength": float(state.effect_strength),
                    "relations": relations,
                })
            sensorimotor_payload = {
                "babbling_coverage": float(sensorimotor.babbling_coverage),
                "known_patterns": int(sensorimotor.known_patterns),
                "primitives": int(sensorimotor.primitives),
                "cognitive_primitives": int(sensorimotor.cognitive_primitives),
                "best_controllability": float(sensorimotor.best_controllability),
                "best_directional_consistency": float(sensorimotor.best_directional_consistency),
                "replay_active": bool(sensorimotor.replay_active),
                "replay_primitive_id": sensorimotor.replay_primitive_id,
                "horizon_samples": {
                    str(key): int(value)
                    for key, value in dict(sensorimotor.horizon_samples).items()
                },
                "passive_baseline_samples": int(sensorimotor.passive_baseline_samples),
                "active_motor_repertoire": list(self.organism.active_motor_repertoire),
                "motor_primitives": motor_primitives,
                "episodes": [
                    {
                        "primitive_id": episode.primitive_id,
                        "start_tick": int(episode.start_tick),
                        "end_tick": int(episode.end_tick),
                        "source": episode.source,
                        "evidence_blocks": list(episode.evidence_blocks),
                        "sample_index": int(episode.sample_index),
                        "materialized": bool(episode.materialized),
                        "competence": bool(episode.competence),
                    }
                    for episode in self.organism.sensorimotor_episodes
                ],
                "actuator_evidence": actuator_evidence,
            }

        self._epoch_metrics["absorbed_material_total"] = float(
            self._epoch_metrics.get("absorbed_material_total", 0.0)
        ) + float(absorbed_energy)
        self._epoch_metrics["mechanical_work_total"] = float(
            self._epoch_metrics.get("mechanical_work_total", 0.0)
        ) + float(mechanical_work_joules)
        self._epoch_metrics["physiological_cost_total"] = float(
            self._epoch_metrics.get("physiological_cost_total", 0.0)
        ) + float(metabolic_work_cost)
        if self.organism.reacclimation_remaining > 0:
            self._epoch_metrics["reacclimation_ticks_consumed"] = int(
                self._epoch_metrics.get("reacclimation_ticks_consumed", 0)
            ) + 1
        else:
            self._epoch_metrics["reacclimation_completed"] = True
        state_name = str(
            getattr(
                getattr(result, "physiology", None),
                "state",
                "unknown",
            ).value
            if getattr(getattr(result, "physiology", None), "state", None) is not None
            else "unknown"
        )
        vital_counts = self._epoch_metrics.setdefault("vital_state_ticks", {})
        if isinstance(vital_counts, dict):
            vital_counts[state_name] = int(vital_counts.get(state_name, 0)) + 1
        physiology_state = getattr(result, "physiology", None)
        prospective_decision = self.organism.last_prospective_decision
        prospective_reason = (
            prospective_decision.reason
            if prospective_decision is not None
            else None
        )
        prospective_payload = {
            "reason": prospective_reason,
            "candidate_count": int(
                self.organism.last_prospective_query_count
            ),
            "selected": bool(
                prospective_decision is not None
                and prospective_decision.reason == "selected"
            ),
            "action_id": (
                prospective_decision.candidate_id
                if prospective_decision is not None
                else None
            ),
            "predicted_outcome": (
                prospective_decision.predicted_outcome
                if prospective_decision is not None
                else None
            ),
            "expected_value": (
                prospective_decision.expected_value
                if prospective_decision is not None
                else None
            ),
            "model_confidence": (
                prospective_decision.model_confidence
                if prospective_decision is not None
                else None
            ),
            "value_confidence": (
                prospective_decision.value_confidence
                if prospective_decision is not None
                else None
            ),
            "value_samples": int(
                self.organism.last_prospective_value_samples
            ),
            "decision_margin": (
                prospective_decision.decision_margin
                if prospective_decision is not None
                else None
            ),
            "query_cost": float(self.organism.last_prospective_cost),
            "known_outcome_values": int(
                self.organism.prospective_outcome_value_count
            ),
        }
        self._last_telemetry_state = {
            "schema_version": 3,
            "tick": int(self.tick_count),
            "organism_id": str(self.organism_id),
            "pre": {
                "physical": pre_physical_state,
                "resource": {
                    "field": float(resource_field),
                    "state": self.resource.checkpoint(),
                },
                "metabolism": {
                    **self._metabolism_payload(metabolic_snapshot),
                    "physical_energy_reserve": float(
                        self.organism.living_body_state.energy_reserve
                    ),
                    "physical_energy_capacity": float(
                        self.organism.living_body_state.max_energy
                    ),
                    "physical_energy_ratio": float(reserve_ratio_after),
                },
                "sensory_input": {
                    "monotonic_timestamp_ns": self._reading_provider.last_monotonic_timestamp_ns,
                    "values": dict(self._reading_provider.last_values),
                },
            },
            "observer_semantics": {
                "sensory": sensory_semantics(
                    self.organism.sensory_system.sensors,
                    joint_specs=self.body_descriptor.observer_joint_specs,
                    contact_region_names=(
                        self.body_descriptor.observer_contact_region_names
                    ),
                    interoceptive_source_ordinals=(
                        self._body_interoception.source_ordinals_by_slot
                    ),
                ),
                "motor": motor_semantics(
                    self._actuator_to_effector,
                    joint_specs=self.body_descriptor.observer_joint_specs,
                ),
                "provenance": {
                    "owner": "observer",
                    "source": "physics3d-apparatus",
                    "feeds_back": False,
                },
            },
            "runtime": {
                "percepts": self._telemetry_value(result.percepts),
                "narrative": self._telemetry_value(getattr(result, "narrative", ())),
                "allocations": self._telemetry_value(result.allocations),
                "perceptual_allocations": self._telemetry_value(
                    result.perceptual_allocations
                ),
                "investigated_capability": result.investigated_capability,
                "evidence_gathered": int(result.evidence_gathered),
                "signal_knowledge": self._telemetry_value(result.signal_knowledge),
                "knowledge_events": self._telemetry_value(result.knowledge_events),
                "signal_references": self._telemetry_value(result.signal_references),
                "assimilation": self._telemetry_value(result.assimilation),
                "homeostasis": self._telemetry_value(result.homeostasis),
                "homeostatic_deviation": float(
                    self.organism.homeostatic_deviation
                ),
                "pending_homeostatic_credit": int(
                    self.organism.pending_homeostatic_credit_count
                ),
                "prospective_agency": prospective_payload,
                "development": self._telemetry_value(result.development),
                "sensory_phenotype": self._telemetry_value(result.sensory_phenotype),
                "runtime_events": list(result.runtime_events),
                "motor_intents": self._telemetry_value(result.motor_intents),
                "experience_records_created": new_experience_records,
            },
            "cognition": self._cognition_payload(cognition),
            "cognitive_topology": self._cognitive_topology_payload(
                getattr(self.organism, "cognitive_bridge", None)
            ),
            "action": self._action_payload(),
            "physics": {
                "substeps": int(self.physics_substeps_per_tick),
                "mechanical_work_joules": float(mechanical_work_joules),
                "resource_contacted": bool(resource_contacted),
                "contact_count": int(contact_count),
                "base_path_length": float(base_path_length),
                "max_contact_normal_force": float(max_contact_force),
                "contact_normal_impulse": float(contact_normal_impulse),
                "final_contacts": self._contact_payload(),
                "raw_substeps": physics_trace if self.capture_physics_trace else None,
            },
            "post": {
                "physical": dict(self._last_physical_state),
                "resource": {
                    "distance": float(resource_distance),
                    "remaining": float(self.resource.remaining),
                    "absorbed_energy": float(absorbed_energy),
                },
                "metabolism": self._metabolism_payload(reserve_snapshot),
                "physiology": {
                    "state": str(getattr(getattr(physiology_state, "state", None), "value", getattr(physiology_state, "state", "unknown"))),
                    "transitions": int(getattr(physiology_state, "transitions", 0) or 0),
                    "death_tick": getattr(physiology_state, "death_tick", None),
                } if physiology_state is not None else None,
            },
            "self_model": self.organism.self_model.export(
                current_tick=self.tick_count
            ),
            "body_schema": body_schema_representation,
            "outcome": {
                "initial_resource_distance": float(self._initial_resource_distance),
                "minimum_resource_distance": float(self._minimum_resource_distance),
                "current_resource_distance": float(resource_distance),
                "resource_progress": float(
                    self._initial_resource_distance - resource_distance
                ),
                "resource_remaining": float(self.resource.remaining),
                "absorbed_energy": float(absorbed_energy),
            },
            "sensorimotor": {
                **sensorimotor_payload,
                "primitive_candidates": int(
                    sensorimotor.primitive_candidates if sensorimotor is not None else 0
                ),
                "recurrent_primitive_candidates": int(
                    sensorimotor.recurrent_primitive_candidates if sensorimotor is not None else 0
                ),
                "max_primitive_samples": int(
                    sensorimotor.max_primitive_samples if sensorimotor is not None else 0
                ),
                "sample_gate_candidates": int(
                    sensorimotor.sample_gate_candidates if sensorimotor is not None else 0
                ),
                "controllability_gate_candidates": int(
                    sensorimotor.controllability_gate_candidates if sensorimotor is not None else 0
                ),
                "variance_gate_candidates": int(
                    sensorimotor.variance_gate_candidates if sensorimotor is not None else 0
                ),
                "direction_gate_candidates": int(
                    sensorimotor.direction_gate_candidates if sensorimotor is not None else 0
                ),
                "full_competence_gate_candidates": int(
                    sensorimotor.full_competence_gate_candidates if sensorimotor is not None else 0
                ),
                "best_candidate_controllability": float(
                    sensorimotor.best_candidate_controllability if sensorimotor is not None else 0.0
                ),
                "best_candidate_directional_consistency": float(
                    sensorimotor.best_candidate_directional_consistency if sensorimotor is not None else 0.0
                ),
                "lowest_recurrent_effect_variance": (
                    sensorimotor.lowest_recurrent_effect_variance
                    if sensorimotor is not None
                    else None
                ),
            },
            "timing_ms": {
                "organism": float(organism_ms),
                "physics": float(physics_ms),
            },
        }

        diagnostics_ms = (time.perf_counter() - diagnostics_started) * 1000.0

        return Tick3D(
            tick=self.tick_count,
            symbiont_tick=self.tick_count,
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
            embodiment_epoch=self.embodiment_epoch,
            body_age_ticks=int(self.organism.living_body_state.age_ticks),
            body_senescence=float(self.organism.living_body_state.senescence),
            reacclimation_remaining=int(self.organism.reacclimation_remaining),
            reacclimating=bool(self.organism.reacclimation_remaining > 0),
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
            motor_origin_detail=motor_origin_detail,
            initial_resource_distance=float(self._initial_resource_distance),
            minimum_resource_distance=float(self._minimum_resource_distance),
            resource_progress=float(
                self._initial_resource_distance - resource_distance
            ),
            motor_origin_cognition=int(self._motor_origin_counts["cognition"]),
            motor_origin_babbling=int(self._motor_origin_counts["babbling"]),
            motor_origin_primitive=int(self._motor_origin_counts["primitive"]),
            motor_origin_primitive_cognition=int(
                self._motor_origin_detail_counts["primitive_cognition"]
            ),
            motor_origin_primitive_verification=int(
                self._motor_origin_detail_counts["primitive_verification"]
            ),
            motor_origin_primitive_prospective=int(
                self._motor_origin_detail_counts["primitive_prospective"]
            ),
            prospective_reason=prospective_reason,
            prospective_candidates=int(
                self.organism.last_prospective_query_count
            ),
            prospective_selected=bool(
                prospective_decision is not None
                and prospective_decision.reason == "selected"
            ),
            prospective_action_id=(
                prospective_decision.candidate_id
                if prospective_decision is not None else None
            ),
            prospective_predicted_outcome=(
                prospective_decision.predicted_outcome
                if prospective_decision is not None else None
            ),
            prospective_expected_value=(
                prospective_decision.expected_value
                if prospective_decision is not None else None
            ),
            prospective_model_confidence=(
                prospective_decision.model_confidence
                if prospective_decision is not None else None
            ),
            prospective_value_confidence=(
                prospective_decision.value_confidence
                if prospective_decision is not None else None
            ),
            prospective_value_samples=int(
                self.organism.last_prospective_value_samples
            ),
            prospective_decision_margin=(
                prospective_decision.decision_margin
                if prospective_decision is not None else None
            ),
            prospective_cost=float(self.organism.last_prospective_cost),
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
            primitive_candidates=int(
                sensorimotor.primitive_candidates if sensorimotor is not None else 0
            ),
            recurrent_primitive_candidates=int(
                sensorimotor.recurrent_primitive_candidates if sensorimotor is not None else 0
            ),
            max_primitive_samples=int(
                sensorimotor.max_primitive_samples if sensorimotor is not None else 0
            ),
            sample_gate_candidates=int(
                sensorimotor.sample_gate_candidates if sensorimotor is not None else 0
            ),
            controllability_gate_candidates=int(
                sensorimotor.controllability_gate_candidates if sensorimotor is not None else 0
            ),
            variance_gate_candidates=int(
                sensorimotor.variance_gate_candidates if sensorimotor is not None else 0
            ),
            direction_gate_candidates=int(
                sensorimotor.direction_gate_candidates if sensorimotor is not None else 0
            ),
            full_competence_gate_candidates=int(
                sensorimotor.full_competence_gate_candidates if sensorimotor is not None else 0
            ),
            best_candidate_controllability=float(
                sensorimotor.best_candidate_controllability if sensorimotor is not None else 0.0
            ),
            best_candidate_directional_consistency=float(
                sensorimotor.best_candidate_directional_consistency if sensorimotor is not None else 0.0
            ),
            lowest_recurrent_effect_variance=(
                sensorimotor.lowest_recurrent_effect_variance
                if sensorimotor is not None
                else None
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
            cognitive_concepts=int(concept_count),
            cognitive_readouts=int(readout_count),
            motor_readout_nodes=int(motor_readout_nodes),
            primitive_readout_nodes=int(primitive_readout_nodes),
            cognitive_motor_output_edges=int(
                self._cognitive_motor_output_edge_count()
            ),
            structural_candidates=int(
                getattr(cognition, "structural_candidates", 0)
                if cognition is not None else 0
            ),
            structural_producers=int(
                getattr(cognition, "structural_producers", 0)
                if cognition is not None else 0
            ),
            oldest_structural_wait_ticks=int(
                getattr(cognition, "oldest_structural_wait_ticks", 0)
                if cognition is not None else 0
            ),
            maturity_nascent=int(maturity.get("nascent", 0)),
            maturity_provisional=int(maturity.get("provisional", 0)),
            maturity_mature=int(maturity.get("mature", 0)),
            maturity_stable=int(maturity.get("stable", 0)),
            maturity_weakening=int(maturity.get("weakening", 0)),
            maturity_retiring=int(maturity.get("retiring", 0)),
            joints=tuple(
                dict(j) for j in self._last_physical_state.get("joints", ())
                if isinstance(j, (dict, Mapping))
            ),
            contact_links=tuple(
                int(c) for c in self._last_physical_state.get("contact_links", ())
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
