"""Bounded opaque symbol sequences and receiver-side compositional learning."""
from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from typing import Iterable, Mapping

from .symbols import MAX_HISTORY, SymbolAction, SymbolPolicy, _id

MAX_SEQUENCE_LENGTH = 4
MAX_SEQUENCES = 128


@dataclass(frozen=True, slots=True)
class SymbolSequence:
    symbols: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 1 <= len(self.symbols) <= MAX_SEQUENCE_LENGTH:
            raise ValueError("symbol sequence length exceeds bound")
        if any(not isinstance(symbol, str) for symbol in self.symbols):
            raise ValueError("sequence symbols must be identifiers")
        for symbol in self.symbols:
            _id(symbol, "sequence symbol")

    @property
    def sequence_id(self) -> str:
        payload = json.dumps(self.symbols, separators=(",", ":"))
        return "sequence." + hashlib.sha256(payload.encode()).hexdigest()[:48]


@dataclass(frozen=True, slots=True)
class SequenceMessage:
    sequence: SymbolSequence
    sender_id: str
    receiver_id: str
    emitted_tick: int

    def __post_init__(self) -> None:
        _id(self.sender_id, "sender_id")
        _id(self.receiver_id, "receiver_id")
        if isinstance(self.emitted_tick, bool) or not isinstance(self.emitted_tick, int) or self.emitted_tick < 0:
            raise ValueError("emitted_tick must be non-negative")


