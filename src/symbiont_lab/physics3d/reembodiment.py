"""Body-independent Symbiont lifecycle and re-embodiment transforms."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from symbiont.actuation.surface import ActuatorSurface
from symbiont.core.embodiment import (
    BodySpecificMemory,
    EmbodimentArchive,
    archive_episode_checkpoint,
)

from .longitudinal import (
    CONTRACT_FINGERPRINT_SCHEMA_VERSION,
    append_epoch_summary,
    archive_contract_memory,
    build_epoch_summary,
    contract_fingerprint,
    historical_motor_candidates,
    inject_memory_candidates,
    memory_for_contract,
)


_MAX_EMBODIMENT_HISTORY = 8
_SCHEMA_VERSION = 1
_CANONICAL_CONTRACT_FINGERPRINT_SCHEMA_VERSION = 3


@dataclass(frozen=True, slots=True)
class PhysicsEmbodimentDescriptor:
    body_kind: str
    receptor_count: int
    effector_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "body_kind": self.body_kind,
            "receptor_count": self.receptor_count,
            "effector_count": self.effector_count,
        }


def _body_vital_state(payload: Mapping[str, Any]) -> str:
    living = payload.get("living_body")
    if isinstance(living, Mapping):
        value = living.get("vital_state")
        if isinstance(value, str) and value:
            return value
    return "unknown"


def _legacy_contract(_payload: Mapping[str, Any]) -> PhysicsEmbodimentDescriptor:
    # Every pre-epoch portable Physics3D checkpoint used anthropomorphic-v4.
    return PhysicsEmbodimentDescriptor("anthropomorphic-v4", 107, 62)


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
    episode = payload.get("embodiment_episode")
    if (
        isinstance(episode, Mapping)
        and int(episode.get("schema_version") or 0) in {2, 3}
    ):
        contract = episode.get("contract")
        contract = contract if isinstance(contract, Mapping) else {}
        return {
            "state": str(episode.get("state") or "suspended"),
            "epoch": max(1, int(episode.get("epoch") or 1)),
            "current": {
                "embodiment_id": str(episode.get("embodiment_id") or ""),
                "body_id": str(episode.get("body_id") or ""),
                "started_tick": int(episode.get("start_symbiont_tick") or 0),
                "embodiment_tick": int(episode.get("embodiment_tick") or 0),
                "contract_fingerprint": str(
                    contract.get("contract_fingerprint") or ""
                ),
                "body_vital_state": _body_vital_state(payload),
            },
            "history_count": len(payload.get("embodiment_epoch_summaries", ()))
            if isinstance(payload.get("embodiment_epoch_summaries"), list)
            else 0,
        }
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

    raw_normalizers = bridge.get("sensory_normalizers")
    if isinstance(raw_normalizers, dict):
        bridge["sensory_normalizers"] = {
            sensor_id: value
            for sensor_id, value in raw_normalizers.items()
            if str(sensor_id) not in removed_ids
        }

    raw_lineage = bridge.get("concept_lineage")
    if isinstance(raw_lineage, list):
        bridge["concept_lineage"] = [
            entry
            for entry in raw_lineage
            if not (
                isinstance(entry, Mapping)
                and isinstance(entry.get("parent_ids"), list)
                and any(str(parent_id) in removed_ids for parent_id in entry["parent_ids"])
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

    def _references_removed(value: object) -> bool:
        if isinstance(value, str):
            return value in removed_ids
        if isinstance(value, Mapping):
            return any(_references_removed(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return any(_references_removed(item) for item in value)
        return False

    raw_candidates = bridge.get("structural_candidates")
    if isinstance(raw_candidates, list):
        bridge["structural_candidates"] = [
            item
            for item in raw_candidates
            if not (
                isinstance(item, Mapping)
                and (
                    str(item.get("family"))
                    in {"motor_readout", "primitive_readout", "predictor"}
                    or _references_removed(item)
                )
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


def _carry_sensorimotor_v2_knowledge(
    previous: Mapping[str, Any],
    fresh_actuation: dict[str, Any],
) -> dict[str, Any]:
    """Carry transferable competence knowledge, never old-body factual authority."""
    previous_actuation = previous.get("actuation")
    if not isinstance(previous_actuation, Mapping):
        return fresh_actuation
    prior_v2 = previous_actuation.get("sensorimotor_v2")
    if not isinstance(prior_v2, Mapping):
        return fresh_actuation

    result = deepcopy(fresh_actuation)
    fresh_v2_raw = result.get("sensorimotor_v2")
    if not isinstance(fresh_v2_raw, Mapping):
        return result
    fresh_v2 = deepcopy(dict(fresh_v2_raw))

    # The fresh template owns the current surface, empty EffectSpace, empty
    # causal ledger, empty execution bindings, exploration state and
    # composition evidence. None of those can cross a Body boundary.
    prior_competences = prior_v2.get("competences", [])
    transferable: list[dict[str, Any]] = []
    if isinstance(prior_competences, list):
        for item in prior_competences:
            if not isinstance(item, Mapping):
                continue
            candidate = deepcopy(dict(item))
            candidate.pop("surface_binding", None)
            # Effect IDs are grounded in the old body's opaque perceptual
            # changes. Preserve strategy/evidence maturity, not old grounding.
            candidate["effect_id"] = None
            transferable.append(candidate)

    fresh_v2["schema_version"] = 2
    fresh_v2["competences"] = transferable
    # Explicitly insist on fresh-body authority even if a malformed template
    # somehow carried these fields.
    fresh_v2["execution_bindings"] = {
        "schema_version": 1,
        "capacity": 512,
        "items": [],
    }
    result["sensorimotor_v2"] = fresh_v2
    result["action_commitment"] = None
    result["last_executed_primitive_id"] = None
    result["pending_motor_observation"] = []
    result["pending_proprioception"] = {}
    return result

def migrate_legacy_memory_store(
    archive: EmbodimentArchive,
    store: Mapping[str, Any] | None,
) -> EmbodimentArchive:
    """One-way import of pre-v2 contract memory into the canonical archive."""
    if not isinstance(store, Mapping) or int(store.get("schema_version") or 0) != 1:
        return archive
    contracts = store.get("contracts")
    if not isinstance(contracts, list):
        return archive
    for index, entry in enumerate(contracts[-8:]):
        if not isinstance(entry, Mapping):
            continue
        fingerprint = str(entry.get("contract_fingerprint") or "")
        if not fingerprint:
            continue
        archive.remember_body(
            BodySpecificMemory(
                body_id=f"legacy-body.{fingerprint[:20]}.{index}",
                contract_fingerprint=fingerprint,
                last_embodiment_id=(
                    f"legacy-embodiment.{int(entry.get('last_seen_epoch') or 0)}"
                ),
                body_schema_prior=(
                    deepcopy(dict(entry["body_schema"]))
                    if isinstance(entry.get("body_schema"), Mapping)
                    else None
                ),
                historical_motor_candidates=tuple(
                    deepcopy(dict(item))
                    for item in entry.get("historical_primitives", [])
                    if isinstance(item, Mapping)
                ),
                motor_cognitive_surface=(
                    deepcopy(dict(entry["motor_cognitive_surface"]))
                    if isinstance(entry.get("motor_cognitive_surface"), Mapping)
                    else None
                ),
                private_model_ids=tuple(
                    str(value)
                    for value in entry.get("private_model_ids", [])
                ),
            )
        )
    return archive


def _legacy_equivalent_contract_fingerprint(
    fresh: Mapping[str, Any],
    descriptor: PhysicsEmbodimentDescriptor,
) -> str:
    """Reconstruct the pre-v3 contract identity for one equivalent interface."""
    legacy_surface = ActuatorSurface.from_count(
        descriptor.effector_count,
        fingerprint_material=(
            f"{descriptor.body_kind}:"
            f"{descriptor.receptor_count}:"
            f"{descriptor.effector_count}"
        ),
    )
    translated = deepcopy(dict(fresh))
    actuation = translated.get("actuation")
    if isinstance(actuation, dict):
        constitution = actuation.get("constitution")
        if isinstance(constitution, dict):
            constitution["contract_fingerprint"] = (
                legacy_surface.contract_fingerprint
            )
    return contract_fingerprint(
        translated,
        receptor_count=descriptor.receptor_count,
        effector_count=descriptor.effector_count,
    )


def prepare_fresh_embodiment_checkpoint(
    previous: Mapping[str, Any],
    fresh: Mapping[str, Any],
    *,
    contract: PhysicsEmbodimentDescriptor,
    canonical_contract_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Move one persistent Symbiont into a fresh Body.

    A fresh Body never inherits physiological age or current motor authority.
    Body-specific knowledge is archived and may return only as a bounded
    historical hypothesis under a matching opaque contract.
    """
    previous = migrate_temporal_domains(previous)
    result = deepcopy(dict(previous))
    # Archive the canonical episode before removing its current authority.
    raw_episode = previous.get("embodiment_episode")
    if (
        isinstance(raw_episode, Mapping)
        and int(raw_episode.get("schema_version") or 0) in {2, 3}
    ):
        raw_archive = previous.get("embodiment_archive")
        archive = EmbodimentArchive.restore(
            raw_archive if isinstance(raw_archive, Mapping) else None
        )
        archive_episode_checkpoint(
            archive,
            raw_episode,
            body_schema_prior=(
                previous.get("body_schema")
                if isinstance(previous.get("body_schema"), Mapping)
                else None
            ),
            living_body=(
                previous.get("living_body")
                if isinstance(previous.get("living_body"), Mapping)
                else None
            ),
            symbiont_tick=int(previous.get("saved_at_tick") or 0),
            end_reason=(
                "body_death"
                if _body_vital_state(previous) == "dead"
                else "body_replaced"
            ),
        )
        result["embodiment_archive"] = archive.checkpoint()
    # A new physical Body always starts a new canonical episode. Never carry
    # the previous body/episode identity through the compatibility transform.
    result.pop("embodiment_episode", None)
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

    previous_contract = PhysicsEmbodimentDescriptor(
        body_kind=str(current.get("body_kind") or "unknown"),
        receptor_count=int(current.get("receptor_count") or 0),
        effector_count=int(current.get("effector_count") or 0),
    )
    saved_tick = int(previous.get("saved_at_tick") or 0)
    started_tick = int(current.get("started_tick") or 0)
    current_fingerprint_version = int(
        current.get("contract_fingerprint_schema_version") or 0
    )
    episode_contract = (
        raw_episode.get("contract")
        if isinstance(raw_episode, Mapping)
        else None
    )
    episode_fingerprint = (
        str(episode_contract.get("contract_fingerprint"))
        if isinstance(episode_contract, Mapping)
        and isinstance(episode_contract.get("contract_fingerprint"), str)
        and episode_contract.get("contract_fingerprint")
        else None
    )
    if episode_fingerprint is not None:
        previous_fingerprint = episode_fingerprint
    elif (
        current_fingerprint_version == CONTRACT_FINGERPRINT_SCHEMA_VERSION
        and isinstance(current.get("contract_fingerprint"), str)
        and current.get("contract_fingerprint")
    ):
        previous_fingerprint = str(current["contract_fingerprint"])
    else:
        previous_fingerprint = contract_fingerprint(
            previous,
            receptor_count=previous_contract.receptor_count,
            effector_count=previous_contract.effector_count,
        )

    if canonical_contract_fingerprint is not None:
        if not canonical_contract_fingerprint:
            raise ValueError("canonical contract fingerprint must not be empty")
        new_fingerprint = str(canonical_contract_fingerprint)
        new_fingerprint_schema = _CANONICAL_CONTRACT_FINGERPRINT_SCHEMA_VERSION
    else:
        new_fingerprint = contract_fingerprint(
            fresh,
            receptor_count=contract.receptor_count,
            effector_count=contract.effector_count,
        )
        new_fingerprint_schema = CONTRACT_FINGERPRINT_SCHEMA_VERSION
    legacy_new_fingerprint = _legacy_equivalent_contract_fingerprint(
        fresh,
        contract,
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

    # EmbodimentArchive is the sole v2 longitudinal memory authority.
    raw_archive = result.get("embodiment_archive")
    archive = EmbodimentArchive.restore(
        raw_archive if isinstance(raw_archive, Mapping) else None
    )
    current_candidates = tuple(
        historical_motor_candidates(
            previous,
            contract_fingerprint_value=previous_fingerprint,
        )
    )
    if (
        isinstance(raw_episode, Mapping)
        and int(raw_episode.get("schema_version") or 0) in {2, 3}
    ):
        body_id = str(raw_episode.get("body_id") or "")
        existing = archive.for_body(body_id) if body_id else None
        if existing is not None:
            archive.remember_body(
                BodySpecificMemory(
                    body_id=existing.body_id,
                    contract_fingerprint=existing.contract_fingerprint,
                    last_embodiment_id=existing.last_embodiment_id,
                    body_schema_prior=existing.body_schema_prior,
                    dynamics_prior=existing.dynamics_prior,
                    execution_binding_priors=existing.execution_binding_priors,
                    historical_causal_state=existing.historical_causal_state,
                    historical_motor_candidates=current_candidates,
                    motor_cognitive_surface=(
                        deepcopy(dict(historical_motor_surface))
                        if isinstance(historical_motor_surface, Mapping)
                        else None
                    ),
                    private_model_ids=(
                        (active_model_id,)
                        if isinstance(active_model_id, str)
                        else ()
                    ),
                )
            )
    else:
        # One-way migration for pre-v2 checkpoints. Their historical store had
        # no physical Body identity, so migrated entries are contract-level
        # priors only and can never be mistaken for same-Body memory.
        migrated_previous_contract = (
            new_fingerprint
            if (
                canonical_contract_fingerprint is not None
                and previous_fingerprint == legacy_new_fingerprint
            )
            else previous_fingerprint
        )
        archive.remember_body(
            BodySpecificMemory(
                body_id=f"legacy-body.{previous_fingerprint[:24]}",
                contract_fingerprint=migrated_previous_contract,
                last_embodiment_id=f"legacy-embodiment.{epoch}",
                body_schema_prior=(
                    deepcopy(dict(previous["body_schema"]))
                    if isinstance(previous.get("body_schema"), Mapping)
                    else None
                ),
                historical_motor_candidates=current_candidates,
                motor_cognitive_surface=(
                    deepcopy(dict(historical_motor_surface))
                    if isinstance(historical_motor_surface, Mapping)
                    else None
                ),
                private_model_ids=(
                    (active_model_id,)
                    if isinstance(active_model_id, str)
                    else ()
                ),
            )
        )
        legacy_known = memory_for_contract(
            previous.get("embodiment_memory")
            if isinstance(previous.get("embodiment_memory"), Mapping)
            else None,
            legacy_new_fingerprint,
        )
        if isinstance(legacy_known, Mapping):
            archive.remember_body(
                BodySpecificMemory(
                    body_id=f"legacy-body.{new_fingerprint[:24]}.historical",
                    contract_fingerprint=new_fingerprint,
                    last_embodiment_id="legacy-embodiment.historical",
                    body_schema_prior=(
                        deepcopy(dict(legacy_known["body_schema"]))
                        if isinstance(legacy_known.get("body_schema"), Mapping)
                        else None
                    ),
                    historical_motor_candidates=tuple(
                        deepcopy(dict(item))
                        for item in legacy_known.get("historical_primitives", [])
                        if isinstance(item, Mapping)
                    ),
                    motor_cognitive_surface=(
                        deepcopy(dict(legacy_known["motor_cognitive_surface"]))
                        if isinstance(legacy_known.get("motor_cognitive_surface"), Mapping)
                        else None
                    ),
                    private_model_ids=tuple(
                        str(value)
                        for value in legacy_known.get("private_model_ids", [])
                    ),
                )
            )

    result["embodiment_archive"] = archive.checkpoint()
    # Remove the superseded writable store after its one-way migration.
    result.pop("embodiment_memory", None)
    matching_memories = archive.for_contract(new_fingerprint)
    known_prior = matching_memories[0] if matching_memories else None
    known_memory = (
        {
            "historical_primitives": [
                deepcopy(item)
                for item in known_prior.historical_motor_candidates
            ],
            "private_model_ids": list(known_prior.private_model_ids),
        }
        if known_prior is not None
        else None
    )

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
    fresh_actuation = inject_memory_candidates(fresh_actuation, known_memory)
    result["actuation"] = _carry_sensorimotor_v2_knowledge(
        previous,
        fresh_actuation,
    )

    # General cognition persists, embodiment-specific motor authority does not.
    if historical_bridge is not None:
        result["cognitive_bridge"] = historical_bridge
    _degrade_active_private_model(result)

    # Body-specific self knowledge is reacquired for every fresh Body.
    for key in ("body_schema", "self_model", "sensory_development", "sensory_system"):
        if key in fresh:
            result[key] = deepcopy(fresh[key])

    # Genome v2 is body-independent. Re-embodiment changes physiology,
    # sensory/actuator surfaces and acquired embodiment state only; genotype
    # and genome hashes remain byte-for-byte unchanged.

    # prepare_fresh_embodiment_checkpoint always creates a new physical Body.
    # A matching interface is therefore a known-contract prior, never same-Body.
    relation = "known-contract" if known_prior is not None else "changed"
    result["embodiment_lifecycle"] = {
        "schema_version": _SCHEMA_VERSION,
        "state": "active",
        "epoch": epoch + 1,
        "current": {
            **contract.as_dict(),
            "contract_fingerprint": new_fingerprint,
            "contract_fingerprint_schema_version": new_fingerprint_schema,
            "started_tick": saved_tick,
            "body_vital_state": "active",
            "contract_relation": relation,
            "known_contract_memory": known_memory is not None,
            "candidate_private_model_ids": (
                list(known_prior.private_model_ids)
                if known_prior is not None
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
    contract: PhysicsEmbodimentDescriptor,
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
    episode = payload.get("embodiment_episode")
    episode_contract = (
        episode.get("contract")
        if isinstance(episode, Mapping)
        and int(episode.get("schema_version") or 0) in {2, 3}
        else None
    )
    canonical_fingerprint = (
        str(episode_contract.get("contract_fingerprint"))
        if isinstance(episode_contract, Mapping)
        and isinstance(episode_contract.get("contract_fingerprint"), str)
        and episode_contract.get("contract_fingerprint")
        else None
    )
    if canonical_fingerprint is not None:
        current["contract_fingerprint"] = canonical_fingerprint
        current["contract_fingerprint_schema_version"] = (
            _CANONICAL_CONTRACT_FINGERPRINT_SCHEMA_VERSION
        )
    else:
        if (
            int(current.get("contract_fingerprint_schema_version") or 0)
            != CONTRACT_FINGERPRINT_SCHEMA_VERSION
            or not isinstance(current.get("contract_fingerprint"), str)
            or not current.get("contract_fingerprint")
        ):
            current["contract_fingerprint"] = contract_fingerprint(
                payload,
                receptor_count=contract.receptor_count,
                effector_count=contract.effector_count,
            )
        current["contract_fingerprint_schema_version"] = (
            CONTRACT_FINGERPRINT_SCHEMA_VERSION
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
        if not (
            isinstance(payload.get("embodiment_episode"), Mapping)
            and int(payload["embodiment_episode"].get("schema_version") or 0)
            in {2, 3}
        ):
            # Pre-v2 compatibility only. Canonical Physics3D checkpoints have
            # already archived the closed episode in EmbodimentArchive.
            _bridge, motor_surface = _detach_body_specific_cognition(payload)
            payload["embodiment_memory"] = archive_contract_memory(
                payload,
                contract_fingerprint_value=str(current["contract_fingerprint"]),
                epoch=epoch,
                motor_cognitive_surface=motor_surface,
                active_private_model_id=_active_private_model_id(payload),
            )
        else:
            payload.pop("embodiment_memory", None)

    return payload


__all__ = [
    "PhysicsEmbodimentDescriptor",
    "lifecycle_summary",
    "migrate_legacy_memory_store",
    "migrate_temporal_domains",
    "prepare_fresh_embodiment_checkpoint",
    "update_lifecycle_for_checkpoint",
]
