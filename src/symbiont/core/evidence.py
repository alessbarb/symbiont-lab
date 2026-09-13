from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable

from ..host.acclimation import CapabilityBaseline, HostAcclimation
from ..host.readings import SensorReading


@dataclass(slots=True, frozen=True)
class DissentRecord:
    """One instance where a batch of new evidence conflicted with the
    existing baseline for a capability, kept rather than silently smoothed
    away (roadmap v0.40)."""

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


class EvidenceRevisionLedger:
    """Revise an existing acclimation baseline from a batch of new evidence
    (e.g. a v0.39 second look), while keeping a bounded, inspectable record
    of every batch that conflicted with the belief it revised (roadmap
    v0.40).

    Revision always happens — a conflicting batch is not held back or
    discarded, since the organism's belief should still move toward what it
    actually observed (the same principle v0.36's ``DriftAwareBaseline``
    holds for continuous streaming values; this is the discrete-batch
    counterpart for a deliberate second look). What "preserving
    contradiction and dissent" means here is narrower and load-bearing: the
    *fact that a conflict occurred* is recorded permanently within the
    bounded ledger, not smoothed away as if the new evidence had agreed all
    along. A future consumer (v0.41's narrative) can therefore say "this
    belief was revised, and it was contested when it happened" rather than
    presenting a falsely-confident history.

    Purely descriptive throughout — a ``DissentRecord`` is a statistical
    disagreement, never a threat or classification signal (same discipline
    as ``docs/adr/ADR-0003-attention-is-not-classification.md``).
    """

    def __init__(self, *, conflict_z: float = 2.0, max_dissent: int = 256) -> None:
        if conflict_z <= 0.0:
            raise ValueError("conflict_z must be positive")
        if max_dissent < 1:
            raise ValueError("max_dissent must be at least 1")
        self._conflict_z = conflict_z
        self._dissent: Deque[DissentRecord] = deque(maxlen=max_dissent)

    @property
    def dissent_history(self) -> tuple[DissentRecord, ...]:
        return tuple(self._dissent)

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
                capability_id=capability_id, baseline=acclimation.baseline(capability_id), dissent=None
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

        acclimation.observe(evidence)
        return EvidenceRevisionResult(
            capability_id=capability_id, baseline=acclimation.baseline(capability_id), dissent=dissent
        )
