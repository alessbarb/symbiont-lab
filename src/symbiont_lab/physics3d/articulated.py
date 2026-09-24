"""Generic opaque articulated Physics3D apparatus.

This module owns only physical mechanics. Human-readable joint/link names are
observer-side metadata; organisms see ordinal rec.N / eff.N channels only.
"""
from __future__ import annotations

import math
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .humanoid import (
    BODY_MATERIAL,
    END_RANGE_DAMPING,
    END_RANGE_MARGIN,
    END_RANGE_STIFFNESS,
    JOINT_LIMIT_SOLVER_TOLERANCE,
    MECHANICAL_LIMIT_GUARD,
    MotorBinding,
    SegmentSpec,
    JointSpec,
    JointTopology,
    SurfaceMaterial,
    apply_surface_material,
)


GLOBAL_KINEMATIC_RECEPTORS = 10
ECOLOGICAL_RECEPTORS = 1
INTEROCEPTIVE_RECEPTOR_COUNT = 4
CARRIER_MASS = 0.05


@dataclass(frozen=True, slots=True)
class ArticulatedBodySpec:
    body_kind: str
    state_schema_version: int
    spawn_height: float
    base_link_name: str
    joint_specs: tuple[JointSpec, ...]
    joint_topology: tuple[JointTopology, ...]
    segments: Mapping[str, SegmentSpec]
    contact_link_names: tuple[str, ...]
    structural_neighbour_names: tuple[tuple[str, str], ...]
    body_material: SurfaceMaterial = BODY_MATERIAL

    @property
    def motor_dof(self) -> int:
        return len(self.joint_specs)

    @property
    def somatic_region_count(self) -> int:
        return 1 + len(self.contact_link_names)

    @property
    def physical_receptor_count(self) -> int:
        return (
            self.motor_dof * 2
            + GLOBAL_KINEMATIC_RECEPTORS
            + self.somatic_region_count * 2
            + ECOLOGICAL_RECEPTORS
        )

    @property
    def total_receptor_count(self) -> int:
        return self.physical_receptor_count + INTEROCEPTIVE_RECEPTOR_COUNT

    @property
    def effector_count(self) -> int:
        return self.motor_dof * 2

    def physical_receptor_ids(self) -> tuple[str, ...]:
        return tuple(f"rec.{i}" for i in range(self.physical_receptor_count))

    def interoceptive_receptor_ids(self) -> tuple[str, ...]:
        return tuple(
            f"rec.{i}"
            for i in range(
                self.physical_receptor_count,
                self.total_receptor_count,
            )
        )

    def receptor_ids(self) -> tuple[str, ...]:
        return tuple(f"rec.{i}" for i in range(self.total_receptor_count))

    def effector_ids(self) -> tuple[str, ...]:
        return tuple(f"eff.{i}" for i in range(self.effector_count))


def _fmt(values: Sequence[float]) -> str:
    return " ".join(f"{float(value):.10g}" for value in values)


