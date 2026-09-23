"""Observer-side physical consequences for Physics3D motor episodes.

This module describes mechanics only. It does not define reward, utility,
anatomical semantics, locomotion goals or action preference, and its outputs
must never feed back into the organism runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


Vector3 = tuple[float, float, float]
Quaternion = tuple[float, float, float, float]


def _vector3(value: object, *, field: str) -> Vector3:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{field} must contain three values")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{field} must be finite")
    return result  # type: ignore[return-value]


def _quaternion(value: object, *, field: str) -> Quaternion:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"{field} must contain four values")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{field} must be finite")
    norm = math.sqrt(sum(item * item for item in result))
    if norm <= 1e-12:
        raise ValueError(f"{field} must have non-zero norm")
    return tuple(item / norm for item in result)  # type: ignore[return-value]


def _sub(left: Vector3, right: Vector3) -> Vector3:
    return tuple(a - b for a, b in zip(left, right))  # type: ignore[return-value]


def _norm(vector: Vector3) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _quat_mul(left: Quaternion, right: Quaternion) -> Quaternion:
    lx, ly, lz, lw = left
    rx, ry, rz, rw = right
    return (
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    )


def _quat_conjugate(value: Quaternion) -> Quaternion:
    return (-value[0], -value[1], -value[2], value[3])


def rotate_world_to_body(vector: Vector3, orientation_world: Quaternion) -> Vector3:
    """Express a world-frame vector in the body's initial local frame."""
    q = _quaternion(orientation_world, field="orientation_world")
    v = (vector[0], vector[1], vector[2], 0.0)
    rotated = _quat_mul(_quat_mul(_quat_conjugate(q), v), q)
    return (rotated[0], rotated[1], rotated[2])


def _relative_rotation(
    before: Quaternion,
    after: Quaternion,
) -> tuple[Vector3, float]:
    relative = _quat_mul(_quat_conjugate(before), after)
    norm = math.sqrt(sum(item * item for item in relative))
    relative = tuple(item / norm for item in relative)  # type: ignore[assignment]
    if relative[3] < 0.0:
        relative = tuple(-item for item in relative)  # type: ignore[assignment]
    xyz = (relative[0], relative[1], relative[2])
    sin_half = _norm(xyz)
    if sin_half <= 1e-12:
        return (0.0, 0.0, 0.0), 0.0
    angle = 2.0 * math.atan2(sin_half, max(0.0, relative[3]))
    axis = tuple(item / sin_half for item in xyz)
    return tuple(item * angle for item in axis), angle  # type: ignore[return-value]


