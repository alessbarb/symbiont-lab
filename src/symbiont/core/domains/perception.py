"""Canonical sensory/perceptual phase of one organism tick."""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ...host.acclimation import HostAcclimation
from ...host.adaptive import AdaptiveSenseModel, SamplingPlan
from ...host.bootstrap import current_time_bucket
from ...host.drift import DriftAwareBaseline, DriftObservation
from ...host.lifecycle import HostLifecycle, LifecycleSnapshot
from ...host.percepts import DEFAULT_PERCEPT_NAMES, Percept
from ...host.readings import (
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
)
from ...host.rhythms import RhythmModel
from ...sensory import SensorySystem
from ..cognition.attention import (
    AttentionAllocation,
    AttentionBudget,
    AttentionCandidate,
    attend_to_host,
)
from ..cognition.host_self_model import SelfModel
from ..cognition.consolidation import novelty_from_drift_kind
from ..embodiment.assimilation import AssimilationDecision, InformationAssimilator
from ..signals.identity import SignalIdentity
from ..signals.knowledge import SignalKnowledgeEngine
from ..signals.knowledge_types import SignalObservation, SignalObservationBatch


@dataclass(frozen=True, slots=True)
class PerceptionServices:
    lifecycle: HostLifecycle
    adaptive_senses: AdaptiveSenseModel
    self_model: SelfModel
    signal_identity: SignalIdentity
    signal_knowledge: SignalKnowledgeEngine
    sensory_system: SensorySystem
    acclimation: HostAcclimation
    rhythm_model: RhythmModel
    drift_baselines: dict[str, DriftAwareBaseline]
    assimilator: InformationAssimilator
    resource_habitats: Mapping[str, Any]
    interoception_provider: Any | None
    reading_providers: tuple[Any, ...]
    charge_metabolism: Callable[[str, float], None]


@dataclass(frozen=True, slots=True)
class PerceptionStepResult:
    snapshot: LifecycleSnapshot
    resource_readings: tuple[SensorReading, ...]
    organism_readings: tuple[SensorReading, ...]
    knowledge_view: tuple[dict[str, Any], ...]
    sampling_plan: SamplingPlan | None
    percept_names: dict[str, str]
    capability_by_percept_name: dict[str, str]
    cognitive_aliases: dict[str, str]
    selected_ids: frozenset[str]
    cognitive_readings: tuple[SensorReading, ...]
    percepts: tuple[Percept, ...]
    sensor_by_cognitive_name: dict[str, Any]
    drift_observations: dict[str, DriftObservation]
    assimilation: tuple[AssimilationDecision, ...]
    allocations: tuple[AttentionAllocation, ...]
    perceptual_allocations: tuple[AttentionAllocation, ...]
    availability_by_capability: dict[str, float]
    pending_proprioception_consumed: bool


