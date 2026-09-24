"""Body-independent Symbiont lifecycle and re-embodiment transforms."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from .longitudinal import (
    append_epoch_summary,
    archive_contract_memory,
    build_epoch_summary,
    contract_fingerprint,
    inject_memory_candidates,
    memory_for_contract,
)


_MAX_EMBODIMENT_HISTORY = 8
_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class EmbodimentContract:
    body_kind: str
    receptor_count: int
    effector_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "body_kind": self.body_kind,
            "receptor_count": self.receptor_count,
            "effector_count": self.effector_count,
        }


def _canonical_hash(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _genome_identity_hash(payload: object) -> str:
    # Must match Genome.genome_hash exactly (default json separators included).
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _body_vital_state(payload: Mapping[str, Any]) -> str:
    living = payload.get("living_body")
    if isinstance(living, Mapping):
        value = living.get("vital_state")
        if isinstance(value, str) and value:
            return value
    return "unknown"


def _legacy_contract(_payload: Mapping[str, Any]) -> EmbodimentContract:
    # Every pre-epoch portable Physics3D checkpoint used anthropomorphic-v4.
    return EmbodimentContract("anthropomorphic-v4", 107, 62)


def migrate_temporal_domains(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Repair the legacy global-tick -> Body-age contamination when unambiguous.

    This migration fixes clock coordinates only. It deliberately does not
    reverse senescence, wear, energy loss or any other historical physiology
    already produced under the contaminated clock.
    """
    result = deepcopy(dict(payload))
    lifecycle = result.get("embodiment_lifecycle")
    living = result.get("living_body")
    if not isinstance(lifecycle, Mapping) or not isinstance(living, dict):
        return result
    if lifecycle.get("schema_version") != _SCHEMA_VERSION:
        return result
    current = lifecycle.get("current")
    if not isinstance(current, Mapping):
        return result

    saved_tick = result.get("saved_at_tick")
    started_tick = current.get("started_tick")
    stored_age = living.get("age_ticks")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (saved_tick, started_tick, stored_age)):
        return result
    if started_tick <= 0 or saved_tick < started_tick:
        return result

    expected_age = saved_tick - started_tick
    if stored_age == expected_age:
        return result

    # Legacy Physics3D wrote Body age from the global runtime tick. Accept a
    # one-tick tolerance because checkpoints are taken after tick completion.
    if abs(stored_age - saved_tick) > 1:
        return result

    old_age = stored_age
    living["age_ticks"] = expected_age
    raw_death = living.get("death_tick")
    if isinstance(raw_death, int) and not isinstance(raw_death, bool):
        if abs(raw_death - old_age) <= 1 or abs(raw_death - saved_tick) <= 1:
            living["death_tick"] = expected_age

    physiology = result.get("physiology")
    if isinstance(physiology, dict):
        raw_phys_death = physiology.get("death_tick")
        if isinstance(raw_phys_death, int) and not isinstance(raw_phys_death, bool):
            if abs(raw_phys_death - old_age) <= 1 or abs(raw_phys_death - saved_tick) <= 1:
                physiology["death_tick"] = expected_age

    result["temporal_migration"] = {
        "schema_version": 1,
        "kind": "global_tick_to_body_age",
        "source_age_ticks": old_age,
        "body_age_ticks": expected_age,
        "started_at_symbiont_tick": started_tick,
        "saved_at_symbiont_tick": saved_tick,
    }
    return result

def lifecycle_summary(payload: Mapping[str, Any]) -> dict[str, object]:
    raw = payload.get("embodiment_lifecycle")
    if isinstance(raw, Mapping) and raw.get("schema_version") == _SCHEMA_VERSION:
        current = raw.get("current")
        return {
            "state": str(raw.get("state") or "dormant"),
            "epoch": int(raw.get("epoch") or 1),
            "current": dict(current) if isinstance(current, Mapping) else {},
            "history_count": len(raw.get("history", ()))
            if isinstance(raw.get("history"), list)
            else 0,
        }
    contract = _legacy_contract(payload)
    return {
        "state": "dormant",
        "epoch": 1,
        "current": {
            **contract.as_dict(),
            "started_tick": 0,
            "body_vital_state": _body_vital_state(payload),
        },
        "history_count": 0,
    }


def _same_contract(current: Mapping[str, Any], contract: EmbodimentContract) -> bool:
    return (
        str(current.get("body_kind") or "") == contract.body_kind
        and int(current.get("receptor_count") or -1) == contract.receptor_count
        and int(current.get("effector_count") or -1) == contract.effector_count
    )