def _joint_positions(payload: object) -> tuple[tuple[int, float], ...]:
    if not isinstance(payload, (list, tuple)):
        return ()
    result: list[tuple[int, float]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        index = item.get("joint_index")
        position = item.get("position")
        if (
            isinstance(index, int)
            and not isinstance(index, bool)
            and isinstance(position, (int, float))
            and not isinstance(position, bool)
            and math.isfinite(float(position))
        ):
            result.append((int(index), float(position)))
    return tuple(sorted(result))


@dataclass(frozen=True, slots=True)
class PhysicalState:
    tick: int
    position_world: Vector3
    orientation_world: Quaternion
    linear_velocity_world: Vector3
    angular_velocity_world: Vector3
    center_of_mass_world: Vector3
    contact_links: frozenset[int]
    joint_positions: tuple[tuple[int, float], ...]


@dataclass(frozen=True, slots=True)
class StateDistance:
    orientation_angle: float
    linear_velocity_delta: float
    angular_velocity_delta: float
    joint_rms_delta: float
    contact_jaccard_distance: float
    com_height_delta: float


@dataclass(frozen=True, slots=True)
class PhysicalConsequence:
    start_tick: int
    end_tick: int
    translation_world: Vector3
    translation_body: Vector3
    com_translation_world: Vector3
    com_translation_body: Vector3
    translation_magnitude: float
    horizontal_translation: float
    vertical_translation: float
    com_translation_magnitude: float
    base_com_agreement: float
    rotation_body: Vector3
    rotation_angle: float
    path_length: float
    translation_efficiency: float
    initial_linear_velocity_world: Vector3
    final_linear_velocity_world: Vector3
    contact_added: tuple[int, ...]
    contact_removed: tuple[int, ...]
    contact_persistence: float
    pose_delta: float
    mechanical_work_joules: float
    metabolic_cost: float


def physical_state_from_payload(
    tick: int,
    payload: Mapping[str, object],
) -> PhysicalState:
    position = _vector3(payload.get("base_position"), field="base_position")
    orientation = _quaternion(
        payload.get("base_orientation"),
        field="base_orientation",
    )
    linear = _vector3(
        payload.get("linear_velocity", (0.0, 0.0, 0.0)),
        field="linear_velocity",
    )
    angular = _vector3(
        payload.get("angular_velocity", (0.0, 0.0, 0.0)),
        field="angular_velocity",
    )
    center = _vector3(
        payload.get("center_of_mass", position),
        field="center_of_mass",
    )
    raw_contacts = payload.get("contact_links", ())
    contacts = frozenset(
        int(item)
        for item in raw_contacts
        if isinstance(item, int) and not isinstance(item, bool)
    ) if isinstance(raw_contacts, (list, tuple, set, frozenset)) else frozenset()
    return PhysicalState(
        tick=int(tick),
        position_world=position,
        orientation_world=orientation,
        linear_velocity_world=linear,
        angular_velocity_world=angular,
        center_of_mass_world=center,
        contact_links=contacts,
        joint_positions=_joint_positions(payload.get("joints", ())),
    )


def state_distance(left: PhysicalState, right: PhysicalState) -> StateDistance:
    _rotation, orientation_angle = _relative_rotation(
        left.orientation_world,
        right.orientation_world,
    )
    left_joints = dict(left.joint_positions)
    right_joints = dict(right.joint_positions)
    shared = sorted(set(left_joints) & set(right_joints))
    joint_rms = (
        math.sqrt(
            sum((right_joints[key] - left_joints[key]) ** 2 for key in shared)
            / len(shared)
        )
        if shared
        else 0.0
    )
    union = left.contact_links | right.contact_links
    contact_distance = (
        1.0 - len(left.contact_links & right.contact_links) / len(union)
        if union
        else 0.0
    )
    return StateDistance(
        orientation_angle=orientation_angle,
        linear_velocity_delta=_norm(
            _sub(right.linear_velocity_world, left.linear_velocity_world)
        ),
        angular_velocity_delta=_norm(
            _sub(right.angular_velocity_world, left.angular_velocity_world)
        ),
        joint_rms_delta=joint_rms,
        contact_jaccard_distance=contact_distance,
        com_height_delta=abs(
            right.center_of_mass_world[2] - left.center_of_mass_world[2]
        ),
    )


def physical_consequence(
    before: PhysicalState,
    after: PhysicalState,
    *,
    path_length: float = 0.0,
    mechanical_work_joules: float = 0.0,
    metabolic_cost: float = 0.0,
) -> PhysicalConsequence:
    if after.tick < before.tick:
        raise ValueError("physical consequence cannot run backwards in time")
    path = max(0.0, float(path_length))
    work = max(0.0, float(mechanical_work_joules))
    cost = max(0.0, float(metabolic_cost))

    translation_world = _sub(after.position_world, before.position_world)
    translation_body = rotate_world_to_body(
        translation_world,
        before.orientation_world,
    )
    com_world = _sub(
        after.center_of_mass_world,
        before.center_of_mass_world,
    )
    com_body = rotate_world_to_body(com_world, before.orientation_world)
    translation_magnitude = _norm(translation_body)
    horizontal = math.hypot(translation_body[0], translation_body[1])
    com_magnitude = _norm(com_body)

    disagreement = _norm(_sub(translation_body, com_body))
    base_com_agreement = 1.0 - min(
        1.0,
        disagreement / max(translation_magnitude, com_magnitude, 1e-12),
    )

    rotation_body, rotation_angle = _relative_rotation(
        before.orientation_world,
        after.orientation_world,
    )
    before_joints = dict(before.joint_positions)
    after_joints = dict(after.joint_positions)
    shared = sorted(set(before_joints) & set(after_joints))
    pose_delta = (
        sum(abs(after_joints[key] - before_joints[key]) for key in shared)
        / len(shared)
        if shared
        else 0.0
    )

    union = before.contact_links | after.contact_links
    contact_persistence = (
        len(before.contact_links & after.contact_links) / len(union)
        if union
        else 1.0
    )

    return PhysicalConsequence(
        start_tick=before.tick,
        end_tick=after.tick,
        translation_world=translation_world,
        translation_body=translation_body,
        com_translation_world=com_world,
        com_translation_body=com_body,
        translation_magnitude=translation_magnitude,
        horizontal_translation=horizontal,
        vertical_translation=translation_body[2],
        com_translation_magnitude=com_magnitude,
        base_com_agreement=base_com_agreement,
        rotation_body=rotation_body,
        rotation_angle=rotation_angle,
        path_length=path,
        translation_efficiency=(horizontal / path if path > 1e-12 else 0.0),
        initial_linear_velocity_world=before.linear_velocity_world,
        final_linear_velocity_world=after.linear_velocity_world,
        contact_added=tuple(sorted(after.contact_links - before.contact_links)),
        contact_removed=tuple(sorted(before.contact_links - after.contact_links)),
        contact_persistence=contact_persistence,
        pose_delta=pose_delta,
        mechanical_work_joules=work,
        metabolic_cost=cost,
    )


__all__ = [
    "PhysicalConsequence",
    "PhysicalState",
    "Quaternion",
    "StateDistance",
    "Vector3",
    "physical_consequence",
    "physical_state_from_payload",
    "rotate_world_to_body",
    "state_distance",
]
