from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..host.acclimation import HostAcclimation
from ..host.adaptive import AdaptiveSenseModel, SamplingPlan
from ..host.bootstrap import current_time_bucket
from ..host.checkpoint import (
    CheckpointError,
    export_checkpoint,
    import_checkpoint,
    load_checkpoint_file,
    normalize_checkpoint,
    save_checkpoint_atomic,
)
from ..host.contracts import DiscoveryPolicy, DiscoveryProvider, HostManifest
from ..host.discovery import HostDiscovery
from ..host.drift import DriftAwareBaseline, DriftObservation
from ..host.lifecycle import HostLifecycle, LifecycleSnapshot
from ..host.percepts import DEFAULT_PERCEPT_NAMES, Percept, synthesize_percepts
from ..host.providers.stdlib import StandardLibraryProvider
from ..host.providers.stdlib_readings import StandardLibraryReadingProvider
from ..host.readings import HostSampler, ReadingProvider
from ..host.rhythms import RhythmModel
from ..host.second_look import SecondLookSession
from ..cognition.checkpoint import export_genome_checkpoint, restore_genome_checkpoint
from ..cognition.genome import Genome
from ..cognition.graph import CognitiveGraph
from ..cognition.limits import KernelLimits
from .attention import AttentionAllocation, attend_to_host
from .cognition_bridge import CognitiveBridge, CognitiveBridgeResult
from .evidence import DissentRecord, EvidenceRevisionLedger
from .narrative import NarrativeEntry, narrate_host
from .selfmodel import LOW_HEALTH_INVESTIGATION_THRESHOLD, SelfModel


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
    cognition: CognitiveBridgeResult | None = None


