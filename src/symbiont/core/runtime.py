from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
from typing import Any

from ..host.acclimation import HostAcclimation
from ..host.adaptive import AdaptiveSenseModel, SamplingPlan
from ..host.checkpoint import export_checkpoint, import_checkpoint, load_checkpoint_file, save_checkpoint_atomic
from ..host.contracts import DiscoveryPolicy, DiscoveryProvider, HostManifest
from ..host.discovery import HostDiscovery
from ..host.drift import DriftAwareBaseline, DriftObservation
from ..host.lifecycle import HostLifecycle, LifecycleSnapshot
from ..host.percepts import DEFAULT_PERCEPT_NAMES, Percept, synthesize_percepts
from ..host.providers.stdlib import StandardLibraryProvider
from ..host.providers.stdlib_readings import StandardLibraryReadingProvider
from ..host.readings import HostSampler, ReadingProvider
from ..host.bootstrap import current_time_bucket
from ..host.rhythms import RhythmModel
from ..host.second_look import SecondLookSession
from .attention import AttentionAllocation, attend_to_host
from .evidence import DissentRecord, EvidenceRevisionLedger
from .narrative import NarrativeEntry, narrate_host
from .selfmodel import LOW_HEALTH_INVESTIGATION_THRESHOLD, SelfModel
from ..cognition.checkpoint import export_genome_checkpoint, restore_genome_checkpoint
from ..cognition.genome import Genome
from ..cognition.limits import KernelLimits


def _parse_running_version(version_string: str) -> tuple[int, int, int]:
    parts = version_string.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (major, minor, patch)


@dataclass(slots=True, frozen=True)
class RuntimeTickResult:
    tick: int
    snapshot: LifecycleSnapshot
    percepts: tuple[Percept, ...]
    drift_observations: dict[str, DriftObservation]
    allocations: tuple[AttentionAllocation, ...]
    investigated_capability: str | None
    evidence_gathered: int
    dissent: DissentRecord | None
    narrative: tuple[NarrativeEntry, ...]
    sampling_plan: SamplingPlan | None = None