@dataclass(frozen=True, slots=True)
class SequenceDecisionRecord:
    decision_id: str
    organism_id: str
    decision_tick: int
    candidate_set_digest: str
    selected_action: SymbolAction
    selected_sequence_id: str | None
    selected_symbols: tuple[str, ...] | None
    selected_recipient_id: str | None
    cost: int

    def __post_init__(self) -> None:
        _id(self.decision_id, "decision_id")
        _id(self.organism_id, "organism_id")
        if isinstance(self.decision_tick, bool) or not isinstance(self.decision_tick, int) or self.decision_tick < 0:
            raise ValueError("decision_tick must be non-negative")
        if not isinstance(self.candidate_set_digest, str) or len(self.candidate_set_digest) != 64 or any(char not in "0123456789abcdef" for char in self.candidate_set_digest):
            raise ValueError("candidate_set_digest must be SHA-256")
        if not isinstance(self.selected_action, SymbolAction):
            raise ValueError("invalid sequence action")
        if isinstance(self.cost, bool) or not isinstance(self.cost, int) or self.cost < 0:
            raise ValueError("sequence decision cost must be non-negative")
        if self.selected_sequence_id is not None:
            _id(self.selected_sequence_id, "selected_sequence_id")
        if self.selected_symbols is not None:
            if not isinstance(self.selected_symbols, tuple):
                raise ValueError("selected_symbols must be a tuple")
            sequence = SymbolSequence(self.selected_symbols)
            if self.selected_sequence_id != sequence.sequence_id:
                raise ValueError("selected sequence identity mismatch")
        if self.selected_recipient_id is not None:
            _id(self.selected_recipient_id, "selected_recipient_id")
        if self.selected_action is SymbolAction.EMIT and (
            self.selected_sequence_id is None
            or self.selected_symbols is None
            or self.selected_recipient_id is None
        ):
            raise ValueError("emission must select sequence and recipient")
        if self.selected_action is SymbolAction.SILENCE and any(value is not None for value in (self.selected_sequence_id, self.selected_symbols, self.selected_recipient_id)):
            raise ValueError("silence cannot select sequence or recipient")

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "SequenceDecisionRecord":
        if not isinstance(payload, Mapping):
            raise ValueError("invalid sequence decision")
        try:
            symbols = payload.get("selected_symbols")
            if symbols is not None:
                if not isinstance(symbols, (tuple, list)):
                    raise ValueError("selected_symbols must be a sequence")
                symbols = tuple(symbols)
            return cls(
                payload["decision_id"], payload["organism_id"], payload["decision_tick"],
                payload["candidate_set_digest"], SymbolAction(payload["selected_action"]),
                payload.get("selected_sequence_id"), symbols,
                payload.get("selected_recipient_id"), payload["cost"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid sequence decision") from exc


@dataclass(frozen=True, slots=True)
class SequenceAssociation:
    sequence_id: str
    symbols: tuple[str, ...]
    outcome_tokens: tuple[str, ...]
    support: int
    contradiction: int
    last_tick: int

    def __post_init__(self) -> None:
        _id(self.sequence_id, "sequence_id")
        SymbolSequence(self.symbols)
        if not 1 <= len(self.outcome_tokens) <= MAX_SEQUENCE_LENGTH:
            raise ValueError("outcome arity exceeds bound")
        for value in self.symbols + self.outcome_tokens:
            _id(value, "sequence token")
        for value in (self.support, self.contradiction, self.last_tick):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("sequence association values must be bounded")


class SequenceGroundingLedger:
    """Receiver-owned grounding for opaque variable-length messages."""

    SCHEMA_VERSION = 1

    def __init__(self, organism_id: str, *, max_associations: int = MAX_SEQUENCES) -> None:
        _id(organism_id, "organism_id")
        if not 1 <= max_associations <= MAX_SEQUENCES:
            raise ValueError("sequence association capacity exceeds bound")
        self.organism_id = organism_id
        self.max_associations = max_associations
        self._exposures: deque[SequenceMessage] = deque(maxlen=MAX_HISTORY)
        self._associations: dict[tuple[str, tuple[str, ...]], SequenceAssociation] = {}
        self._cost = 0

    @property
    def exposures(self) -> tuple[SequenceMessage, ...]:
        return tuple(self._exposures)

    @property
    def associations(self) -> tuple[SequenceAssociation, ...]:
        return tuple(self._associations[key] for key in sorted(self._associations))

    @property
    def cost(self) -> int:
        return self._cost

    def receive(self, message: SequenceMessage, *, tick: int) -> None:
        if message.receiver_id != self.organism_id:
            raise ValueError("sequence receiver ownership mismatch")
        if message in self._exposures:
            raise ValueError("duplicate sequence exposure rejected")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be non-negative")
        self._exposures.append(message)
        self._cost += len(message.sequence.symbols)

    def observe_outcome(self, outcome_tokens: tuple[str, ...], *, tick: int, supported: bool = True) -> SequenceAssociation:
        if not 1 <= len(outcome_tokens) <= MAX_SEQUENCE_LENGTH:
            raise ValueError("outcome arity exceeds bound")
        for token in outcome_tokens:
            _id(token, "outcome token")
        if not self._exposures:
            raise ValueError("no local sequence exposure available")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be non-negative")
        selected = self._exposures[-1]
        sequence = selected.sequence
        key = (sequence.sequence_id, outcome_tokens)
        current = self._associations.get(key)
        if current is None and len(self._associations) >= self.max_associations:
            raise ValueError("sequence association capacity exceeded")
        item = SequenceAssociation(sequence.sequence_id, sequence.symbols, outcome_tokens,
                                   (current.support if current else 0) + int(supported),
                                   (current.contradiction if current else 0) + int(not supported), tick)
        self._associations[key] = item
        self._cost += len(sequence.symbols)
        return item

    def predict_exact(self, sequence: SymbolSequence) -> tuple[str, ...] | None:
        candidates = [item for item in self.associations if item.sequence_id == sequence.sequence_id and item.support > item.contradiction]
        if not candidates:
            return None
        return max(candidates, key=lambda item: (item.support - item.contradiction, item.last_tick, item.outcome_tokens)).outcome_tokens

    def forget(self, *, current_tick: int, max_age: int) -> int:
        removed = [key for key, item in self._associations.items() if current_tick - item.last_tick > max_age]
        for key in removed:
            del self._associations[key]
        return len(removed)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "organism_id": self.organism_id,
            "max_associations": self.max_associations,
            "exposures": [{"symbols": item.sequence.symbols, "sender_id": item.sender_id, "receiver_id": item.receiver_id, "emitted_tick": item.emitted_tick} for item in self.exposures],
            "associations": [{"sequence_id": item.sequence_id, "symbols": item.symbols, "outcome_tokens": item.outcome_tokens, "support": item.support, "contradiction": item.contradiction, "last_tick": item.last_tick} for item in self.associations],
            "cost": self._cost,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None, *, organism_id: str) -> "SequenceGroundingLedger":
        if payload is None:
            return cls(organism_id)
        if not isinstance(payload, Mapping):
            raise ValueError("invalid sequence grounding checkpoint")
        if payload.get("schema_version") != cls.SCHEMA_VERSION or payload.get("organism_id") != organism_id:
            raise ValueError("invalid sequence grounding checkpoint")
        ledger = cls(organism_id, max_associations=payload["max_associations"])
        exposures = payload.get("exposures", [])
        associations = payload.get("associations", [])
        if not isinstance(exposures, list) or not isinstance(associations, list) or len(exposures) > MAX_HISTORY or len(associations) > ledger.max_associations:
            raise ValueError("sequence grounding rows exceed bound")
        for row in exposures:
            if not isinstance(row, Mapping):
                raise ValueError("invalid sequence exposure row")
            ledger._exposures.append(SequenceMessage(SymbolSequence(tuple(row["symbols"])), row["sender_id"], row["receiver_id"], row["emitted_tick"]))
        for row in associations:
            if not isinstance(row, Mapping):
                raise ValueError("invalid sequence association row")
            item = SequenceAssociation(**row)
            if item.sequence_id != SymbolSequence(item.symbols).sequence_id:
                raise ValueError("sequence identity mismatch")
            ledger._associations[(item.sequence_id, item.outcome_tokens)] = item
        ledger._cost = payload.get("cost", 0)
        if isinstance(ledger._cost, bool) or not isinstance(ledger._cost, int) or ledger._cost < 0:
            raise ValueError("invalid sequence grounding cost")
        return ledger


class SequenceChannel:
    def __init__(self, *, authorized_pairs: set[tuple[str, str]], max_deliveries: int = 256) -> None:
        if len(authorized_pairs) > MAX_HISTORY or not 1 <= max_deliveries <= MAX_HISTORY * 4:
            raise ValueError("sequence channel bound exceeded")
        if any(not isinstance(pair, tuple) or len(pair) != 2 for pair in authorized_pairs):
            raise ValueError("invalid authorized sequence pair")
        for sender, receiver in authorized_pairs:
            _id(sender, "sender_id")
            _id(receiver, "receiver_id")
        self.authorized_pairs = frozenset(authorized_pairs)
        self.max_deliveries = max_deliveries
        self.deliveries = 0

    def deliver(self, message: SequenceMessage, *, receiver: SequenceGroundingLedger, tick: int) -> None:
        if (message.sender_id, message.receiver_id) not in self.authorized_pairs:
            raise ValueError("unauthorized sequence delivery")
        if self.deliveries >= self.max_deliveries:
            raise ValueError("sequence channel capacity exceeded")
        receiver.receive(message, tick=tick)
        self.deliveries += 1


def choose_sequence(policy: SymbolPolicy, *, local_context_tokens: tuple[str, ...], neighbor_ids: Iterable[str], tick: int) -> SequenceDecisionRecord:
    """Choose a variable-length opaque message from local state only."""
    neighbors = tuple(sorted(set(neighbor_ids)))
    candidate_digest = policy._digest((policy.symbol_space, neighbors, local_context_tokens))
    decision_id = "sequence-decision." + policy._digest((policy.organism_id, policy.seed, tick, len(policy.decisions), candidate_digest))[:48]
    if not local_context_tokens or not neighbors:
        return SequenceDecisionRecord(decision_id, policy.organism_id, tick, candidate_digest, SymbolAction.SILENCE, None, None, None, 0)
    for token in local_context_tokens:
        _id(token, "local context token")
    candidates = []
    # The whole local state is treated as an opaque context.  ``index`` below
    # is only the serialized position in a candidate message; it is not a
    # semantic slot and has no relation to evaluator-side world dimensions.
    context_digest = policy._digest((policy.seed, local_context_tokens))
    for length in range(1, MAX_SEQUENCE_LENGTH + 1):
        symbols = tuple(
            max(policy.symbol_space, key=lambda symbol: policy._digest((context_digest, length, index, symbol)))
            for index in range(length)
        )
        candidates.append(SymbolSequence(symbols))
    sequence = max(candidates, key=lambda candidate: policy._digest((context_digest, candidate.symbols)))
    if int(policy._digest((policy.seed, local_context_tokens, tick))[:2], 16) < 64:
        return SequenceDecisionRecord(decision_id, policy.organism_id, tick, candidate_digest, SymbolAction.SILENCE, None, None, None, 0)
    recipient = max(neighbors, key=lambda value: policy._digest((policy.seed, local_context_tokens, value, tick)))
    return SequenceDecisionRecord(decision_id, policy.organism_id, tick, candidate_digest, SymbolAction.EMIT, sequence.sequence_id, sequence.symbols, recipient, len(sequence.symbols))


__all__ = ["SequenceGroundingLedger", "SequenceAssociation", "SequenceChannel", "SequenceDecisionRecord", "SequenceMessage", "SymbolSequence", "choose_sequence"]
