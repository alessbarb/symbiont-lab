"""Bounded longitudinal memory and epoch summaries for Physics3D re-embodiment."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

_MEMORY_SCHEMA_VERSION = 1
_SUMMARY_SCHEMA_VERSION = 1
_MAX_CONTRACT_MEMORIES = 8
_MAX_EPOCH_SUMMARIES = 16
_MAX_HISTORICAL_PRIMITIVES = 32
CONTRACT_FINGERPRINT_SCHEMA_VERSION = 2


def _canonical_hash(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def contract_fingerprint(
    payload: Mapping[str, Any],
    *,
    receptor_count: int,
    effector_count: int,
) -> str:
    """Hash the opaque sensorimotor constitution without anatomy labels."""
    actuation = payload.get("actuation")
    constitution = (
        actuation.get("constitution")
        if isinstance(actuation, Mapping)
        else None
    )
    sensorimotor = (
        actuation.get("sensorimotor")
        if isinstance(actuation, Mapping)
        else None
    )
    raw_groups = (
        sensorimotor.get("exclusive_actuator_groups")
        if isinstance(sensorimotor, Mapping)
        else None
    )
    motor_unit_groups: list[list[str]] | None = None
    if raw_groups is not None:
        if not isinstance(raw_groups, list):
            raise ValueError(
                "exclusive actuator groups must be a list in embodiment contract"
            )
        normalized: list[tuple[str, ...]] = []
        for raw_group in raw_groups:
            if not isinstance(raw_group, (list, tuple)):
                raise ValueError(
                    "exclusive actuator group must be a sequence in embodiment contract"
                )
            group = tuple(sorted(str(value) for value in raw_group))
            if len(group) < 2 or len(set(group)) != len(group):
                raise ValueError(
                    "exclusive actuator group is invalid in embodiment contract"
                )
            normalized.append(group)
        motor_unit_groups = [
            list(group) for group in sorted(normalized)
        ]

    material = {
        "schema_version": CONTRACT_FINGERPRINT_SCHEMA_VERSION,
        "receptor_count": int(receptor_count),
        "effector_count": int(effector_count),
        # Constitution is deterministic from MotorGenes. Learned proposer,
        # actuator health and sensory phenotype state are intentionally absent:
        # a contract fingerprint must survive learning inside the same Body type.
        "actuation_constitution": constitution,
        # Physical grouping is part of embodiment truth even though the
        # organism sees only opaque actuator ids. Two bodies with the same
        # channel count but different antagonistic groupings are not the same
        # motor contract.
        "exclusive_actuator_groups": motor_unit_groups,
    }
    return _canonical_hash(material)


def _historical_primitives(
    payload: Mapping[str, Any],
    *,
    contract_fingerprint_value: str,
) -> list[dict[str, object]]:
    actuation = payload.get("actuation")
    if not isinstance(actuation, Mapping):
        return []
    sensorimotor = actuation.get("sensorimotor")
    if not isinstance(sensorimotor, Mapping):
        return []
    raw = sensorimotor.get("primitives")
    if not isinstance(raw, list):
        return []
    result: list[dict[str, object]] = []
    for item in raw[:_MAX_HISTORICAL_PRIMITIVES]:
        if not isinstance(item, Mapping):
            continue
        primitive_id = item.get("primitive_id")
        sequence = item.get("sequence")
        if isinstance(primitive_id, str) and primitive_id and isinstance(sequence, list):
            result.append({
                "primitive_id": primitive_id,
                "embodiment_fingerprint": str(contract_fingerprint_value),
                "sequence": deepcopy(sequence),
            })
    return result


def archive_contract_memory(
    checkpoint: Mapping[str, Any],
    *,
    contract_fingerprint_value: str,
    epoch: int,
    motor_cognitive_surface: Mapping[str, Any] | None,
    active_private_model_id: str | None,
) -> dict[str, Any]:
    """Archive bounded body-specific knowledge without granting current authority."""
    raw_store = checkpoint.get("embodiment_memory")
    store = (
        deepcopy(dict(raw_store))
        if isinstance(raw_store, Mapping)
        and raw_store.get("schema_version") == _MEMORY_SCHEMA_VERSION
        else {"schema_version": _MEMORY_SCHEMA_VERSION, "contracts": []}
    )
    contracts = store.get("contracts")
    if not isinstance(contracts, list):
        contracts = []

    entry = {
        "contract_fingerprint": str(contract_fingerprint_value),
        "last_seen_epoch": int(epoch),
        "body_schema": deepcopy(checkpoint.get("body_schema")),
        "historical_primitives": _historical_primitives(
            checkpoint,
            contract_fingerprint_value=contract_fingerprint_value,
        ),
        "motor_cognitive_surface": deepcopy(motor_cognitive_surface),
        "private_model_ids": (
            [active_private_model_id]
            if isinstance(active_private_model_id, str)
            else []
        ),
        "state": "historical",
    }
    existing = None
    for index, candidate in enumerate(contracts):
        if (
            isinstance(candidate, Mapping)
            and candidate.get("contract_fingerprint") == contract_fingerprint_value
        ):
            existing = index
            break
    if existing is not None:
        previous = contracts.pop(existing)
        if isinstance(previous, Mapping):
            entry["first_seen_epoch"] = int(previous.get("first_seen_epoch") or epoch)
        else:
            entry["first_seen_epoch"] = int(epoch)
    else:
        entry["first_seen_epoch"] = int(epoch)
    contracts.append(entry)
    contracts = contracts[-_MAX_CONTRACT_MEMORIES:]
    store["contracts"] = contracts
    return store


def memory_for_contract(
    store: Mapping[str, Any] | None,
    contract_fingerprint_value: str,
) -> dict[str, Any] | None:
    if not isinstance(store, Mapping) or store.get("schema_version") != _MEMORY_SCHEMA_VERSION:
        return None
    contracts = store.get("contracts")
    if not isinstance(contracts, list):
        return None
    for entry in reversed(contracts):
        if (
            isinstance(entry, Mapping)
            and entry.get("contract_fingerprint") == contract_fingerprint_value
        ):
            return deepcopy(dict(entry))
    return None


def inject_memory_candidates(
    fresh_actuation: dict[str, Any],
    memory: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Seed only non-authoritative historical hypotheses into a fresh learner."""
    if not isinstance(memory, Mapping):
        return fresh_actuation
    raw = memory.get("historical_primitives")
    if not isinstance(raw, list):
        return fresh_actuation
    sensorimotor = fresh_actuation.get("sensorimotor")
    if not isinstance(sensorimotor, dict):
        return fresh_actuation
    if int(sensorimotor.get("schema_version") or -1) != 10:
        raise ValueError(
            "fresh embodiment must provide canonical sensorimotor schema v10"
        )
    expected_scope = sensorimotor.get("embodiment_fingerprint")
    if (
        not isinstance(expected_scope, str)
        or expected_scope != memory.get("contract_fingerprint")
    ):
        raise ValueError(
            "historical motor memory does not match fresh embodiment contract"
        )
    sensorimotor["historical_candidates"] = [
        deepcopy(item)
        for item in raw[:_MAX_HISTORICAL_PRIMITIVES]
        if isinstance(item, Mapping)
    ]
    return fresh_actuation