class OrganismRuntime:
    """Continuous cognitive cycle over safe local perceptions.

    In developmental mode discovery remains broad inside the provider's fixed safety
    boundary, while *sampling* becomes selective. The organism routinely exercises
    senses it has learned to value and spends a small rotating budget on unknown or
    dormant surfaces so early developmental choices never become irreversible.
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
        discover_senses: bool = False,
        bootstrap_semantic_senses: bool = True,
        adaptive_senses: AdaptiveSenseModel | None = None,
        self_model: SelfModel | None = None,
        genome: Genome | None = None,
        kernel_limits: KernelLimits | None = None,
    ) -> None:
        if attention_budget <= 0.0:
            raise ValueError("attention_budget must be positive")
        if investigate_ticks < 0:
            raise ValueError("investigate_ticks must be non-negative (0 disables investigation)")
        if tick_count < 0:
            raise ValueError("tick_count must be non-negative")

        discovery_providers: list[DiscoveryProvider] = []
        reading_providers: list[ReadingProvider] = []
        self._bootstrap_semantic_senses = bootstrap_semantic_senses
        self._adaptive_senses = adaptive_senses if adaptive_senses is not None else AdaptiveSenseModel()
        self._discover_senses = discover_senses

        if bootstrap_semantic_senses:
            discovery_providers.append(StandardLibraryProvider())
            reading_providers.append(StandardLibraryReadingProvider())

        if discover_senses and platform.system() == "Linux":
            from ..host.providers.linux_surfaces import LinuxSurfaceProvider

            linux_provider = LinuxSurfaceProvider()
            discovery_providers.append(linux_provider)
            reading_providers.append(linux_provider)

        self._reading_providers = tuple(reading_providers)
        self._lifecycle = HostLifecycle(
            discovery=HostDiscovery(providers=tuple(discovery_providers), policy=discovery_policy),
            reading_providers=self._reading_providers,
        )
        self._acclimation = acclimation if acclimation is not None else HostAcclimation(min_samples=min_samples)
        self._rhythm_model = rhythm_model if rhythm_model is not None else RhythmModel(min_samples=min_samples)
        self._drift_baselines = dict(drift_baselines) if drift_baselines is not None else {}
        self._evidence_ledger = EvidenceRevisionLedger(conflict_z=conflict_z)
        self._attention_budget = attention_budget
        self._investigate_ticks = investigate_ticks
        self._tick_count = tick_count
        self._self_model = self_model if self_model is not None else SelfModel()
        self._genome = genome
        self._kernel_limits = kernel_limits if kernel_limits is not None else KernelLimits()

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def acclimation(self) -> HostAcclimation:
        return self._acclimation

    @property
    def rhythm_model(self) -> RhythmModel:
        return self._rhythm_model

    @property
    def adaptive_senses(self) -> AdaptiveSenseModel:
        return self._adaptive_senses

    @property
    def self_model(self) -> SelfModel:
        return self._self_model

    @property
    def genome(self) -> Genome | None:
        return self._genome

    def _sampling_selector(self, manifest: HostManifest) -> tuple[str, ...] | None:
        if not self._discover_senses:
            return None
        plan = self._adaptive_senses.sampling_plan(
            capability.capability_id for capability in manifest.available
        )
        requested = set(plan.requested_ids)
        if self._bootstrap_semantic_senses:
            # Explicit semantic bootstrap remains a compatibility opt-in. If the
            # caller chose it, its historical senses stay sampled independently of
            # the developmental repertoire.
            requested.update(
                capability_id
                for capability_id in DEFAULT_PERCEPT_NAMES
                if manifest.supports(capability_id)
            )
        return tuple(sorted(requested))

    def tick(self) -> RuntimeTickResult:
        snapshot = self._lifecycle.tick(
            sampling_selector=self._sampling_selector if self._discover_senses else None
        )
        sampling_plan = self._adaptive_senses.last_sampling_plan if self._discover_senses else None

        # Only actually sampled readings enter sensory development. Unsampled
        # dormant surfaces remain known through discovery but contribute no fake
        # zero/unavailable observations.
        self._adaptive_senses.observe(snapshot.readings)
        for outcome in snapshot.sampling_outcomes:
            self._self_model.observe(outcome=outcome, tick=self._tick_count)
        for evicted_name in self._adaptive_senses.drain_evicted_percept_names():
            # A sense the developmental layer retired to stay bounded must
            # not leave its percept-keyed drift baseline behind forever —
            # otherwise the drift-baseline dict grows without bound even
            # while sensory state itself stays capped (roadmap safety
            # finding B06).
            self._drift_baselines.pop(evicted_name, None)
        learned_names = self._adaptive_senses.percept_names() if self._discover_senses else {}

        percept_names: dict[str, str] = {}
        if self._bootstrap_semantic_senses:
            percept_names.update(DEFAULT_PERCEPT_NAMES)
        percept_names.update(learned_names)

        selected_ids = set(percept_names)
        cognitive_readings = tuple(
            reading for reading in snapshot.readings if reading.capability_id in selected_ids
        )

        percepts = synthesize_percepts(cognitive_readings, percept_names=percept_names)
        self._acclimation.observe(cognitive_readings)
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

        # ``selected_ids`` reflects every capability cognition has ever
        # learned to value, including one no longer present in this tick's
        # real manifest. Restricting to what the manifest actually offers
        # right now (roadmap safety finding B03) stops a capability the
        # organism merely remembers from permanently consuming the entire
        # attention budget once it is truly gone.
        currently_available_ids = {capability.capability_id for capability in snapshot.manifest.available}
        eligible_ids = selected_ids & currently_available_ids
        self._self_model.reconcile(eligible_ids)
        rank_costs = {
            capability_id: self._self_model.relative_cost(capability_id, reference_ids=eligible_ids)
            for capability_id in eligible_ids
        }
        allocations = attend_to_host(
            self._acclimation,
            budget=self._attention_budget,
            eligible_capability_ids=eligible_ids,
            rank_costs=rank_costs,
        )
        investigated_capability: str | None = None
        evidence_gathered = 0
        dissent: DissentRecord | None = None
        evidence_counts: dict[str, int] = {}
        dissent_by_capability: dict[str, DissentRecord] = {}

        if self._investigate_ticks > 0:
            # Try allocations in ranked order; one candidate transiently
            # unsupported by this tick's manifest must not forfeit
            # investigation entirely for every other candidate (finding A05).
            for allocation in allocations:
                candidate = allocation.name
                if candidate not in selected_ids or not snapshot.manifest.supports(candidate):
                    continue
                if (
                    self._self_model.is_established(candidate)
                    and self._self_model.health(candidate, current_tick=self._tick_count)
                    < LOW_HEALTH_INVESTIGATION_THRESHOLD
                ):
                    # Chronically broken, established sense: don't spend the
                    # bounded investigation budget on it (roadmap v0.53).
                    continue
                session = SecondLookSession(
                    manifest=snapshot.manifest,
                    capability_id=candidate,
                    max_ticks=self._investigate_ticks,
                    sampler=HostSampler(self._reading_providers),
                )
                result = session.run_to_completion()
                investigated_capability = candidate
                evidence_gathered = len(result.readings)
                evidence_counts[candidate] = evidence_gathered
                for outcome in result.outcomes:
                    self._self_model.observe(outcome=outcome, tick=self._tick_count)
                revision = self._evidence_ledger.revise(
                    acclimation=self._acclimation,
                    capability_id=candidate,
                    evidence=result.readings,
                )
                dissent = revision.dissent
                if dissent is not None:
                    dissent_by_capability[candidate] = dissent
                break

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
            sampling_plan=sampling_plan,
        )

    def run(self, ticks: int) -> tuple[RuntimeTickResult, ...]:
        if ticks < 1:
            raise ValueError("ticks must be at least 1")
        return tuple(self.tick() for _ in range(ticks))

    def checkpoint(self) -> dict[str, Any]:
        payload = export_checkpoint(
            acclimation=self._acclimation,
            rhythm_model=self._rhythm_model,
            drift_baselines=self._drift_baselines,
            saved_at_tick=self._tick_count,
        )
        payload["sensory_development"] = self._adaptive_senses.export()
        payload["self_model"] = self._self_model.export()
        payload["genome"] = export_genome_checkpoint(self._genome)
        return payload

    def save(self, path: str | Path) -> None:
        save_checkpoint_atomic(self.checkpoint(), path)

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any], **kwargs: Any) -> "OrganismRuntime":
        min_samples = int(kwargs.get("min_samples", 5))
        acclimation, rhythm_model, drift_baselines = import_checkpoint(
            payload,
            acclimation=HostAcclimation(min_samples=min_samples),
            rhythm_model=RhythmModel(min_samples=min_samples),
        )
        adaptive_senses = AdaptiveSenseModel.restore(payload.get("sensory_development"))
        allowed_sense_ids = set(adaptive_senses.percept_names())
        if kwargs.get("bootstrap_semantic_senses", True):
            allowed_sense_ids.update(DEFAULT_PERCEPT_NAMES)
        self_model = SelfModel.restore(payload.get("self_model"), allowed_sense_ids=allowed_sense_ids)
        from .. import __version__ as _symbiont_version  # deferred: avoids a circular import at module load

        kernel_limits = kwargs.get("kernel_limits") or KernelLimits()
        genome = restore_genome_checkpoint(
            payload.get("genome"),
            kernel_limits=kernel_limits,
            running_version=_parse_running_version(_symbiont_version),
        )
        return cls(
            **kwargs,
            acclimation=acclimation,
            rhythm_model=rhythm_model,
            drift_baselines=drift_baselines,
            adaptive_senses=adaptive_senses,
            self_model=self_model,
            genome=genome,
            tick_count=payload.get("saved_at_tick") or 0,
        )

    @classmethod
    def load_or_create(cls, path: str | Path, **kwargs: Any) -> "OrganismRuntime":
        payload = load_checkpoint_file(path)
        if payload is None:
            return cls(**kwargs)
        return cls.from_checkpoint(payload, **kwargs)
