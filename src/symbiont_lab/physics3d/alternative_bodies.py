"""Alternative Physics3D body constitutions for cross-morphology studies."""
from __future__ import annotations

import math

from .articulated import ArticulatedBodySpec, ArticulatedPhysics
from .humanoid import (
    GROUND_MATERIAL,
    JointSpec,
    JointTopology,
    SegmentSpec,
)


def _deg(value: float) -> float:
    return math.radians(value)


# ---------------------------------------------------------------------------
# crawler-v1: four-limbed, low-centre-of-mass body; 3 DoF per limb.
# ---------------------------------------------------------------------------

CRAWLER_JOINT_SPECS: tuple[JointSpec, ...] = (
    JointSpec("front_left_hip_yaw", (0, 0, 1), _deg(-45), _deg(45), 12.0, 1.5, 5.0),
    JointSpec("front_left_hip_pitch", (0, 1, 0), _deg(-65), _deg(75), 18.0, 2.0, 5.0),
    JointSpec("front_left_knee_pitch", (0, 1, 0), _deg(-100), _deg(25), 14.0, 1.6, 6.0),
    JointSpec("front_right_hip_yaw", (0, 0, 1), _deg(-45), _deg(45), 12.0, 1.5, 5.0),
    JointSpec("front_right_hip_pitch", (0, 1, 0), _deg(-65), _deg(75), 18.0, 2.0, 5.0),
    JointSpec("front_right_knee_pitch", (0, 1, 0), _deg(-100), _deg(25), 14.0, 1.6, 6.0),
    JointSpec("rear_left_hip_yaw", (0, 0, 1), _deg(-45), _deg(45), 14.0, 1.5, 5.0),
    JointSpec("rear_left_hip_pitch", (0, 1, 0), _deg(-75), _deg(65), 20.0, 2.0, 5.0),
    JointSpec("rear_left_knee_pitch", (0, 1, 0), _deg(-25), _deg(100), 16.0, 1.6, 6.0),
    JointSpec("rear_right_hip_yaw", (0, 0, 1), _deg(-45), _deg(45), 14.0, 1.5, 5.0),
    JointSpec("rear_right_hip_pitch", (0, 1, 0), _deg(-75), _deg(65), 20.0, 2.0, 5.0),
    JointSpec("rear_right_knee_pitch", (0, 1, 0), _deg(-25), _deg(100), 16.0, 1.6, 6.0),
)

CRAWLER_SEGMENTS = {
    "body": SegmentSpec(10.0, (0.62, 0.34, 0.20), (0, 0, 0), (0.34, 0.46, 0.56, 1)),
    "front_left_upper": SegmentSpec(1.0, (0.28, 0.10, 0.10), (-0.14, 0, 0), (0.30, 0.64, 0.76, 1)),
    "front_left_lower": SegmentSpec(0.7, (0.28, 0.09, 0.09), (-0.14, 0, 0), (0.36, 0.72, 0.82, 1)),
    "front_left_foot": SegmentSpec(0.25, (0.16, 0.12, 0.06), (-0.06, 0, -0.02), (0.40, 0.76, 0.84, 1)),
    "front_right_upper": SegmentSpec(1.0, (0.28, 0.10, 0.10), (0.14, 0, 0), (0.82, 0.52, 0.26, 1)),
    "front_right_lower": SegmentSpec(0.7, (0.28, 0.09, 0.09), (0.14, 0, 0), (0.88, 0.60, 0.30, 1)),
    "front_right_foot": SegmentSpec(0.25, (0.16, 0.12, 0.06), (0.06, 0, -0.02), (0.92, 0.66, 0.34, 1)),
    "rear_left_upper": SegmentSpec(1.2, (0.30, 0.11, 0.11), (-0.15, 0, 0), (0.30, 0.64, 0.76, 1)),
    "rear_left_lower": SegmentSpec(0.8, (0.30, 0.09, 0.09), (-0.15, 0, 0), (0.36, 0.72, 0.82, 1)),
    "rear_left_foot": SegmentSpec(0.28, (0.18, 0.13, 0.06), (-0.07, 0, -0.02), (0.40, 0.76, 0.84, 1)),
    "rear_right_upper": SegmentSpec(1.2, (0.30, 0.11, 0.11), (0.15, 0, 0), (0.82, 0.52, 0.26, 1)),
    "rear_right_lower": SegmentSpec(0.8, (0.30, 0.09, 0.09), (0.15, 0, 0), (0.88, 0.60, 0.30, 1)),
    "rear_right_foot": SegmentSpec(0.28, (0.18, 0.13, 0.06), (0.07, 0, -0.02), (0.92, 0.66, 0.34, 1)),
}

