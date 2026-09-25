"""Embodiment-local body schema observation phase."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...sensory import SensorySystem
from ..cognition.host_self_model import SelfModel
from ..embodiment.body_schema import BodySchemaEngine
from ..signals.identity import SignalIdentity


@dataclass(frozen=True, slots=True)
class EmbodimentServices:
    body_schema: BodySchemaEngine
    sensory_system: SensorySystem
    self_model: SelfModel
    signal_identity: SignalIdentity


@dataclass(frozen=True, slots=True)
class EmbodimentStepResult:
    sensory_phenotype: dict[str, Any]


class EmbodimentDomain:
    """Update current-body representation from organism-owned observations."""

    def observe(
        self,
        *,
        services: EmbodimentServices,
        tick: int,
        cognitive_self_observation: dict[str, Any] | None,
    ) -> EmbodimentStepResult:
        source_ids = {
            source_id
            for sensor in services.sensory_system.sensors
            for source_id in sensor.source_ids
        }
        sensory_phenotype = services.sensory_system.phenotype_view(
            signal_ids_by_source={
                source_id: services.signal_identity.signal_id(source_id)
                for source_id in sorted(source_ids)
            }
        )
        if services.sensory_system.plasticity_enabled:
            services.body_schema.observe_sensory_phenotype(
                sensory_phenotype,
                tick=tick,
            )
        else:
            services.body_schema.observe_self_model(
                services.self_model.export(current_tick=tick),
                tick=tick,
            )
        if cognitive_self_observation is not None:
            services.body_schema.observe_cognition(
                cognitive_self_observation,
                tick=tick,
            )
        return EmbodimentStepResult(
            sensory_phenotype=sensory_phenotype,
        )