def _detach_body_specific_cognition(
    checkpoint: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Archive and remove cognition whose authority depends on one embodiment.

    Fresh embodiment must not inherit active sensory identities, body-derived
    predictors or motor/primitive readouts. General concepts remain as durable
    cognition, but all incident edges to removed body-bound nodes disappear so
    they can only become useful again through fresh evidence.
    """
    raw_bridge = checkpoint.get("cognitive_bridge")
    if not isinstance(raw_bridge, Mapping):
        return (
            deepcopy(raw_bridge) if isinstance(raw_bridge, dict) else None,
            None,
        )

    bridge = deepcopy(dict(raw_bridge))
    graph = bridge.get("graph")
    if not isinstance(graph, dict):
        return bridge, None

    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return bridge, None

    def body_bound_node(node: Mapping[str, Any]) -> bool:
        node_id = str(node.get("node_id") or "")
        kind = str(node.get("kind") or "")
        return (
            kind in {"sense", "predictor"}
            or node_id.startswith("readout_motor:")
            or node_id.startswith("readout_primitive:")
        )

    removed_ids = {
        str(node.get("node_id"))
        for node in nodes
        if isinstance(node, Mapping) and body_bound_node(node)
    }
    if not removed_ids:
        return bridge, {"nodes": [], "edges": []}

    archived_nodes = [
        deepcopy(node)
        for node in nodes
        if isinstance(node, Mapping) and str(node.get("node_id")) in removed_ids
    ]
    archived_edges = [
        deepcopy(edge)
        for edge in edges
        if isinstance(edge, Mapping)
        and (
            str(edge.get("source_id")) in removed_ids
            or str(edge.get("target_id")) in removed_ids
        )
    ]

    graph["nodes"] = [
        node
        for node in nodes
        if not (
            isinstance(node, Mapping)
            and str(node.get("node_id")) in removed_ids
        )
    ]
    graph["edges"] = [
        edge
        for edge in edges
        if not (
            isinstance(edge, Mapping)
            and (
                str(edge.get("source_id")) in removed_ids
                or str(edge.get("target_id")) in removed_ids
            )
        )
    ]

    for key in (
        "node_born_tick",
        "node_observation_count",
        "node_active_count",
        "sense_last_seen_tick",
        "concept_last_active_tick",
        "orphan_since_tick",
        "unrouted_since_tick",
        "predictor_utility",
        "predictor_retirement",
    ):
        raw = bridge.get(key)
        if isinstance(raw, dict):
            bridge[key] = {
                node_id: value
                for node_id, value in raw.items()
                if str(node_id) not in removed_ids
            }

    raw_shadow = bridge.get("shadow_predictions")
    if isinstance(raw_shadow, list):
        bridge["shadow_predictions"] = [
            item
            for item in raw_shadow
            if not (
                isinstance(item, Mapping)
                and (
                    str(item.get("source_id")) in removed_ids
                    or str(item.get("target_id")) in removed_ids
                )
            )
        ]

    raw_preliminary = bridge.get("shadow_preliminary_support")
    if isinstance(raw_preliminary, list):
        bridge["shadow_preliminary_support"] = [
            item
            for item in raw_preliminary
            if not (
                isinstance(item, Mapping)
                and (
                    str(item.get("source_id")) in removed_ids
                    or str(item.get("target_id")) in removed_ids
                )
            )
        ]

    raw_candidates = bridge.get("structural_candidates")
    if isinstance(raw_candidates, list):
        bridge["structural_candidates"] = [
            item
            for item in raw_candidates
            if not (
                isinstance(item, Mapping)
                and str(item.get("family"))
                in {"motor_readout", "primitive_readout", "predictor"}
            )
        ]

    return bridge, {
        "nodes": archived_nodes,
        "edges": archived_edges,
    }


def _degrade_active_private_model(
    checkpoint: dict[str, Any],
) -> str | None:
    """Keep prior private models but remove old-body inference authority."""
    registry = checkpoint.get("private_model_registry")
    if not isinstance(registry, dict):
        return None
    records = registry.get("records")
    if not isinstance(records, list):
        return None

    active_id: str | None = None
    for record in records:
        if not isinstance(record, dict) or record.get("state") != "active":
            continue
        model_id = record.get("model_id")
        if isinstance(model_id, str):
            active_id = model_id
        record["state"] = "degraded"
    return active_id


def _active_private_model_id(checkpoint: Mapping[str, Any]) -> str | None:
    registry = checkpoint.get("private_model_registry")
    records = registry.get("records") if isinstance(registry, Mapping) else None
    if not isinstance(records, list):
        return None
    for record in records:
        if (
            isinstance(record, Mapping)
            and record.get("state") == "active"
            and isinstance(record.get("model_id"), str)
        ):
            return str(record["model_id"])
    return None


def prepare_fresh_embodiment_checkpoint(
    previous: Mapping[str, Any],
    fresh: Mapping[str, Any],
    *,
    contract: EmbodimentContract,
) -> dict[str, Any]:
    """Move one persistent Symbiont into a fresh Body.

    A fresh Body never inherits physiological age or current motor authority.
    Body-specific knowledge is archived and may return only as a bounded
    historical hypothesis under a matching opaque contract.
    """
    previous = migrate_temporal_domains(previous)
    result = deepcopy(dict(previous))
    prior_lifecycle = previous.get("embodiment_lifecycle")
    if isinstance(prior_lifecycle, Mapping) and prior_lifecycle.get("schema_version") == _SCHEMA_VERSION:
        epoch = max(1, int(prior_lifecycle.get("epoch") or 1))
        prior_current = prior_lifecycle.get("current")
        current = (
            dict(prior_current)
            if isinstance(prior_current, Mapping)
            else {**_legacy_contract(previous).as_dict(), "started_tick": 0}
        )
        history = (
            deepcopy(prior_lifecycle.get("history"))
            if isinstance(prior_lifecycle.get("history"), list)
            else []
        )
    else:
        epoch = 1
        current = {**_legacy_contract(previous).as_dict(), "started_tick": 0}
        history = []

    previous_contract = EmbodimentContract(
        body_kind=str(current.get("body_kind") or "unknown"),
        receptor_count=int(current.get("receptor_count") or 0),
        effector_count=int(current.get("effector_count") or 0),
    )
    same_descriptor = _same_contract(current, contract)
    saved_tick = int(previous.get("saved_at_tick") or 0)
    started_tick = int(current.get("started_tick") or 0)
    previous_fingerprint = str(
        current.get("contract_fingerprint")
        or contract_fingerprint(
            previous,
            receptor_count=previous_contract.receptor_count,
            effector_count=previous_contract.effector_count,
        )
    )
    new_fingerprint = contract_fingerprint(
        fresh,
        receptor_count=contract.receptor_count,
        effector_count=contract.effector_count,
    )
    same_contract = (
        same_descriptor
        and previous_fingerprint == new_fingerprint
    )

    historical_bridge, historical_motor_surface = _detach_body_specific_cognition(previous)
    active_model_id = _active_private_model_id(previous)
    metrics = current.get("metrics") if isinstance(current.get("metrics"), Mapping) else {}
    summary = build_epoch_summary(
        previous,
        epoch=epoch,
        started_tick=started_tick,
        contract_fingerprint_value=previous_fingerprint,
        body_kind=previous_contract.body_kind,
        metrics=metrics,
        reembodied_alive=_body_vital_state(previous) != "dead",
    )
    append_epoch_summary(result, summary)

    result["embodiment_memory"] = archive_contract_memory(
        previous,
        contract_fingerprint_value=previous_fingerprint,
        epoch=epoch,
        motor_cognitive_surface=historical_motor_surface,
        active_private_model_id=active_model_id,
    )
    known_memory = memory_for_contract(result.get("embodiment_memory"), new_fingerprint)

    history.append({
        "epoch": epoch,
        "body_kind": previous_contract.body_kind,
        "receptor_count": previous_contract.receptor_count,
        "effector_count": previous_contract.effector_count,
        "contract_fingerprint": previous_fingerprint,
        "started_tick": started_tick,
        "ended_tick": saved_tick,
        "end_body_vital_state": _body_vital_state(previous),
        "body_schema": deepcopy(previous.get("body_schema")),
        "motor_cognitive_surface": historical_motor_surface,
        "active_private_model_id": active_model_id,
        "epoch_summary": deepcopy(summary),
    })
    history = history[-_MAX_EMBODIMENT_HISTORY:]

    # A fresh Body owns fresh physiology regardless of Symbiont history.
    for key in ("living_body", "metabolism", "homeostasis", "physiology"):
        if key in fresh:
            result[key] = deepcopy(fresh[key])
    result["pending_embodied_work"] = 0.0
    result["resting_requested"] = False
    result["last_runtime_vital_state"] = "active"

    # Every fresh Body starts with fresh actuator health and learning surfaces.
    fresh_actuation = deepcopy(fresh.get("actuation"))
    if not isinstance(fresh_actuation, dict):
        fresh_actuation = {"enabled": False}
    result["actuation"] = inject_memory_candidates(fresh_actuation, known_memory)

    # General cognition persists, embodiment-specific motor authority does not.
    if historical_bridge is not None:
        result["cognitive_bridge"] = historical_bridge
    _degrade_active_private_model(result)

    # Body-specific self knowledge is reacquired for every fresh Body.
    for key in ("body_schema", "self_model", "sensory_development", "sensory_system"):
        if key in fresh:
            result[key] = deepcopy(fresh[key])

    # Only the motor constitution itself changes when the opaque contract changes.
    if not same_contract:
        old_genome = result.get("genome")
        new_genome = fresh.get("genome")
        if isinstance(old_genome, dict) and isinstance(new_genome, Mapping):
            if "motor" in new_genome:
                old_genome["motor"] = deepcopy(new_genome["motor"])
            else:
                old_genome.pop("motor", None)
            genome_fields = {
                key: value
                for key, value in old_genome.items()
                if key != "genome_hash"
            }
            old_genome["genome_hash"] = _genome_identity_hash(genome_fields)
            fingerprint = result.get("constitution_fingerprint")
            if not isinstance(fingerprint, dict):
                fingerprint = {"schema_version": 1}
                result["constitution_fingerprint"] = fingerprint
            fingerprint["genome_hash"] = _canonical_hash(old_genome)

    relation = (
        "same-known"
        if same_contract and known_memory is not None
        else "known-return"
        if known_memory is not None
        else "changed"
    )
    result["embodiment_lifecycle"] = {
        "schema_version": _SCHEMA_VERSION,
        "state": "active",
        "epoch": epoch + 1,
        "current": {
            **contract.as_dict(),
            "contract_fingerprint": new_fingerprint,
            "started_tick": saved_tick,
            "body_vital_state": "active",
            "contract_relation": relation,
            "known_contract_memory": known_memory is not None,
            "candidate_private_model_ids": (
                list(known_memory.get("private_model_ids", ()))
                if isinstance(known_memory, Mapping)
                else []
            ),
            "metrics": {
                "absorbed_material_total": 0.0,
                "mechanical_work_total": 0.0,
                "physiological_cost_total": 0.0,
                "reacclimation_ticks_consumed": 0,
                "reacclimation_completed": False,
                "vital_state_ticks": {},
            },
        },
        "history": history,
    }
    return result

def update_lifecycle_for_checkpoint(
    payload: dict[str, Any],
    *,
    contract: EmbodimentContract,
    state: str,
    metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach execution lifecycle metadata without changing organism cognition."""
    if state not in {"active", "dormant", "suspended"}:
        raise ValueError("invalid Symbiont lifecycle state")

    raw = payload.get("embodiment_lifecycle")
    if isinstance(raw, Mapping) and raw.get("schema_version") == _SCHEMA_VERSION:
        epoch = max(1, int(raw.get("epoch") or 1))
        history = deepcopy(raw.get("history")) if isinstance(raw.get("history"), list) else []
        current_raw = raw.get("current")
        current = dict(current_raw) if isinstance(current_raw, Mapping) else {}
    else:
        epoch = 1
        history = []
        current = {"started_tick": 0}

    current.update(contract.as_dict())
    current["body_vital_state"] = _body_vital_state(payload)
    current.setdefault("started_tick", 0)
    current.setdefault(
        "contract_fingerprint",
        contract_fingerprint(
            payload,
            receptor_count=contract.receptor_count,
            effector_count=contract.effector_count,
        ),
    )
    if metrics is not None:
        current["metrics"] = deepcopy(dict(metrics))

    payload["embodiment_lifecycle"] = {
        "schema_version": _SCHEMA_VERSION,
        "state": state,
        "epoch": epoch,
        "current": current,
        "history": history[-_MAX_EMBODIMENT_HISTORY:],
    }

    if current["body_vital_state"] == "dead":
        summary = build_epoch_summary(
            payload,
            epoch=epoch,
            started_tick=int(current.get("started_tick") or 0),
            contract_fingerprint_value=str(current["contract_fingerprint"]),
            body_kind=str(contract.body_kind),
            metrics=current.get("metrics") if isinstance(current.get("metrics"), Mapping) else {},
            reembodied_alive=False,
        )
        append_epoch_summary(payload, summary)
        current["closed"] = True
        current["epoch_summary"] = deepcopy(summary)
        _bridge, motor_surface = _detach_body_specific_cognition(payload)
        payload["embodiment_memory"] = archive_contract_memory(
            payload,
            contract_fingerprint_value=str(current["contract_fingerprint"]),
            epoch=epoch,
            motor_cognitive_surface=motor_surface,
            active_private_model_id=_active_private_model_id(payload),
        )

    return payload


__all__ = [
    "EmbodimentContract",
    "lifecycle_summary",
    "migrate_temporal_domains",
    "prepare_fresh_embodiment_checkpoint",
    "update_lifecycle_for_checkpoint",
]