def _count_graph_kind(payload: Mapping[str, Any], kind: str) -> int:
    bridge = payload.get("cognitive_bridge")
    graph = bridge.get("graph") if isinstance(bridge, Mapping) else None
    nodes = graph.get("nodes") if isinstance(graph, Mapping) else None
    if not isinstance(nodes, list):
        return 0
    return sum(
        1
        for item in nodes
        if isinstance(item, Mapping) and item.get("kind") == kind
    )


def _count_motor_readouts(payload: Mapping[str, Any]) -> int:
    bridge = payload.get("cognitive_bridge")
    graph = bridge.get("graph") if isinstance(bridge, Mapping) else None
    nodes = graph.get("nodes") if isinstance(graph, Mapping) else None
    if not isinstance(nodes, list):
        return 0
    return sum(
        1
        for item in nodes
        if isinstance(item, Mapping)
        and str(item.get("node_id") or "").startswith(("readout_motor:", "readout_primitive:"))
    )


def infer_end_reason(payload: Mapping[str, Any], *, reembodied_alive: bool = False) -> str:
    living = payload.get("living_body")
    if reembodied_alive:
        return "reembodied_alive"
    if not isinstance(living, Mapping):
        return "unknown"
    vital = str(living.get("vital_state") or "")
    if vital != "dead":
        return "stopped_alive"
    energy = living.get("energy_reserve")
    integrity = living.get("structural_integrity")
    if isinstance(energy, (int, float)) and float(energy) <= 0.0:
        return "dead_energy"
    if isinstance(integrity, (int, float)) and float(integrity) <= 0.0:
        return "dead_structure"
    return "dead_unrecoverable_pressure"