CRAWLER_TOPOLOGY: tuple[JointTopology, ...] = (
    JointTopology("front_left_hip_yaw", "body", "fl_yaw_carrier", (-0.26, 0.15, 0.0)),
    JointTopology("front_left_hip_pitch", "fl_yaw_carrier", "front_left_upper", (0, 0, 0)),
    JointTopology("front_left_knee_pitch", "front_left_upper", "front_left_lower", (-0.28, 0, 0)),
    JointTopology("front_right_hip_yaw", "body", "fr_yaw_carrier", (0.26, 0.15, 0.0)),
    JointTopology("front_right_hip_pitch", "fr_yaw_carrier", "front_right_upper", (0, 0, 0)),
    JointTopology("front_right_knee_pitch", "front_right_upper", "front_right_lower", (0.28, 0, 0)),
    JointTopology("rear_left_hip_yaw", "body", "rl_yaw_carrier", (-0.26, -0.15, 0.0)),
    JointTopology("rear_left_hip_pitch", "rl_yaw_carrier", "rear_left_upper", (0, 0, 0)),
    JointTopology("rear_left_knee_pitch", "rear_left_upper", "rear_left_lower", (-0.30, 0, 0)),
    JointTopology("rear_right_hip_yaw", "body", "rr_yaw_carrier", (0.26, -0.15, 0.0)),
    JointTopology("rear_right_hip_pitch", "rr_yaw_carrier", "rear_right_upper", (0, 0, 0)),
    JointTopology("rear_right_knee_pitch", "rear_right_upper", "rear_right_lower", (0.30, 0, 0)),
)

# Feet are fixed geometry on the distal links in v1; lower links are the
# mechanically contacting endpoints. This intentionally keeps motor DoF = 12.
CRAWLER_SPEC = ArticulatedBodySpec(
    body_kind="crawler-v1",
    state_schema_version=1,
    spawn_height=0.44,
    base_link_name="body",
    joint_specs=CRAWLER_JOINT_SPECS,
    joint_topology=CRAWLER_TOPOLOGY,
    segments=CRAWLER_SEGMENTS,
    contact_link_names=(
        "front_left_upper", "front_left_lower",
        "front_right_upper", "front_right_lower",
        "rear_left_upper", "rear_left_lower",
        "rear_right_upper", "rear_right_lower",
    ),
    structural_neighbour_names=(
        ("body", "front_left_upper"),
        ("front_left_upper", "front_left_lower"),
        ("body", "front_right_upper"),
        ("front_right_upper", "front_right_lower"),
        ("body", "rear_left_upper"),
        ("rear_left_upper", "rear_left_lower"),
        ("body", "rear_right_upper"),
        ("rear_right_upper", "rear_right_lower"),
    ),
)


class CrawlerPhysics(ArticulatedPhysics):
    SPEC = CRAWLER_SPEC


# ---------------------------------------------------------------------------
# asymmetric-v1: intentionally unbalanced biped with unequal upper limbs.
# ---------------------------------------------------------------------------

