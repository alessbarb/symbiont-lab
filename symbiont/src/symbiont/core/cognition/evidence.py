from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Iterable, Mapping

from ...host.acclimation import CapabilityBaseline, HostAcclimation
from ...host.readings import SensorReading


@dataclass(slots=True, frozen=True)
class DissentRecord:
    """One current-run instance where new evidence conflicted with a baseline."""

    capability_id: str
    prior_mean: float
    prior_stdev: float
    evidence_mean: float
    z_score: float


@dataclass(slots=True, frozen=True)
class EvidenceRevisionResult:
    capability_id: str
    baseline: CapabilityBaseline | None
    dissent: DissentRecord | None


from ..foundation.limits import OrganismLimits

_DEFAULT_LIMITS = OrganismLimits()


class EvidenceRevisionLedger:
    """Revise beliefs while preserving bounded contradiction memory.

    Detailed numeric dissent records are retained only for the current run;
    persisting their means would weaken the checkpoint's privacy boundary.
    Across restarts the ledger persists only a bounded per-capability count
    saying that a belief has previously been contested. That is sufficient
    to preserve the epistemic fact of contradiction without turning the
    checkpoint into a history of evidence values.
    """

    def __init__(
        self,
        *,
        conflict_z: float = 2.0,
        max_dissent: int = _DEFAULT_LIMITS.max_dissent,
    ) -> None:
        if conflict_z <= 0.0:
            raise ValueError("conflict_z must be positive")
        if max_dissent < 1:
            raise ValueError("max_dissent must be at least 1")
        self._conflict_z = conflict_z
        self._max_dissent = max_dissent
        self._dissent: Deque[DissentRecord] = deque(maxlen=max_dissent)
        self._conflict_counts: dict[str, int] = {}

    @property
    def dissent_history(self) -> tuple[DissentRecord, ...]:
        return tuple(self._dissent)

    @property
    def conflict_counts(self) -> Mapping[str, int]:
        return dict(self._conflict_counts)

    def _remember_conflict(self, capability_id: str) -> None:
        if (
            capability_id not in self._conflict_counts
            and len(self._conflict_counts) >= self._max_dissent
        ):
            oldest = next(iter(self._conflict_counts))
            del self._conflict_counts[oldest]
        self._conflict_counts[capability_id] = self._conflict_counts.get(capability_id, 0) + 1

    def export_checkpoint(self) -> dict[str, Any]:
        return {
            "conflict_counts": [
                {"capability_id": capability_id, "count": count}
                for capability_id, count in self._conflict_counts.items()
            ]
        }

    @classmethod
    def restore_checkpoint(
        cls,
        payload: Mapping[str, object] | None,
        *,
        conflict_z: float = 2.0,
        max_dissent: int = 256,
        allowed_capability_ids: Iterable[str] | None = None,
    ) -> "EvidenceRevisionLedger":
        ledger = cls(conflict_z=conflict_z, max_dissent=max_dissent)
        if not payload:
            return ledger
        if not isinstance(payload, Mapping):
            raise ValueError("evidence ledger checkpoint must be an object")
        raw_counts = payload.get("conflict_counts", [])
        if not isinstance(raw_counts, list):
            raise ValueError("evidence ledger conflict_counts must be a list")
        allowed = set(allowed_capability_ids) if allowed_capability_ids is not None else None
        for entry in raw_counts[:max_dissent]:
            if not isinstance(entry, Mapping):
                raise ValueError("evidence ledger conflict entry must be an object")
            capability_id = entry.get("capability_id")
            count = entry.get("count")
            if not isinstance(capability_id, str) or not capability_id:
                raise ValueError("evidence ledger capability_id must be a non-empty string")
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise ValueError("evidence ledger conflict count must be a positive integer")
            if allowed is None or capability_id in allowed:
                ledger._conflict_counts[capability_id] = count
        return ledger

    def revise(
        self,
        *,
        acclimation: HostAcclimation,
        capability_id: str,
        evidence: Iterable[SensorReading],
    ) -> EvidenceRevisionResult:
        evidence = tuple(evidence)
        values = [reading.value for reading in evidence if reading.value is not None]
        if not values:
            return EvidenceRevisionResult(
                capability_id=capability_id,
                baseline=acclimation.baseline(capability_id),
                dissent=None,
            )

        prior = acclimation.baseline(capability_id)
        dissent: DissentRecord | None = None
        if prior is not None and prior.stdev > 0.0:
            evidence_mean = sum(values) / len(values)
            z_score = (evidence_mean - prior.mean) / prior.stdev
            if abs(z_score) >= self._conflict_z:
                dissent = DissentRecord(
                    capability_id=capability_id,
                    prior_mean=prior.mean,
                    prior_stdev=prior.stdev,
                    evidence_mean=evidence_mean,
                    z_score=z_score,
                )
                self._dissent.append(dissent)
                self._remember_conflict(capability_id)

        acclimation.observe(evidence)
        return EvidenceRevisionResult(
            capability_id=capability_id,
            baseline=acclimation.baseline(capability_id),
            dissent=dissent,
        )
