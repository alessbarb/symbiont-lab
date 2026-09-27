"""Provisional intervention families (Agency Acquisition v1 §11-§12, §79).

An InterventionSignature groups concrete ActionAttempts that appear to be
variations of the same motor pattern *before* any ActionDimension or
MotorCompetence exists.  Identity is derived only from organism-observable
motor structure: the opaque set of channels driven and their relative
activation profile (and, for sequences, the ordered step signatures plus an
optional controller seed).  Absolute intensity is deliberately not part of
identity; it is tracked as a variant histogram so exploration can notice
missing intensity variants of an otherwise known family.

Nothing here knows about actuator anatomy, ActionDimensions or competences.
"""

from __future__ import annotations

import hashlib
import math
from collections import OrderedDict
from dataclasses import dataclass
from typing import Mapping, Sequence

from .action import MotorCommand

_SCHEMA = "symbiont-intervention-signature-v1"
# Relative activation buckets (relative to the strongest driven channel).
# Two buckets separate "dominant" from "secondary" channels without turning
# smoothing noise into new identities.
_RELATIVE_LEVELS = 2
_INTENSITY_BUCKETS = 4
_MIN_ACTIVATION = 1e-9


def opaque_channel_ref(actuator_id: str) -> str:
    """Opaque organism-side reference for one driven output channel."""
    if not actuator_id:
        raise ValueError("actuator id must be non-empty")
    digest = hashlib.sha256(f"{_SCHEMA}:channel:{actuator_id}".encode("utf-8")).hexdigest()[:16]
    return f"channel.{digest}"