ASYMMETRIC_JOINT_SPECS: tuple[JointSpec, ...] = (
    JointSpec("trunk_roll", (0, 1, 0), _deg(-35), _deg(35), 20.0, 2.5, 4.0),
    JointSpec("trunk_pitch", (1, 0, 0), _deg(-40), _deg(55), 22.0, 2.8, 4.0),
    # Left upper limb: 4 DoF.
    JointSpec("left_shoulder_yaw", (0, 0, 1), _deg(-100), _deg(100), 10.0, 1.2, 5.0),
    JointSpec("left_shoulder_pitch", (1, 0, 0), _deg(-55), _deg(165), 11.0, 1.3, 5.0),
    JointSpec("left_elbow_pitch", (1, 0, 0), _deg(0), _deg(145), 7.0, 0.9, 6.0),
    JointSpec("left_wrist_pitch", (1, 0, 0), _deg(-60), _deg(75), 3.0, 0.4, 7.0),
    # Right upper limb: only 2 DoF and shorter/heavier.
    JointSpec("right_shoulder_pitch", (1, 0, 0), _deg(-35), _deg(120), 13.0, 1.5, 4.5),
    JointSpec("right_elbow_pitch", (1, 0, 0), _deg(10), _deg(110), 9.0, 1.1, 5.0),
    # Left leg: 4 DoF.
    JointSpec("left_hip_roll", (0, 1, 0), _deg(-25), _deg(45), 25.0, 3.0, 4.0),
    JointSpec("left_hip_pitch", (1, 0, 0), _deg(-25), _deg(125), 30.0, 3.5, 4.0),
    JointSpec("left_knee_pitch", (1, 0, 0), _deg(0), _deg(140), 25.0, 2.6, 5.0),
    JointSpec("left_ankle_pitch", (1, 0, 0), _deg(-20), _deg(45), 13.0, 1.8, 5.0),
    # Right leg: 3 DoF, heavier and no ankle actuator.
    JointSpec("right_hip_roll", (0, 1, 0), _deg(-35), _deg(20), 28.0, 3.3, 3.8),
    JointSpec("right_hip_pitch", (1, 0, 0), _deg(-15), _deg(110), 34.0, 3.8, 3.8),
    JointSpec("right_knee_pitch", (1, 0, 0), _deg(5), _deg(125), 29.0, 3.0, 4.5),
)

ASYMMETRIC_SEGMENTS = {
    "pelvis": SegmentSpec(5.0, (0.34, 0.22, 0.22), (0, 0, 0), (0.34, 0.45, 0.56, 1)),
    "torso": SegmentSpec(13.0, (0.42, 0.24, 0.50), (0, 0, 0.21), (0.38, 0.50, 0.62, 1)),
    "left_upper_arm": SegmentSpec(0.8, (0.12, 0.12, 0.31), (0, 0, -0.155), (0.28, 0.66, 0.80, 1)),
    "left_forearm": SegmentSpec(0.5, (0.10, 0.10, 0.27), (0, 0, -0.135), (0.34, 0.72, 0.84, 1)),
    "left_hand": SegmentSpec(0.18, (0.09, 0.14, 0.17), (0, 0, -0.085), (0.38, 0.76, 0.86, 1)),
    "right_upper_arm": SegmentSpec(1.6, (0.15, 0.15, 0.25), (0, 0, -0.125), (0.82, 0.48, 0.22, 1)),
    "right_forearm": SegmentSpec(1.0, (0.13, 0.13, 0.21), (0, 0, -0.105), (0.90, 0.58, 0.28, 1)),
    "left_thigh": SegmentSpec(4.0, (0.15, 0.15, 0.39), (0, 0, -0.195), (0.28, 0.66, 0.80, 1)),
    "left_shin": SegmentSpec(1.3, (0.13, 0.13, 0.39), (0, 0, -0.195), (0.34, 0.72, 0.84, 1)),
    "left_foot": SegmentSpec(0.45, (0.12, 0.27, 0.07), (0, -0.07, -0.035), (0.38, 0.76, 0.86, 1)),
    "right_thigh": SegmentSpec(5.4, (0.18, 0.18, 0.36), (0, 0, -0.18), (0.82, 0.48, 0.22, 1)),
    "right_shin": SegmentSpec(2.0, (0.15, 0.15, 0.35), (0, 0, -0.175), (0.90, 0.58, 0.28, 1)),
    "right_foot": SegmentSpec(0.7, (0.15, 0.30, 0.08), (0, -0.08, -0.04), (0.94, 0.64, 0.32, 1)),
}

