"""Epistemic investigation and evidence-revision phase."""
from __future__ import annotations

from dataclasses import dataclass

from ...host.acclimation import HostAcclimation
from ...host.drift import DriftObservation
from ...host.lifecycle import LifecycleSnapshot
from ...host.readings import ReadingProvider
from ...host.second_look import SecondLookSession
from ...host.readings import HostSampler
from ..cognition.attention import AttentionAllocation
from ..cognition.evidence import DissentRecord, EvidenceRevisionLedger
from ..cognition.host_self_model import LOW_HEALTH_INVESTIGATION_THRESHOLD, SelfModel
from ..foundation.narrative import NarrativeEntry, narrate_host
from .context import TickContext


@dataclass(frozen=True, slots=True)
class EpistemicServices:
    self_model: SelfModel
    evidence_ledger: EvidenceRevisionLedger
    acclimation: HostAcclimation
    reading_providers: tuple[ReadingProvider, ...]


@dataclass(frozen=True, slots=True)
class EpistemicStepResult:
    investigated_capability: str | None
    evidence_gathered: int
    dissent: DissentRecord | None
    evidence_counts: dict[str, int]
    dissent_by_capability: dict[str, DissentRecord]
    narrative: tuple[NarrativeEntry, ...]


class EpistemicDomain:
    """Perform bounded second-look investigation without affecting action."""

    def investigate(
        self,
        *,
        services: EpistemicServices,
        context: TickContext,
        snapshot: LifecycleSnapshot,
        drift_observations: dict[str, DriftObservation],
        capability_by_percept_name: dict[str, str],
        selected_ids: set[str],
        allocations: tuple[AttentionAllocation, ...],
        investigate_ticks: int,
    ) -> EpistemicStepResult:
        investigated_capability: str | None = None
        evidence_gathered = 0
        dissent: DissentRecord | None = None
        evidence_counts: dict[str, int] = {}
        dissent_by_capability: dict[str, DissentRecord] = {}

        if investigate_ticks > 0:
            investigation_candidates: list[str] = []
            for percept_name, observation in drift_observations.items():
                if observation.kind.value == "regime_shift":
                    capability_id = capability_by_percept_name.get(
                        percept_name
                    )
                    if (
                        capability_id
                        and capability_id in selected_ids
                        and snapshot.manifest.supports(capability_id)
                    ):
                        investigation_candidates.append(capability_id)
            for allocation in allocations:
                if allocation.name not in investigation_candidates:
                    investigation_candidates.append(allocation.name)

            for candidate in investigation_candidates:
                if (
                    candidate not in selected_ids
                    or not snapshot.manifest.supports(candidate)
                ):
                    continue
                if (
                    services.self_model.is_established(candidate)
                    and services.self_model.health(
                        candidate,
                        current_tick=max(0, context.symbiont_tick - 1),
                    )
                    < LOW_HEALTH_INVESTIGATION_THRESHOLD
                ):
                    continue
                session = SecondLookSession(
                    manifest=snapshot.manifest,
                    capability_id=candidate,
                    max_ticks=investigate_ticks,
                    sampler=HostSampler(services.reading_providers),
                )
                result = session.run_to_completion()
                investigated_capability = candidate
                evidence_gathered = len(result.readings)
                evidence_counts[candidate] = evidence_gathered
                for outcome in result.outcomes:
                    services.self_model.observe(
                        outcome=outcome,
                        tick=max(0, context.symbiont_tick - 1),
                    )
                revision = services.evidence_ledger.revise(
                    acclimation=services.acclimation,
                    capability_id=candidate,
                    evidence=result.readings,
                )
                dissent = revision.dissent
                if dissent is not None:
                    dissent_by_capability[candidate] = dissent
                break

        narrative = narrate_host(
            services.acclimation,
            allocations=allocations,
            evidence_counts=evidence_counts,
            dissent_by_capability=dissent_by_capability,
        )
        return EpistemicStepResult(
            investigated_capability=investigated_capability,
            evidence_gathered=evidence_gathered,
            dissent=dissent,
            evidence_counts=evidence_counts,
            dissent_by_capability=dissent_by_capability,
            narrative=narrative,
        )