def build_epoch_summary(
    payload: Mapping[str, Any],
    *,
    epoch: int,
    started_tick: int,
    contract_fingerprint_value: str,
    body_kind: str,
    metrics: Mapping[str, Any] | None = None,
    reembodied_alive: bool = False,
) -> dict[str, Any]:
    saved_tick = int(payload.get("saved_at_tick") or started_tick)
    living = payload.get("living_body")
    living = living if isinstance(living, Mapping) else {}
    body_schema = payload.get("body_schema")
    body_schema = body_schema if isinstance(body_schema, Mapping) else {}
    parts = body_schema.get("parts")
    actuation = payload.get("actuation")
    actuation = actuation if isinstance(actuation, Mapping) else {}
    sensorimotor = actuation.get("sensorimotor")
    sensorimotor = sensorimotor if isinstance(sensorimotor, Mapping) else {}
    primitives = sensorimotor.get("primitives")
    proposer = actuation.get("proposer")
    candidates = proposer.get("candidates") if isinstance(proposer, Mapping) else None
    private_registry = payload.get("private_model_registry")
    private_records = (
        private_registry.get("records")
        if isinstance(private_registry, Mapping)
        else []
    )
    if not isinstance(private_records, list):
        private_records = []
    model_states: dict[str, int] = {}
    active_model_id = None
    for record in private_records:
        if not isinstance(record, Mapping):
            continue
        state = str(record.get("state") or "unknown")
        model_states[state] = model_states.get(state, 0) + 1
        if state == "active" and isinstance(record.get("model_id"), str):
            active_model_id = record.get("model_id")

    body_age = int(living.get("age_ticks") or max(0, saved_tick - started_tick))
    max_energy = float(living.get("max_energy") or 0.0)
    energy = float(living.get("energy_reserve") or 0.0)
    metric_payload = dict(metrics) if isinstance(metrics, Mapping) else {}
    return {
        "schema_version": _SUMMARY_SCHEMA_VERSION,
        "epoch": int(epoch),
        "contract_fingerprint": str(contract_fingerprint_value),
        "body_kind": str(body_kind),
        "started_at_symbiont_tick": int(started_tick),
        "ended_at_symbiont_tick": int(saved_tick),
        "duration_body_ticks": int(body_age),
        "end_reason": infer_end_reason(payload, reembodied_alive=reembodied_alive),
        "body_vital_state": str(living.get("vital_state") or "unknown"),
        "body_death_age_ticks": living.get("death_tick"),
        "final_energy_ratio": (energy / max_energy if max_energy > 0.0 else 0.0),
        "final_structural_integrity": float(living.get("structural_integrity") or 0.0),
        "final_senescence": float(living.get("senescence") or 0.0),
        "final_fatigue": float(living.get("fatigue") or 0.0),
        "absorbed_material_total": float(metric_payload.get("absorbed_material_total") or 0.0),
        "mechanical_work_total": float(metric_payload.get("mechanical_work_total") or 0.0),
        "physiological_cost_total": float(metric_payload.get("physiological_cost_total") or 0.0),
        "body_schema_state": str(body_schema.get("state") or "unknown"),
        "body_schema_part_count": len(parts) if isinstance(parts, list) else 0,
        "motor_primitive_count": len(primitives) if isinstance(primitives, list) else 0,
        "motor_candidate_count": len(candidates) if isinstance(candidates, Mapping) else 0,
        "motor_supported_count": sum(
            1
            for item in (candidates.values() if isinstance(candidates, Mapping) else ())
            if isinstance(item, Mapping) and item.get("probing_state") == "active"
        ),
        "motor_readout_count": _count_motor_readouts(payload),
        "predictor_count": _count_graph_kind(payload, "predictor"),
        "private_model_state_counts": model_states,
        "active_private_model_id": active_model_id,
        "reacclimation_ticks_consumed": int(metric_payload.get("reacclimation_ticks_consumed") or 0),
        "reacclimation_completed": bool(metric_payload.get("reacclimation_completed", False)),
        "vital_state_ticks": deepcopy(metric_payload.get("vital_state_ticks") or {}),
    }


def append_epoch_summary(
    payload: dict[str, Any],
    summary: Mapping[str, Any],
) -> None:
    raw = payload.get("embodiment_epoch_summaries")
    summaries = deepcopy(raw) if isinstance(raw, list) else []
    epoch = int(summary.get("epoch") or 0)
    summaries = [
        item
        for item in summaries
        if not (isinstance(item, Mapping) and int(item.get("epoch") or 0) == epoch)
    ]
    summaries.append(deepcopy(dict(summary)))
    payload["embodiment_epoch_summaries"] = summaries[-_MAX_EPOCH_SUMMARIES:]


__all__ = [
    "CONTRACT_FINGERPRINT_SCHEMA_VERSION",
    "append_epoch_summary",
    "archive_contract_memory",
    "build_epoch_summary",
    "contract_fingerprint",
    "inject_memory_candidates",
    "memory_for_contract",
]