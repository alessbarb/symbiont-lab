"""Canonical cognition/learning phase of one organism tick."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ...host.drift import DriftObservation
from ...host.percepts import Percept
from ...host.readings import SensorReading
from ...sensory import SensorySystem
from ..cognition.attention import AttentionAllocation
from ..cognition.bridge import CognitiveBridge, CognitiveBridgeResult
from ..cognition.host_self_model import SelfModel
from ..cognition.self_model import project_cognitive_self_observation


@dataclass(frozen=True, slots=True)
class CognitionServices:
    cognitive_bridge: CognitiveBridge | None
    sensory_system: SensorySystem
    self_model: SelfModel
    charge_metabolism: Callable[[str, float], None]


@dataclass(frozen=True, slots=True)
class CognitionStepResult:
    cognition: CognitiveBridgeResult | None
    cognitive_self_observation: dict[str, Any] | None


class CognitionDomain:
    """Run cognition and learning without owning physical action."""

    def step(
        self,
        *,
        services: CognitionServices,
        tick: int,
        percepts: tuple[Percept, ...],
        cognitive_readings: tuple[SensorReading, ...],
        percept_names: Mapping[str, str],
        developed_names: Mapping[str, str],
        cognitive_aliases: Mapping[str, str],
        allocations: tuple[AttentionAllocation, ...],
        perceptual_allocations: tuple[AttentionAllocation, ...],
        availability_by_capability: Mapping[str, float],
        drift_observations: Mapping[str, DriftObservation],
        active_motor_actuator_ids: tuple[str, ...],
        motor_effect_actuator_ids: tuple[str, ...],
        active_competence_ids: tuple[str, ...],
        plasticity_enabled: bool,
        auto_promote_predictors: bool,
        reacclimation_remaining: int,
        current_tick: int,
        cognitive_self_namespace_key: str,
    ) -> CognitionStepResult:
        result: CognitiveBridgeResult | None = None
        cognitive_self_observation: dict[str, Any] | None = None
        bridge = services.cognitive_bridge

        if bridge is not None:
            sense_values = {
                percept.name: percept.value
                for percept in percepts
                if percept.value is not None
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

            attended_sense_ids: set[str] = set()
            sense_modulation: dict[str, float] = {}
            if services.sensory_system.plasticity_enabled:
                sensor_by_name = {
                    sensor.cognitive_name: sensor
                    for sensor in services.sensory_system.sensors
                }
                for allocation in perceptual_allocations:
                    sensor = sensor_by_name.get(allocation.name)
                    if sensor is None:
                        continue
                    attended_sense_ids.add(sensor.cognitive_name)
                    sense_modulation[sensor.cognitive_name] = max(
                        0.0,
                        min(1.0, sensor.health * sensor.confidence),
                    )
            else:
                for allocation in allocations:
                    capability_id = allocation.name
                    node_names = {
                        name
                        for name in (
                            percept_names.get(capability_id),
                            cognitive_aliases.get(capability_id),
                        )
                        if name is not None
                    }
                    availability = availability_by_capability.get(
                        capability_id, 1.0
                    )
                    health = services.self_model.health(
                        capability_id,
                        current_tick=current_tick,
                    )
                    modulation = max(
                        0.0, min(1.0, availability * health)
                    )
                    for node_name in node_names:
                        attended_sense_ids.add(node_name)
                        sense_modulation[node_name] = modulation

            result = bridge.tick(
                sense_values,
                tick=tick,
                attended_sense_ids=attended_sense_ids,
                sense_modulation=sense_modulation,
                plasticity_enabled=plasticity_enabled,
                active_motor_actuator_ids=active_motor_actuator_ids,
                motor_effect_actuator_ids=motor_effect_actuator_ids,
                active_primitive_ids=active_competence_ids,
            )
            if auto_promote_predictors:
                bridge.nominate_shadow_prediction(tick=tick)

            activations = getattr(result, "activations", None)
            if (
                isinstance(activations, dict)
                and getattr(result, "consecutive_failures", 0) == 0
                and reacclimation_remaining <= 0
            ):
                known_sensory_nodes = (
                    set(percept_names.values())
                    | set(developed_names.values())
                    | set(cognitive_aliases.values())
                )
                cognitive_self_observation = (
                    project_cognitive_self_observation(
                        activations,
                        sensory_ids=known_sensory_nodes,
                        namespace_key=cognitive_self_namespace_key,
                    )
                )

        predictive_gain_by_name: dict[str, float] = {}
        if bridge is not None:
            for candidate in getattr(bridge, "shadow_predictions", ()):
                predictive_gain_by_name[candidate.source_id] = max(
                    predictive_gain_by_name.get(candidate.source_id, 0.0),
                    max(0.0, candidate.predictive_gain),
                )
        services.sensory_system.update_downstream_utility(
            predictive_gain_by_name
        )
        sensory_mutations = services.sensory_system.plastic_step(tick=tick)
        if sensory_mutations:
            services.charge_metabolism(
                "cognition",
                sum(
                    min(0.01, mutation.cost * 0.01)
                    for mutation in sensory_mutations
                ),
            )

        return CognitionStepResult(
            cognition=result,
            cognitive_self_observation=cognitive_self_observation,
        )