class PerceptionDomain:
    """Discover, transduce and allocate attention without action authority."""

    def step(
        self,
        *,
        services: PerceptionServices,
        tick: int,
        discover_senses: bool,
        bootstrap_semantic_senses: bool,
        attention_budget: float,
        sampling_selector: Callable[..., Any] | None,
        pending_proprioception: Mapping[str, float],
    ) -> PerceptionStepResult:
        snapshot = services.lifecycle.tick(
            sampling_selector=sampling_selector if discover_senses else None
        )
        resource_readings = tuple(
            SensorReading(
                capability_id=f"habitat_surface.{resource_id}",
                source="shared_habitat",
                value=resource.snapshot().available_resources,
                unit=Unit.COUNT,
                monotonic_timestamp_ns=time.monotonic_ns(),
                quality=ReadingQuality.NOMINAL,
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            )
            for resource_id, resource in sorted(services.resource_habitats.items())
        )
        raw_organism_readings = (*snapshot.readings, *resource_readings)
        if services.interoception_provider is not None:
            from ...host.providers.interoception import InteroceptionProvider

            raw_organism_readings = tuple(
                reading
                for reading in raw_organism_readings
                if reading.source != "interoception"
                or InteroceptionProvider.organism_facing(reading.capability_id)
            )
        organism_readings = tuple(
            services.interoception_provider.normalize_for_organism(reading)
            if services.interoception_provider is not None
            else reading
            for reading in raw_organism_readings
        )
        readings_by_capability = {
            reading.capability_id: reading for reading in organism_readings
        }
        observations: list[SignalObservation] = []
        for capability in snapshot.manifest.available:
            reading = readings_by_capability.get(capability.capability_id)
            observations.append(
                SignalObservation(
                    signal_id=services.signal_identity.signal_id(
                        capability.capability_id
                    ),
                    available=True,
                    selected=(
                        capability.capability_id
                        in snapshot.sampled_capability_ids
                    ),
                    value=None if reading is None else reading.value,
                    quality=(
                        "unavailable"
                        if reading is None
                        else reading.quality.value
                    ),
                )
            )
        for reading in resource_readings:
            observations.append(
                SignalObservation(
                    signal_id=services.signal_identity.signal_id(
                        reading.capability_id
                    ),
                    available=True,
                    selected=True,
                    value=reading.value,
                    quality=reading.quality.value,
                )
            )

        relation_percept_names = (
            services.adaptive_senses.percept_names()
            if discover_senses
            else {}
        )
        name_to_capability = {
            name: capability
            for capability, name in relation_percept_names.items()
        }

        def opaque_sense_id(value: str) -> str:
            capability = name_to_capability.get(value, value)
            return services.signal_identity.signal_id(capability)

        candidate_pairs = tuple(
            (opaque_sense_id(relation.sense_a), opaque_sense_id(relation.sense_b))
            for relation in services.adaptive_senses.strongest_relations(limit=64)
            if relation.sense_a != relation.sense_b
        )
        resource_signal_ids = tuple(
            services.signal_identity.signal_id(reading.capability_id)
            for reading in resource_readings
        )
        candidate_pairs += tuple(
            (left, right)
            for index, left in enumerate(resource_signal_ids)
            for right in resource_signal_ids[index + 1 :]
        )[: 64 - len(candidate_pairs)]

        attempted: dict[str, tuple[str, bool]] = {}
        for outcome in snapshot.sampling_outcomes:
            if (
                outcome.capability_id not in readings_by_capability
                and outcome.kind.value
                in {"missing", "unavailable", "provider_failed"}
            ):
                favorable = False
            elif (
                outcome.kind.value == "succeeded"
                and outcome.quality is not None
                and outcome.quality.value == "nominal"
            ):
                favorable = True
            elif outcome.kind.value in {
                "succeeded",
                "missing",
                "unavailable",
                "provider_failed",
            }:
                favorable = False
            else:
                continue
            attempted[outcome.capability_id] = (
                outcome.provider_id,
                favorable,
            )
        outcomes = tuple(
            (services.signal_identity.signal_id(capability_id), favorable)
            for capability_id, (provider_id, favorable) in attempted.items()
            if not any(
                provider_id == other_provider and capability_id != other_id
                for other_id, (other_provider, _favorable) in attempted.items()
            )
        )
        services.signal_knowledge.observe(
            SignalObservationBatch(tick, tuple(observations)),
            candidate_pairs=candidate_pairs,
            outcomes=outcomes,
        )
        knowledge_view = services.signal_knowledge.view()

        interoceptive_reading_count = sum(
            reading.source == "interoception" for reading in snapshot.readings
        )
        external_reading_count = max(
            0, len(snapshot.readings) - interoceptive_reading_count
        )
        services.charge_metabolism(
            "observation",
            min(0.02, external_reading_count * 0.01)
            + interoceptive_reading_count * 0.002,
        )
        sampling_plan = (
            services.adaptive_senses.last_sampling_plan
            if discover_senses
            else None
        )

        services.adaptive_senses.observe(organism_readings)
        for outcome in snapshot.sampling_outcomes:
            services.self_model.observe(outcome=outcome, tick=tick - 1)
        for evicted_name in services.adaptive_senses.drain_evicted_percept_names():
            services.drift_baselines.pop(evicted_name, None)

        active_learned_names = (
            services.adaptive_senses.percept_names() if discover_senses else {}
        )
        developed_names = (
            services.adaptive_senses.developed_percept_names()
            if discover_senses
            else {}
        )
        semantic_names = (
            DEFAULT_PERCEPT_NAMES
            if bootstrap_semantic_senses
            and not services.sensory_system.plasticity_enabled
            else {}
        )
        opaque_source_names = (
            {
                reading.capability_id: services.signal_identity.signal_id(
                    reading.capability_id
                )
                for reading in organism_readings
            }
            if services.sensory_system.plasticity_enabled
            else {}
        )
        habitat_names = {
            capability_id: services.signal_identity.signal_id(capability_id)
            for resource_id in services.resource_habitats
            for capability_id in (f"habitat_surface.{resource_id}",)
        }
        interoceptive_names = {
            reading.capability_id: services.signal_identity.signal_id(
                reading.capability_id
            )
            for reading in organism_readings
            if reading.source == "interoception"
        }

        selected_names: dict[str, str] = dict(semantic_names)
        selected_names.update(opaque_source_names)
        selected_names.update(active_learned_names)
        selected_names.update(habitat_names)
        selected_names.update(interoceptive_names)
        percept_names = {
            capability_id: developed_names.get(capability_id, selected_name)
            for capability_id, selected_name in selected_names.items()
        }
        capability_by_percept_name = {
            name: capability_id
            for capability_id, name in percept_names.items()
        }
        cognitive_aliases = {
            capability_id: semantic_name
            for capability_id, semantic_name in semantic_names.items()
            if percept_names.get(capability_id) not in (None, semantic_name)
        }

        selected_ids = set(percept_names)
        cognitive_readings = tuple(
            reading
            for reading in organism_readings
            if reading.capability_id in selected_ids
        )
        consumed_proprioception = False
        if pending_proprioception:
            now = time.monotonic_ns()
            proprio_names = {
                capability_id: services.signal_identity.signal_id(capability_id)
                for capability_id in pending_proprioception
            }
            proprio_readings = tuple(
                SensorReading(
                    capability_id=capability_id,
                    source="actuation",
                    value=value,
                    unit=Unit.RATIO,
                    monotonic_timestamp_ns=now,
                    quality=ReadingQuality.NOMINAL,
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
                for capability_id, value in sorted(
                    pending_proprioception.items()
                )
            )
            percept_names.update(proprio_names)
            cognitive_readings = (*cognitive_readings, *proprio_readings)
            consumed_proprioception = True

        percepts = services.sensory_system.transduce(
            cognitive_readings,
            percept_names=percept_names,
            tick=tick,
        )
        sensor_by_cognitive_name = {
            sensor.cognitive_name: sensor
            for sensor in services.sensory_system.sensors
        }

        acquisition_costs: dict[str, float] = {}
        for outcome in snapshot.sampling_outcomes:
            acquisition_costs[outcome.capability_id] = (
                acquisition_costs.get(outcome.capability_id, 0.0)
                + outcome.attributed_elapsed_s
            )
        services.sensory_system.update_acquisition_costs(acquisition_costs)
        services.acclimation.observe(cognitive_readings)
        services.rhythm_model.observe(
            percepts, time_bucket=current_time_bucket()
        )
        for percept in percepts:
            sensor = sensor_by_cognitive_name.get(percept.name)
            if (
                percept.name not in capability_by_percept_name
                and sensor is not None
                and len(sensor.source_ids) == 1
            ):
                capability_by_percept_name[percept.name] = sensor.source_ids[0]

        drift_observations: dict[str, DriftObservation] = {}
        for percept in percepts:
            if percept.value is None:
                continue
            baseline = services.drift_baselines.get(percept.name)
            if baseline is None:
                baseline = DriftAwareBaseline()
                services.drift_baselines[percept.name] = baseline
            drift_observations[percept.name] = baseline.observe(percept.value)

        assimilation: list[AssimilationDecision] = []
        for observation in drift_observations.values():
            decision = services.assimilator.evaluate(
                novelty=novelty_from_drift_kind(observation.kind),
                surprise=0.0,
                attention=0.0,
                reliability=1.0,
                cost=0.0,
            )
            assimilation.append(decision)
            services.charge_metabolism(
                "persistence",
                0.005
                if decision.action.value == "incorporate"
                else 0.001,
            )

        currently_available_ids = {
            capability.capability_id
            for capability in snapshot.manifest.available
        }
        eligible_ids = selected_ids & currently_available_ids
        services.self_model.reconcile(eligible_ids)
        rank_costs = {
            capability_id: services.self_model.relative_cost(
                capability_id, reference_ids=eligible_ids
            )
            for capability_id in eligible_ids
        }
        allocations = attend_to_host(
            services.acclimation,
            budget=attention_budget,
            eligible_capability_ids=eligible_ids,
            rank_costs=rank_costs,
        )

        perceptual_allocations: tuple[AttentionAllocation, ...] = ()
        if services.sensory_system.plasticity_enabled:
            allocated_sources = {
                allocation.name for allocation in allocations
            } | {
                reading.capability_id for reading in resource_readings
            }
            available_percepts = {
                percept.name
                for percept in percepts
                if percept.value is not None
            }
            candidates: list[AttentionCandidate] = []
            for sensor in services.sensory_system.sensors:
                if sensor.cognitive_name not in available_percepts:
                    continue
                if not allocated_sources.intersection(sensor.source_ids):
                    continue
                developmental_uncertainty = 1.0 / (
                    1.0 + max(0, sensor.age_ticks) / 8.0
                )
                uncertainty = max(
                    1.0 - sensor.confidence,
                    developmental_uncertainty,
                )
                utility_factor = (
                    1.0 + 4.0 * sensor.utility
                    if sensor.utility_observations >= 8
                    else 1.0
                )
                candidates.append(
                    AttentionCandidate(
                        name=sensor.cognitive_name,
                        uncertainty=uncertainty,
                        cost=1.0,
                        rank_cost=max(
                            0.10,
                            (
                                1.0 + sensor.transduction_cost * 10.0
                            )
                            / utility_factor,
                        ),
                        observations=sensor.utility_observations,
                    )
                )
            if candidates:
                perceptual_allocations = AttentionBudget(
                    budget=max(1.0, float(len(allocations)))
                ).allocate(candidates)

        interoceptive_capability_ids = {
            capability.capability_id
            for capability in snapshot.manifest.available
            if capability.source == "interoception"
        }
        interoceptive_allocations = sum(
            allocation.name in interoceptive_capability_ids
            for allocation in allocations
        )
        services.charge_metabolism(
            "cognition",
            (len(allocations) - interoceptive_allocations) * 0.02
            + interoceptive_allocations * 0.005,
        )
        availability_by_capability = {
            state.capability_id: state.availability
            for state in services.adaptive_senses.states
        }
        return PerceptionStepResult(
            snapshot=snapshot,
            resource_readings=resource_readings,
            organism_readings=organism_readings,
            knowledge_view=knowledge_view,
            sampling_plan=sampling_plan,
            percept_names=percept_names,
            capability_by_percept_name=capability_by_percept_name,
            cognitive_aliases=cognitive_aliases,
            selected_ids=frozenset(selected_ids),
            cognitive_readings=cognitive_readings,
            percepts=percepts,
            sensor_by_cognitive_name=sensor_by_cognitive_name,
            drift_observations=drift_observations,
            assimilation=tuple(assimilation),
            allocations=allocations,
            perceptual_allocations=perceptual_allocations,
            availability_by_capability=availability_by_capability,
            pending_proprioception_consumed=consumed_proprioception,
        )