def _box_inertia(mass: float, size: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = size
    return (
        mass * (y * y + z * z) / 12.0,
        mass * (x * x + z * z) / 12.0,
        mass * (x * x + y * y) / 12.0,
    )


def _segment_link_xml(name: str, segment: SegmentSpec) -> str:
    ixx, iyy, izz = _box_inertia(segment.mass, segment.size)
    return f"""
  <link name="{name}">
    <inertial>
      <origin xyz="{_fmt(segment.origin)}" rpy="0 0 0"/>
      <mass value="{segment.mass:.10g}"/>
      <inertia ixx="{ixx:.10g}" ixy="0" ixz="0" iyy="{iyy:.10g}" iyz="0" izz="{izz:.10g}"/>
    </inertial>
    <visual>
      <origin xyz="{_fmt(segment.origin)}" rpy="0 0 0"/>
      <geometry><box size="{_fmt(segment.size)}"/></geometry>
      <material name="{name}_material"><color rgba="{_fmt(segment.color)}"/></material>
    </visual>
    <collision>
      <origin xyz="{_fmt(segment.origin)}" rpy="0 0 0"/>
      <geometry><box size="{_fmt(segment.size)}"/></geometry>
    </collision>
  </link>"""


def _carrier_link_xml(name: str) -> str:
    return f"""
  <link name="{name}">
    <inertial>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <mass value="{CARRIER_MASS:.10g}"/>
      <inertia ixx="0.0001" ixy="0" ixz="0" iyy="0.0001" iyz="0" izz="0.0001"/>
    </inertial>
  </link>"""


def _mechanical_joint_limits(spec: JointSpec) -> tuple[float, float]:
    span = spec.upper - spec.lower
    guard = min(MECHANICAL_LIMIT_GUARD, span * 0.1)
    return spec.lower + guard, spec.upper - guard


def _end_range_resistance(spec: JointSpec, *, position: float, velocity: float) -> float:
    lower_zone = spec.lower + min(END_RANGE_MARGIN, (spec.upper - spec.lower) * 0.2)
    upper_zone = spec.upper - min(END_RANGE_MARGIN, (spec.upper - spec.lower) * 0.2)
    torque = 0.0
    if position < lower_zone:
        torque = END_RANGE_STIFFNESS * (lower_zone - position) - END_RANGE_DAMPING * velocity
    elif position > upper_zone:
        torque = -END_RANGE_STIFFNESS * (position - upper_zone) - END_RANGE_DAMPING * velocity
    bound = spec.max_motor_torque * 1.5
    return max(-bound, min(bound, torque))


def _restore_vector(
    payload: Mapping[str, object],
    key: str,
    expected_size: int,
) -> tuple[float, ...]:
    raw = payload.get(key)
    if not isinstance(raw, (list, tuple)) or len(raw) != expected_size:
        raise ValueError(f"{key} must contain {expected_size} values")
    values: list[float] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{key} must contain numeric values")
        values.append(float(item))
    return tuple(values)


def build_articulated_urdf(spec: ArticulatedBodySpec) -> str:
    if len(spec.joint_specs) != len(spec.joint_topology):
        raise ValueError("joint specs/topology length mismatch")
    if tuple(item.joint_name for item in spec.joint_topology) != tuple(
        item.name for item in spec.joint_specs
    ):
        raise ValueError("joint topology order must match joint specs")

    links = {spec.base_link_name, *(item.child_link for item in spec.joint_topology)}
    link_xml = [
        _segment_link_xml(name, spec.segments[name])
        if name in spec.segments
        else _carrier_link_xml(name)
        for name in links
    ]
    by_name = {item.name: item for item in spec.joint_specs}
    joint_xml: list[str] = []
    for topo in spec.joint_topology:
        joint = by_name[topo.joint_name]
        lower, upper = _mechanical_joint_limits(joint)
        joint_xml.append(
            f"""
  <joint name="{joint.name}" type="revolute">
    <parent link="{topo.parent_link}"/>
    <child link="{topo.child_link}"/>
    <origin xyz="{_fmt(topo.origin)}" rpy="0 0 0"/>
    <axis xyz="{_fmt(joint.axis)}"/>
    <limit lower="{lower:.12g}" upper="{upper:.12g}" effort="{joint.max_motor_torque:.12g}" velocity="{joint.max_velocity:.12g}"/>
    <dynamics damping="{joint.passive_damping:.12g}" friction="0"/>
  </joint>"""
        )
    return (
        '<?xml version="1.0"?>\n'
        f'<robot name="symbiont_{spec.body_kind.replace("-", "_")}">'
        + "".join(link_xml)
        + "".join(joint_xml)
        + "\n</robot>\n"
    )


class ArticulatedPhysics:
    """Configurable PyBullet body with opaque ordinal sensorimotor contract."""

    SPEC: ArticulatedBodySpec

    def __init__(self, pybullet_module, client_id: int) -> None:
        spec = self.SPEC
        self.p = pybullet_module
        self.client_id = client_id
        self._sensor_values: dict[str, float] = {}
        self._applied_torque_by_joint: dict[int, float] = {}
        self._external_field_signal = 0.0
        self.body_id = self._create_body(spec.spawn_height)
        self._bind_loaded_constitution()
        self.motor_bindings = tuple(
            MotorBinding(
                joint_index=joint_index,
                positive_port=f"eff.{ordinal * 2}",
                negative_port=f"eff.{ordinal * 2 + 1}",
            )
            for ordinal, joint_index in enumerate(self.motor_joint_indices)
        )
        self.receptor_ids = spec.physical_receptor_ids()
        self.effector_ids = spec.effector_ids()
        self.observer_joint_specs = spec.joint_specs
        self.observer_contact_region_names = (
            spec.base_link_name,
            *spec.contact_link_names,
        )
        self._configure_self_collisions()
        self._configure_joint_dynamics()
        self._configure_surface_materials()
        self._disable_default_motors()

    @staticmethod
    def _decode_name(value: object) -> str:
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)

    def _create_body(self, spawn_height: float) -> int:
        urdf = build_articulated_urdf(self.SPEC)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".urdf",
            prefix=f"symbiont-{self.SPEC.body_kind}-",
            encoding="utf-8",
            delete=False,
        ) as handle:
            handle.write(urdf)
            path = handle.name
        try:
            flags = (
                int(getattr(self.p, "URDF_USE_INERTIA_FROM_FILE", 0))
                | int(getattr(self.p, "URDF_USE_SELF_COLLISION", 0))
            )
            body_id = self.p.loadURDF(
                path,
                basePosition=(0.0, 0.0, float(spawn_height)),
                baseOrientation=(0.0, 0.0, 0.0, 1.0),
                useFixedBase=False,
                flags=flags,
                physicsClientId=self.client_id,
            )
        finally:
            Path(path).unlink(missing_ok=True)
        if int(body_id) < 0:
            raise RuntimeError(f"failed to load {self.SPEC.body_kind} URDF")
        return int(body_id)

    def _bind_loaded_constitution(self) -> None:
        spec = self.SPEC
        count = int(self.p.getNumJoints(self.body_id, physicsClientId=self.client_id))
        if count != spec.motor_dof:
            raise RuntimeError(
                f"{spec.body_kind} loaded {count} joints, expected {spec.motor_dof}"
            )
        index_by_joint_name: dict[str, int] = {}
        index_by_link_name: dict[str, int] = {spec.base_link_name: -1}
        parent_by_index: dict[int, int] = {}
        for index in range(count):
            info = self.p.getJointInfo(self.body_id, index, physicsClientId=self.client_id)
            index_by_joint_name[self._decode_name(info[1])] = index
            index_by_link_name[self._decode_name(info[12])] = index
            parent_by_index[index] = int(info[16])

        missing = [item.name for item in spec.joint_specs if item.name not in index_by_joint_name]
        if missing:
            raise RuntimeError(f"URDF missing joints: {missing}")
        self.motor_joint_indices = tuple(
            index_by_joint_name[item.name] for item in spec.joint_specs
        )
        if self.motor_joint_indices != tuple(range(spec.motor_dof)):
            raise RuntimeError(
                f"Bullet reordered {spec.body_kind} joints; opaque contract unsafe"
            )
        self._joint_ordinal_by_index = {
            joint_index: ordinal
            for ordinal, joint_index in enumerate(self.motor_joint_indices)
        }
        self._link_index_by_name = index_by_link_name
        self._contact_links = (
            -1,
            *(index_by_link_name[name] for name in spec.contact_link_names),
        )
        self._direct_pairs = {
            tuple(sorted((parent_by_index[index], index)))
            for index in range(count)
        }
        self._structural_collision_exclusions = {
            tuple(sorted((index_by_link_name[left], index_by_link_name[right])))
            for left, right in spec.structural_neighbour_names
        }
        self._verify_loaded_joint_contract()

    def _verify_loaded_joint_contract(self) -> None:
        for ordinal, joint_index in enumerate(self.motor_joint_indices):
            info = self.p.getJointInfo(
                self.body_id, joint_index, physicsClientId=self.client_id
            )
            spec = self.SPEC.joint_specs[ordinal]
            lower, upper = _mechanical_joint_limits(spec)
            if abs(float(info[8]) - lower) > 1e-6 or abs(float(info[9]) - upper) > 1e-6:
                raise RuntimeError(f"Bullet did not load limits for {spec.name}")

    def _configure_self_collisions(self) -> None:
        excluded = self._direct_pairs | self._structural_collision_exclusions
        links = tuple(range(-1, self.SPEC.motor_dof))
        for offset, link_a in enumerate(links):
            for link_b in links[offset + 1:]:
                pair = tuple(sorted((link_a, link_b)))
                self.p.setCollisionFilterPair(
                    self.body_id,
                    self.body_id,
                    link_a,
                    link_b,
                    enableCollision=0 if pair in excluded else 1,
                    physicsClientId=self.client_id,
                )

    def _configure_joint_dynamics(self) -> None:
        for ordinal, joint_index in enumerate(self.motor_joint_indices):
            self.p.changeDynamics(
                self.body_id,
                joint_index,
                maxJointVelocity=float(self.SPEC.joint_specs[ordinal].max_velocity),
                physicsClientId=self.client_id,
            )

    def _configure_surface_materials(self) -> None:
        for link_index in range(-1, self.SPEC.motor_dof):
            apply_surface_material(
                self.p,
                self.body_id,
                link_index,
                self.SPEC.body_material,
                client_id=self.client_id,
            )

    def _disable_default_motors(self) -> None:
        for joint_index in self.motor_joint_indices:
            self.p.setJointMotorControl2(
                self.body_id,
                joint_index,
                self.p.VELOCITY_CONTROL,
                targetVelocity=0.0,
                force=0.0,
                physicsClientId=self.client_id,
            )

    def set_opaque_environment_state(self, *, external_field: float) -> None:
        value = float(external_field)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("external_field must be within [0, 1]")
        self._external_field_signal = value

    @staticmethod
    def _bounded_contact_load(value: float, scale: float = 120.0) -> float:
        return math.tanh(max(0.0, float(value)) / max(scale, 1e-12))

    @staticmethod
    def _signed_unit(value: float, scale: float) -> float:
        return 0.5 + 0.5 * math.tanh(float(value) / max(scale, 1e-12))

    def sample_receptors(self) -> Mapping[str, float]:
        values: list[float] = []
        if hasattr(self.p, "getJointStates"):
            states = self.p.getJointStates(
                self.body_id,
                self.motor_joint_indices,
                physicsClientId=self.client_id,
            )
        else:
            states = [
                self.p.getJointState(self.body_id, idx, physicsClientId=self.client_id)
                for idx in self.motor_joint_indices
            ]
        for state in states:
            values.extend((
                self._signed_unit(state[0], math.pi),
                self._signed_unit(state[1], 6.0),
            ))

        _position, orientation = self.p.getBasePositionAndOrientation(
            self.body_id, physicsClientId=self.client_id
        )
        linear_velocity, angular_velocity = self.p.getBaseVelocity(
            self.body_id, physicsClientId=self.client_id
        )
        values.extend(max(0.0, min(1.0, 0.5 + 0.5 * float(q))) for q in orientation)
        values.extend(self._signed_unit(v, 4.0) for v in linear_velocity)
        values.extend(self._signed_unit(v, 6.0) for v in angular_velocity)

        contacts = self.p.getContactPoints(
            bodyA=self.body_id, physicsClientId=self.client_id
        )
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

        peak_force = {link: 0.0 for link in self._contact_links}
        for item in contacts:
            if len(item) <= 9:
                continue
            force = max(0.0, float(item[9]))
            link_a = int(item[3])
            if link_a in peak_force:
                peak_force[link_a] = max(peak_force[link_a], force)
            if (
                len(item) > 4
                and int(item[1]) == self.body_id
                and int(item[2]) == self.body_id
            ):
                link_b = int(item[4])
                if link_b in peak_force:
                    peak_force[link_b] = max(peak_force[link_b], force)
        values.extend(self._bounded_contact_load(peak_force[link]) for link in self._contact_links)

        if len(values) != len(self.receptor_ids):
            raise RuntimeError(
                f"physics receptor contract mismatch: {len(values)} != {len(self.receptor_ids)}"
            )
        self._sensor_values = dict(zip(self.receptor_ids, values))
        return dict(self._sensor_values)

    def receptor_value(self, receptor_id: str) -> float:
        return float(self._sensor_values.get(receptor_id, 0.0))

    def apply_effectors(
        self,
        activations: Mapping[str, float],
        *,
        torque_scale: float = 1.0,
    ) -> None:
        scale = max(0.0, float(torque_scale))
        applied: dict[int, float] = {}
        for ordinal, binding in enumerate(self.motor_bindings):
            positive = max(0.0, min(1.0, float(activations.get(binding.positive_port, 0.0))))
            negative = max(0.0, min(1.0, float(activations.get(binding.negative_port, 0.0))))
            spec = self.SPEC.joint_specs[ordinal]
            applied[binding.joint_index] = (
                (positive - negative) * spec.max_motor_torque * scale
            )
        self._applied_torque_by_joint = applied
        self.prepare_physics_substep()

    def prepare_physics_substep(self) -> None:
        if hasattr(self.p, "getJointStates"):
            states = self.p.getJointStates(
                self.body_id,
                self.motor_joint_indices,
                physicsClientId=self.client_id,
            )
        else:
            states = [
                self.p.getJointState(self.body_id, idx, physicsClientId=self.client_id)
                for idx in self.motor_joint_indices
            ]
        for ordinal, (joint_index, state) in enumerate(zip(self.motor_joint_indices, states)):
            spec = self.SPEC.joint_specs[ordinal]
            passive = _end_range_resistance(
                spec,
                position=float(state[0]),
                velocity=float(state[1]),
            )
            commanded = float(self._applied_torque_by_joint.get(joint_index, 0.0))
            self.p.setJointMotorControl2(
                self.body_id,
                joint_index,
                self.p.TORQUE_CONTROL,
                force=float(commanded + passive),
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
        states = (
            self.p.getJointStates(self.body_id, indices, physicsClientId=self.client_id)
            if hasattr(self.p, "getJointStates")
            else [
                self.p.getJointState(self.body_id, idx, physicsClientId=self.client_id)
                for idx in indices
            ]
        )
        return float(sum(
            abs(torque * float(state[1])) * float(dt)
            for (_, torque), state in zip(active, states)
        ))

    def export_physical_state(self) -> dict[str, object]:
        base_position, base_orientation = self.p.getBasePositionAndOrientation(
            self.body_id, physicsClientId=self.client_id
        )
        linear_velocity, angular_velocity = self.p.getBaseVelocity(
            self.body_id, physicsClientId=self.client_id
        )
        states = cast(
            Sequence[Sequence[object]],
            self.p.getJointStates(
                self.body_id,
                self.motor_joint_indices,
                physicsClientId=self.client_id,
            )
            if hasattr(self.p, "getJointStates")
            else [
                self.p.getJointState(self.body_id, idx, physicsClientId=self.client_id)
                for idx in self.motor_joint_indices
            ],
        )
        joints = [
            {
                "joint_index": int(joint_index),
                "joint_name": self.SPEC.joint_specs[ordinal].name,
                "position": float(state[0]),
                "velocity": float(state[1]),
                "applied_torque": float(self._applied_torque_by_joint.get(joint_index, 0.0)),
            }
            for ordinal, (joint_index, state) in enumerate(
                zip(self.motor_joint_indices, states)
            )
        ]

        links: list[dict[str, object]] = []
        weighted_com = [0.0, 0.0, 0.0]
        total_mass = 0.0
        for name, index in sorted(self._link_index_by_name.items(), key=lambda item: item[1]):
            if index == -1:
                link_position = base_position
                link_orientation = base_orientation
                com = base_position
            else:
                state = self.p.getLinkState(
                    self.body_id,
                    index,
                    computeForwardKinematics=True,
                    physicsClientId=self.client_id,
                )
                link_position, link_orientation, com = state[4], state[5], state[0]
            mass = 1.0
            if hasattr(self.p, "getDynamicsInfo"):
                dynamics = self.p.getDynamicsInfo(
                    self.body_id, index, physicsClientId=self.client_id
                )
                if dynamics and isinstance(dynamics[0], (int, float)):
                    mass = max(0.0, float(dynamics[0]))
            total_mass += mass
            for axis in range(3):
                weighted_com[axis] += mass * float(com[axis])
            links.append({
                "link_index": int(index),
                "link_name": str(name),
                "position": [float(x) for x in link_position],
                "orientation": [float(x) for x in link_orientation],
            })
        center_of_mass = (
            [value / total_mass for value in weighted_com]
            if total_mass > 0.0
            else [float(value) for value in base_position]
        )
        contacts = self.p.getContactPoints(bodyA=self.body_id, physicsClientId=self.client_id)
        return {
            "schema_version": self.SPEC.state_schema_version,
            "body_kind": self.SPEC.body_kind,
            "base_position": [float(x) for x in base_position],
            "base_orientation": [float(x) for x in base_orientation],
            "linear_velocity": [float(x) for x in linear_velocity],
            "angular_velocity": [float(x) for x in angular_velocity],
            "center_of_mass": center_of_mass,
            "total_mass": float(total_mass),
            "joints": joints,
            "links": links,
            "contact_links": sorted({
                int(item[3]) for item in contacts if len(item) > 3
            }),
            "contact_count": len(contacts),
        }

    def restore_physical_state(
        self,
        payload: Mapping[str, object],
        *,
        strict_anatomical_limits: bool = True,
    ) -> None:
        if payload.get("schema_version") != self.SPEC.state_schema_version:
            raise ValueError("unsupported physics body state schema")
        if payload.get("body_kind") != self.SPEC.body_kind:
            raise ValueError(f"body state is not compatible with {self.SPEC.body_kind}")
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
                raise ValueError("joint state contains invalid values")
            if raw_index not in expected:
                raise ValueError(f"unexpected joint index: {raw_index}")
            ordinal = self._joint_ordinal_by_index[raw_index]
            spec = self.SPEC.joint_specs[ordinal]
            joint_position = float(raw_position)
            if not (
                spec.lower - JOINT_LIMIT_SOLVER_TOLERANCE
                <= joint_position
                <= spec.upper + JOINT_LIMIT_SOLVER_TOLERANCE
            ) and strict_anatomical_limits:
                raise ValueError(
                    f"joint state outside hard anatomical limit: {spec.name}"
                )
            lower, upper = _mechanical_joint_limits(spec)
            joint_position = max(lower, min(upper, joint_position))
            joint_velocity = float(raw_velocity)
            if joint_position == lower and joint_velocity < 0.0:
                joint_velocity = 0.0
            elif joint_position == upper and joint_velocity > 0.0:
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
