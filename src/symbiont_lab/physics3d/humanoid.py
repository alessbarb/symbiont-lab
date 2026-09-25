"""Hard-limited anthropomorphic Physics3D body backed by PyBullet URDF.

Human-readable anatomy exists only inside this apparatus module. Symbiont sees
only opaque rec.N/eff.N channels. The URDF is generated from the canonical
constitution at runtime so joint ranges are mechanical constraints owned by
Bullet, not controller suggestions.
"""
from __future__ import annotations

import math
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast


BODY_KIND = "anthropomorphic-v6"
BODY_STATE_SCHEMA_VERSION = 6
JOINT_LIMIT_SOLVER_TOLERANCE = math.radians(0.5)
MECHANICAL_LIMIT_GUARD = math.radians(2.0)
PHYSICS_SOLVER_ITERATIONS = 120
PHYSICS_SOLVER_RESIDUAL_THRESHOLD = 1e-9
PHYSICS_CONSTRAINT_ERP = 0.8
END_RANGE_MARGIN = math.radians(6.0)
END_RANGE_STIFFNESS = 18.0
END_RANGE_DAMPING = 1.5
PASSIVE_TONE_STIFFNESS_FRACTION = 0.55
PASSIVE_TONE_TORQUE_CAP_FRACTION = 0.45
PASSIVE_DAMPING_TORQUE_CAP_FRACTION = 1.0
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
    return tuple(f"rec.{i}" for i in range(PHYSICAL_RECEPTOR_COUNT))


def interoceptive_receptor_contract_ids() -> tuple[str, ...]:
    return tuple(
        f"rec.{i}"
        for i in range(
            PHYSICAL_RECEPTOR_COUNT,
            PHYSICAL_RECEPTOR_COUNT + INTEROCEPTIVE_RECEPTOR_COUNT,
        )
    )


def receptor_contract_ids() -> tuple[str, ...]:
    return tuple(f"rec.{i}" for i in range(TOTAL_RECEPTOR_COUNT))


def effector_contract_ids(motor_count: int = MOTOR_DOF) -> tuple[str, ...]:
    if motor_count < 1:
        raise ValueError("motor_count must be positive")
    return tuple(f"eff.{i}" for i in range(motor_count * 2))


@dataclass(frozen=True, slots=True)
class MotorBinding:
    joint_index: int
    positive_port: str
    negative_port: str


@dataclass(frozen=True, slots=True)
class ActuatorWork:
    positive_j: float
    negative_j: float
    absolute_j: float
    net_j: float


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


@dataclass(frozen=True, slots=True)
class JointSpec:
    name: str
    axis: tuple[float, float, float]
    lower: float
    upper: float
    max_motor_torque: float
    passive_damping: float
    max_velocity: float


@dataclass(frozen=True, slots=True)
class SegmentSpec:
    mass: float
    size: tuple[float, float, float]
    origin: tuple[float, float, float]
    color: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class JointTopology:
    joint_name: str
    parent_link: str
    child_link: str
    origin: tuple[float, float, float]


def _deg(value: float) -> float:
    return math.radians(value)


