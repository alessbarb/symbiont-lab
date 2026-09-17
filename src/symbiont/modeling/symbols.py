"""Bounded opaque-symbol substrate for emergent grounding experiments.

The substrate deliberately contains no symbol-to-meaning table.  A symbol is
only an opaque identifier; outcome associations are created by the receiving
organism after local experience.
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Mapping

MAX_SYMBOLS = 32
MAX_ID = 96
MAX_ASSOCIATIONS = 128
MAX_HISTORY = 256
MAX_EMISSIONS_PER_TICK = 1


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_ID:
        raise ValueError(f"{name} must be a bounded identifier")
    if any(ord(char) < 33 or ord(char) > 126 for char in value):
        raise ValueError(f"{name} must contain printable ASCII only")
    return value


def build_opaque_symbol(namespace: str, index: int) -> str:
    """Create a canonical identifier whose spelling carries no domain label."""
    _id(namespace, "symbol namespace")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < MAX_SYMBOLS:
        raise ValueError("symbol index exceeds its bound")
    digest = hashlib.sha256(f"{namespace}:{index}".encode()).hexdigest()[:12]
    return f"symbol.{digest}"


def default_symbol_space(namespace: str = "native") -> tuple[str, ...]:
    _id(namespace, "symbol namespace")
    return tuple(build_opaque_symbol(namespace, index) for index in range(MAX_SYMBOLS))


class SymbolAction(StrEnum):
    SILENCE = "silence"
    EMIT = "emit"


@dataclass(frozen=True, slots=True)
class SymbolDecisionRecord:
    decision_id: str
    organism_id: str
    decision_tick: int
    candidate_symbols_digest: str
    selected_action: SymbolAction
    selected_symbol_id: str | None
    selected_recipient_id: str | None
    cost: int
    local_state_digest: str

    def __post_init__(self) -> None:
        _id(self.decision_id, "decision_id")
        _id(self.organism_id, "organism_id")
        if isinstance(self.decision_tick, bool) or not isinstance(self.decision_tick, int) or self.decision_tick < 0:
            raise ValueError("decision_tick must be non-negative")
        for value, name in ((self.candidate_symbols_digest, "candidate_symbols_digest"), (self.local_state_digest, "local_state_digest")):
            if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValueError(f"{name} must be a SHA-256 digest")
        if not isinstance(self.selected_action, SymbolAction):
            raise ValueError("invalid symbol action")
        if self.selected_symbol_id is not None:
            _id(self.selected_symbol_id, "selected_symbol_id")
        if self.selected_recipient_id is not None:
            _id(self.selected_recipient_id, "selected_recipient_id")
        if isinstance(self.cost, bool) or not isinstance(self.cost, int) or self.cost < 0:
            raise ValueError("symbol decision cost must be non-negative")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "organism_id": self.organism_id,
            "decision_tick": self.decision_tick,
            "candidate_symbols_digest": self.candidate_symbols_digest,
            "selected_action": self.selected_action.value,
            "selected_symbol_id": self.selected_symbol_id,
            "selected_recipient_id": self.selected_recipient_id,
            "cost": self.cost,
            "local_state_digest": self.local_state_digest,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "SymbolDecisionRecord":
        try:
            return cls(
                str(payload["decision_id"]), str(payload["organism_id"]), payload["decision_tick"],
                str(payload["candidate_symbols_digest"]), SymbolAction(payload["selected_action"]),
                payload.get("selected_symbol_id"), payload.get("selected_recipient_id"), payload["cost"],
                str(payload["local_state_digest"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid symbol decision") from exc


@dataclass(frozen=True, slots=True)
class SymbolMessage:
    symbol_id: str
    sender_id: str
    receiver_id: str
    emitted_tick: int
    transmission_depth: int = 0

    def __post_init__(self) -> None:
        _id(self.symbol_id, "symbol_id")
        _id(self.sender_id, "sender_id")
        _id(self.receiver_id, "receiver_id")
        if isinstance(self.emitted_tick, bool) or not isinstance(self.emitted_tick, int) or self.emitted_tick < 0:
            raise ValueError("emitted_tick must be non-negative")
        if isinstance(self.transmission_depth, bool) or not isinstance(self.transmission_depth, int) or not 0 <= self.transmission_depth <= 32:
            raise ValueError("transmission_depth exceeds its bound")


@dataclass(frozen=True, slots=True)
class SymbolAssociation:
    symbol_id: str
    outcome_token: str
    support: int
    contradiction: int
    last_tick: int

    def __post_init__(self) -> None:
        _id(self.symbol_id, "symbol_id")
        _id(self.outcome_token, "outcome_token")
        for value, name in ((self.support, "support"), (self.contradiction, "contradiction"), (self.last_tick, "last_tick")):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a bounded non-negative integer")


class SymbolGroundingLedger:
    """Receiver-owned symbol exposure and local outcome associations."""

    SCHEMA_VERSION = 1

    def __init__(self, organism_id: str, *, max_associations: int = MAX_ASSOCIATIONS) -> None:
        _id(organism_id, "organism_id")
        if isinstance(max_associations, bool) or not 1 <= max_associations <= MAX_ASSOCIATIONS:
            raise ValueError("max_associations exceeds its bound")
        self.organism_id = organism_id
        self.max_associations = max_associations
        self._exposures: deque[SymbolMessage] = deque(maxlen=MAX_HISTORY)
        self._associations: dict[tuple[str, str], SymbolAssociation] = {}
        self._history: deque[dict[str, object]] = deque(maxlen=MAX_HISTORY)
        self._cost = 0

    @property
    def exposures(self) -> tuple[SymbolMessage, ...]:
        return tuple(self._exposures)

    @property
    def associations(self) -> tuple[SymbolAssociation, ...]:
        return tuple(self._associations[key] for key in sorted(self._associations))

    @property
    def cost(self) -> int:
        return self._cost

    def receive(self, message: SymbolMessage, *, tick: int) -> None:
        if message.receiver_id != self.organism_id:
            raise ValueError("symbol receiver ownership mismatch")
        if message in self._exposures:
            raise ValueError("duplicate symbol exposure rejected")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be non-negative")
        self._exposures.append(message)
        self._history.append({"kind": "exposure", "symbol_id": message.symbol_id, "sender_id": message.sender_id, "tick": tick})
        self._cost += 1

    def observe_outcome(self, outcome_token: str, *, tick: int, supported: bool = True, symbol_id: str | None = None) -> SymbolAssociation:
        _id(outcome_token, "outcome_token")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be non-negative")
        candidates = [item for item in self._exposures if symbol_id is None or item.symbol_id == symbol_id]
        if not candidates:
            raise ValueError("no local symbol exposure available")
        selected = candidates[-1]
        key = (selected.symbol_id, outcome_token)
        current = self._associations.get(key)
        if current is None and len(self._associations) >= self.max_associations:
            raise ValueError("symbol association capacity exceeded")
        association = SymbolAssociation(
            selected.symbol_id,
            outcome_token,
            (current.support if current else 0) + int(supported),
            (current.contradiction if current else 0) + int(not supported),
            tick,
        )
        self._associations[key] = association
        self._history.append({"kind": "outcome", "symbol_id": selected.symbol_id, "outcome_token": outcome_token, "supported": supported, "tick": tick})
        self._cost += 1
        return association

    def predict(self, symbol_id: str) -> str | None:
        _id(symbol_id, "symbol_id")
        candidates = [item for item in self.associations if item.symbol_id == symbol_id and item.support > item.contradiction]
        if not candidates:
            return None
        return max(candidates, key=lambda item: (item.support - item.contradiction, item.last_tick, item.outcome_token)).outcome_token

    def grounding_strength(self, symbol_id: str) -> int:
        predicted = self.predict(symbol_id)
        if predicted is None:
            return 0
        item = self._associations[(symbol_id, predicted)]
        return max(0, item.support - item.contradiction)

    def forget(self, *, current_tick: int, max_age: int) -> int:
        if isinstance(max_age, bool) or not isinstance(max_age, int) or max_age < 0:
            raise ValueError("max_age must be non-negative")
        removed = [key for key, item in self._associations.items() if current_tick - item.last_tick > max_age]
        for key in removed:
            del self._associations[key]
        return len(removed)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "organism_id": self.organism_id,
            "max_associations": self.max_associations,
            "exposures": [message.__dict__ if hasattr(message, "__dict__") else {field: getattr(message, field) for field in message.__dataclass_fields__} for message in self.exposures],
            "associations": [{field: getattr(item, field) for field in item.__dataclass_fields__} for item in self.associations],
            "history": list(self._history),
            "cost": self._cost,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None, *, organism_id: str) -> "SymbolGroundingLedger":
        if payload is None:
            return cls(organism_id)
        if payload.get("schema_version") != cls.SCHEMA_VERSION or payload.get("organism_id") != organism_id:
            raise ValueError("invalid symbol grounding checkpoint")
        if not isinstance(payload.get("exposures", []), list) or len(payload["exposures"]) > MAX_HISTORY:
            raise ValueError("invalid symbol exposures")
        if not isinstance(payload.get("associations", []), list) or len(payload["associations"]) > MAX_ASSOCIATIONS:
            raise ValueError("invalid symbol associations")
        ledger = cls(organism_id, max_associations=payload["max_associations"])
        for row in payload.get("exposures", []):
            ledger._exposures.append(SymbolMessage(**row))
        for row in payload.get("associations", []):
            item = SymbolAssociation(**row)
            ledger._associations[(item.symbol_id, item.outcome_token)] = item
        if not isinstance(payload.get("history", []), list) or len(payload["history"]) > MAX_HISTORY:
            raise ValueError("invalid symbol history")
        ledger._history.extend(payload.get("history", []))
        ledger._cost = payload.get("cost", 0)
        if isinstance(ledger._cost, bool) or not isinstance(ledger._cost, int) or ledger._cost < 0:
            raise ValueError("invalid symbol grounding cost")
        return ledger


class SymbolChannel:
    """Authorized in-memory symbolic transport; no discovery or host I/O."""

    def __init__(self, *, authorized_pairs: set[tuple[str, str]], max_deliveries: int = 256) -> None:
        if len(authorized_pairs) > MAX_HISTORY:
            raise ValueError("authorized symbol pairs exceed bound")
        if isinstance(max_deliveries, bool) or not 1 <= max_deliveries <= MAX_HISTORY * 4:
            raise ValueError("max_deliveries exceeds bound")
        self.authorized_pairs = frozenset(authorized_pairs)
        self.max_deliveries = max_deliveries
        self.deliveries = 0

    def deliver(self, message: SymbolMessage, *, receiver: SymbolGroundingLedger, tick: int) -> None:
        if (message.sender_id, message.receiver_id) not in self.authorized_pairs:
            raise ValueError("unauthorized symbol delivery")
        if self.deliveries >= self.max_deliveries:
            raise ValueError("symbol channel capacity exceeded")
        receiver.receive(message, tick=tick)
        self.deliveries += 1


class SymbolPolicy:
    """Seeded local baseline that selects an opaque symbol without meaning labels."""

    SCHEMA_VERSION = 1

    def __init__(self, organism_id: str, *, seed: int = 0, symbol_space: tuple[str, ...] | None = None) -> None:
        _id(organism_id, "organism_id")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**31 - 1:
            raise ValueError("symbol policy seed exceeds bound")
        self.organism_id = organism_id
        self.seed = seed
        self.symbol_space = tuple(symbol_space or default_symbol_space())
        if not 1 <= len(self.symbol_space) <= MAX_SYMBOLS or len(set(self.symbol_space)) != len(self.symbol_space):
            raise ValueError("invalid symbol space")
        for symbol in self.symbol_space:
            _id(symbol, "symbol")
        self._decisions: deque[SymbolDecisionRecord] = deque(maxlen=MAX_HISTORY)
        self._cost = 0

    @property
    def decisions(self) -> tuple[SymbolDecisionRecord, ...]:
        return tuple(self._decisions)

    @property
    def cost(self) -> int:
        return self._cost

    @staticmethod
    def _digest(value: object) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def choose(self, *, local_context_token: str, neighbor_ids: Iterable[str], tick: int) -> SymbolDecisionRecord:
        _id(local_context_token, "local_context_token")
        neighbors = tuple(sorted(set(neighbor_ids)))
        for neighbor in neighbors:
            _id(neighbor, "neighbor_id")
        candidates = tuple((symbol, receiver) for symbol in self.symbol_space for receiver in neighbors)
        candidate_digest = self._digest(candidates)
        if not candidates:
            return self._record(tick, candidate_digest, SymbolAction.SILENCE, None, None, 0)
        ranked = sorted(candidates, key=lambda item: self._digest((self.seed, local_context_token, item)), reverse=True)
        symbol, receiver = ranked[0]
        # A deterministic bounded silence gate prevents forced signalling.
        if int(self._digest((self.seed, local_context_token, tick))[:2], 16) < 32:
            return self._record(tick, candidate_digest, SymbolAction.SILENCE, None, None, 0)
        return self._record(tick, candidate_digest, SymbolAction.EMIT, symbol, receiver, 1)

    def choose_grounded(
        self,
        ledger: SymbolGroundingLedger,
        *,
        outcome_token: str,
        neighbor_ids: Iterable[str],
        tick: int,
    ) -> SymbolDecisionRecord:
        """Select a locally learned cue for a locally observed outcome."""
        _id(outcome_token, "outcome_token")
        neighbors = tuple(sorted(set(neighbor_ids)))
        for neighbor in neighbors:
            _id(neighbor, "neighbor_id")
        known = tuple(sorted(
            item.symbol_id for item in ledger.associations
            if item.outcome_token == outcome_token and item.support > item.contradiction
        ))
        candidates = tuple((symbol, receiver) for symbol in known for receiver in neighbors)
        candidate_digest = self._digest(candidates)
        if not candidates:
            return self._record(tick, candidate_digest, SymbolAction.SILENCE, None, None, 0)
        symbol, receiver = sorted(candidates, key=lambda item: (self._digest((self.seed, outcome_token, item)), item), reverse=True)[0]
        return self._record(tick, candidate_digest, SymbolAction.EMIT, symbol, receiver, 1)

    def _record(self, tick: int, candidate_digest: str, action: SymbolAction, symbol: str | None, receiver: str | None, cost: int) -> SymbolDecisionRecord:
        payload = (self.organism_id, self.seed, tick, len(self._decisions), action.value, symbol, receiver)
        record = SymbolDecisionRecord("symbol-decision." + self._digest(payload)[:48], self.organism_id, tick, candidate_digest, action, symbol, receiver, cost, self._digest(payload))
        self._decisions.append(record)
        self._cost += cost
        return record

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "organism_id": self.organism_id,
            "seed": self.seed,
            "symbol_space": list(self.symbol_space),
            "cost": self._cost,
            "decisions": [item.canonical_payload() for item in self.decisions],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None, *, organism_id: str) -> "SymbolPolicy":
        if payload is None:
            return cls(organism_id)
        if payload.get("schema_version") != cls.SCHEMA_VERSION or payload.get("organism_id") != organism_id:
            raise ValueError("invalid symbol policy checkpoint")
        if not isinstance(payload.get("symbol_space"), list) or not isinstance(payload.get("decisions", []), list):
            raise ValueError("invalid symbol policy rows")
        if len(payload["decisions"]) > MAX_HISTORY:
            raise ValueError("symbol policy history exceeds bound")
        policy = cls(organism_id, seed=payload["seed"], symbol_space=tuple(payload["symbol_space"]))
        for row in payload.get("decisions", []):
            policy._decisions.append(SymbolDecisionRecord.restore(row))
        policy._cost = payload.get("cost", 0)
        if isinstance(policy._cost, bool) or not isinstance(policy._cost, int) or policy._cost < 0:
            raise ValueError("invalid symbol policy cost")
        return policy


__all__ = [
    "SymbolAction", "SymbolAssociation", "SymbolChannel", "SymbolDecisionRecord",
    "SymbolGroundingLedger", "SymbolMessage", "SymbolPolicy", "build_opaque_symbol",
    "default_symbol_space",
]
