"""Procedural anthropomorphic physics body backed by PyBullet.

Human-readable anatomical names exist only inside this apparatus module. They
never cross the EmbodimentSession boundary into Symbiont cognition.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping


def receptor_contract_ids() -> tuple[str, ...]:
    """Opaque physical receptor surface exposed by the apparatus."""
    # 14 motor joints * (position, velocity) + base orientation (4)
    # + linear velocity (3) + angular velocity (3) + five contacts
    # + two opaque ecological/interoceptive channels.
    return tuple(f"rec.{i}" for i in range(45))


def effector_contract_ids(motor_count: int = 8) -> tuple[str, ...]:
    """Paired opaque motor surface; zero on both ports means zero torque."""
    if motor_count < 1:
        raise ValueError("motor_count must be positive")
    return tuple(f"eff.{i}" for i in range(motor_count * 2))


@dataclass(frozen=True, slots=True)
class MotorBinding:
    joint_index: int
    positive_port: str
    negative_port: str


@dataclass(frozen=True, slots=True)
class SurfaceMaterial:
    lateral_friction: float
    spinning_friction: float
    rolling_friction: float
    restitution: float
    linear_damping: float
    angular_damping: float


@dataclass(frozen=True, slots=True)
class JointLimit:
    lower: float
    upper: float
    stop_margin: float = 0.08
    stiffness: float = 90.0
    damping: float = 5.0
    max_stop_torque: float = 60.0


BODY_MATERIAL = SurfaceMaterial(
    lateral_friction=0.80,
    spinning_friction=0.02,
    rolling_friction=0.002,
    restitution=0.02,
    linear_damping=0.03,
    angular_damping=0.05,
)

GROUND_MATERIAL = SurfaceMaterial(
    lateral_friction=0.95,
    spinning_friction=0.03,
    rolling_friction=0.002,
    restitution=0.0,
    linear_damping=0.0,
    angular_damping=0.0,
)

# Apparatus-only mechanical constitution. These names/limits never cross into
# cognition; the organism experiences only the physical consequences.
JOINT_LIMITS: dict[int, JointLimit] = {
    0: JointLimit(lower=-1.20, upper=1.20),  # axial waist
    1: JointLimit(lower=-0.70, upper=0.70),  # lateral trunk
    3: JointLimit(lower=-1.45, upper=1.45),  # left shoulder lateral
    4: JointLimit(lower=-2.00, upper=2.00),  # left shoulder sagittal
    5: JointLimit(lower=-0.15, upper=2.40),  # left elbow
    6: JointLimit(lower=-1.45, upper=1.45),  # right shoulder lateral
    7: JointLimit(lower=-2.00, upper=2.00),  # right shoulder sagittal
    8: JointLimit(lower=-0.15, upper=2.40),  # right elbow
    9: JointLimit(lower=-0.85, upper=0.85),  # left hip lateral
    10: JointLimit(lower=-1.55, upper=1.20), # left hip sagittal
    11: JointLimit(lower=-0.15, upper=2.35), # left knee
    12: JointLimit(lower=-0.85, upper=0.85), # right hip lateral
    13: JointLimit(lower=-1.55, upper=1.20), # right hip sagittal
    14: JointLimit(lower=-0.15, upper=2.35), # right knee
}

JOINT_AXES: dict[int, tuple[float, float, float]] = {
    0: (0.0, 0.0, 1.0),
    1: (1.0, 0.0, 0.0),
    3: (1.0, 0.0, 0.0),
    4: (0.0, 1.0, 0.0),
    5: (0.0, 1.0, 0.0),
    6: (1.0, 0.0, 0.0),
    7: (0.0, 1.0, 0.0),
    8: (0.0, 1.0, 0.0),
    9: (1.0, 0.0, 0.0),
    10: (0.0, 1.0, 0.0),
    11: (0.0, 1.0, 0.0),
    12: (1.0, 0.0, 0.0),
    13: (0.0, 1.0, 0.0),
    14: (0.0, 1.0, 0.0),
}



def apply_surface_material(
    pybullet_module,
    body_id: int,
    link_index: int,
    material: SurfaceMaterial,
    *,
    client_id: int,
) -> None:
    pybullet_module.changeDynamics(
        body_id,
        link_index,
        lateralFriction=material.lateral_friction,
        spinningFriction=material.spinning_friction,
        rollingFriction=material.rolling_friction,
        restitution=material.restitution,
        linearDamping=material.linear_damping,
        angularDamping=material.angular_damping,
        physicsClientId=client_id,
    )


class HumanoidPhysics:
    """Small procedural articulated body suitable for weak laptops."""

    def __init__(self, pybullet_module, client_id: int, *, spawn_height: float = 1.15) -> None:
        self.p = pybullet_module
        self.client_id = client_id
        self._sensor_values: dict[str, float] = {}
        self._applied_torque_by_joint: dict[int, float] = {}
        self._external_field_signal = 0.0
        self._internal_state_signal = 1.0
        self.body_id = self._create_body(spawn_height)
        self.motor_joint_indices = tuple(sorted(JOINT_LIMITS))
        self.motor_bindings = tuple(
            MotorBinding(
                joint_index=joint_index,
                positive_port=f"eff.{slot * 2}",
                negative_port=f"eff.{slot * 2 + 1}",
            )
            for slot, joint_index in enumerate(self.motor_joint_indices)
        )
        self.receptor_ids = receptor_contract_ids()
        self.effector_ids = effector_contract_ids(len(self.motor_bindings))
        self._configure_self_collisions()
        self._disable_default_motors()

    def _box(self, half_extents: tuple[float, float, float], color: tuple[float, float, float, float]):
        p = self.p
        collision = p.createCollisionShape(
            p.GEOM_BOX,
            halfExtents=half_extents,
            physicsClientId=self.client_id,
        )
        visual = p.createVisualShape(
            p.GEOM_BOX,
            halfExtents=half_extents,
            rgbaColor=color,
            physicsClientId=self.client_id,
        )
        return collision, visual

    def _create_body(self, spawn_height: float) -> int:
        p = self.p
        pelvis_c, pelvis_v = self._box((0.16, 0.10, 0.11), (0.35, 0.58, 0.72, 1.0))
        torso_c, torso_v = self._box((0.20, 0.11, 0.26), (0.31, 0.54, 0.70, 1.0))
        head_c, head_v = self._box((0.11, 0.11, 0.11), (0.58, 0.75, 0.82, 1.0))
        upper_c, upper_v = self._box((0.07, 0.07, 0.19), (0.32, 0.60, 0.73, 1.0))
        lower_c, lower_v = self._box((0.06, 0.06, 0.18), (0.39, 0.67, 0.77, 1.0))
        thigh_c, thigh_v = self._box((0.08, 0.08, 0.24), (0.27, 0.52, 0.66, 1.0))
        shin_c, shin_v = self._box((0.07, 0.07, 0.23), (0.33, 0.61, 0.71, 1.0))

        # Invisible low-mass carrier links provide serial rotational degrees of
        # freedom without exposing anatomical labels to the organism.
        carrier = -1

        masses = [
            0.15, 5.5, 1.2,
            0.10, 1.0, 0.8,
            0.10, 1.0, 0.8,
            0.12, 2.2, 1.6,
            0.12, 2.2, 1.6,
        ]
        collisions = [
            carrier, torso_c, head_c,
            carrier, upper_c, lower_c,
            carrier, upper_c, lower_c,
            carrier, thigh_c, shin_c,
            carrier, thigh_c, shin_c,
        ]
        visuals = [
            carrier, torso_v, head_v,
            carrier, upper_v, lower_v,
            carrier, upper_v, lower_v,
            carrier, thigh_v, shin_v,
            carrier, thigh_v, shin_v,
        ]
        positions = [
            (0.0, 0.0, 0.10),   # waist axial carrier from pelvis
            (0.0, 0.0, 0.21),   # torso from waist carrier
            (0.0, 0.0, 0.37),   # head from torso
            (-0.27, 0.0, 0.16), # left shoulder carrier
            (0.0, 0.0, 0.0),    # left upper arm
            (0.0, 0.0, -0.34),  # left lower arm
            (0.27, 0.0, 0.16),  # right shoulder carrier
            (0.0, 0.0, 0.0),    # right upper arm
            (0.0, 0.0, -0.34),  # right lower arm
            (-0.11, 0.0, -0.24),# left hip carrier
            (0.0, 0.0, 0.0),    # left thigh
            (0.0, 0.0, -0.43),  # left shin
            (0.11, 0.0, -0.24), # right hip carrier
            (0.0, 0.0, 0.0),    # right thigh
            (0.0, 0.0, -0.43),  # right shin
        ]
        orientations = [(0.0, 0.0, 0.0, 1.0)] * 15
        inertial_positions = [(0.0, 0.0, 0.0)] * 15
        inertial_orientations = [(0.0, 0.0, 0.0, 1.0)] * 15

        fixed = p.JOINT_FIXED
        revolute = p.JOINT_REVOLUTE
        joint_types = [
            revolute, revolute, fixed,
            revolute, revolute, revolute,
            revolute, revolute, revolute,
            revolute, revolute, revolute,
            revolute, revolute, revolute,
        ]
        joint_axes = [
            JOINT_AXES.get(index, (0.0, 0.0, 1.0))
            for index in range(15)
        ]
        # createMultiBody parent indices are one-based for links (0=base).
        parents = [
            0, 1, 2,
            2, 4, 5,
            2, 7, 8,
            0, 10, 11,
            0, 13, 14,
        ]

        body_id = p.createMultiBody(
            baseMass=4.0,
            baseCollisionShapeIndex=pelvis_c,
            baseVisualShapeIndex=pelvis_v,
            basePosition=(0.0, 0.0, spawn_height),
            baseOrientation=(0.0, 0.0, 0.0, 1.0),
            linkMasses=masses,
            linkCollisionShapeIndices=collisions,
            linkVisualShapeIndices=visuals,
            linkPositions=positions,
            linkOrientations=orientations,
            linkInertialFramePositions=inertial_positions,
            linkInertialFrameOrientations=inertial_orientations,
            linkParentIndices=parents,
            linkJointTypes=joint_types,
            linkJointAxis=joint_axes,
            physicsClientId=self.client_id,
        )
        for link_index in range(-1, 15):
            apply_surface_material(
                p,
                body_id,
                link_index,
                BODY_MATERIAL,
                client_id=self.client_id,
            )
        return body_id

    @staticmethod
    def _directly_connected_link_pairs() -> set[tuple[int, int]]:
        """Pairs whose collision is disabled because their joint volumes overlap."""
        return {
            (-1, 0),
            (0, 1),
            (1, 2),
            (1, 3),
            (3, 4),
            (4, 5),
            (1, 6),
            (6, 7),
            (7, 8),
            (-1, 9),
            (9, 10),
            (10, 11),
            (-1, 12),
            (12, 13),
            (13, 14),
        }

    def _configure_self_collisions(self) -> None:
        """Enable body self-collision except across directly joined neighbours.

        This is apparatus physics only: no anatomical labels or collision-pair
        identities cross into cognition. Adjacent links are excluded because
        their boxes intentionally overlap around the joint pivot; every other
        pair is collision-enabled so limbs cannot pass through torso or each
        other.
        """
        p = self.p
        link_indices = tuple(range(-1, 15))
        excluded = {
            tuple(sorted(pair))
            for pair in self._directly_connected_link_pairs()
        }
        for offset, link_a in enumerate(link_indices):
            for link_b in link_indices[offset + 1 :]:
                pair = tuple(sorted((link_a, link_b)))
                p.setCollisionFilterPair(
                    self.body_id,
                    self.body_id,
                    link_a,
                    link_b,
                    enableCollision=0 if pair in excluded else 1,
                    physicsClientId=self.client_id,
                )

    def _disable_default_motors(self) -> None:
        p = self.p
        for joint_index in self.motor_joint_indices:
            p.setJointMotorControl2(
                self.body_id,
                joint_index,
                p.VELOCITY_CONTROL,
                targetVelocity=0.0,
                force=0.0,
                physicsClientId=self.client_id,
            )

    def set_opaque_environment_state(
        self,
        *,
        external_field: float,
        internal_state: float,
    ) -> None:
        """Update two anonymous bounded receptor values.

        The apparatus receives only scalar magnitudes. Resource identity,
        coordinates, labels and metabolic compartment names never cross this
        sensory boundary.
        """
        for value, label in (
            (external_field, "external_field"),
            (internal_state, "internal_state"),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not 0.0 <= float(value) <= 1.0
            ):
                raise ValueError(f"{label} must be within [0, 1]")
        self._external_field_signal = float(external_field)
        self._internal_state_signal = float(internal_state)

    @staticmethod
    def _signed_unit(value: float, scale: float) -> float:
        return 0.5 + 0.5 * math.tanh(float(value) / max(scale, 1e-12))

    def sample_receptors(self) -> Mapping[str, float]:
        """Return physical measurements in stable opaque receptor slots."""
        p = self.p
        values: list[float] = []
        for joint_index in self.motor_joint_indices:
            position, velocity, *_ = p.getJointState(
                self.body_id, joint_index, physicsClientId=self.client_id
            )
            values.append(self._signed_unit(position, math.pi))
            values.append(self._signed_unit(velocity, 6.0))

        base_position, base_orientation = p.getBasePositionAndOrientation(
            self.body_id, physicsClientId=self.client_id
        )
        linear_velocity, angular_velocity = p.getBaseVelocity(
            self.body_id, physicsClientId=self.client_id
        )
        del base_position
        values.extend(max(0.0, min(1.0, 0.5 + 0.5 * q)) for q in base_orientation)
        values.extend(self._signed_unit(v, 4.0) for v in linear_velocity)
        values.extend(self._signed_unit(v, 6.0) for v in angular_velocity)

        contact_links = (-1, 5, 8, 11, 14)
        contacts = p.getContactPoints(
            bodyA=self.body_id,
            physicsClientId=self.client_id,
        )
        active_links = {int(item[3]) for item in contacts}
        values.extend(1.0 if link in active_links else 0.0 for link in contact_links)
        values.append(self._external_field_signal)
        values.append(self._internal_state_signal)

        if len(values) != len(self.receptor_ids):
            raise RuntimeError(
                f"physics receptor contract mismatch: {len(values)} != {len(self.receptor_ids)}"
            )
        self._sensor_values = dict(zip(self.receptor_ids, values))
        return dict(self._sensor_values)

    def receptor_value(self, receptor_id: str) -> float:
        return float(self._sensor_values.get(receptor_id, 0.0))

    def export_physical_state(self) -> dict:
        """Capture body pose/velocity without any cognitive state."""
        p = self.p
        base_position, base_orientation = p.getBasePositionAndOrientation(
            self.body_id,
            physicsClientId=self.client_id,
        )
        linear_velocity, angular_velocity = p.getBaseVelocity(
            self.body_id,
            physicsClientId=self.client_id,
        )
        joints = []
        for joint_index in self.motor_joint_indices:
            position, velocity, *_ = p.getJointState(
                self.body_id,
                joint_index,
                physicsClientId=self.client_id,
            )
            joints.append(
                {
                    "joint_index": int(joint_index),
                    "position": float(position),
                    "velocity": float(velocity),
                    "applied_torque": float(self._applied_torque_by_joint.get(joint_index, 0.0)),
                }
            )
        contacts = p.getContactPoints(
            bodyA=self.body_id,
            physicsClientId=self.client_id,
        )
        active_links = sorted({int(item[3]) for item in contacts})
        return {
            "schema_version": 1,
            "body_kind": "anthropomorphic-v1",
            "base_position": [float(x) for x in base_position],
            "base_orientation": [float(x) for x in base_orientation],
            "linear_velocity": [float(x) for x in linear_velocity],
            "angular_velocity": [float(x) for x in angular_velocity],
            "joints": joints,
            "contact_links": active_links,
        }

    def restore_physical_state(self, payload: Mapping[str, object]) -> None:
        """Restore one compatible body pose after the body has been constructed."""
        if int(payload.get("schema_version", -1)) != 1:
            raise ValueError("unsupported physics body state schema")
        if payload.get("body_kind") != "anthropomorphic-v1":
            raise ValueError("body state is not compatible with anthropomorphic-v1")
        p = self.p
        position = tuple(float(x) for x in payload["base_position"])
        orientation = tuple(float(x) for x in payload["base_orientation"])
        linear_velocity = tuple(float(x) for x in payload["linear_velocity"])
        angular_velocity = tuple(float(x) for x in payload["angular_velocity"])
        if len(position) != 3 or len(orientation) != 4:
            raise ValueError("invalid base pose in body state")
        if len(linear_velocity) != 3 or len(angular_velocity) != 3:
            raise ValueError("invalid base velocity in body state")
        p.resetBasePositionAndOrientation(
            self.body_id,
            position,
            orientation,
            physicsClientId=self.client_id,
        )
        p.resetBaseVelocity(
            self.body_id,
            linearVelocity=linear_velocity,
            angularVelocity=angular_velocity,
            physicsClientId=self.client_id,
        )
        expected = set(self.motor_joint_indices)
        seen: set[int] = set()
        for item in payload.get("joints", []):
            joint_index = int(item["joint_index"])
            if joint_index not in expected:
                raise ValueError(f"unexpected joint index in body state: {joint_index}")
            seen.add(joint_index)
            p.resetJointState(
                self.body_id,
                joint_index,
                targetValue=float(item["position"]),
                targetVelocity=float(item["velocity"]),
                physicsClientId=self.client_id,
            )
        if seen != expected:
            raise ValueError("body state does not contain every motor joint")

    def apply_effectors(
        self,
        activations: Mapping[str, float],
        *,
        max_torque: float = 18.0,
    ) -> None:
        """Convert paired opaque activations into signed joint torques."""
        p = self.p
        applied: dict[int, float] = {}
        for binding in self.motor_bindings:
            positive = max(0.0, min(1.0, float(activations.get(binding.positive_port, 0.0))))
            negative = max(0.0, min(1.0, float(activations.get(binding.negative_port, 0.0))))
            torque = (positive - negative) * max_torque
            applied[binding.joint_index] = float(torque)
            p.setJointMotorControl2(
                self.body_id,
                binding.joint_index,
                p.TORQUE_CONTROL,
                force=torque,
                physicsClientId=self.client_id,
            )
        self._applied_torque_by_joint = applied
        self.prepare_physics_substep()

    @staticmethod
    def _joint_stop_torque(
        limit: JointLimit,
        *,
        position: float,
        velocity: float,
    ) -> float:
        lower_stop = limit.lower + limit.stop_margin
        upper_stop = limit.upper - limit.stop_margin
        torque = 0.0
        if position < lower_stop:
            torque = (
                limit.stiffness * (lower_stop - position)
                - limit.damping * velocity
            )
        elif position > upper_stop:
            torque = (
                limit.stiffness * (upper_stop - position)
                - limit.damping * velocity
            )
        return max(-limit.max_stop_torque, min(limit.max_stop_torque, torque))

    def prepare_physics_substep(self) -> None:
        """Apply commanded torque plus passive mechanical joint-stop forces."""
        p = self.p
        for joint_index in self.motor_joint_indices:
            position, velocity, *_ = p.getJointState(
                self.body_id,
                joint_index,
                physicsClientId=self.client_id,
            )
            limit = JOINT_LIMITS[joint_index]
            stop_torque = self._joint_stop_torque(
                limit,
                position=float(position),
                velocity=float(velocity),
            )
            commanded = self._applied_torque_by_joint.get(joint_index, 0.0)
            p.setJointMotorControl2(
                self.body_id,
                joint_index,
                p.TORQUE_CONTROL,
                force=float(commanded + stop_torque),
                physicsClientId=self.client_id,
            )

    def mechanical_work_step(self, dt: float) -> float:
        """Measure absolute joint work over one physical integration interval."""
        if not math.isfinite(float(dt)) or dt <= 0.0:
            raise ValueError("dt must be finite and positive")
        work = 0.0
        for joint_index, torque in self._applied_torque_by_joint.items():
            _position, velocity, *_ = self.p.getJointState(
                self.body_id,
                joint_index,
                physicsClientId=self.client_id,
            )
            work += abs(float(torque) * float(velocity)) * float(dt)
        return float(work)