def _digest(material: str) -> str:
    return hashlib.sha256(f"{_SCHEMA}:{material}".encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class InterventionSignature:
    signature_id: str

    channel_refs: tuple[str, ...]
    temporal_pattern_ref: str | None

    dimensionality: int

    def __post_init__(self) -> None:
        if not self.signature_id.startswith("intervention.signature."):
            raise ValueError("signature_id must be an opaque intervention reference")
        if not self.channel_refs:
            raise ValueError("an intervention signature drives at least one channel")
        if tuple(sorted(set(self.channel_refs))) != self.channel_refs:
            raise ValueError("channel_refs must be sorted and unique")
        if any(not ref.startswith("channel.") for ref in self.channel_refs):
            raise ValueError("channel_refs must be opaque organism-side references")
        if self.temporal_pattern_ref is not None and not self.temporal_pattern_ref.startswith(
            "temporal."
        ):
            raise ValueError("temporal_pattern_ref must be opaque")
        if self.dimensionality != len(self.channel_refs):
            raise ValueError("dimensionality must equal the number of driven channels")


@dataclass(slots=True)
class _SignatureStats:
    attempts: int = 0
    first_tick: int = 0
    last_tick: int = 0
    intensity_counts: tuple[int, ...] = (0,) * _INTENSITY_BUCKETS


def _relative_profile(channels: Mapping[str, float]) -> tuple[tuple[str, int], ...]:
    driven = {
        opaque_channel_ref(str(actuator_id)): float(value)
        for actuator_id, value in channels.items()
        if math.isfinite(float(value)) and float(value) > _MIN_ACTIVATION
    }
    if not driven:
        return ()
    peak = max(driven.values())
    return tuple(
        sorted(
            (ref, max(1, min(_RELATIVE_LEVELS, math.ceil(value / peak * _RELATIVE_LEVELS))))
            for ref, value in driven.items()
        )
    )


def _intensity_bucket(channels: Mapping[str, float]) -> int:
    values = [float(value) for value in channels.values() if float(value) > _MIN_ACTIVATION]
    peak = max(values, default=0.0)
    return max(0, min(_INTENSITY_BUCKETS - 1, int(peak * _INTENSITY_BUCKETS)))


class InterventionSignatureRegistry:
    """Bounded organism-internal registry of provisional intervention families."""

    SCHEMA_VERSION = 1

    def __init__(self, *, capacity: int = 512, command_memory: int = 256) -> None:
        if capacity < 1 or command_memory < 1:
            raise ValueError("registry bounds must be positive")
        self.capacity = int(capacity)
        self._command_memory = int(command_memory)
        self._signatures: dict[str, InterventionSignature] = {}
        self._stats: dict[str, _SignatureStats] = {}
        # Recent command -> signature identities, used to name sequences of
        # commands that were actually issued.  Ephemeral and bounded.
        self._by_command: OrderedDict[str, str] = OrderedDict()
        # channel set -> single-step family members (derived index).
        self._families: dict[tuple[str, ...], set[str]] = {}

    # -- identity ---------------------------------------------------------
    @staticmethod
    def _build(
        profile: tuple[tuple[str, int], ...],
        *,
        temporal_pattern_ref: str | None = None,
        channel_refs: tuple[str, ...] | None = None,
    ) -> InterventionSignature:
        refs = channel_refs if channel_refs is not None else tuple(ref for ref, _ in profile)
        material = repr((profile, temporal_pattern_ref))
        return InterventionSignature(
            signature_id=f"intervention.signature.{_digest(material)}",
            channel_refs=tuple(sorted(set(refs))),
            temporal_pattern_ref=temporal_pattern_ref,
            dimensionality=len(set(refs)),
        )

    def signature_for_pattern(self, channels: Mapping[str, float]) -> InterventionSignature:
        """Pure identity of one motor pattern; records no attempt."""
        profile = _relative_profile(channels)
        if not profile:
            raise ValueError("an intervention requires at least one driven channel")
        return self._build(profile)

    def signature_for_pattern_sequence(
        self,
        patterns: Sequence[Mapping[str, float]],
        *,
        controller_seed_ref: str | None,
    ) -> tuple[InterventionSignature, tuple[InterventionSignature, ...]]:
        """Temporal signature of an ordered pattern sequence plus its step signatures."""
        steps = tuple(self.signature_for_pattern(pattern) for pattern in patterns if pattern)
        if not steps:
            raise ValueError("a temporal intervention requires at least one driven step")
        return self._temporal(steps, controller_seed_ref=controller_seed_ref), steps

    def _temporal(
        self,
        steps: tuple[InterventionSignature, ...],
        *,
        controller_seed_ref: str | None,
    ) -> InterventionSignature:
        temporal_ref = "temporal." + _digest(
            repr((tuple(step.signature_id for step in steps), controller_seed_ref))
        )
        channel_refs = tuple(sorted({ref for step in steps for ref in step.channel_refs}))
        return self._build((), temporal_pattern_ref=temporal_ref, channel_refs=channel_refs)

    # -- observed interventions ------------------------------------------
    def signature_for_command(
        self,
        *,
        command: MotorCommand,
        controller_id: str,
        tick: int,
    ) -> InterventionSignature:
        """Name the family of one issued command and record the attempt.

        ``controller_id`` is validated provenance only: single-command
        identity is purely motor, so exploration and a learned controller
        emitting the same opaque pattern accumulate evidence in one family.
        """
        if not controller_id:
            raise ValueError("controller_id must be non-empty")
        if command.controller_id != controller_id:
            raise ValueError("command was not produced by this controller")
        channels = dict(command.channels)
        signature = self.signature_for_pattern(channels)
        self._record(signature, tick=tick, intensity=_intensity_bucket(channels))
        self._by_command[command.command_id] = signature.signature_id
        self._by_command.move_to_end(command.command_id)
        while len(self._by_command) > self._command_memory:
            self._by_command.popitem(last=False)
        return signature

    def signature_for_sequence(
        self,
        *,
        command_refs: tuple[str, ...],
        controller_seed_ref: str | None,
        tick: int | None = None,
    ) -> InterventionSignature:
        """Temporal family of several already-issued commands (§79)."""
        if not command_refs:
            raise ValueError("a temporal intervention requires issued commands")
        missing = [ref for ref in command_refs if ref not in self._by_command]
        if missing:
            raise KeyError("sequence references commands this registry never observed")
        steps = tuple(self._signatures[self._by_command[ref]] for ref in command_refs)
        signature = self._temporal(steps, controller_seed_ref=controller_seed_ref)
        if tick is not None:
            self._record(signature, tick=tick, intensity=None)
        return signature

    def _record(
        self, signature: InterventionSignature, *, tick: int, intensity: int | None
    ) -> None:
        if tick < 0:
            raise ValueError("tick must be non-negative")
        self._signatures[signature.signature_id] = signature
        if signature.temporal_pattern_ref is None:
            self._families.setdefault(signature.channel_refs, set()).add(signature.signature_id)
        stats = self._stats.get(signature.signature_id)
        if stats is None:
            stats = _SignatureStats(first_tick=int(tick), last_tick=int(tick))
            self._stats[signature.signature_id] = stats
        stats.attempts += 1
        stats.last_tick = max(stats.last_tick, int(tick))
        if intensity is not None:
            counts = list(stats.intensity_counts)
            counts[intensity] += 1
            stats.intensity_counts = tuple(counts)
        self._enforce_bound()

    def _enforce_bound(self) -> None:
        if len(self._signatures) <= self.capacity:
            return
        retained = sorted(
            self._stats.items(),
            key=lambda item: (-item[1].attempts, -item[1].last_tick, item[0]),
        )[: self.capacity]
        keep = {signature_id for signature_id, _ in retained}
        self._signatures = {k: v for k, v in self._signatures.items() if k in keep}
        self._stats = {k: v for k, v in self._stats.items() if k in keep}
        self._rebuild_families()
        for command_ref in [k for k, v in self._by_command.items() if v not in keep]:
            del self._by_command[command_ref]

    # -- read views -------------------------------------------------------
    def get(self, signature_id: str) -> InterventionSignature | None:
        return self._signatures.get(signature_id)

    def signature_of_command(self, command_ref: str) -> str | None:
        return self._by_command.get(command_ref)

    def attempt_support(self, signature_id: str) -> int:
        stats = self._stats.get(signature_id)
        return stats.attempts if stats is not None else 0

    def intensity_coverage(self, signature_id: str) -> float:
        """Fraction of coarse intensity variants of this family actually tried."""
        stats = self._stats.get(signature_id)
        if stats is None:
            return 0.0
        return sum(1 for count in stats.intensity_counts if count > 0) / _INTENSITY_BUCKETS

    def _rebuild_families(self) -> None:
        self._families = {}
        for signature in self._signatures.values():
            if signature.temporal_pattern_ref is None:
                self._families.setdefault(signature.channel_refs, set()).add(signature.signature_id)

    def family(self, channel_refs: tuple[str, ...]) -> tuple[str, ...]:
        """Single-step signatures driving exactly this opaque channel set."""
        return tuple(sorted(self._families.get(tuple(sorted(set(channel_refs))), ())))

    @property
    def items(self) -> tuple[InterventionSignature, ...]:
        return tuple(sorted(self._signatures.values(), key=lambda item: item.signature_id))

    @property
    def recurring_count(self) -> int:
        return sum(1 for stats in self._stats.values() if stats.attempts >= 2)

    # -- persistence ------------------------------------------------------
    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self.capacity,
            "signatures": [
                {
                    "signature_id": item.signature_id,
                    "channel_refs": list(item.channel_refs),
                    "temporal_pattern_ref": item.temporal_pattern_ref,
                    "attempts": self._stats[item.signature_id].attempts,
                    "first_tick": self._stats[item.signature_id].first_tick,
                    "last_tick": self._stats[item.signature_id].last_tick,
                    "intensity_counts": list(self._stats[item.signature_id].intensity_counts),
                }
                for item in self.items
            ],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None) -> "InterventionSignatureRegistry":
        if payload is None:
            return cls()
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported intervention signature checkpoint")
        obj = cls(capacity=int(payload.get("capacity", 512)))
        raw = payload.get("signatures", [])
        if not isinstance(raw, list) or len(raw) > obj.capacity:
            raise ValueError("invalid or unbounded intervention signatures")
        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid intervention signature entry")
            refs = tuple(str(value) for value in entry.get("channel_refs", []))
            temporal = entry.get("temporal_pattern_ref")
            signature = InterventionSignature(
                signature_id=str(entry["signature_id"]),
                channel_refs=refs,
                temporal_pattern_ref=str(temporal) if temporal is not None else None,
                dimensionality=len(refs),
            )
            counts = tuple(int(value) for value in entry.get("intensity_counts", []))
            if len(counts) != _INTENSITY_BUCKETS or any(value < 0 for value in counts):
                raise ValueError("invalid intervention intensity histogram")
            attempts = int(entry.get("attempts", 0))
            if attempts < 0:
                raise ValueError("invalid intervention attempt support")
            obj._signatures[signature.signature_id] = signature
            obj._stats[signature.signature_id] = _SignatureStats(
                attempts=attempts,
                first_tick=int(entry.get("first_tick", 0)),
                last_tick=int(entry.get("last_tick", 0)),
                intensity_counts=counts,
            )
        obj._rebuild_families()
        return obj


__all__ = [
    "InterventionSignature",
    "InterventionSignatureRegistry",
    "opaque_channel_ref",
]
