"""Procedural anthropomorphic-v2 physics body backed by PyBullet.

Human-readable anatomical names exist only inside this apparatus module. They
never cross the EmbodimentSession boundary into Symbiont cognition.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Mapping, cast


BODY_KIND = "anthropomorphic-v2"
BODY_STATE_SCHEMA_VERSION = 2
MOTOR_DOF = 31
SOMATIC_REGION_COUNT = 15
GLOBAL_KINEMATIC_RECEPTORS = 10
ECOLOGICAL_RECEPTORS = 1
PHYSICAL_RECEPTOR_COUNT = (
    MOTOR_DOF * 2
    + GLOBAL_KINEMATIC_RECEPTORS
    + SOMATIC_REGION_COUNT * 2
    + ECOLOGICAL_RECEPTORS
)
INTEROCEPTIVE_RECEPTOR_COUNT = 4
TOTAL_RECEPTOR_COUNT = PHYSICAL_RECEPTOR_COUNT + INTEROCEPTIVE_RECEPTOR_COUNT


def physical_receptor_contract_ids() -> tuple[str, ...]:
    """Opaque PyBullet-derived receptor surface owned by the body apparatus."""
    return tuple(f"rec.{i}" for i in range(PHYSICAL_RECEPTOR_COUNT))


def interoceptive_receptor_contract_ids() -> tuple[str, ...]:
    """Four opaque body-state slots immediately after the physical surface."""
    return tuple(
        f"rec.{i}"
        for i in range(
            PHYSICAL_RECEPTOR_COUNT,
            PHYSICAL_RECEPTOR_COUNT + INTEROCEPTIVE_RECEPTOR_COUNT,
        )
    )


def receptor_contract_ids() -> tuple[str, ...]:
    """Complete opaque Physics3D surface."""
    return tuple(f"rec.{i}" for i in range(TOTAL_RECEPTOR_COUNT))


def effector_contract_ids(motor_count: int = MOTOR_DOF) -> tuple[str, ...]:
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
    stop_margin: float = 0.06
    stiffness: float = 100.0
    damping: float = 6.0
    max_stop_torque: float = 70.0


@dataclass(frozen=True, slots=True)
class JointSpec:
    name: str
    axis: tuple[float, float, float]
    lower: float
    upper: float
    max_motor_torque: float
    passive_damping: float
    max_velocity: float


def _deg(value: float) -> float:
    return math.radians(value)


# Apparatus-only mechanical constitution. Anatomical names never cross into
# cognition; only opaque rec.N/eff.N channels do.
JOINT_SPECS: tuple[JointSpec, ...] = (
    # name, axis, lower, upper, max torque [N m], passive damping [N m s/rad],
    # soft physiological speed limit [rad/s].
    JointSpec("trunk_yaw", (0.0, 0.0, 1.0), _deg(-45), _deg(45), 18.0, 2.8, 3.5),
    JointSpec("trunk_roll", (1.0, 0.0, 0.0), _deg(-30), _deg(30), 18.0, 2.8, 3.5),
    JointSpec("trunk_pitch", (0.0, 1.0, 0.0), _deg(-35), _deg(55), 22.0, 3.2, 3.5),
    JointSpec("neck_yaw", (0.0, 0.0, 1.0), _deg(-70), _deg(70), 3.0, 0.45, 4.5),
    JointSpec("neck_pitch", (0.0, 1.0, 0.0), _deg(-45), _deg(55), 3.0, 0.45, 4.5),
    JointSpec("left_shoulder_yaw", (0.0, 0.0, 1.0), _deg(-90), _deg(90), 9.0, 1.2, 5.0),
    JointSpec("left_shoulder_roll", (1.0, 0.0, 0.0), _deg(-30), _deg(160), 10.0, 1.3, 5.0),
    JointSpec("left_shoulder_pitch", (0.0, 1.0, 0.0), _deg(-45), _deg(170), 10.0, 1.3, 5.0),
    JointSpec("left_elbow_pitch", (0.0, 1.0, 0.0), _deg(0), _deg(145), 7.0, 0.9, 6.0),
    JointSpec("left_forearm_roll", (0.0, 0.0, 1.0), _deg(-80), _deg(80), 3.5, 0.45, 7.0),
    JointSpec("left_wrist_pitch", (0.0, 1.0, 0.0), _deg(-60), _deg(75), 2.5, 0.35, 7.0),
    JointSpec("left_wrist_deviation", (1.0, 0.0, 0.0), _deg(-20), _deg(35), 2.0, 0.35, 7.0),
    JointSpec("right_shoulder_yaw", (0.0, 0.0, 1.0), _deg(-90), _deg(90), 9.0, 1.2, 5.0),
    JointSpec("right_shoulder_roll", (1.0, 0.0, 0.0), _deg(-160), _deg(30), 10.0, 1.3, 5.0),
    JointSpec("right_shoulder_pitch", (0.0, 1.0, 0.0), _deg(-45), _deg(170), 10.0, 1.3, 5.0),
    JointSpec("right_elbow_pitch", (0.0, 1.0, 0.0), _deg(0), _deg(145), 7.0, 0.9, 6.0),
    JointSpec("right_forearm_roll", (0.0, 0.0, 1.0), _deg(-80), _deg(80), 3.5, 0.45, 7.0),
    JointSpec("right_wrist_pitch", (0.0, 1.0, 0.0), _deg(-60), _deg(75), 2.5, 0.35, 7.0),
    JointSpec("right_wrist_deviation", (1.0, 0.0, 0.0), _deg(-35), _deg(20), 2.0, 0.35, 7.0),
    JointSpec("left_hip_yaw", (0.0, 0.0, 1.0), _deg(-40), _deg(40), 22.0, 3.0, 4.0),
    JointSpec("left_hip_roll", (1.0, 0.0, 0.0), _deg(-20), _deg(40), 24.0, 3.2, 4.0),
    JointSpec("left_hip_pitch", (0.0, 1.0, 0.0), _deg(-20), _deg(125), 28.0, 3.5, 4.0),
    JointSpec("left_knee_pitch", (0.0, 1.0, 0.0), _deg(0), _deg(140), 24.0, 2.6, 5.0),
    JointSpec("left_ankle_pitch", (0.0, 1.0, 0.0), _deg(-20), _deg(45), 12.0, 1.8, 5.0),
    JointSpec("left_ankle_roll", (1.0, 0.0, 0.0), _deg(-15), _deg(15), 10.0, 1.6, 5.0),
    JointSpec("right_hip_yaw", (0.0, 0.0, 1.0), _deg(-40), _deg(40), 22.0, 3.0, 4.0),
    JointSpec("right_hip_roll", (1.0, 0.0, 0.0), _deg(-40), _deg(20), 24.0, 3.2, 4.0),
    JointSpec("right_hip_pitch", (0.0, 1.0, 0.0), _deg(-20), _deg(125), 28.0, 3.5, 4.0),
    JointSpec("right_knee_pitch", (0.0, 1.0, 0.0), _deg(0), _deg(140), 24.0, 2.6, 5.0),
    JointSpec("right_ankle_pitch", (0.0, 1.0, 0.0), _deg(-20), _deg(45), 12.0, 1.8, 5.0),
    JointSpec("right_ankle_roll", (1.0, 0.0, 0.0), _deg(-15), _deg(15), 10.0, 1.6, 5.0),
)
if len(JOINT_SPECS) != MOTOR_DOF:
    raise RuntimeError("anthropomorphic-v2 joint constitution must expose 31 DoF")

JOINT_LIMITS: dict[int, JointLimit] = {
    index: JointLimit(spec.lower, spec.upper)
    for index, spec in enumerate(JOINT_SPECS)
}
JOINT_AXES: dict[int, tuple[float, float, float]] = {
    index: spec.axis for index, spec in enumerate(JOINT_SPECS)
}


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


def _restore_vector(
    payload: Mapping[str, object],
    key: str,
    expected_size: int,
) -> tuple[float, ...]:
    raw_value = payload.get(key)
    if not isinstance(raw_value, (list, tuple)):
        raise ValueError(f"{key} must be a list or tuple")
    if len(raw_value) != expected_size:
        raise ValueError(f"{key} must contain {expected_size} values")
    values: list[float] = []
    for value in raw_value:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must contain only numeric values")
        values.append(float(value))
    return tuple(values)


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
    """31-DoF anthropomorphic body with rigid hands and load-bearing feet."""

    def __init__(self, pybullet_module, client_id: int, *, spawn_height: float = 1.08) -> None:
        self.p = pybullet_module
        self.client_id = client_id
        self._sensor_values: dict[str, float] = {}
        self._applied_torque_by_joint: dict[int, float] = {}
        self._external_field_signal = 0.0
        self._contact_links: tuple[int, ...] = ()
        self._direct_pairs: set[tuple[int, int]] = set()
        self._structural_collision_exclusions: set[tuple[int, int]] = set()
        self.body_id = self._create_body(spawn_height)
        self.motor_joint_indices = tuple(range(MOTOR_DOF))
        self.motor_bindings = tuple(
            MotorBinding(
                joint_index=joint_index,
                positive_port=f"eff.{slot * 2}",
                negative_port=f"eff.{slot * 2 + 1}",
            )
            for slot, joint_index in enumerate(self.motor_joint_indices)
        )
        self.receptor_ids = physical_receptor_contract_ids()
        self.effector_ids = effector_contract_ids(len(self.motor_bindings))
        self._configure_self_collisions()
        self._disable_default_motors()

    def _box(
        self,
        half_extents: tuple[float, float, float],
        color: tuple[float, float, float, float],
        *,
        frame: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ):
        p = self.p
        collision = p.createCollisionShape(
            p.GEOM_BOX,
            halfExtents=half_extents,
            collisionFramePosition=frame,
            physicsClientId=self.client_id,
        )
        visual = p.createVisualShape(
            p.GEOM_BOX,
            halfExtents=half_extents,
            visualFramePosition=frame,
            rgbaColor=color,
            physicsClientId=self.client_id,
        )
        return collision, visual

    def _limb(
        self,
        radius: float,
        length: float,
        color: tuple[float, float, float, float],
    ):
        # Links are anchored at the proximal joint, so offset geometry distally.
        return self._box(
            (radius, radius, length / 2.0),
            color,
            frame=(0.0, 0.0, -length / 2.0),
        )

    def _create_body(self, spawn_height: float) -> int:
        p = self.p
        carrier = -1
        pelvis_c, pelvis_v = self._box((0.16, 0.10, 0.11), (0.28, 0.44, 0.58, 1.0))
        torso_c, torso_v = self._box(
            (0.20, 0.11, 0.25),
            (0.32, 0.50, 0.65, 1.0),
            frame=(0.0, 0.0, 0.21),
        )
        head_c, head_v = self._box(
            (0.105, 0.105, 0.115),
            (0.55, 0.68, 0.76, 1.0),
            frame=(0.0, 0.0, 0.12),
        )

        left = (0.22, 0.60, 0.76, 1.0)
        left2 = (0.28, 0.70, 0.84, 1.0)
        right = (0.85, 0.50, 0.22, 1.0)
        right2 = (0.92, 0.62, 0.28, 1.0)
        l_upper_c, l_upper_v = self._limb(0.065, 0.31, left)
        l_fore_c, l_fore_v = self._limb(0.055, 0.27, left2)
        r_upper_c, r_upper_v = self._limb(0.065, 0.31, right)
        r_fore_c, r_fore_v = self._limb(0.055, 0.27, right2)
        l_hand_c, l_hand_v = self._box(
            (0.045, 0.075, 0.09), left2, frame=(0.0, 0.0, -0.09)
        )
        r_hand_c, r_hand_v = self._box(
            (0.045, 0.075, 0.09), right2, frame=(0.0, 0.0, -0.09)
        )
        l_thigh_c, l_thigh_v = self._limb(0.075, 0.40, left)
        l_shin_c, l_shin_v = self._limb(0.065, 0.40, left2)
        r_thigh_c, r_thigh_v = self._limb(0.075, 0.40, right)
        r_shin_c, r_shin_v = self._limb(0.065, 0.40, right2)
        l_foot_c, l_foot_v = self._box(
            (0.055, 0.13, 0.035), left2, frame=(0.0, -0.075, -0.035)
        )
        r_foot_c, r_foot_v = self._box(
            (0.055, 0.13, 0.035), right2, frame=(0.0, -0.075, -0.035)
        )

        masses: list[float] = []
        collisions: list[int] = []
        visuals: list[int] = []
        positions: list[tuple[float, float, float]] = []
        parents: list[int] = []
        contact_links: list[int] = []

        def add(
            parent_link: int,
            position: tuple[float, float, float],
            mass: float,
            collision: int = carrier,
            visual: int = carrier,
            *,
            contact: bool = False,
        ) -> int:
            index = len(masses)
            masses.append(float(mass))
            collisions.append(collision)
            visuals.append(visual)
            positions.append(position)
            # PyBullet createMultiBody uses 0 for base, and link index + 1.
            parents.append(0 if parent_link < 0 else parent_link + 1)
            if contact:
                contact_links.append(index)
            return index

        # Trunk: 3 DoF. Mass lives on the pitch link.
        trunk_yaw = add(-1, (0.0, 0.0, 0.10), 0.02)
        trunk_roll = add(trunk_yaw, (0.0, 0.0, 0.0), 0.02)
        trunk_pitch = add(
            trunk_roll, (0.0, 0.0, 0.0), 12.2, torso_c, torso_v, contact=True
        )
        # Neck: 2 DoF.
        neck_yaw = add(trunk_pitch, (0.0, 0.0, 0.48), 0.02)
        neck_pitch = add(
            neck_yaw, (0.0, 0.0, 0.0), 2.0, head_c, head_v, contact=True
        )

        def add_arm(side: float, start_parent: int, colors: tuple):
            upper_c, upper_v, fore_c, fore_v, hand_c, hand_v = colors
            shoulder_yaw = add(start_parent, (side * 0.28, 0.0, 0.36), 0.02)
            shoulder_roll = add(shoulder_yaw, (0.0, 0.0, 0.0), 0.02)
            shoulder_pitch = add(
                shoulder_roll, (0.0, 0.0, 0.0), 0.82, upper_c, upper_v, contact=True
            )
            elbow_pitch = add(shoulder_pitch, (0.0, 0.0, -0.31), 0.02)
            forearm_roll = add(
                elbow_pitch, (0.0, 0.0, 0.0), 0.48, fore_c, fore_v, contact=True
            )
            wrist_pitch = add(forearm_roll, (0.0, 0.0, -0.27), 0.02)
            wrist_deviation = add(
                wrist_pitch, (0.0, 0.0, 0.0), 0.18, hand_c, hand_v, contact=True
            )
            return wrist_deviation

        add_arm(
            -1.0,
            trunk_pitch,
            (l_upper_c, l_upper_v, l_fore_c, l_fore_v, l_hand_c, l_hand_v),
        )
        add_arm(
            1.0,
            trunk_pitch,
            (r_upper_c, r_upper_v, r_fore_c, r_fore_v, r_hand_c, r_hand_v),
        )

        def add_leg(side: float, colors: tuple):
            thigh_c, thigh_v, shin_c, shin_v, foot_c, foot_v = colors
            hip_yaw = add(-1, (side * 0.10, 0.0, -0.10), 0.02)
            hip_roll = add(hip_yaw, (0.0, 0.0, 0.0), 0.02)
            hip_pitch = add(
                hip_roll, (0.0, 0.0, 0.0), 4.25, thigh_c, thigh_v, contact=True
            )
            knee_pitch = add(
                hip_pitch, (0.0, 0.0, -0.40), 1.30, shin_c, shin_v, contact=True
            )
            ankle_pitch = add(knee_pitch, (0.0, 0.0, -0.40), 0.02)
            ankle_roll = add(
                ankle_pitch, (0.0, 0.0, 0.0), 0.42, foot_c, foot_v, contact=True
            )
            return ankle_roll

        add_leg(
            -1.0,
            (l_thigh_c, l_thigh_v, l_shin_c, l_shin_v, l_foot_c, l_foot_v),
        )
        add_leg(
            1.0,
            (r_thigh_c, r_thigh_v, r_shin_c, r_shin_v, r_foot_c, r_foot_v),
        )

        if len(masses) != MOTOR_DOF:
            raise RuntimeError(f"anthropomorphic-v2 built {len(masses)} joints, expected {MOTOR_DOF}")

        # Pelvis is also a somatic region.
        self._contact_links = (-1, *tuple(contact_links))
        if len(self._contact_links) != SOMATIC_REGION_COUNT:
            raise RuntimeError(
                f"anthropomorphic-v2 has {len(self._contact_links)} somatic regions, "
                f"expected {SOMATIC_REGION_COUNT}"
            )

        orientations = [(0.0, 0.0, 0.0, 1.0)] * MOTOR_DOF
        inertial_positions = [(0.0, 0.0, 0.0)] * MOTOR_DOF
        inertial_orientations = [(0.0, 0.0, 0.0, 1.0)] * MOTOR_DOF
        joint_types = [p.JOINT_REVOLUTE] * MOTOR_DOF
        joint_axes = [JOINT_AXES[index] for index in range(MOTOR_DOF)]

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
        self._direct_pairs = {
            tuple(sorted((-1 if parent == 0 else parent - 1, index)))
            for index, parent in enumerate(parents)
        }

        # Multi-axis anatomical joints are represented by chains of revolute
        # carrier links with no geometry. Physical neighbours can therefore be
        # separated by one or more carrier links even though their shapes meet
        # or slightly overlap at the joint. Those pairs must not self-collide:
        # otherwise Bullet resolves the intended anatomical overlap as a large
        # separating impulse and the newborn body can be launched violently.
        self._structural_collision_exclusions = {
            (-1, trunk_pitch),     # pelvis <-> torso
            (trunk_pitch, neck_pitch),
            (trunk_pitch, 7),      # torso <-> left upper arm
            (trunk_pitch, 14),     # torso <-> right upper arm
            (7, 9),                # left upper arm <-> forearm
            (9, 11),               # left forearm <-> hand
            (14, 16),              # right upper arm <-> forearm
            (16, 18),              # right forearm <-> hand
            (-1, 21),              # pelvis <-> left thigh
            (22, 24),              # left shin <-> foot
            (-1, 27),              # pelvis <-> right thigh
            (28, 30),              # right shin <-> foot
        }
        self._structural_collision_exclusions = {
            tuple(sorted(pair)) for pair in self._structural_collision_exclusions
        }

        for link_index in range(-1, MOTOR_DOF):
            apply_surface_material(
                p, body_id, link_index, BODY_MATERIAL, client_id=self.client_id
            )
        return body_id

    def _directly_connected_link_pairs(self) -> set[tuple[int, int]]:
        return set(self._direct_pairs)

    def _self_collision_exclusions(self) -> set[tuple[int, int]]:
        return (
            self._directly_connected_link_pairs()
            | set(self._structural_collision_exclusions)
        )

    def _configure_self_collisions(self) -> None:
        p = self.p
        link_indices = tuple(range(-1, MOTOR_DOF))
        excluded = self._self_collision_exclusions()
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

    def set_opaque_environment_state(self, *, external_field: float) -> None:
        if (
            isinstance(external_field, bool)
            or not isinstance(external_field, (int, float))
            or not math.isfinite(float(external_field))
            or not 0.0 <= float(external_field) <= 1.0
        ):
            raise ValueError("external_field must be within [0, 1]")
        self._external_field_signal = float(external_field)

    @staticmethod
    def _bounded_contact_load(value: float, scale: float = 120.0) -> float:
        return math.tanh(max(0.0, float(value)) / max(scale, 1e-12))

    @staticmethod
    def _signed_unit(value: float, scale: float) -> float:
        return 0.5 + 0.5 * math.tanh(float(value) / max(scale, 1e-12))

    def sample_receptors(self) -> Mapping[str, float]:
        p = self.p
        values: list[float] = []
        if hasattr(p, "getJointStates"):
            raw_states = p.getJointStates(
                self.body_id, self.motor_joint_indices, physicsClientId=self.client_id
            )
        else:
            raw_states = [
                p.getJointState(self.body_id, joint_index, physicsClientId=self.client_id)
                for joint_index in self.motor_joint_indices
            ]
        for state in raw_states:
            values.append(self._signed_unit(state[0], math.pi))
            values.append(self._signed_unit(state[1], 6.0))

        _base_position, base_orientation = p.getBasePositionAndOrientation(
            self.body_id, physicsClientId=self.client_id
        )
        linear_velocity, angular_velocity = p.getBaseVelocity(
            self.body_id, physicsClientId=self.client_id
        )
        values.extend(max(0.0, min(1.0, 0.5 + 0.5 * q)) for q in base_orientation)
        values.extend(self._signed_unit(v, 4.0) for v in linear_velocity)
        values.extend(self._signed_unit(v, 6.0) for v in angular_velocity)

        contacts = p.getContactPoints(bodyA=self.body_id, physicsClientId=self.client_id)
        active_links = {int(item[3]) for item in contacts if len(item) > 3}
        values.extend(1.0 if link in active_links else 0.0 for link in self._contact_links)
        values.append(self._external_field_signal)

        peak_force_by_link = {link: 0.0 for link in self._contact_links}
        for item in contacts:
            if len(item) <= 9:
                continue
            link = int(item[3])
            if link in peak_force_by_link:
                peak_force_by_link[link] = max(
                    peak_force_by_link[link], max(0.0, float(item[9]))
                )
        values.extend(
            self._bounded_contact_load(peak_force_by_link[link])
            for link in self._contact_links
        )

        if len(values) != len(self.receptor_ids):
            raise RuntimeError(
                f"physics receptor contract mismatch: {len(values)} != {len(self.receptor_ids)}"
            )
        self._sensor_values = dict(zip(self.receptor_ids, values))
        return dict(self._sensor_values)

    def receptor_value(self, receptor_id: str) -> float:
        return float(self._sensor_values.get(receptor_id, 0.0))

    def export_physical_state(self) -> dict:
        p = self.p
        base_position, base_orientation = p.getBasePositionAndOrientation(
            self.body_id, physicsClientId=self.client_id
        )
        linear_velocity, angular_velocity = p.getBaseVelocity(
            self.body_id, physicsClientId=self.client_id
        )
        raw_joint_states = cast(
            Sequence[Sequence[object]],
            p.getJointStates(
                self.body_id, self.motor_joint_indices, physicsClientId=self.client_id
            ),
        )
        joints = [
            {
                "joint_index": int(joint_index),
                "position": float(raw_joint_state[0]),
                "velocity": float(raw_joint_state[1]),
                "applied_torque": float(self._applied_torque_by_joint.get(joint_index, 0.0)),
            }
            for joint_index, raw_joint_state in zip(self.motor_joint_indices, raw_joint_states)
        ]
        contacts = cast(
            Sequence[Sequence[object]],
            p.getContactPoints(bodyA=self.body_id, physicsClientId=self.client_id),
        )
        active_links = sorted(
            {
                int(item[3])
                for item in contacts
                if len(item) > 3
                and isinstance(item[3], (int, float))
                and not isinstance(item[3], bool)
            }
        )
        return {
            "schema_version": BODY_STATE_SCHEMA_VERSION,
            "body_kind": BODY_KIND,
            "base_position": [float(x) for x in base_position],
            "base_orientation": [float(x) for x in base_orientation],
            "linear_velocity": [float(x) for x in linear_velocity],
            "angular_velocity": [float(x) for x in angular_velocity],
            "joints": joints,
            "contact_links": active_links,
            "contact_count": len(contacts),
        }

    def restore_physical_state(self, payload: Mapping[str, object]) -> None:
        if payload.get("schema_version") != BODY_STATE_SCHEMA_VERSION:
            raise ValueError("unsupported physics body state schema")
        if payload.get("body_kind") != BODY_KIND:
            raise ValueError(f"body state is not compatible with {BODY_KIND}")
        p = self.p
        position = _restore_vector(payload, "base_position", 3)
        orientation = _restore_vector(payload, "base_orientation", 4)
        linear_velocity = _restore_vector(payload, "linear_velocity", 3)
        angular_velocity = _restore_vector(payload, "angular_velocity", 3)
        expected = set(self.motor_joint_indices)
        seen: set[int] = set()
        validated_joints: list[tuple[int, float, float]] = []
        raw_joints = payload.get("joints")
        if not isinstance(raw_joints, (list, tuple)):
            raise ValueError("joints must be a list or tuple")
        for item in raw_joints:
            if not isinstance(item, Mapping):
                raise ValueError("each joint state must be a mapping")
            raw_joint_index = item.get("joint_index")
            raw_position = item.get("position")
            raw_velocity = item.get("velocity")
            if (
                isinstance(raw_joint_index, bool)
                or not isinstance(raw_joint_index, int)
                or isinstance(raw_position, bool)
                or not isinstance(raw_position, (int, float))
                or isinstance(raw_velocity, bool)
                or not isinstance(raw_velocity, (int, float))
            ):
                raise ValueError("joint state contains invalid numeric values")
            if raw_joint_index not in expected:
                raise ValueError(f"unexpected joint index in body state: {raw_joint_index}")
            seen.add(raw_joint_index)
            validated_joints.append(
                (raw_joint_index, float(raw_position), float(raw_velocity))
            )
        if seen != expected:
            raise ValueError("body state does not contain every motor joint")

        p.resetBasePositionAndOrientation(
            self.body_id, position, orientation, physicsClientId=self.client_id
        )
        p.resetBaseVelocity(
            self.body_id,
            linearVelocity=linear_velocity,
            angularVelocity=angular_velocity,
            physicsClientId=self.client_id,
        )
        for joint_index, joint_position, joint_velocity in validated_joints:
            p.resetJointState(
                self.body_id,
                joint_index,
                targetValue=joint_position,
                targetVelocity=joint_velocity,
                physicsClientId=self.client_id,
            )

    def apply_effectors(
        self,
        activations: Mapping[str, float],
        *,
        torque_scale: float = 1.0,
    ) -> None:
        p = self.p
        applied: dict[int, float] = {}
        for binding in self.motor_bindings:
            positive = max(0.0, min(1.0, float(activations.get(binding.positive_port, 0.0))))
            negative = max(0.0, min(1.0, float(activations.get(binding.negative_port, 0.0))))
            spec = JOINT_SPECS[binding.joint_index]
            torque = (
                (positive - negative)
                * spec.max_motor_torque
                * max(0.0, float(torque_scale))
            )
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
            torque = limit.stiffness * (lower_stop - position) - limit.damping * velocity
        elif position > upper_stop:
            torque = limit.stiffness * (upper_stop - position) - limit.damping * velocity
        return max(-limit.max_stop_torque, min(limit.max_stop_torque, torque))

    def prepare_physics_substep(self) -> None:
        p = self.p
        if hasattr(p, "getJointStates"):
            raw_states = p.getJointStates(
                self.body_id, self.motor_joint_indices, physicsClientId=self.client_id
            )
        else:
            raw_states = [
                p.getJointState(self.body_id, joint_index, physicsClientId=self.client_id)
                for joint_index in self.motor_joint_indices
            ]
        for joint_index, state in zip(self.motor_joint_indices, raw_states):
            position = float(state[0])
            velocity = float(state[1])
            spec = JOINT_SPECS[joint_index]
            stop_torque = self._joint_stop_torque(
                JOINT_LIMITS[joint_index],
                position=position,
                velocity=velocity,
            )
            commanded = self._applied_torque_by_joint.get(joint_index, 0.0)

            # Passive viscoelastic resistance exists throughout the range, not
            # only at the anatomical stops. Beyond the physiological soft speed
            # limit, progressively stronger braking prevents unbounded angular
            # acceleration while remaining a continuous physical torque.
            passive_torque = -spec.passive_damping * velocity
            overspeed = max(0.0, abs(velocity) - spec.max_velocity)
            if overspeed > 0.0:
                passive_torque += -math.copysign(
                    min(spec.max_motor_torque * 2.0, overspeed * spec.passive_damping * 4.0),
                    velocity,
                )

            total_torque = commanded + stop_torque + passive_torque
            torque_bound = (
                spec.max_motor_torque
                + JOINT_LIMITS[joint_index].max_stop_torque
                + spec.max_motor_torque * 2.0
            )
            total_torque = max(-torque_bound, min(torque_bound, total_torque))
            p.setJointMotorControl2(
                self.body_id,
                joint_index,
                p.TORQUE_CONTROL,
                force=float(total_torque),
                physicsClientId=self.client_id,
            )

    def mechanical_work_step(self, dt: float) -> float:
        if not math.isfinite(float(dt)) or dt <= 0.0:
            raise ValueError("dt must be finite and positive")
        active = [
            (idx, float(torque))
            for idx, torque in self._applied_torque_by_joint.items()
            if abs(float(torque)) > 1e-9
        ]
        if not active:
            return 0.0
        indices = [item[0] for item in active]
        raw_states = self.p.getJointStates(
            self.body_id, indices, physicsClientId=self.client_id
        )
        return float(
            sum(
                abs(torque * float(state[1])) * float(dt)
                for (_, torque), state in zip(active, raw_states)
            )
        )
