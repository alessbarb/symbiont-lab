from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..host.acclimation import HostAcclimation
from ..host.checkpoint import export_checkpoint, import_checkpoint, load_checkpoint_file, save_checkpoint_atomic
from ..host.contracts import DiscoveryPolicy
from ..host.discovery import HostDiscovery
from ..host.drift import DriftAwareBaseline, DriftObservation
from ..host.lifecycle import HostLifecycle, LifecycleSnapshot
from ..host.percepts import Percept, synthesize_percepts
from ..host.providers.stdlib import StandardLibraryProvider
from ..host.providers.stdlib_readings import StandardLibraryReadingProvider
from ..host.bootstrap import current_time_bucket
from ..host.rhythms import RhythmModel
from ..host.second_look import SecondLookSession
from .attention import AttentionAllocation, attend_to_host
from .evidence import DissentRecord, EvidenceRevisionLedger
from .narrative import NarrativeEntry, narrate_host


@dataclass(slots=True, frozen=True)
class RuntimeTickResult:
    """Everything one cycle of :class:`OrganismRuntime` did, in order —
    discover+observe, acclimate, perceive, track drift, attend, optionally
    investigate and revise, then explain. Nothing here is new state: every
    field is already something v0.30-v0.43 produce on their own; this is
    only the record of one pass through the cycle that now connects them.
    """

    tick: int
    snapshot: LifecycleSnapshot
    percepts: tuple[Percept, ...]
    drift_observations: dict[str, DriftObservation]
    allocations: tuple[AttentionAllocation, ...]
    investigated_capability: str | None
    evidence_gathered: int
    dissent: DissentRecord | None
    narrative: tuple[NarrativeEntry, ...]


