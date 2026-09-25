"""Embodiment-local body schema observation phase."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...sensory import SensorySystem
from ..cognition.host_self_model import SelfModel
from ..embodiment.body_schema import BodySchemaEngine
from ..signals.identity import SignalIdentity
from .cognition import CognitionStepResult
from .context import TickContext


@dataclass(slots=True)
class EmbodimentIdentityState:
    embodiment_id: str | None = None
    body_id: str | None = None
    expected_embodiment_tick: int | None = None


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
    """Own current embodiment identity and body-schema observations."""

    def __init__(self) -> None:
        self.identity = EmbodimentIdentityState()

    def bind(
        self,
        *,
        embodiment_id: str,
        body_id: str | None,
        embodiment_tick: int | None,
        new_episode: bool,
    ) -> None:
        if not embodiment_id:
            raise ValueError("embodiment_id must not be empty")
        if body_id is not None and not body_id:
            raise ValueError("body_id must be non-empty when provided")
        if embodiment_tick is not None and embodiment_tick < 0:
            raise ValueError("embodiment_tick must be non-negative")

        state = self.identity
        if not new_episode and state.embodiment_id is not None:
            if state.embodiment_id != embodiment_id:
                raise RuntimeError("restored embodiment identity does not match current episode")
            if state.body_id is not None and body_id is not None and state.body_id != body_id:
                raise RuntimeError("restored body identity does not match current episode")

        state.embodiment_id = embodiment_id
        if body_id is not None:
            state.body_id = body_id
        state.expected_embodiment_tick = embodiment_tick

    def context(
        self,
        *,
        symbiont_id: str,
        symbiont_tick: int,
        fallback_embodiment_id: str | None = None,
    ) -> TickContext:
        state = self.identity
        embodiment_id = state.embodiment_id or fallback_embodiment_id
        return TickContext(
            symbiont_id=symbiont_id,
            symbiont_tick=symbiont_tick,
            embodiment_id=embodiment_id,
            embodiment_tick=(
                state.expected_embodiment_tick if state.embodiment_id is not None else None
            ),
            body_id=(state.body_id if state.embodiment_id is not None else None),
        )

    def validate_context(self, context: TickContext) -> None:
        state = self.identity
        if state.embodiment_id is None:
            return
        if context.embodiment_id != state.embodiment_id:
            raise ValueError("tick context belongs to another EmbodimentEpisode")
        if state.body_id is not None and context.body_id != state.body_id:
            raise ValueError("tick context belongs to another Body")
        if (
            state.expected_embodiment_tick is not None
            and context.embodiment_tick != state.expected_embodiment_tick
        ):
            raise ValueError("tick context embodiment time is not the expected body time")

    def complete_context(self, context: TickContext) -> None:
        state = self.identity
        if state.embodiment_id is not None and context.embodiment_tick is not None:
            state.expected_embodiment_tick = context.embodiment_tick + 1

    @staticmethod
    def advance_reacclimation(remaining: int) -> int:
        if remaining < 0:
            raise ValueError("reacclimation remaining must be non-negative")
        return max(0, int(remaining) - 1)

    def observe(
        self,
        *,
        services: EmbodimentServices,
        context: TickContext,
        cognition: CognitionStepResult,
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
                tick=context.symbiont_tick,
            )
        else:
            services.body_schema.observe_self_model(
                services.self_model.export(current_tick=context.symbiont_tick),
                tick=context.symbiont_tick,
            )
        if cognition.cognitive_self_observation is not None:
            services.body_schema.observe_cognition(
                cognition.cognitive_self_observation,
                tick=context.symbiont_tick,
            )
        return EmbodimentStepResult(
            sensory_phenotype=sensory_phenotype,
        )
