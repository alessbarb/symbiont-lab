"""Bounded, factual communication telemetry.

This module is deliberately observational.  It contains no policy, meaning,
ground truth, evaluator labels, or feedback path to an organism.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from typing import Any, Mapping

MAX_TELEMETRY_EVENTS = 2048
MAX_EVENT_BYTES = 4096
MAX_SYMBOLS_PER_EVENT = 4
MAX_ID_LENGTH = 128


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_ID_LENGTH or "\x00" in value:
        raise ValueError(f"{name} must be a bounded identifier")
    return value


def _nonnegative(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class CommunicationEvent:
    event_id: str
    tick: int
    event_kind: str
    sender_id: str
    receiver_id: str
    message_id: str
    symbol_ids: tuple[str, ...]
    cost: int
    delivery_status: str
    sender_generation: int | None = None
    receiver_generation: int | None = None

    def __post_init__(self) -> None:
        _id(self.event_id, "event_id")
        _nonnegative(self.tick, "tick")
        if self.event_kind not in {"EMIT", "DELIVER", "RECEIVE", "RETRANSMIT", "SILENCE"}:
            raise ValueError("unsupported communication event kind")
        _id(self.sender_id, "sender_id")
        _id(self.receiver_id, "receiver_id")
        _id(self.message_id, "message_id")
        if (
            not isinstance(self.symbol_ids, tuple)
            or not 1 <= len(self.symbol_ids) <= MAX_SYMBOLS_PER_EVENT
        ):
            raise ValueError("event symbol count exceeds bound")
        for symbol in self.symbol_ids:
            _id(symbol, "symbol_id")
        _nonnegative(self.cost, "cost")
        if self.delivery_status not in {"selected", "delivered", "rejected", "unknown"}:
            raise ValueError("unsupported delivery status")
        for value, name in (
            (self.sender_generation, "sender_generation"),
            (self.receiver_generation, "receiver_generation"),
        ):
            if value is not None:
                _nonnegative(value, name)

    @property
    def canonical_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tick": self.tick,
            "event_kind": self.event_kind,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_id": self.message_id,
            "symbol_ids": list(self.symbol_ids),
            "cost": self.cost,
            "delivery_status": self.delivery_status,
            "sender_generation": self.sender_generation,
            "receiver_generation": self.receiver_generation,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any]) -> "CommunicationEvent":
        if not isinstance(payload, Mapping):
            raise ValueError("invalid communication event")
        try:
            return cls(
                payload["event_id"],
                payload["tick"],
                payload["event_kind"],
                payload["sender_id"],
                payload["receiver_id"],
                payload["message_id"],
                tuple(payload["symbol_ids"]),
                payload["cost"],
                payload["delivery_status"],
                payload.get("sender_generation"),
                payload.get("receiver_generation"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid communication event") from exc


@dataclass(frozen=True, slots=True)
class GroundingEvent:
    event_id: str
    tick: int
    organism_id: str
    message_id: str
    exposure_count: int
    association_strength_before: int
    association_strength_after: int
    support_delta: int
    contradiction_delta: int
    cost: int

    def __post_init__(self) -> None:
        _id(self.event_id, "event_id")
        _nonnegative(self.tick, "tick")
        _id(self.organism_id, "organism_id")
        _id(self.message_id, "message_id")
        for value, name in (
            (self.exposure_count, "exposure_count"),
            (self.association_strength_before, "association_strength_before"),
            (self.association_strength_after, "association_strength_after"),
            (self.cost, "cost"),
        ):
            _nonnegative(value, name)
        if isinstance(self.support_delta, bool) or not isinstance(self.support_delta, int):
            raise ValueError("support_delta must be an integer")
        if isinstance(self.contradiction_delta, bool) or not isinstance(
            self.contradiction_delta, int
        ):
            raise ValueError("contradiction_delta must be an integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tick": self.tick,
            "organism_id": self.organism_id,
            "message_id": self.message_id,
            "exposure_count": self.exposure_count,
            "association_strength_before": self.association_strength_before,
            "association_strength_after": self.association_strength_after,
            "support_delta": self.support_delta,
            "contradiction_delta": self.contradiction_delta,
            "cost": self.cost,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any]) -> "GroundingEvent":
        if not isinstance(payload, Mapping):
            raise ValueError("invalid grounding event")
        try:
            return cls(**payload)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid grounding event") from exc


class CommunicationTelemetry:
    """A deterministic bounded append-only observation buffer."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        max_events: int = MAX_TELEMETRY_EVENTS,
        max_events_per_tick: int = 256,
        max_age_ticks: int | None = None,
    ) -> None:
        if (
            isinstance(max_events, bool)
            or not isinstance(max_events, int)
            or isinstance(max_events_per_tick, bool)
            or not isinstance(max_events_per_tick, int)
        ):
            raise ValueError("telemetry capacities must be integers")
        max_events_per_tick = min(max_events, max_events_per_tick)
        if (
            not 1 <= max_events <= MAX_TELEMETRY_EVENTS
            or not 1 <= max_events_per_tick <= max_events
        ):
            raise ValueError("telemetry capacity exceeds bound")
        if max_age_ticks is not None and (
            isinstance(max_age_ticks, bool)
            or not isinstance(max_age_ticks, int)
            or max_age_ticks < 0
        ):
            raise ValueError("max_age_ticks must be non-negative")
        self.max_events = max_events
        self.max_events_per_tick = max_events_per_tick
        self.max_age_ticks = max_age_ticks
        self._events: deque[CommunicationEvent] = deque()
        self._grounding: deque[GroundingEvent] = deque()
        self._event_ids: set[str] = set()
        self._grounding_ids: set[str] = set()
        self._current_tick: int | None = None
        self._truncated = False

    @property
    def events(self) -> tuple[CommunicationEvent, ...]:
        return tuple(self._events)

    @property
    def grounding_events(self) -> tuple[GroundingEvent, ...]:
        return tuple(self._grounding)

    @property
    def history_truncated(self) -> bool:
        return self._truncated

    @property
    def earliest_available_tick(self) -> int | None:
        ticks = [event.tick for event in self._events] + [event.tick for event in self._grounding]
        return min(ticks) if ticks else None

    def _prune(self, tick: int) -> None:
        cutoff = tick - self.max_age_ticks if self.max_age_ticks is not None else None
        while self._events and (
            len(self._events) > self.max_events
            or (cutoff is not None and self._events[0].tick < cutoff)
        ):
            self._event_ids.discard(self._events.popleft().event_id)
            self._truncated = True
        while self._grounding and (
            len(self._grounding) > self.max_events
            or (cutoff is not None and self._grounding[0].tick < cutoff)
        ):
            self._grounding_ids.discard(self._grounding.popleft().event_id)
            self._truncated = True

    def record(self, event: CommunicationEvent) -> bool:
        if (
            not isinstance(event, CommunicationEvent)
            or len(event.canonical_bytes) > MAX_EVENT_BYTES
        ):
            raise ValueError("communication event exceeds telemetry bound")
        if event.event_id in self._event_ids:
            return False
        if sum(1 for item in self._events if item.tick == event.tick) >= self.max_events_per_tick:
            self._truncated = True
            return False
        self._events.append(event)
        self._event_ids.add(event.event_id)
        self._current_tick = max(self._current_tick or event.tick, event.tick)
        self._prune(event.tick)
        return True

    def record_grounding(self, event: GroundingEvent) -> bool:
        if (
            not isinstance(event, GroundingEvent)
            or len(json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")).encode())
            > MAX_EVENT_BYTES
        ):
            raise ValueError("grounding event exceeds telemetry bound")
        if event.event_id in self._grounding_ids:
            return False
        if (
            sum(1 for item in self._grounding if item.tick == event.tick)
            >= self.max_events_per_tick
        ):
            self._truncated = True
            return False
        self._grounding.append(event)
        self._grounding_ids.add(event.event_id)
        self._current_tick = max(self._current_tick or event.tick, event.tick)
        self._prune(event.tick)
        return True

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "max_events": self.max_events,
            "max_events_per_tick": self.max_events_per_tick,
            "max_age_ticks": self.max_age_ticks,
            "events": [event.to_dict() for event in self._events],
            "grounding_events": [event.to_dict() for event in self._grounding],
            "history_truncated": self._truncated,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any]) -> "CommunicationTelemetry":
        if not isinstance(payload, Mapping) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported telemetry checkpoint")
        telemetry = cls(
            max_events=payload["max_events"],
            max_events_per_tick=payload["max_events_per_tick"],
            max_age_ticks=payload.get("max_age_ticks"),
        )
        events = payload.get("events", [])
        grounding = payload.get("grounding_events", [])
        if (
            not isinstance(events, list)
            or not isinstance(grounding, list)
            or len(events) > telemetry.max_events
            or len(grounding) > telemetry.max_events
        ):
            raise ValueError("telemetry checkpoint exceeds bound")
        for raw in events:
            if not telemetry.record(CommunicationEvent.restore(raw)):
                raise ValueError("duplicate communication event")
        for raw in grounding:
            if not telemetry.record_grounding(GroundingEvent.restore(raw)):
                raise ValueError("duplicate grounding event")
        telemetry._truncated = payload.get("history_truncated") is True
        return telemetry

    def export(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "events": [event.to_dict() for event in self._events],
            "grounding_events": [event.to_dict() for event in self._grounding],
            "history_truncated": self._truncated,
            "earliest_available_tick": self.earliest_available_tick,
        }


__all__ = ["CommunicationEvent", "CommunicationTelemetry", "GroundingEvent", "MAX_TELEMETRY_EVENTS"]
