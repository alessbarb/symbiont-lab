"""Read-only spatial truth adapter. Never a world model given to Symbiont."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4


class PhysicsWorldObserver:
    """Session-scoped IDs; geometry comes from the active collision engine."""

    def __init__(self) -> None:
        self.world_id = f"physics3d.{uuid4().hex}"
        self._ids: dict[int, str] = {}
        self._next_id = 0

    def capture(self, runtime) -> dict:
        p, client = runtime.p, runtime.client_id
        body = runtime.apparatus.body_id
        native = {
            p.getBodyUniqueId(i, physicsClientId=client)
            for i in range(p.getNumBodies(physicsClientId=client))
        }
        for removed in set(self._ids) - native:
            del self._ids[removed]
        for uid in sorted(native):
            if uid not in self._ids:
                self._ids[uid] = f"entity.{self._next_id}"
                self._next_id += 1
        entities = {}
        shape_names = {
            p.GEOM_PLANE: "plane",
            p.GEOM_SPHERE: "sphere",
            p.GEOM_BOX: "box",
            p.GEOM_CYLINDER: "cylinder",
            p.GEOM_CAPSULE: "capsule",
        }
        for uid in sorted(native - {body}):
            for link in range(-1, p.getNumJoints(uid, physicsClientId=client)):
                if link == -1:
                    pos, orn = p.getBasePositionAndOrientation(uid, physicsClientId=client)
                else:
                    state = p.getLinkState(uid, link, physicsClientId=client)
                    pos, orn = state[0], state[1]
                shapes = []
                for shape in p.getCollisionShapeData(uid, link, physicsClientId=client):
                    shapes.append(
                        {
                            "kind": shape_names.get(shape[2], "unsupported"),
                            "dimensions": list(shape[3]),
                            "position": list(shape[5]),
                            "orientation": list(shape[6]),
                        }
                    )
                dynamics = p.getDynamicsInfo(uid, link, physicsClientId=client)
                eid = self._ids[uid] if link == -1 else f"{self._ids[uid]}.link.{link}"
                entity = {
                    "id": eid,
                    "position": list(pos),
                    "orientation": list(orn),
                    "shapes": shapes,
                    "exists": True,
                    "material": {"mass": dynamics[0], "lateral_friction": dynamics[1], "restitution": dynamics[5]},
                    "provenance": "physics-collision-geometry",
                }
                if uid == runtime.resource.body_id:
                    entity["field"] = {
                        "radius": runtime.resource.field_radius,
                        "active": runtime.resource.remaining > 0,
                        "form": "isotropic-scalar",
                    }
                entities[eid] = entity
        descriptor = runtime.body_descriptor
        specs = descriptor.observer_joint_specs
        regions = descriptor.observer_contact_region_names
        # Joint names and link attachments are apparatus facts, not cognitive names.
        joint_links = {}

        def decode(value):
            return value.decode() if isinstance(value, bytes) else str(value)

        for index in range(p.getNumJoints(body, physicsClientId=client)):
            info = p.getJointInfo(body, index, physicsClientId=client)
            joint_links[decode(info[1])] = decode(info[12])
        receptors = {}
        ordinal = 0
        for spec in specs:
            for channel in ("angle", "angular_velocity"):
                receptors[f"rec.{ordinal}"] = {
                    "modality": "proprioception",
                    "joint": spec.name,
                    "link": joint_links.get(spec.name),
                    "channel": channel,
                }
                ordinal += 1
        for _ in range(10):
            receptors[f"rec.{ordinal}"] = {"modality": "kinematics", "link": None}
            ordinal += 1
        for region in regions:
            receptors[f"rec.{ordinal}"] = {"modality": "contact", "link": region}
            ordinal += 1
        receptors[f"rec.{ordinal}"] = {
            "modality": "scalar_field",
            "link": None,
            "source_entity_id": self._ids[runtime.resource.body_id],
            "source_attribution": "observer-only; no direction or object identity sensed",
        }
        ordinal += 1
        for region in regions:
            receptors[f"rec.{ordinal}"] = {"modality": "contact_load", "link": region}
            ordinal += 1
        contacts = []
        raw = runtime.passive_physical_state()
        link_names = {
            int(item.get("link_index", -999)): item.get("link_name")
            for item in raw.get("links", ())
        }
        # Link indexes are not exported by every apparatus, so read engine names.
        for i in range(p.getNumJoints(body, physicsClientId=client)):
            name = p.getJointInfo(body, i, physicsClientId=client)[12]
            link_names[i] = name.decode() if isinstance(name, bytes) else str(name)
        base_name = p.getBodyInfo(body, physicsClientId=client)[0]
        link_names[-1] = base_name.decode() if isinstance(base_name, bytes) else str(base_name)
        for i, item in enumerate(p.getContactPoints(bodyA=body, physicsClientId=client)):
            counterpart = self._ids.get(item[2]) if item[2] != body else None
            if counterpart and item[4] != -1:
                counterpart += f".link.{item[4]}"
            contacts.append(
                {
                    "id": f"contact.{i}",
                    "link": link_names.get(item[3]),
                    "entity_id": counterpart,
                    "self_contact": item[2] == body,
                    "position": list(item[5]),
                    "normal": list(item[7]),
                    "normal_force": float(item[9]),
                    "phase": "post-action",
                }
            )
        return {
            "world_id": self.world_id,
            "entities": entities,
            "receptors": receptors,
            "contacts": contacts,
            "coordinates": {"up": "z", "units": "metres", "quaternion": "xyzw"},
            "environment": "physics3d",
            "environment_recipe": deepcopy(getattr(runtime, "environment_recipe", None)),
            "provenance": {"owner": "observer", "feeds_back": False},
        }
