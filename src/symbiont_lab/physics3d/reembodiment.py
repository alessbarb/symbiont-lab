"""Body-independent Symbiont lifecycle and re-embodiment transforms."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping


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


def _fresh_actuation_with_transfer(
    previous: Mapping[str, Any],
    fresh: Mapping[str, Any],
    *,
    same_contract: bool,
) -> dict[str, Any]:
    fresh_actuation = deepcopy(fresh.get("actuation"))
    if not isinstance(fresh_actuation, dict):
        return {"enabled": False}
    if not same_contract:
        return fresh_actuation

    previous_actuation = previous.get("actuation")
    if not isinstance(previous_actuation, Mapping):
        return fresh_actuation

    # Same opaque contract: transfer learned motor evidence, never actuator
    # health or unfinished cross-run causal traces.
    for key in ("proposer", "sensorimotor", "selection_threshold", "exploration_mode"):
        if key in previous_actuation:
            fresh_actuation[key] = deepcopy(previous_actuation[key])
    fresh_actuation["pending_motor_observation"] = []
    fresh_actuation["pending_proprioception"] = {}
    fresh_actuation["last_executed_primitive_id"] = None
    fresh_actuation["pending_primitive_choice_context"] = None
    return fresh_actuation


def prepare_fresh_embodiment_checkpoint(
    previous: Mapping[str, Any],
    fresh: Mapping[str, Any],
    *,
    contract: EmbodimentContract,
) -> dict[str, Any]:
    """Move one persistent Symbiont into a fresh body without reviving the old body."""
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

    same_contract = _same_contract(current, contract)
    saved_tick = int(previous.get("saved_at_tick") or 0)
    history.append({
        "epoch": epoch,
        "body_kind": str(current.get("body_kind") or "unknown"),
        "receptor_count": int(current.get("receptor_count") or 0),
        "effector_count": int(current.get("effector_count") or 0),
        "started_tick": int(current.get("started_tick") or 0),
        "ended_tick": saved_tick,
        "end_body_vital_state": _body_vital_state(previous),
        "body_schema": deepcopy(previous.get("body_schema")),
    })
    history = history[-_MAX_EMBODIMENT_HISTORY:]

    # Physical physiology always belongs to the new body.
    for key in ("living_body", "metabolism", "homeostasis", "physiology"):
        if key in fresh:
            result[key] = deepcopy(fresh[key])
    result["pending_embodied_work"] = 0.0
    result["resting_requested"] = False
    result["last_runtime_vital_state"] = "active"

    result["actuation"] = _fresh_actuation_with_transfer(
        previous, fresh, same_contract=same_contract
    )

    if not same_contract:
        # Start a new active schema.  The previous schema is retained above as
        # historical evidence; there is deliberately no old->new channel map.
        for key in ("body_schema", "self_model", "sensory_development", "sensory_system"):
            if key in fresh:
                result[key] = deepcopy(fresh[key])

        old_genome = result.get("genome")
        new_genome = fresh.get("genome")
        if isinstance(old_genome, dict) and isinstance(new_genome, Mapping):
            if "motor" in new_genome:
                old_genome["motor"] = deepcopy(new_genome["motor"])
            else:
                old_genome.pop("motor", None)
            fingerprint = result.get("constitution_fingerprint")
            if not isinstance(fingerprint, dict):
                fingerprint = {"schema_version": 1}
                result["constitution_fingerprint"] = fingerprint
            fingerprint["genome_hash"] = _canonical_hash(old_genome)

    result["embodiment_lifecycle"] = {
        "schema_version": _SCHEMA_VERSION,
        "state": "active",
        "epoch": epoch + 1,
        "current": {
            **contract.as_dict(),
            "started_tick": saved_tick,
            "body_vital_state": "active",
            "contract_relation": "same" if same_contract else "changed",
        },
        "history": history,
    }
    return result


def update_lifecycle_for_checkpoint(
    payload: dict[str, Any],
    *,
    contract: EmbodimentContract,
    state: str,
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
    payload["embodiment_lifecycle"] = {
        "schema_version": _SCHEMA_VERSION,
        "state": state,
        "epoch": epoch,
        "current": current,
        "history": history[-_MAX_EMBODIMENT_HISTORY:],
    }
    return payload


__all__ = [
    "EmbodimentContract",
    "lifecycle_summary",
    "prepare_fresh_embodiment_checkpoint",
    "update_lifecycle_for_checkpoint",
]