JOINT_SPECS: tuple[JointSpec, ...] = (
    JointSpec("trunk_yaw", (0.0, 0.0, 1.0), _deg(-45), _deg(45), 18.0, 2.8, 3.5),
    JointSpec("trunk_roll", (0.0, 1.0, 0.0), _deg(-30), _deg(30), 18.0, 2.8, 3.5),
    JointSpec("trunk_pitch", (1.0, 0.0, 0.0), _deg(-35), _deg(55), 22.0, 3.2, 3.5),
    JointSpec("neck_yaw", (0.0, 0.0, 1.0), _deg(-70), _deg(70), 3.0, 0.45, 4.5),
    JointSpec("neck_pitch", (1.0, 0.0, 0.0), _deg(-45), _deg(55), 3.0, 0.45, 4.5),
    JointSpec("left_shoulder_yaw", (0.0, 0.0, 1.0), _deg(-90), _deg(90), 9.0, 1.2, 5.0),
    JointSpec("left_shoulder_roll", (0.0, 1.0, 0.0), _deg(-30), _deg(160), 10.0, 1.3, 5.0),
    JointSpec("left_shoulder_pitch", (1.0, 0.0, 0.0), _deg(-45), _deg(170), 10.0, 1.3, 5.0),
    JointSpec("left_elbow_pitch", (1.0, 0.0, 0.0), _deg(0), _deg(145), 7.0, 0.9, 6.0),
    JointSpec("left_forearm_roll", (0.0, 0.0, 1.0), _deg(-80), _deg(80), 3.5, 0.45, 7.0),
    JointSpec("left_wrist_pitch", (1.0, 0.0, 0.0), _deg(-60), _deg(75), 2.5, 0.35, 7.0),
    JointSpec("left_wrist_deviation", (0.0, 1.0, 0.0), _deg(-20), _deg(35), 2.0, 0.35, 7.0),
    JointSpec("right_shoulder_yaw", (0.0, 0.0, 1.0), _deg(-90), _deg(90), 9.0, 1.2, 5.0),
    JointSpec("right_shoulder_roll", (0.0, 1.0, 0.0), _deg(-160), _deg(30), 10.0, 1.3, 5.0),
    JointSpec("right_shoulder_pitch", (1.0, 0.0, 0.0), _deg(-45), _deg(170), 10.0, 1.3, 5.0),
    JointSpec("right_elbow_pitch", (1.0, 0.0, 0.0), _deg(0), _deg(145), 7.0, 0.9, 6.0),
    JointSpec("right_forearm_roll", (0.0, 0.0, 1.0), _deg(-80), _deg(80), 3.5, 0.45, 7.0),
    JointSpec("right_wrist_pitch", (1.0, 0.0, 0.0), _deg(-60), _deg(75), 2.5, 0.35, 7.0),
    JointSpec("right_wrist_deviation", (0.0, 1.0, 0.0), _deg(-35), _deg(20), 2.0, 0.35, 7.0),
    JointSpec("left_hip_yaw", (0.0, 0.0, 1.0), _deg(-40), _deg(40), 22.0, 3.0, 4.0),
    JointSpec("left_hip_roll", (0.0, 1.0, 0.0), _deg(-20), _deg(40), 24.0, 3.2, 4.0),
    JointSpec("left_hip_pitch", (1.0, 0.0, 0.0), _deg(-20), _deg(125), 28.0, 3.5, 4.0),
    JointSpec("left_knee_pitch", (1.0, 0.0, 0.0), _deg(0), _deg(140), 24.0, 2.6, 5.0),
    JointSpec("left_ankle_pitch", (1.0, 0.0, 0.0), _deg(-20), _deg(45), 12.0, 1.8, 5.0),
    JointSpec("left_ankle_roll", (0.0, 1.0, 0.0), _deg(-15), _deg(15), 10.0, 1.6, 5.0),
    JointSpec("right_hip_yaw", (0.0, 0.0, 1.0), _deg(-40), _deg(40), 22.0, 3.0, 4.0),
    JointSpec("right_hip_roll", (0.0, 1.0, 0.0), _deg(-40), _deg(20), 24.0, 3.2, 4.0),
    JointSpec("right_hip_pitch", (1.0, 0.0, 0.0), _deg(-20), _deg(125), 28.0, 3.5, 4.0),
    JointSpec("right_knee_pitch", (1.0, 0.0, 0.0), _deg(0), _deg(140), 24.0, 2.6, 5.0),
    JointSpec("right_ankle_pitch", (1.0, 0.0, 0.0), _deg(-20), _deg(45), 12.0, 1.8, 5.0),
    JointSpec("right_ankle_roll", (0.0, 1.0, 0.0), _deg(-15), _deg(15), 10.0, 1.6, 5.0),
)
if len(JOINT_SPECS) != MOTOR_DOF:
    raise RuntimeError("anthropomorphic-v6 must expose exactly 31 motor DoF")

JOINT_LIMITS: dict[int, JointLimit] = {
    ordinal: JointLimit(spec.lower, spec.upper)
    for ordinal, spec in enumerate(JOINT_SPECS)
}
JOINT_AXES: dict[int, tuple[float, float, float]] = {
    ordinal: spec.axis for ordinal, spec in enumerate(JOINT_SPECS)
}


BODY_MATERIAL = SurfaceMaterial(0.80, 0.02, 0.002, 0.02, 0.03, 0.05)
GROUND_MATERIAL = SurfaceMaterial(0.95, 0.03, 0.002, 0.0, 0.0, 0.0)

_LEFT = (0.22, 0.60, 0.76, 1.0)
_LEFT2 = (0.28, 0.70, 0.84, 1.0)
_RIGHT = (0.85, 0.50, 0.22, 1.0)
_RIGHT2 = (0.92, 0.62, 0.28, 1.0)

CARRIER_MASS = 0.05

SEGMENTS: dict[str, SegmentSpec] = {
    "pelvis": SegmentSpec(4.0, (0.32, 0.20, 0.22), (0.0, 0.0, 0.0), (0.28, 0.44, 0.58, 1.0)),
    "torso": SegmentSpec(12.2, (0.40, 0.22, 0.50), (0.0, 0.0, 0.21), (0.32, 0.50, 0.65, 1.0)),
    "head": SegmentSpec(2.0, (0.21, 0.21, 0.23), (0.0, 0.0, 0.12), (0.55, 0.68, 0.76, 1.0)),
    "left_upper_arm": SegmentSpec(0.82, (0.13, 0.13, 0.31), (0.0, 0.0, -0.155), _LEFT),
    "left_forearm": SegmentSpec(0.48, (0.11, 0.11, 0.27), (0.0, 0.0, -0.135), _LEFT2),
    "left_hand": SegmentSpec(0.18, (0.09, 0.15, 0.18), (0.0, 0.0, -0.09), _LEFT2),
    "right_upper_arm": SegmentSpec(0.82, (0.13, 0.13, 0.31), (0.0, 0.0, -0.155), _RIGHT),
    "right_forearm": SegmentSpec(0.48, (0.11, 0.11, 0.27), (0.0, 0.0, -0.135), _RIGHT2),
    "right_hand": SegmentSpec(0.18, (0.09, 0.15, 0.18), (0.0, 0.0, -0.09), _RIGHT2),
    "left_thigh": SegmentSpec(4.25, (0.15, 0.15, 0.40), (0.0, 0.0, -0.20), _LEFT),
    "left_shin": SegmentSpec(1.30, (0.13, 0.13, 0.40), (0.0, 0.0, -0.20), _LEFT2),
    "left_foot": SegmentSpec(0.42, (0.11, 0.26, 0.07), (0.0, -0.075, -0.035), _LEFT2),
    "right_thigh": SegmentSpec(4.25, (0.15, 0.15, 0.40), (0.0, 0.0, -0.20), _RIGHT),
    "right_shin": SegmentSpec(1.30, (0.13, 0.13, 0.40), (0.0, 0.0, -0.20), _RIGHT2),
    "right_foot": SegmentSpec(0.42, (0.11, 0.26, 0.07), (0.0, -0.075, -0.035), _RIGHT2),
}