ASYMMETRIC_TOPOLOGY: tuple[JointTopology, ...] = (
    JointTopology("trunk_roll", "pelvis", "trunk_roll_carrier", (0, 0, 0.10)),
    JointTopology("trunk_pitch", "trunk_roll_carrier", "torso", (0, 0, 0)),
    JointTopology("left_shoulder_yaw", "torso", "left_shoulder_yaw_carrier", (-0.28, 0, 0.36)),
    JointTopology("left_shoulder_pitch", "left_shoulder_yaw_carrier", "left_upper_arm", (0, 0, 0)),
    JointTopology("left_elbow_pitch", "left_upper_arm", "left_forearm", (0, 0, -0.31)),
    JointTopology("left_wrist_pitch", "left_forearm", "left_hand", (0, 0, -0.27)),
    JointTopology("right_shoulder_pitch", "torso", "right_upper_arm", (0.28, 0, 0.34)),
    JointTopology("right_elbow_pitch", "right_upper_arm", "right_forearm", (0, 0, -0.25)),
    JointTopology("left_hip_roll", "pelvis", "left_hip_roll_carrier", (-0.10, 0, -0.10)),
    JointTopology("left_hip_pitch", "left_hip_roll_carrier", "left_thigh", (0, 0, 0)),
    JointTopology("left_knee_pitch", "left_thigh", "left_shin", (0, 0, -0.39)),
    JointTopology("left_ankle_pitch", "left_shin", "left_foot", (0, 0, -0.39)),
    JointTopology("right_hip_roll", "pelvis", "right_hip_roll_carrier", (0.11, 0, -0.10)),
    JointTopology("right_hip_pitch", "right_hip_roll_carrier", "right_thigh", (0, 0, 0)),
    JointTopology("right_knee_pitch", "right_thigh", "right_shin", (0, 0, -0.36)),
)

ASYMMETRIC_SPEC = ArticulatedBodySpec(
    body_kind="asymmetric-v1",
    state_schema_version=1,
    spawn_height=1.02,
    base_link_name="pelvis",
    joint_specs=ASYMMETRIC_JOINT_SPECS,
    joint_topology=ASYMMETRIC_TOPOLOGY,
    segments=ASYMMETRIC_SEGMENTS,
    contact_link_names=(
        "torso",
        "left_upper_arm", "left_forearm", "left_hand",
        "right_upper_arm", "right_forearm",
        "left_thigh", "left_shin", "left_foot",
        "right_thigh", "right_shin",
    ),
    structural_neighbour_names=(
        ("pelvis", "torso"),
        ("torso", "left_upper_arm"),
        ("left_upper_arm", "left_forearm"),
        ("left_forearm", "left_hand"),
        ("torso", "right_upper_arm"),
        ("right_upper_arm", "right_forearm"),
        ("pelvis", "left_thigh"),
        ("left_thigh", "left_shin"),
        ("left_shin", "left_foot"),
        ("pelvis", "right_thigh"),
        ("right_thigh", "right_shin"),
    ),
)


class AsymmetricPhysics(ArticulatedPhysics):
    SPEC = ASYMMETRIC_SPEC


__all__ = [
    "ASYMMETRIC_SPEC",
    "AsymmetricPhysics",
    "CRAWLER_SPEC",
    "CrawlerPhysics",
    "GROUND_MATERIAL",
]