class OrganismRuntime:
    """A single continuous cognitive cycle (roadmap v0.44, Milestone D #55):
    discover, observe, acclimate, perceive, track drift, allocate attention,
    investigate, revise beliefs, explain — replacing the one-shot CLI verbs
    v0.30-v0.43 shipped as separate, disconnected commands. :meth:`save`/
    :meth:`from_checkpoint`/:meth:`load_or_create` (v0.46) give it durable,
    crash/restart-safe state across process restarts.

    This class invents no new sensing, scoring or trust logic of its own —
    it only wires together primitives every earlier release already built
    and tested, into one repeatable cycle: :meth:`tick` runs the cycle once
    and returns a full, inspectable record of what happened; :meth:`run`
    repeats it. Resource and consent governance (how often the organism may
    run, within what budget) is deliberately out of scope here — that is
    v0.45's job. This release only proves the cycle itself closes and
    repeats correctly.

    Investigation is bounded and optional: each tick, at most the single
    highest-attention capability is looked at more closely via a
    :class:`~symbiont.host.second_look.SecondLookSession`, and only if it is
    still available in that tick's own manifest — the same authorization
    check v0.39 already enforces, not a new one.
    """

    def __init__(
        self,
        *,
        discovery_policy: DiscoveryPolicy | None = None,
        attention_budget: float = 1.0,
        investigate_ticks: int = 2,
        conflict_z: float = 2.0,
        min_samples: int = 5,
        acclimation: HostAcclimation | None = None,
        rhythm_model: RhythmModel | None = None,
        drift_baselines: dict[str, DriftAwareBaseline] | None = None,
        tick_count: int = 0,
    ) -> None:
        if attention_budget <= 0.0:
            raise ValueError("attention_budget must be positive")
        if investigate_ticks < 0:
            raise ValueError("investigate_ticks must be non-negative (0 disables investigation)")
        if tick_count < 0:
            raise ValueError("tick_count must be non-negative")

        self._lifecycle = HostLifecycle(
            discovery=HostDiscovery(providers=(StandardLibraryProvider(),), policy=discovery_policy),
            reading_providers=(StandardLibraryReadingProvider(),),
        )
        self._acclimation = acclimation if acclimation is not None else HostAcclimation(min_samples=min_samples)
        self._rhythm_model = rhythm_model if rhythm_model is not None else RhythmModel(min_samples=min_samples)
        self._drift_baselines: dict[str, DriftAwareBaseline] = (
            dict(drift_baselines) if drift_baselines is not None else {}
        )
        self._evidence_ledger = EvidenceRevisionLedger(conflict_z=conflict_z)
        self._attention_budget = attention_budget
        self._investigate_ticks = investigate_ticks
        self._tick_count = tick_count

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def acclimation(self) -> HostAcclimation:
        return self._acclimation

    @property
    def rhythm_model(self) -> RhythmModel:
        return self._rhythm_model

    def tick(self) -> RuntimeTickResult:
        snapshot = self._lifecycle.tick()
        self._acclimation.observe(snapshot.readings)

        percepts = synthesize_percepts(snapshot.readings)
        self._rhythm_model.observe(percepts, time_bucket=current_time_bucket())

        drift_observations: dict[str, DriftObservation] = {}
        for percept in percepts:
            if percept.value is None:
                continue
            baseline = self._drift_baselines.get(percept.name)
            if baseline is None:
                baseline = DriftAwareBaseline()
                self._drift_baselines[percept.name] = baseline
            drift_observations[percept.name] = baseline.observe(percept.value)

        allocations = attend_to_host(self._acclimation, budget=self._attention_budget)

        investigated_capability: str | None = None
        evidence_gathered = 0
        dissent: DissentRecord | None = None
        evidence_counts: dict[str, int] = {}
        dissent_by_capability: dict[str, DissentRecord] = {}

        if allocations and self._investigate_ticks > 0:
            candidate = allocations[0].name
            if snapshot.manifest.supports(candidate):
                session = SecondLookSession(
                    manifest=snapshot.manifest, capability_id=candidate, max_ticks=self._investigate_ticks
                )
                result = session.run_to_completion()
                investigated_capability = candidate
                evidence_gathered = len(result.readings)
                evidence_counts[candidate] = evidence_gathered
                revision = self._evidence_ledger.revise(
                    acclimation=self._acclimation, capability_id=candidate, evidence=result.readings
                )
                dissent = revision.dissent
                if dissent is not None:
                    dissent_by_capability[candidate] = dissent

        narrative = narrate_host(
            self._acclimation,
            allocations=allocations,
            evidence_counts=evidence_counts,
            dissent_by_capability=dissent_by_capability,
        )

        self._tick_count += 1
        return RuntimeTickResult(
            tick=self._tick_count,
            snapshot=snapshot,
            percepts=percepts,
            drift_observations=drift_observations,
            allocations=allocations,
            investigated_capability=investigated_capability,
            evidence_gathered=evidence_gathered,
            dissent=dissent,
            narrative=narrative,
        )

    def run(self, ticks: int) -> tuple[RuntimeTickResult, ...]:
        if ticks < 1:
            raise ValueError("ticks must be at least 1")
        return tuple(self.tick() for _ in range(ticks))

    def checkpoint(self) -> dict[str, Any]:
        """Export this runtime's current safe abstract state, including how
        many ticks it has run, via v0.37/v0.46's checkpoint format."""
        return export_checkpoint(
            acclimation=self._acclimation,
            rhythm_model=self._rhythm_model,
            drift_baselines=self._drift_baselines,
            saved_at_tick=self._tick_count,
        )

    def save(self, path: str | Path) -> None:
        """Atomically write this runtime's checkpoint to disk (roadmap
        v0.46). See :func:`~symbiont.host.checkpoint.save_checkpoint_atomic`
        for the atomicity guarantee."""
        save_checkpoint_atomic(self.checkpoint(), path)

    @classmethod
    def from_checkpoint(
        cls,
        payload: dict[str, Any],
        *,
        discovery_policy: DiscoveryPolicy | None = None,
        attention_budget: float = 1.0,
        investigate_ticks: int = 2,
        conflict_z: float = 2.0,
        min_samples: int = 5,
    ) -> "OrganismRuntime":
        """Restore a runtime's beliefs from a checkpoint payload and resume
        ticking from where it left off (roadmap v0.46 — crash/restart
        recovery). Only the safe abstract state a checkpoint already
        carries is restored; there is no raw telemetry to recover, by
        construction. A payload from an older schema version is migrated
        forward automatically (see
        :func:`~symbiont.host.checkpoint.import_checkpoint`).
        """
        acclimation, rhythm_model, drift_baselines = import_checkpoint(
            payload,
            acclimation=HostAcclimation(min_samples=min_samples),
            rhythm_model=RhythmModel(min_samples=min_samples),
        )
        saved_at_tick = payload.get("saved_at_tick") or 0
        return cls(
            discovery_policy=discovery_policy,
            attention_budget=attention_budget,
            investigate_ticks=investigate_ticks,
            conflict_z=conflict_z,
            min_samples=min_samples,
            acclimation=acclimation,
            rhythm_model=rhythm_model,
            drift_baselines=drift_baselines,
            tick_count=saved_at_tick,
        )

    @classmethod
    def load_or_create(
        cls,
        path: str | Path,
        **kwargs: Any,
    ) -> "OrganismRuntime":
        """Restore from ``path`` if a checkpoint exists there, otherwise
        start a fresh runtime — the crash/restart recovery entry point
        (roadmap v0.46): a first run and a resumed run call the same
        function and get the right behavior either way."""
        payload = load_checkpoint_file(path)
        if payload is None:
            return cls(**kwargs)
        return cls.from_checkpoint(payload, **kwargs)