JOINT_TOPOLOGY: tuple[JointTopology, ...] = (
    JointTopology("trunk_yaw", "pelvis", "trunk_yaw_carrier", (0.0, 0.0, 0.10)),
    JointTopology("trunk_roll", "trunk_yaw_carrier", "trunk_roll_carrier", (0.0, 0.0, 0.0)),
    JointTopology("trunk_pitch", "trunk_roll_carrier", "torso", (0.0, 0.0, 0.0)),
    JointTopology("neck_yaw", "torso", "neck_yaw_carrier", (0.0, 0.0, 0.48)),
    JointTopology("neck_pitch", "neck_yaw_carrier", "head", (0.0, 0.0, 0.0)),
    JointTopology("left_shoulder_yaw", "torso", "left_shoulder_yaw_carrier", (-0.28, 0.0, 0.36)),
    JointTopology("left_shoulder_roll", "left_shoulder_yaw_carrier", "left_shoulder_roll_carrier", (0.0, 0.0, 0.0)),
    JointTopology("left_shoulder_pitch", "left_shoulder_roll_carrier", "left_upper_arm", (0.0, 0.0, 0.0)),
    JointTopology("left_elbow_pitch", "left_upper_arm", "left_elbow_carrier", (0.0, 0.0, -0.31)),
    JointTopology("left_forearm_roll", "left_elbow_carrier", "left_forearm", (0.0, 0.0, 0.0)),
    JointTopology("left_wrist_pitch", "left_forearm", "left_wrist_carrier", (0.0, 0.0, -0.27)),
    JointTopology("left_wrist_deviation", "left_wrist_carrier", "left_hand", (0.0, 0.0, 0.0)),
    JointTopology("right_shoulder_yaw", "torso", "right_shoulder_yaw_carrier", (0.28, 0.0, 0.36)),
    JointTopology("right_shoulder_roll", "right_shoulder_yaw_carrier", "right_shoulder_roll_carrier", (0.0, 0.0, 0.0)),
    JointTopology("right_shoulder_pitch", "right_shoulder_roll_carrier", "right_upper_arm", (0.0, 0.0, 0.0)),
    JointTopology("right_elbow_pitch", "right_upper_arm", "right_elbow_carrier", (0.0, 0.0, -0.31)),
    JointTopology("right_forearm_roll", "right_elbow_carrier", "right_forearm", (0.0, 0.0, 0.0)),
    JointTopology("right_wrist_pitch", "right_forearm", "right_wrist_carrier", (0.0, 0.0, -0.27)),
    JointTopology("right_wrist_deviation", "right_wrist_carrier", "right_hand", (0.0, 0.0, 0.0)),
    JointTopology("left_hip_yaw", "pelvis", "left_hip_yaw_carrier", (-0.10, 0.0, -0.10)),
    JointTopology("left_hip_roll", "left_hip_yaw_carrier", "left_hip_roll_carrier", (0.0, 0.0, 0.0)),
    JointTopology("left_hip_pitch", "left_hip_roll_carrier", "left_thigh", (0.0, 0.0, 0.0)),
    JointTopology("left_knee_pitch", "left_thigh", "left_shin", (0.0, 0.0, -0.40)),
    JointTopology("left_ankle_pitch", "left_shin", "left_ankle_pitch_carrier", (0.0, 0.0, -0.40)),
    JointTopology("left_ankle_roll", "left_ankle_pitch_carrier", "left_foot", (0.0, 0.0, 0.0)),
    JointTopology("right_hip_yaw", "pelvis", "right_hip_yaw_carrier", (0.10, 0.0, -0.10)),
    JointTopology("right_hip_roll", "right_hip_yaw_carrier", "right_hip_roll_carrier", (0.0, 0.0, 0.0)),
    JointTopology("right_hip_pitch", "right_hip_roll_carrier", "right_thigh", (0.0, 0.0, 0.0)),
    JointTopology("right_knee_pitch", "right_thigh", "right_shin", (0.0, 0.0, -0.40)),
    JointTopology("right_ankle_pitch", "right_shin", "right_ankle_pitch_carrier", (0.0, 0.0, -0.40)),
    JointTopology("right_ankle_roll", "right_ankle_pitch_carrier", "right_foot", (0.0, 0.0, 0.0)),
)
if tuple(item.joint_name for item in JOINT_TOPOLOGY) != tuple(spec.name for spec in JOINT_SPECS):
    raise RuntimeError("joint topology order must exactly match JOINT_SPECS")

