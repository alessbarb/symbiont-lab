"""Body catalog for Physics3D embodiments.

The registry is apparatus-owned.  It exposes only body contracts and factories;
it never supplies semantic labels to the organism.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .alternative_bodies import (
    ASYMMETRIC_SPEC,
    CRAWLER_SPEC,
    AsymmetricPhysics,
    CrawlerPhysics,
)
from .humanoid import (
    BODY_KIND,
    BODY_STATE_SCHEMA_VERSION,
    CONTACT_LINK_NAMES,
    GROUND_MATERIAL,
    JOINT_SPECS,
    JOINT_TOPOLOGY,
    MOTOR_DOF,
    SEGMENTS,
    TOTAL_RECEPTOR_COUNT,
    HumanoidPhysics,
    effector_contract_ids,
    interoceptive_receptor_contract_ids,
    receptor_contract_ids,
)


@dataclass(frozen=True, slots=True)
class BodyDescriptor:
    body_kind: str
    display_name: str
    version: int
    motor_dof: int
    receptor_count: int
    effector_count: int
    receptor_ids: tuple[str, ...]
    interoceptive_receptor_ids: tuple[str, ...]
    effector_ids: tuple[str, ...]
    apparatus_factory: Callable[[Any, int], Any]
    ground_material: Any
    observer_joint_specs: tuple[Any, ...] = ()
    observer_contact_region_names: tuple[str, ...] = ()
    observer_segments: Any = None
    observer_joint_topology: tuple[Any, ...] = ()
    observer_base_link_name: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.body_kind,
            "body_kind": self.body_kind,
            "display_name": self.display_name,
            "version": self.version,
            "motor_dof": self.motor_dof,
            "receptor_count": self.receptor_count,
            "effector_count": self.effector_count,
            "available": True,
            "observer_model": {
                "base_link": self.observer_base_link_name,
                "segments": {
                    str(name): {
                        "size": [float(value) for value in segment.size],
                        "origin": [float(value) for value in segment.origin],
                    }
                    for name, segment in (
                        self.observer_segments.items() if self.observer_segments is not None else ()
                    )
                },
                "joints": [
                    {
                        "name": str(topology.joint_name),
                        "parent": str(topology.parent_link),
                        "child": str(topology.child_link),
                        "origin": [float(value) for value in topology.origin],
                        "axis": [float(value) for value in self.observer_joint_specs[index].axis],
                    }
                    for index, topology in enumerate(self.observer_joint_topology)
                ],
            },
        }


class BodyRegistry:
    def __init__(self, descriptors: tuple[BodyDescriptor, ...]) -> None:
        self._descriptors = {descriptor.body_kind: descriptor for descriptor in descriptors}
        if not self._descriptors:
            raise ValueError("body registry requires at least one descriptor")

    def get(self, body_kind: str) -> BodyDescriptor:
        try:
            return self._descriptors[str(body_kind)]
        except KeyError as exc:
            raise ValueError(f"unsupported body kind: {body_kind}") from exc

    def list(self) -> tuple[BodyDescriptor, ...]:
        return tuple(self._descriptors[key] for key in sorted(self._descriptors))


ANTHROPOMORPHIC_V6 = BodyDescriptor(
    body_kind=BODY_KIND,
    display_name="Anthropomorphic",
    version=BODY_STATE_SCHEMA_VERSION,
    motor_dof=MOTOR_DOF,
    receptor_count=TOTAL_RECEPTOR_COUNT,
    effector_count=MOTOR_DOF * 2,
    receptor_ids=receptor_contract_ids(),
    interoceptive_receptor_ids=interoceptive_receptor_contract_ids(),
    effector_ids=effector_contract_ids(),
    apparatus_factory=HumanoidPhysics,
    ground_material=GROUND_MATERIAL,
    observer_joint_specs=JOINT_SPECS,
    observer_contact_region_names=("pelvis", *CONTACT_LINK_NAMES),
    observer_segments=SEGMENTS,
    observer_joint_topology=JOINT_TOPOLOGY,
    observer_base_link_name="pelvis",
)

CRAWLER_V1 = BodyDescriptor(
    body_kind=CRAWLER_SPEC.body_kind,
    display_name="Crawler",
    version=CRAWLER_SPEC.state_schema_version,
    motor_dof=CRAWLER_SPEC.motor_dof,
    receptor_count=CRAWLER_SPEC.total_receptor_count,
    effector_count=CRAWLER_SPEC.effector_count,
    receptor_ids=CRAWLER_SPEC.receptor_ids(),
    interoceptive_receptor_ids=CRAWLER_SPEC.interoceptive_receptor_ids(),
    effector_ids=CRAWLER_SPEC.effector_ids(),
    apparatus_factory=CrawlerPhysics,
    ground_material=GROUND_MATERIAL,
    observer_joint_specs=CRAWLER_SPEC.joint_specs,
    observer_contact_region_names=(
        CRAWLER_SPEC.base_link_name,
        *CRAWLER_SPEC.contact_link_names,
    ),
    observer_segments=CRAWLER_SPEC.segments,
    observer_joint_topology=CRAWLER_SPEC.joint_topology,
    observer_base_link_name=CRAWLER_SPEC.base_link_name,
)

ASYMMETRIC_V1 = BodyDescriptor(
    body_kind=ASYMMETRIC_SPEC.body_kind,
    display_name="Asymmetric",
    version=ASYMMETRIC_SPEC.state_schema_version,
    motor_dof=ASYMMETRIC_SPEC.motor_dof,
    receptor_count=ASYMMETRIC_SPEC.total_receptor_count,
    effector_count=ASYMMETRIC_SPEC.effector_count,
    receptor_ids=ASYMMETRIC_SPEC.receptor_ids(),
    interoceptive_receptor_ids=ASYMMETRIC_SPEC.interoceptive_receptor_ids(),
    effector_ids=ASYMMETRIC_SPEC.effector_ids(),
    apparatus_factory=AsymmetricPhysics,
    ground_material=GROUND_MATERIAL,
    observer_joint_specs=ASYMMETRIC_SPEC.joint_specs,
    observer_contact_region_names=(
        ASYMMETRIC_SPEC.base_link_name,
        *ASYMMETRIC_SPEC.contact_link_names,
    ),
    observer_segments=ASYMMETRIC_SPEC.segments,
    observer_joint_topology=ASYMMETRIC_SPEC.joint_topology,
    observer_base_link_name=ASYMMETRIC_SPEC.base_link_name,
)

DEFAULT_BODY_REGISTRY = BodyRegistry(
    (
        ANTHROPOMORPHIC_V6,
        CRAWLER_V1,
        ASYMMETRIC_V1,
    )
)


__all__ = [
    "ANTHROPOMORPHIC_V6",
    "CRAWLER_V1",
    "ASYMMETRIC_V1",
    "BodyDescriptor",
    "BodyRegistry",
    "DEFAULT_BODY_REGISTRY",
]
