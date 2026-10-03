"""Embodiment-local execution authority for learned motor competences."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Mapping

from ..capacity import CapacityPressure
from .competence import CompetenceMaturity, MotorCompetence


class BindingStatus(StrEnum):
    """Cross-Domain Revision Coherence v1 §3.2."""

    VALID = "valid"
    STALE = "stale"
    INVALIDATED = "invalidated"


class StalenessReason(StrEnum):
    SURFACE_NOT_CURRENT = "surface_not_current"
    EMBODIMENT_NOT_CURRENT = "embodiment_not_current"
    CONTROLLER_UNAVAILABLE = "controller_unavailable"
    EVIDENCE_AGED = "evidence_aged"


class InvalidationReason(StrEnum):
    CAUSAL_RELATION_REVISED = "causal_relation_revised"
    EFFECT_SUPERSEDED = "effect_superseded"
    EVIDENCE_CONTRADICTED = "evidence_contradicted"


@dataclass(frozen=True, slots=True)
class CompetenceExecutionBinding:
    """Current-body evidence that one general competence can execute here.

    ``reliability`` is historical; current executability is ``status``.
    ``last_evidence_tick`` is the last confirmation, independent of
    ``status_changed_tick`` (an invalidation may follow the last confirmation).
    """

    competence_id: str
    surface_fingerprint: str
    effect_id: str
    evidence_refs: tuple[str, ...]
    reliability: float
    controllability: float
    last_evidence_tick: int
    status: BindingStatus = BindingStatus.VALID
    status_reason: StalenessReason | InvalidationReason | None = None
    valid_from_tick: int = 0
    status_changed_tick: int = 0
    revision: int = 0

    def __post_init__(self) -> None:
        if not self.competence_id or not self.surface_fingerprint or not self.effect_id:
            raise ValueError("execution binding identifiers must be non-empty")
        if not self.evidence_refs:
            raise ValueError("execution binding requires current factual evidence")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("binding reliability must be in [0,1]")
        if not 0.0 <= self.controllability <= 1.0:
            raise ValueError("binding controllability must be in [0,1]")
        if self.last_evidence_tick < 0:
            raise ValueError("last_evidence_tick must be non-negative")
        if self.status is BindingStatus.VALID and self.status_reason is not None:
            raise ValueError("a valid binding carries no status reason")
        if self.status is BindingStatus.STALE and not isinstance(
            self.status_reason, StalenessReason
        ):
            raise ValueError("a stale binding needs a staleness reason")
        if self.status is BindingStatus.INVALIDATED and not isinstance(
            self.status_reason, InvalidationReason
        ):
            raise ValueError("an invalidated binding needs an invalidation reason")
        if min(self.valid_from_tick, self.status_changed_tick, self.revision) < 0:
            raise ValueError("binding lifecycle ticks and revision must be non-negative")


@dataclass(frozen=True, slots=True)
class BindingTransition:
    """One lifecycle change, for the caller to trace (previous state lives here only)."""

    competence_id: str
    previous_status: BindingStatus
    previous_revision: int
    binding: CompetenceExecutionBinding
    cause_refs: tuple[str, ...] = ()


class CompetenceExecutionBindingRegistry:
    """Bounded current-embodiment authority, separate from competence knowledge."""

    SCHEMA_VERSION = 2

    def __init__(self, *, capacity: int = 512) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self._items: dict[str, CompetenceExecutionBinding] = {}
        # Wave 0 measurement only (Cross-Domain Revision Coherence v1 §2.1).
        self.pressure = CapacityPressure(self.capacity)
        # Lifecycle changes not yet traced by the owner of provenance.
        self._transitions: list[BindingTransition] = []
        # Executions since each binding's last confirmation that did not
        # confirm it (binding evidence for §3.9 decision 1).
        self._unconfirmed: dict[str, dict[str, object]] = {}
        # Binding Degradation v1 §2: per-binding revision history (reference
        # and later executions); cleared when a new revision starts.
        self._history: dict[str, dict[str, Any]] = {}

    def bind_from_evidence(
        self,
        *,
        competence_id: str,
        surface_fingerprint: str,
        effect_id: str,
        evidence_refs: tuple[str, ...],
        reliability: float,
        controllability: float,
        tick: int,
    ) -> CompetenceExecutionBinding:
        existing = self._items.get(competence_id)
        refs = tuple(
            dict.fromkeys(
                (existing.evidence_refs if existing is not None else ()) + tuple(evidence_refs)
            )
        )
        revalidated = existing is not None and existing.status is not BindingStatus.VALID
        binding = CompetenceExecutionBinding(
            competence_id=competence_id,
            surface_fingerprint=surface_fingerprint,
            effect_id=effect_id,
            evidence_refs=refs,
            reliability=max(0.0, min(1.0, float(reliability))),
            controllability=max(0.0, min(1.0, float(controllability))),
            last_evidence_tick=int(tick),
            valid_from_tick=(
                existing.valid_from_tick if existing is not None and not revalidated else int(tick)
            ),
            status_changed_tick=(
                int(tick) if existing is None or revalidated else existing.status_changed_tick
            ),
            revision=(existing.revision + int(revalidated)) if existing is not None else 0,
        )
        self._items[competence_id] = binding
        self._unconfirmed.pop(competence_id, None)  # confirmed
        if revalidated:
            self._transitions.append(
                BindingTransition(competence_id, existing.status, existing.revision, binding)
            )
        if existing is None:
            self.pressure.note_admitted(competence_id)
        self._enforce_bound()
        return binding

    def _enforce_bound(self) -> None:
        if len(self._items) <= self.capacity:
            return
        retained = sorted(
            self._items.values(),
            key=lambda item: (
                -item.last_evidence_tick,
                -item.controllability,
                -item.reliability,
                item.competence_id,
            ),
        )[: self.capacity]
        before = tuple(self._items)
        self._items = {item.competence_id: item for item in retained}
        self.pressure.note_evicted(ref for ref in before if ref not in self._items)

    def get(self, competence_id: str) -> CompetenceExecutionBinding | None:
        return self._items.get(competence_id)

    def set_status(
        self,
        competence_id: str,
        status: BindingStatus,
        reason: StalenessReason | InvalidationReason | None,
        *,
        tick: int,
        cause_refs: tuple[str, ...] = (),
    ) -> BindingTransition | None:
        """Apply a lifecycle change decided by binding evidence; None if unchanged.

        Leaving INVALIDATED requires new evidence (``bind_from_evidence``).
        """
        binding = self._items.get(competence_id)
        if binding is None or (binding.status, binding.status_reason) == (status, reason):
            return None
        if binding.status is BindingStatus.INVALIDATED:
            return None
        changed = replace(
            binding,
            status=status,
            status_reason=reason,
            status_changed_tick=int(tick),
            valid_from_tick=int(tick) if status is BindingStatus.VALID else binding.valid_from_tick,
            revision=binding.revision + 1,
        )
        self._items[competence_id] = changed
        transition = BindingTransition(
            competence_id, binding.status, binding.revision, changed, tuple(cause_refs)
        )
        self._transitions.append(transition)
        return transition

    def note_unconfirmed_execution(
        self, competence_id: str, *, windows: int, commitment_id: str
    ) -> tuple[int, float, tuple[str, ...]]:
        """Record one execution that did not confirm the binding.

        Returns (executions, mean windows, recent commitment ids) since the
        binding's last confirmation.
        """
        entry = self._unconfirmed.setdefault(
            competence_id, {"executions": 0, "windows": 0, "commitments": []}
        )
        entry["executions"] = int(entry["executions"]) + 1
        entry["windows"] = int(entry["windows"]) + max(1, int(windows))
        commitments = [*list(entry["commitments"]), commitment_id][-8:]
        entry["commitments"] = commitments
        executions = int(entry["executions"])
        return executions, int(entry["windows"]) / executions, tuple(commitments)

    def note_execution(
        self, competence_id: str, *, matched: bool, commitment_id: str, reference_size: int
    ) -> dict[str, Any] | None:
        """Binding Degradation v1 §2: count one execution of a VALID binding.

        The first ``reference_size`` executions of the current revision form
        the frozen reference; later ones are degradation evidence. Each
        commitment counts once.
        """
        binding = self._items.get(competence_id)
        if binding is None or binding.status is not BindingStatus.VALID:
            return None
        entry = self._history.get(competence_id)
        if entry is None or entry["revision"] != binding.revision:
            entry = {
                "revision": binding.revision,
                "ref_n": 0,
                "ref_k": 0,
                "new_n": 0,
                "new_k": 0,
                "commitments": [],
            }
            self._history[competence_id] = entry
        counted = list(entry["commitments"])
        if commitment_id in counted:
            return entry
        if int(entry["ref_n"]) < reference_size:
            entry["ref_n"] = int(entry["ref_n"]) + 1
            entry["ref_k"] = int(entry["ref_k"]) + int(matched)
        else:
            entry["new_n"] = int(entry["new_n"]) + 1
            entry["new_k"] = int(entry["new_k"]) + int(matched)
        entry["commitments"] = [*counted, commitment_id][-64:]
        return entry

    def drain_transitions(self) -> tuple[BindingTransition, ...]:
        drained = tuple(self._transitions)
        self._transitions.clear()
        return drained

    def is_executable(
        self,
        competence: MotorCompetence,
        *,
        surface_fingerprint: str | None,
    ) -> bool:
        if surface_fingerprint is None:
            return False
        binding = self._items.get(competence.competence_id)
        return (
            binding is not None
            and binding.status is BindingStatus.VALID
            and binding.surface_fingerprint == surface_fingerprint
            and bool(binding.evidence_refs)
            and competence.maturity in {CompetenceMaturity.ESTABLISHED, CompetenceMaturity.ROBUST}
        )

    def invalid_for_surface(self, surface_fingerprint: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                competence_id
                for competence_id, binding in self._items.items()
                if binding.surface_fingerprint != surface_fingerprint
            )
        )

    @property
    def items(self) -> tuple[CompetenceExecutionBinding, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.competence_id))

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self.capacity,
            "items": [
                {
                    "competence_id": item.competence_id,
                    "surface_fingerprint": item.surface_fingerprint,
                    "effect_id": item.effect_id,
                    "evidence_refs": list(item.evidence_refs),
                    "reliability": item.reliability,
                    "controllability": item.controllability,
                    "last_evidence_tick": item.last_evidence_tick,
                    "status": item.status.value,
                    "status_reason": (
                        item.status_reason.value if item.status_reason is not None else None
                    ),
                    "valid_from_tick": item.valid_from_tick,
                    "status_changed_tick": item.status_changed_tick,
                    "revision": item.revision,
                }
                for item in self.items
            ],
            "capacity_pressure": self.pressure.checkpoint(),
            "revision_history": {
                competence_id: dict(entry) for competence_id, entry in sorted(self._history.items())
            },
            "unconfirmed_executions": {
                competence_id: dict(entry)
                for competence_id, entry in sorted(self._unconfirmed.items())
            },
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, Any] | None,
    ) -> "CompetenceExecutionBindingRegistry":
        if payload is None:
            return cls()
        version = payload.get("schema_version")
        if version not in (1, cls.SCHEMA_VERSION):
            raise ValueError("unsupported competence execution binding checkpoint")
        obj = cls(capacity=int(payload.get("capacity", 512)))
        raw = payload.get("items", [])
        if not isinstance(raw, list) or len(raw) > obj.capacity:
            raise ValueError("invalid or unbounded competence execution bindings")
        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid competence execution binding")
            binding = CompetenceExecutionBinding(
                competence_id=str(entry["competence_id"]),
                surface_fingerprint=str(entry["surface_fingerprint"]),
                effect_id=str(entry["effect_id"]),
                evidence_refs=tuple(str(value) for value in entry.get("evidence_refs", [])),
                reliability=float(entry.get("reliability", 0.0)),
                controllability=float(entry.get("controllability", 0.0)),
                last_evidence_tick=int(entry.get("last_evidence_tick", 0)),
                # v1 bindings had no lifecycle: they migrate as VALID, revision 0.
                status=BindingStatus(entry.get("status", BindingStatus.VALID.value)),
                status_reason=_reason(entry.get("status_reason")),
                valid_from_tick=int(entry.get("valid_from_tick", 0)),
                status_changed_tick=int(entry.get("status_changed_tick", 0)),
                revision=int(entry.get("revision", 0)),
            )
            obj._items[binding.competence_id] = binding
        obj.pressure = CapacityPressure.restore(
            payload.get("capacity_pressure"), capacity=obj.capacity
        )
        for competence_id, entry in dict(payload.get("revision_history", {})).items():
            if competence_id in obj._items:
                obj._history[str(competence_id)] = {
                    "revision": int(entry["revision"]),
                    "ref_n": int(entry["ref_n"]),
                    "ref_k": int(entry["ref_k"]),
                    "new_n": int(entry["new_n"]),
                    "new_k": int(entry["new_k"]),
                    "commitments": [str(ref) for ref in entry.get("commitments", [])][-64:],
                }
        for competence_id, entry in dict(payload.get("unconfirmed_executions", {})).items():
            if competence_id in obj._items:
                obj._unconfirmed[str(competence_id)] = {
                    "executions": int(entry["executions"]),
                    "windows": int(entry["windows"]),
                    "commitments": [str(ref) for ref in entry.get("commitments", [])][-8:],
                }
        return obj


def _reason(raw: object) -> StalenessReason | InvalidationReason | None:
    if raw is None:
        return None
    value = str(raw)
    if value in StalenessReason._value2member_map_:
        return StalenessReason(value)
    return InvalidationReason(value)


__all__ = [
    "BindingStatus",
    "BindingTransition",
    "CompetenceExecutionBinding",
    "CompetenceExecutionBindingRegistry",
    "InvalidationReason",
    "StalenessReason",
]
