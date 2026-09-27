"""Observer-only Body in World projection and revisioned spatial deltas."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCENE_CONTRACT = "body-in-world-v1"


def project_world_scene(rich: Mapping[str, Any]) -> dict | None:
    truth = rich.get("world_observation")
    if not isinstance(truth, Mapping):
        return None  # Older recordings have no world evidence.
    pre = rich.get("pre", {})
    samples = pre.get("sensory_input", {}).get("sampled_values")
    # Missing aggregate sampling is unavailable, never evidence of non-sampling.
    complete_sampling = isinstance(samples, Mapping)
    samples = samples if complete_sampling else {}
    semantics = rich.get("observer_semantics", {}).get("sensory", {})
    percepts = {
        str(p["name"]): p
        for p in rich.get("runtime", {}).get("percepts", ())
        if isinstance(p, Mapping) and p.get("name")
    }
    self_model = rich.get("self_model", {})
    evidence = {}
    for rid, anchor in truth.get("receptors", {}).items():
        signals = []
        for sid, mapping in semantics.items():
            if rid not in mapping.get("source_ids", ()):
                continue
            percept = percepts.get(sid)
            signals.append(
                {
                    "id": sid,
                    "source_ids": mapping.get("source_ids", []),
                    "percept": deepcopy(percept),
                    "self_model": deepcopy(self_model.get(sid)),
                    "represented": sid in self_model,
                    "mapping": "observer-source-lineage",
                }
            )
        evidence[rid] = {
            "id": rid,
            "sampled": (rid in samples) if complete_sampling else None,
            "sample": samples.get(rid),
            "signals": signals,
            "percept_emitted": any(
                s["percept"] is not None and s["percept"].get("value") is not None for s in signals
            ),
            "phase": "pre-action",
            "tick": rich.get("tick"),
        }
    return {
        "contract": SCENE_CONTRACT,
        "world_id": truth["world_id"],
        "tick": rich.get("tick"),
        "organism_id": rich.get("organism_id"),
        "embodiment_id": rich.get("embodiment", {}).get("embodiment_id"),
        "body_id": rich.get("embodiment", {}).get("body_id"),
        "coordinates": truth["coordinates"],
        "environment": truth["environment"],
        "entities": deepcopy(truth.get("entities", {})),
        "receptors": deepcopy(truth.get("receptors", {})),
        "contacts": deepcopy(truth.get("contacts", [])),
        "evidence": evidence,
        "sample_pose": {
            "base_position": pre.get("physical", {}).get("base_position"),
            "links": deepcopy(pre.get("physical", {}).get("links", [])),
        },
        "availability": {
            "spatial_object_identity": "not-exported",
            "spatial_memory": "not-exported",
            "object_familiarity": "not-exported",
            "spatial_predictions": "not-exported",
            "vision": "unsupported",
            "reach": "not-exported",
        },
        "provenance": {
            "owner": "observer",
            "feeds_back": False,
            "source_attribution": "not-organism-object-recognition",
        },
    }


class WorldScenePublisher:
    def __init__(self) -> None:
        self.previous: dict | None = None
        self.revision = 0

    def event(self, scene: dict) -> dict:
        previous = self.previous
        self.revision += 1
        current = deepcopy(scene)
        current["revision"] = self.revision
        self.previous = current
        if previous is None or previous["world_id"] != current["world_id"]:
            return {"type": "world_scene", "kind": "snapshot", **current}
        upserts, transforms = {}, {}
        before, after = previous["entities"], current["entities"]
        for eid, entity in after.items():
            if before.get(eid) == entity:
                continue
            old = before.get(eid, {})
            if old and {k: v for k, v in old.items() if k not in ("position", "orientation")} == {
                k: v for k, v in entity.items() if k not in ("position", "orientation")
            }:
                transforms[eid] = {k: entity[k] for k in ("position", "orientation")}
            else:
                upserts[eid] = entity
        changes = {
            k: v
            for k, v in current.items()
            if k not in ("entities", "revision", "world_id", "contract") and previous.get(k) != v
        }
        return {
            "type": "world_scene",
            "kind": "delta",
            "contract": SCENE_CONTRACT,
            "world_id": current["world_id"],
            "revision": self.revision,
            "base_revision": previous["revision"],
            "upserts": upserts,
            "removals": sorted(before.keys() - after.keys()),
            "transforms": transforms,
            "changes": changes,
        }


def apply_world_event(current: dict | None, event: dict) -> dict:
    if event.get("contract") != SCENE_CONTRACT:
        raise ValueError("unsupported spatial scene contract")
    if event.get("kind") == "snapshot":
        return deepcopy(event)
    if (
        current is None
        or current["world_id"] != event["world_id"]
        or current["revision"] != event.get("base_revision")
    ):
        raise ValueError("world scene revision gap")
    result = deepcopy(current)
    for eid in event.get("removals", ()):
        result["entities"].pop(eid, None)
    result["entities"].update(deepcopy(event.get("upserts", {})))
    for eid, transform in event.get("transforms", {}).items():
        if eid not in result["entities"]:
            raise ValueError("transform references absent entity")
        result["entities"][eid].update(deepcopy(transform))
    result.update(deepcopy(event.get("changes", {})))
    result["revision"] = event["revision"]
    result["kind"] = "snapshot"
    return result