CONTACT_LINK_NAMES = (
    "torso", "head",
    "left_upper_arm", "left_forearm", "left_hand",
    "right_upper_arm", "right_forearm", "right_hand",
    "left_thigh", "left_shin", "left_foot",
    "right_thigh", "right_shin", "right_foot",
)
STRUCTURAL_NEIGHBOUR_NAMES = (
    ("pelvis", "torso"), ("torso", "head"),
    ("torso", "left_upper_arm"), ("left_upper_arm", "left_forearm"),
    ("left_forearm", "left_hand"),
    ("torso", "right_upper_arm"), ("right_upper_arm", "right_forearm"),
    ("right_forearm", "right_hand"),
    ("pelvis", "left_thigh"), ("left_shin", "left_foot"),
    ("pelvis", "right_thigh"), ("right_shin", "right_foot"),
    # Carriers with zero offset share AABB space with their structural neighbours;
    # exclude them to suppress spurious self-collision impulses in trunk and hips.
    ("pelvis", "left_hip_roll_carrier"),
    ("pelvis", "right_hip_roll_carrier"),
    ("trunk_yaw_carrier", "torso"),
)


def _fmt(values: Sequence[float]) -> str:
    return " ".join(f"{float(value):.10g}" for value in values)


def _box_inertia(mass: float, size: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = size
    return (
        mass * (y * y + z * z) / 12.0,
        mass * (x * x + z * z) / 12.0,
        mass * (x * x + y * y) / 12.0,
    )


CYLINDRICAL_COLLISION_LINKS = frozenset({
    "left_upper_arm",
    "left_forearm",
    "right_upper_arm",
    "right_forearm",
    "left_thigh",
    "left_shin",
    "right_thigh",
    "right_shin",
})


def _cylinder_inertia(
    mass: float,
    *,
    radius: float,
    length: float,
) -> tuple[float, float, float]:
    transverse = mass * (3.0 * radius * radius + length * length) / 12.0
    axial = 0.5 * mass * radius * radius
    return transverse, transverse, axial


def _segment_link_xml(name: str, segment: SegmentSpec) -> str:
    xyz = _fmt(segment.origin)
    size = _fmt(segment.size)
    color = _fmt(segment.color)

    if name in CYLINDRICAL_COLLISION_LINKS:
        radius = min(segment.size[0], segment.size[1]) / 2.0
        length = segment.size[2]
        ixx, iyy, izz = _cylinder_inertia(
            segment.mass,
            radius=radius,
            length=length,
        )
        collision_geometry = (
            f'<cylinder radius="{radius:.10g}" length="{length:.10g}"/>'
        )
    else:
        ixx, iyy, izz = _box_inertia(segment.mass, segment.size)
        collision_geometry = f'<box size="{size}"/>'

    return f"""
  <link name="{name}">
    <inertial>
      <origin xyz="{xyz}" rpy="0 0 0"/>
      <mass value="{segment.mass:.10g}"/>
      <inertia ixx="{ixx:.10g}" ixy="0" ixz="0" iyy="{iyy:.10g}" iyz="0" izz="{izz:.10g}"/>
    </inertial>
    <visual>
      <origin xyz="{xyz}" rpy="0 0 0"/>
      <geometry><box size="{size}"/></geometry>
      <material name="{name}_material"><color rgba="{color}"/></material>
    </visual>
    <collision>
      <origin xyz="{xyz}" rpy="0 0 0"/>
      <geometry>{collision_geometry}</geometry>
    </collision>
  </link>"""


def _carrier_link_xml(name: str) -> str:
    # Small but non-zero inertia avoids singular mass matrices while adding no
    # collision or visual geometry.
    return f"""
  <link name="{name}">
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="{CARRIER_MASS:.10g}"/>
      <inertia ixx="0.0001" ixy="0" ixz="0" iyy="0.0001" iyz="0" izz="0.0001"/>
    </inertial>
  </link>"""


def mechanical_joint_limits(spec: JointSpec) -> tuple[float, float]:
    """Return Bullet stop limits inset from the canonical anatomical envelope.

    Bullet revolute constraints exhibit a small, repeatable solver penetration
    under aggressive torque. The guard band keeps that numerical slop inside
    the organism's true anatomical range rather than redefining the anatomy.
    """
    span = spec.upper - spec.lower
    guard = min(MECHANICAL_LIMIT_GUARD, span * 0.1)
    return spec.lower + guard, spec.upper - guard


def build_anthropomorphic_urdf() -> str:
    links = {"pelvis", *(item.child_link for item in JOINT_TOPOLOGY)}
    link_xml = []
    for name in links:
        if name in SEGMENTS:
            link_xml.append(_segment_link_xml(name, SEGMENTS[name]))
        else:
            link_xml.append(_carrier_link_xml(name))

    spec_by_name = {spec.name: spec for spec in JOINT_SPECS}
    joint_xml = []
    for item in JOINT_TOPOLOGY:
        spec = spec_by_name[item.joint_name]
        mechanical_lower, mechanical_upper = mechanical_joint_limits(spec)
        joint_xml.append(
            f"""
  <joint name="{spec.name}" type="revolute">
    <parent link="{item.parent_link}"/>
    <child link="{item.child_link}"/>
    <origin xyz="{_fmt(item.origin)}" rpy="0 0 0"/>
    <axis xyz="{_fmt(spec.axis)}"/>
    <limit lower="{mechanical_lower:.12g}" upper="{mechanical_upper:.12g}" effort="{spec.max_motor_torque:.12g}" velocity="{spec.max_velocity:.12g}"/>
    <dynamics damping="0" friction="0"/>
  </joint>"""
        )
    return (
        "<?xml version=\"1.0\"?>\n"
        "<robot name=\"symbiont_anthropomorphic_v6\">"
        + "".join(link_xml)
        + "".join(joint_xml)
        + "\n</robot>\n"
    )


def configure_physics_solver(pybullet_module, client_id: int, time_step: float) -> None:
    """Canonical constraint solver settings for the anthropomorphic body."""
    pybullet_module.setPhysicsEngineParameter(
        numSolverIterations=PHYSICS_SOLVER_ITERATIONS,
        solverResidualThreshold=PHYSICS_SOLVER_RESIDUAL_THRESHOLD,
        erp=PHYSICS_CONSTRAINT_ERP,
        fixedTimeStep=float(time_step),
        physicsClientId=client_id,
    )


def _end_range_resistance(
    spec: JointSpec,
    *,
    position: float,
    velocity: float,
) -> float:
    """Passive ligament-like resistance entirely inside the hard URDF range."""
    lower_zone = spec.lower + min(END_RANGE_MARGIN, (spec.upper - spec.lower) * 0.2)
    upper_zone = spec.upper - min(END_RANGE_MARGIN, (spec.upper - spec.lower) * 0.2)
    torque = 0.0
    if position < lower_zone:
        torque = END_RANGE_STIFFNESS * (lower_zone - position) - END_RANGE_DAMPING * velocity
    elif position > upper_zone:
        torque = -END_RANGE_STIFFNESS * (position - upper_zone) - END_RANGE_DAMPING * velocity
    bound = spec.max_motor_torque * 1.5
    return max(-bound, min(bound, torque))



def _neutral_rest_position(spec: JointSpec) -> float:
    lower, upper = mechanical_joint_limits(spec)
    return max(lower, min(upper, 0.0))


def _passive_postural_tone(
    spec: JointSpec,
    *,
    position: float,
    velocity: float,
) -> float:
    """Elastic body property, not a controller or learned target.

    Every joint has a neutral mechanical rest configuration.  URDF joint
    damping supplies passive dissipation; this term supplies only elastic
    neutral-rest tone.  This is the digital analogue of passive tissue
    elasticity and resting muscle tone:
    it contains no task, gait, balance strategy or anatomy visible to the
    organism.  The apparatus owns it exactly like mass, inertia and friction.
    """
    rest = _neutral_rest_position(spec)
    stiffness = spec.max_motor_torque * PASSIVE_TONE_STIFFNESS_FRACTION
    # Under TORQUE_CONTROL Bullet does not provide a sufficiently reliable
    # passive joint-damping contribution for the humanoid's low-inertia axial
    # joints. Own the complete viscoelastic tissue model here instead:
    # elastic neutral-rest torque plus velocity-opposing damping. The URDF
    # damping term is therefore zeroed below to avoid double counting.
    elastic_cap = (
        spec.max_motor_torque * PASSIVE_TONE_TORQUE_CAP_FRACTION
    )
    damping_cap = (
        spec.max_motor_torque * PASSIVE_DAMPING_TORQUE_CAP_FRACTION
    )
    elastic = max(
        -elastic_cap,
        min(elastic_cap, stiffness * (rest - position)),
    )
    damping = max(
        -damping_cap,
        min(damping_cap, -spec.passive_damping * velocity),
    )
    return elastic + damping


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
    """31-DoF humanoid with Bullet-enforced anatomical joint constraints."""

    def __init__(self, pybullet_module, client_id: int, *, spawn_height: float = 1.08) -> None:
        self.p = pybullet_module
        self.client_id = client_id
        self._sensor_values: dict[str, float] = {}
        self._applied_torque_by_joint: dict[int, float] = {}
        self._external_field_signal = 0.0
        self.body_id = self._create_body(spawn_height)
        self._bind_loaded_constitution()
        self.motor_bindings = tuple(
            MotorBinding(
                joint_index=joint_index,
                positive_port=f"eff.{ordinal * 2}",
                negative_port=f"eff.{ordinal * 2 + 1}",
            )
            for ordinal, joint_index in enumerate(self.motor_joint_indices)
        )
        self.receptor_ids = physical_receptor_contract_ids()
        self.effector_ids = effector_contract_ids(len(self.motor_bindings))
        self._configure_self_collisions()
        self._configure_joint_dynamics()
        self._configure_surface_materials()
        self._disable_default_motors()

    def _create_body(self, spawn_height: float) -> int:
        urdf = build_anthropomorphic_urdf()
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".urdf",
            prefix="symbiont-anthropomorphic-v6-",
            encoding="utf-8",
            delete=False,
        ) as handle:
            handle.write(urdf)
            urdf_path = handle.name
        try:
            flags = (
                int(getattr(self.p, "URDF_USE_INERTIA_FROM_FILE", 0))
                | int(getattr(self.p, "URDF_USE_SELF_COLLISION", 0))
            )
            body_id = self.p.loadURDF(
                urdf_path,
                basePosition=(0.0, 0.0, float(spawn_height)),
                baseOrientation=(0.0, 0.0, 0.0, 1.0),
                useFixedBase=False,
                flags=flags,
                physicsClientId=self.client_id,
            )
        finally:
            Path(urdf_path).unlink(missing_ok=True)
        if int(body_id) < 0:
            raise RuntimeError("failed to load anthropomorphic-v6 URDF")
        return int(body_id)

    @staticmethod
    def _decode_name(value: object) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    def _bind_loaded_constitution(self) -> None:
        p = self.p
        joint_count = int(p.getNumJoints(self.body_id, physicsClientId=self.client_id))
        if joint_count != MOTOR_DOF:
            raise RuntimeError(
                f"anthropomorphic-v6 loaded {joint_count} joints, expected {MOTOR_DOF}"
            )

        index_by_joint_name: dict[str, int] = {}
        index_by_link_name: dict[str, int] = {"pelvis": -1}
        parent_by_index: dict[int, int] = {}
        for joint_index in range(joint_count):
            info = p.getJointInfo(
                self.body_id, joint_index, physicsClientId=self.client_id
            )
            joint_name = self._decode_name(info[1])
            link_name = self._decode_name(info[12])
            index_by_joint_name[joint_name] = joint_index
            index_by_link_name[link_name] = joint_index
            parent_by_index[joint_index] = int(info[16])

        missing = [spec.name for spec in JOINT_SPECS if spec.name not in index_by_joint_name]
        if missing:
            raise RuntimeError(f"URDF missing canonical joints: {missing}")

        self.motor_joint_indices = tuple(
            index_by_joint_name[spec.name] for spec in JOINT_SPECS
        )
        # Stable ordinal identity is part of the opaque receptor/effector
        # WARN(fail-closed): contract. Fail closed if Bullet ever reorders our generated tree.
        if self.motor_joint_indices != tuple(range(MOTOR_DOF)):
            raise RuntimeError(
                "Bullet reordered anthropomorphic-v6 joints; opaque ordinal contract unsafe"
            )

        self._joint_ordinal_by_index = {
            joint_index: ordinal
            for ordinal, joint_index in enumerate(self.motor_joint_indices)
        }
        self._link_index_by_name = index_by_link_name
        self._contact_links = (
            -1,
            *(index_by_link_name[name] for name in CONTACT_LINK_NAMES),
        )
        if len(self._contact_links) != SOMATIC_REGION_COUNT:
            raise RuntimeError("anthropomorphic-v5 somatic surface is incomplete")

        self._direct_pairs: set[tuple[int, int]] = {
            (min(parent_by_index[index], index), max(parent_by_index[index], index))
            for index in range(joint_count)
        }
        self._structural_collision_exclusions: set[tuple[int, int]] = {
            (
                min(index_by_link_name[left], index_by_link_name[right]),
                max(index_by_link_name[left], index_by_link_name[right]),
            )
            for left, right in STRUCTURAL_NEIGHBOUR_NAMES
        }
        self._verify_loaded_joint_contract()

    def _verify_loaded_joint_contract(self) -> None:
        for ordinal, joint_index in enumerate(self.motor_joint_indices):
            info = self.p.getJointInfo(
                self.body_id, joint_index, physicsClientId=self.client_id
            )
            spec = JOINT_SPECS[ordinal]
            lower = float(info[8])
            upper = float(info[9])
            max_force = float(info[10])
            max_velocity = float(info[11])
            mechanical_lower, mechanical_upper = mechanical_joint_limits(spec)
            if (
                abs(lower - mechanical_lower) > 1e-6
                or abs(upper - mechanical_upper) > 1e-6
            ):
                raise RuntimeError(f"Bullet did not load limits for {spec.name}")
            if abs(max_force - spec.max_motor_torque) > 1e-6:
                raise RuntimeError(f"Bullet did not load effort for {spec.name}")
            if abs(max_velocity - spec.max_velocity) > 1e-6:
                raise RuntimeError(f"Bullet did not load velocity for {spec.name}")

    def _directly_connected_link_pairs(self) -> set[tuple[int, int]]:
        return set(self._direct_pairs)

    def _self_collision_exclusions(self) -> set[tuple[int, int]]:
        return self._directly_connected_link_pairs() | set(
            self._structural_collision_exclusions
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

    def _configure_joint_dynamics(self) -> None:
        p = self.p
        for ordinal, joint_index in enumerate(self.motor_joint_indices):
            spec = JOINT_SPECS[ordinal]
            p.changeDynamics(
                self.body_id,
                joint_index,
                maxJointVelocity=float(spec.max_velocity),
                physicsClientId=self.client_id,
            )

    def _configure_surface_materials(self) -> None:
        for link_index in range(-1, MOTOR_DOF):
            apply_surface_material(
                self.p,
                self.body_id,
                link_index,
                BODY_MATERIAL,
                client_id=self.client_id,
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
                self.body_id,
                self.motor_joint_indices,
                physicsClientId=self.client_id,
            )
        else:
            raw_states = [
                p.getJointState(
                    self.body_id,
                    joint_index,
                    physicsClientId=self.client_id,
                )
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
        # PyBullet normalizes contact tuples so the queried body is always
        # item[1]/item[3]. Exception: self-contacts (bodyA == bodyB == body_id)
        # have no canonical ordering — item[3] is linkIndexA and item[4] is
        # linkIndexB; both links participate and must be recorded.
        active_links: set[int] = set()
        for item in contacts:
            if len(item) > 3:
                active_links.add(int(item[3]))
            if (
                len(item) > 4
                and int(item[1]) == self.body_id
                and int(item[2]) == self.body_id
            ):
                active_links.add(int(item[4]))
        values.extend(1.0 if link in active_links else 0.0 for link in self._contact_links)
        values.append(self._external_field_signal)

        peak_force_by_link = {link: 0.0 for link in self._contact_links}
        for item in contacts:
            if len(item) <= 9:
                continue
            force = max(0.0, float(item[9]))
            link_a = int(item[3])
            if link_a in peak_force_by_link:
                peak_force_by_link[link_a] = max(peak_force_by_link[link_a], force)
            # For self-contacts, also credit the second participating link.
            if (
                int(item[1]) == self.body_id
                and int(item[2]) == self.body_id
                and len(item) > 4
            ):
                link_b = int(item[4])
                if link_b in peak_force_by_link:
                    peak_force_by_link[link_b] = max(peak_force_by_link[link_b], force)
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
        if hasattr(p, "getJointStates"):
            raw_joint_states = cast(
                Sequence[Sequence[object]],
                p.getJointStates(
                    self.body_id, self.motor_joint_indices, physicsClientId=self.client_id
                ),
            )
        else:
            raw_joint_states = cast(
                Sequence[tuple[float, float, object, object]],
                [
                    p.getJointState(self.body_id, i, physicsClientId=self.client_id)
                    for i in self.motor_joint_indices
                ],
            )
        joints = [
            {
                "joint_index": int(joint_index),
                "joint_name": JOINT_SPECS[ordinal].name,
                "position": float(raw_state[0]),
                "velocity": float(raw_state[1]),
                "applied_torque": float(
                    self._applied_torque_by_joint.get(joint_index, 0.0)
                ),
            }
            for ordinal, (joint_index, raw_state) in enumerate(
                zip(self.motor_joint_indices, raw_joint_states)
            )
        ]
        links = []
        weighted_com = [0.0, 0.0, 0.0]
        total_mass = 0.0
        for link_name, link_index in sorted(
            self._link_index_by_name.items(),
            key=lambda item: item[1],
        ):
            if link_index == -1:
                link_position = base_position
                link_orientation = base_orientation
                link_com_position = base_position
            else:
                link_state = p.getLinkState(
                    self.body_id,
                    link_index,
                    computeForwardKinematics=True,
                    physicsClientId=self.client_id,
                )
                # World link-frame pose, not inertial COM pose. Visual and
                # collision geometry are defined relative to this frame.
                link_position = link_state[4]
                link_orientation = link_state[5]
                # PyBullet elements 0/1 are the inertial COM world pose.
                link_com_position = link_state[0]

            mass = 1.0
            if hasattr(p, "getDynamicsInfo"):
                dynamics = p.getDynamicsInfo(
                    self.body_id,
                    link_index,
                    physicsClientId=self.client_id,
                )
                if dynamics and isinstance(dynamics[0], (int, float)):
                    mass = max(0.0, float(dynamics[0]))
            if mass > 0.0:
                total_mass += mass
                for axis in range(3):
                    weighted_com[axis] += mass * float(link_com_position[axis])

            links.append(
                {
                    "link_index": int(link_index),
                    "link_name": str(link_name),
                    "position": [float(x) for x in link_position],
                    "orientation": [float(x) for x in link_orientation],
                }
            )

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
        center_of_mass = (
            [value / total_mass for value in weighted_com]
            if total_mass > 0.0
            else [float(value) for value in base_position]
        )
        return {
            "schema_version": BODY_STATE_SCHEMA_VERSION,
            "body_kind": BODY_KIND,
            "base_position": [float(x) for x in base_position],
            "base_orientation": [float(x) for x in base_orientation],
            "linear_velocity": [float(x) for x in linear_velocity],
            "angular_velocity": [float(x) for x in angular_velocity],
            "center_of_mass": [float(x) for x in center_of_mass],
            "total_mass": float(total_mass),
            "joints": joints,
            "links": links,
            "contact_links": active_links,
            "contact_count": len(contacts),
        }

    def restore_physical_state(
        self,
        payload: Mapping[str, object],
        *,
        strict_anatomical_limits: bool = True,
    ) -> None:
        if payload.get("schema_version") != BODY_STATE_SCHEMA_VERSION:
            raise ValueError("unsupported physics body state schema")
        if payload.get("body_kind") != BODY_KIND:
            raise ValueError(f"body state is not compatible with {BODY_KIND}")

        position = _restore_vector(payload, "base_position", 3)
        orientation = _restore_vector(payload, "base_orientation", 4)
        linear_velocity = _restore_vector(payload, "linear_velocity", 3)
        angular_velocity = _restore_vector(payload, "angular_velocity", 3)
        raw_joints = payload.get("joints")
        if not isinstance(raw_joints, (list, tuple)):
            raise ValueError("joints must be a list or tuple")

        expected = set(self.motor_joint_indices)
        seen: set[int] = set()
        validated: list[tuple[int, float, float]] = []
        for item in raw_joints:
            if not isinstance(item, Mapping):
                raise ValueError("each joint state must be a mapping")
            raw_index = item.get("joint_index")
            raw_position = item.get("position")
            raw_velocity = item.get("velocity")
            if (
                isinstance(raw_index, bool)
                or not isinstance(raw_index, int)
                or isinstance(raw_position, bool)
                or not isinstance(raw_position, (int, float))
                or isinstance(raw_velocity, bool)
                or not isinstance(raw_velocity, (int, float))
            ):
                raise ValueError("joint state contains invalid numeric values")
            if raw_index not in expected:
                raise ValueError(f"unexpected joint index in body state: {raw_index}")
            ordinal = self._joint_ordinal_by_index[raw_index]
            spec = JOINT_SPECS[ordinal]
            joint_position = float(raw_position)
            if not (
                spec.lower - JOINT_LIMIT_SOLVER_TOLERANCE
                <= joint_position
                <= spec.upper + JOINT_LIMIT_SOLVER_TOLERANCE
            ):
                if strict_anatomical_limits:
                    raise ValueError(
                        f"joint state outside hard anatomical limit: {spec.name}"
                    )
                # Rendering uses a separate passive PyBullet body. A live
                # simulation frame can transiently contain solver penetration
                # beyond the canonical envelope after a contact impulse. The
                # renderer must remain observational: project that copy onto
                # the mechanical manifold rather than rejecting the frame.
                # Checkpoint/replay restoration keeps the strict default above.
            # Bullet may report a sub-degree solver penetration at a hard stop.
            # Canonical restoration projects only tolerated penetration back
            # onto the declared mechanical manifold; visual restoration also
            # projects larger live-solver excursions without mutating reality.
            mechanical_lower, mechanical_upper = mechanical_joint_limits(spec)
            joint_position = max(
                mechanical_lower,
                min(mechanical_upper, joint_position),
            )
            joint_velocity = float(raw_velocity)
            # Suppress outward velocity when the joint is at a mechanical hard
            # stop. joint_position was clamped to mechanical_lower/upper above,
            # so compare against those same values (not spec.lower/upper which
            # are 2° more extreme and can never be reached after clamping).
            if joint_position == mechanical_lower and joint_velocity < 0.0:
                joint_velocity = 0.0
            elif joint_position == mechanical_upper and joint_velocity > 0.0:
                joint_velocity = 0.0
            seen.add(raw_index)
            validated.append((raw_index, joint_position, joint_velocity))
        if seen != expected:
            raise ValueError("body state does not contain every motor joint")

        self.p.resetBasePositionAndOrientation(
            self.body_id, position, orientation, physicsClientId=self.client_id
        )
        self.p.resetBaseVelocity(
            self.body_id,
            linearVelocity=linear_velocity,
            angularVelocity=angular_velocity,
            physicsClientId=self.client_id,
        )
        for joint_index, joint_position, joint_velocity in validated:
            self.p.resetJointState(
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
        scale = max(0.0, float(torque_scale))
        applied: dict[int, float] = {}
        for ordinal, binding in enumerate(self.motor_bindings):
            positive = max(
                0.0, min(1.0, float(activations.get(binding.positive_port, 0.0)))
            )
            negative = max(
                0.0, min(1.0, float(activations.get(binding.negative_port, 0.0)))
            )
            spec = JOINT_SPECS[ordinal]
            torque = (positive - negative) * spec.max_motor_torque * scale
            applied[binding.joint_index] = float(torque)
        self._applied_torque_by_joint = applied
        self.prepare_physics_substep()

    def prepare_physics_substep(self) -> None:
        # Bullet/URDF owns the hard anatomical range. Near either end of that
        # range, passive ligament-like resistance rises before the hard stop.
        p = self.p
        if hasattr(p, "getJointStates"):
            states = p.getJointStates(
                self.body_id,
                self.motor_joint_indices,
                physicsClientId=self.client_id,
            )
        else:
            states = [
                p.getJointState(self.body_id, i, physicsClientId=self.client_id)
                for i in self.motor_joint_indices
            ]
        for ordinal, (joint_index, state) in enumerate(
            zip(self.motor_joint_indices, states)
        ):
            spec = JOINT_SPECS[ordinal]
            position = float(state[0])
            velocity = float(state[1])
            passive = (
                _passive_postural_tone(
                    spec,
                    position=position,
                    velocity=velocity,
                )
                + _end_range_resistance(
                    spec,
                    position=position,
                    velocity=velocity,
                )
            )
            commanded = float(self._applied_torque_by_joint.get(joint_index, 0.0))
            self.p.setJointMotorControl2(
                self.body_id,
                joint_index,
                self.p.TORQUE_CONTROL,
                force=float(commanded + passive),
                physicsClientId=self.client_id,
            )

    def actuator_work_step(self, dt: float) -> ActuatorWork:
        if not math.isfinite(float(dt)) or dt <= 0.0:
            raise ValueError("dt must be finite and positive")
        active = [
            (idx, float(torque))
            for idx, torque in self._applied_torque_by_joint.items()
            if abs(float(torque)) > 1e-9
        ]
        if not active:
            return ActuatorWork(0.0, 0.0, 0.0, 0.0)
        indices = [item[0] for item in active]
        p = self.p
        if hasattr(p, "getJointStates"):
            raw_states = p.getJointStates(
                self.body_id, indices, physicsClientId=self.client_id
            )
        else:
            raw_states = [
                p.getJointState(self.body_id, i, physicsClientId=self.client_id)
                for i in indices
            ]

        positive = 0.0
        negative = 0.0
        for (_, torque), state in zip(active, raw_states):
            work = torque * float(state[1]) * float(dt)
            if work >= 0.0:
                positive += work
            else:
                negative += -work
        return ActuatorWork(
            positive_j=float(positive),
            negative_j=float(negative),
            absolute_j=float(positive + negative),
            net_j=float(positive - negative),
        )

    def mechanical_work_step(self, dt: float) -> float:
        """Absolute commanded actuator work retained as the metabolic effort scalar."""
        return self.actuator_work_step(dt).absolute_j