class OrganismRuntime:
    """Continuous cognitive cycle over safe local perceptions.

    In developmental mode discovery remains broad inside the provider's fixed safety
    boundary, while sampling becomes selective. Cognitive learning happens only
    after attention has been allocated for the current tick, so attention and the
    self-model can constrain plastic updates instead of merely describing them.
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
        evidence_ledger: EvidenceRevisionLedger | None = None,
        genome: Genome | None = None,
        kernel_limits: KernelLimits | None = None,
        cognitive_graph: CognitiveGraph | None = None,
        cognitive_bridge: CognitiveBridge | None = None,
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
        self._evidence_ledger = (
            evidence_ledger if evidence_ledger is not None else EvidenceRevisionLedger(conflict_z=conflict_z)
        )
        self._attention_budget = attention_budget
        self._investigate_ticks = investigate_ticks
        self._tick_count = tick_count
        self._self_model = self_model if self_model is not None else SelfModel()
        self._genome = genome
        self._kernel_limits = kernel_limits if kernel_limits is not None else KernelLimits()
        self._cognitive_bridge: CognitiveBridge | None = cognitive_bridge
        if self._cognitive_bridge is None and genome is not None and cognitive_graph is not None:
            self._cognitive_bridge = CognitiveBridge(
                graph=cognitive_graph, genome=genome, kernel_limits=self._kernel_limits
            )

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
    def evidence_ledger(self) -> EvidenceRevisionLedger:
        return self._evidence_ledger

    @property
    def genome(self) -> Genome | None:
        return self._genome

    @property
    def cognitive_bridge(self) -> CognitiveBridge | None:
        return self._cognitive_bridge

    def _sampling_selector(self, manifest: HostManifest) -> tuple[str, ...] | None:
        if not self._discover_senses:
            return None
        plan = self._adaptive_senses.sampling_plan(
            capability.capability_id for capability in manifest.available
        )
        requested = set(plan.requested_ids)
        if self._bootstrap_semantic_senses:
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

        self._adaptive_senses.observe(snapshot.readings)
        for outcome in snapshot.sampling_outcomes:
            self._self_model.observe(outcome=outcome, tick=self._tick_count)
        for evicted_name in self._adaptive_senses.drain_evicted_percept_names():
            self._drift_baselines.pop(evicted_name, None)

        active_learned_names = self._adaptive_senses.percept_names() if self._discover_senses else {}
        developed_names = self._adaptive_senses.developed_percept_names() if self._discover_senses else {}
        semantic_names = DEFAULT_PERCEPT_NAMES if self._bootstrap_semantic_senses else {}

        selected_names: dict[str, str] = dict(semantic_names)
        selected_names.update(active_learned_names)
        percept_names = {
            capability_id: developed_names.get(capability_id, selected_name)
            for capability_id, selected_name in selected_names.items()
        }
        cognitive_aliases = {
            capability_id: semantic_name
            for capability_id, semantic_name in semantic_names.items()
            if percept_names.get(capability_id) not in (None, semantic_name)
        }

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

        currently_available_ids = {
            capability.capability_id for capability in snapshot.manifest.available
        }
        eligible_ids = selected_ids & currently_available_ids
        self._self_model.reconcile(eligible_ids)
        rank_costs = {
            capability_id: self._self_model.relative_cost(
                capability_id, reference_ids=eligible_ids
            )
            for capability_id in eligible_ids
        }
        allocations = attend_to_host(
            self._acclimation,
            budget=self._attention_budget,
            eligible_capability_ids=eligible_ids,
            rank_costs=rank_costs,
        )

        cognition_result: CognitiveBridgeResult | None = None
        if self._cognitive_bridge is not None:
            sense_values = {
                percept.name: percept.value for percept in percepts if percept.value is not None
            }
            raw_values = {
                reading.capability_id: float(reading.value)
                for reading in cognitive_readings
                if reading.value is not None
            }
            for capability_id, alias in cognitive_aliases.items():
                raw_value = raw_values.get(capability_id)
                if raw_value is not None:
                    sense_values.setdefault(alias, raw_value)

            availability_by_capability = {
                state.capability_id: state.availability for state in self._adaptive_senses.states
            }
            attended_sense_ids: set[str] = set()
            sense_modulation: dict[str, float] = {}
            for allocation in allocations:
                capability_id = allocation.name
                node_names = {
                    name
                    for name in (percept_names.get(capability_id), cognitive_aliases.get(capability_id))
                    if name is not None
                }
                availability = availability_by_capability.get(capability_id, 1.0)
                health = self._self_model.health(capability_id, current_tick=self._tick_count)
                modulation = max(0.0, min(1.0, availability * health))
                for node_name in node_names:
                    attended_sense_ids.add(node_name)
                    sense_modulation[node_name] = modulation

            cognition_result = self._cognitive_bridge.tick(
                sense_values,
                tick=self._tick_count + 1,
                attended_sense_ids=attended_sense_ids,
                sense_modulation=sense_modulation,
            )

        investigated_capability: str | None = None
        evidence_gathered = 0
        dissent: DissentRecord | None = None
        evidence_counts: dict[str, int] = {}
        dissent_by_capability: dict[str, DissentRecord] = {}

        if self._investigate_ticks > 0:
            for allocation in allocations:
                candidate = allocation.name
                if candidate not in selected_ids or not snapshot.manifest.supports(candidate):
                    continue
                if (
                    self._self_model.is_established(candidate)
                    and self._self_model.health(candidate, current_tick=self._tick_count)
                    < LOW_HEALTH_INVESTIGATION_THRESHOLD
                ):
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
            cognition=cognition_result,
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
        payload["self_model"] = self._self_model.export(current_tick=self._tick_count)
        payload["evidence_ledger"] = self._evidence_ledger.export_checkpoint()
        payload["genome"] = export_genome_checkpoint(self._genome)
        payload["cognitive_bridge"] = (
            self._cognitive_bridge.export_checkpoint()
            if self._cognitive_bridge is not None
            else None
        )
        return payload

    def save(self, path: str | Path) -> None:
        payload = self.checkpoint()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(encoded) > self._kernel_limits.max_plastic_checkpoint_bytes:
            raise CheckpointError(
                "checkpoint exceeds kernel_limits.max_plastic_checkpoint_bytes "
                f"({len(encoded)} > {self._kernel_limits.max_plastic_checkpoint_bytes})"
            )
        save_checkpoint_atomic(payload, path)

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any], **kwargs: Any) -> "OrganismRuntime":
        normalized = normalize_checkpoint(payload)
        min_samples = int(kwargs.get("min_samples", 5))
        acclimation, rhythm_model, drift_baselines = import_checkpoint(
            normalized,
            acclimation=HostAcclimation(min_samples=min_samples),
            rhythm_model=RhythmModel(min_samples=min_samples),
        )
        adaptive_senses = AdaptiveSenseModel.restore(normalized.get("sensory_development"))
        allowed_sense_ids = set(adaptive_senses.developed_percept_names())
        if kwargs.get("bootstrap_semantic_senses", True):
            allowed_sense_ids.update(DEFAULT_PERCEPT_NAMES)
        self_model = SelfModel.restore(
            normalized.get("self_model"),
            allowed_sense_ids=allowed_sense_ids,
            current_tick=normalized.get("saved_at_tick") or 0,
        )
        evidence_ledger = EvidenceRevisionLedger.restore_checkpoint(
            normalized.get("evidence_ledger"),
            conflict_z=float(kwargs.get("conflict_z", 2.0)),
            allowed_capability_ids=acclimation.known_capabilities,
        )
        from .. import __version__ as _symbiont_version

        kernel_limits = kwargs.get("kernel_limits") or KernelLimits()
        genome = restore_genome_checkpoint(
            normalized.get("genome"),
            kernel_limits=kernel_limits,
            running_version=_parse_running_version(_symbiont_version),
        )
        cognitive_bridge = None
        if genome is not None:
            cognitive_bridge = CognitiveBridge.restore(
                normalized.get("cognitive_bridge"),
                genome=genome,
                kernel_limits=kernel_limits,
            )
        return cls(
            **kwargs,
            acclimation=acclimation,
            rhythm_model=rhythm_model,
            drift_baselines=drift_baselines,
            adaptive_senses=adaptive_senses,
            self_model=self_model,
            evidence_ledger=evidence_ledger,
            genome=genome,
            cognitive_bridge=cognitive_bridge,
            tick_count=normalized.get("saved_at_tick") or 0,
        )

    @classmethod
    def load_or_create(cls, path: str | Path, **kwargs: Any) -> "OrganismRuntime":
        payload = load_checkpoint_file(path)
        if payload is None:
            return cls(**kwargs)
        return cls.from_checkpoint(payload, **kwargs)
