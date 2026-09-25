"""Runtime lifecycle-event state and passive interoceptive reporting."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ...host.drift import DriftObservation
from ...host.percepts import Percept


@dataclass(slots=True)
class LifecycleEventState:
    last_vital_state: str | None = None
    last_development_phase: str | None = None
    first_sense_emitted: bool = False
    first_concept_emitted: bool = False
    first_prediction_emitted: bool = False


class LifecycleDomain:
    """Own lifecycle-event chronology; never selects or executes actions."""

    def __init__(self, state: LifecycleEventState | None = None) -> None:
        self.state = state if state is not None else LifecycleEventState()

    def events(
        self,
        *,
        homeostatic_snapshot: Any,
        physiology_snapshot: Any,
        development_snapshot: Any,
        cognition_result: Any | None,
        percepts: tuple[Percept, ...],
        knowledge_view: tuple[dict[str, Any], ...],
        drift_observations: dict[str, DriftObservation],
        action_executed: bool,
    ) -> tuple[str, ...]:
        events: list[str] = []
        if homeostatic_snapshot.action.value != "maintain":
            events.append("homeostatic_rescue")

        current_state = physiology_snapshot.state.value
        current_phase = development_snapshot.phase.value
        if current_phase != self.state.last_development_phase:
            events.append("development")
        if current_state in {"stressed", "agonizing", "dormant"}:
            events.append("stress")
        if (
            self.state.last_vital_state
            in {"stressed", "agonizing", "dormant"}
            and current_state == "active"
        ):
            events.append("recovery")
        if current_state == "active":
            events.append("regulation")
        if cognition_result is not None:
            events.append("learning")

        if not self.state.first_sense_emitted and percepts:
            events.append("first_sense")
            self.state.first_sense_emitted = True
        if (
            not self.state.first_concept_emitted
            and cognition_result is not None
            and getattr(cognition_result, "readouts", ())
        ):
            events.append("first_concept")
            self.state.first_concept_emitted = True

        knowledge_has_prediction = any(
            claim.get("kind") == "lead_prediction"
            for profile in knowledge_view
            for claim in profile.get("claims", ())
        )
        if (
            not self.state.first_prediction_emitted
            and (
                (
                    cognition_result is not None
                    and getattr(
                        cognition_result, "prediction_errors", ()
                    )
                )
                or knowledge_has_prediction
            )
        ):
            events.append("first_prediction")
            self.state.first_prediction_emitted = True

        if any(
            getattr(item, "kind", None)
            and getattr(item.kind, "value", item.kind) == "regime_shift"
            for item in drift_observations.values()
        ):
            events.append("regime_shift")
        if (
            current_phase == "terminal"
            and self.state.last_development_phase != "terminal"
        ):
            events.append("terminal")
        if action_executed:
            events.append("action_executed")
        if current_state == "dead":
            events.extend(("death", "resource_release"))

        self.state.last_vital_state = current_state
        self.state.last_development_phase = current_phase
        return tuple(dict.fromkeys(events))

    @staticmethod
    def update_interoception_metrics(
        *,
        provider: Any | None,
        tick_start: float,
        cognition_result: Any | None,
        living_body_state: Any,
        homeostasis: Any,
        degradation: Any,
        metabolism_snapshot: Any,
    ) -> None:
        if provider is None:
            return
        tick_latency = time.monotonic() - tick_start
        surprise = 0.0
        if (
            cognition_result is not None
            and getattr(cognition_result, "prediction_errors", None)
        ):
            errors = cognition_result.prediction_errors
            surprise = (
                min(
                    1.0,
                    sum(abs(error.error) for error in errors) / len(errors),
                )
                if errors
                else 0.0
            )
        metabolic_ratio = living_body_state.energy_reserve / max(
            1e-9,
            living_body_state.max_energy,
        )
        pressure_ratio = {
            "normal": 0.0,
            "elevated": 0.33,
            "severe": 0.66,
            "unrecoverable": 1.0,
        }.get(metabolism_snapshot.pressure.value, 1.0)
        provider.update_metrics(
            tick_latency=tick_latency,
            epistemic_surprise=surprise,
            metabolic_reserve=max(0.0, min(1.0, metabolic_ratio)),
            integrity=homeostasis.integrity,
            metabolic_pressure=pressure_ratio,
            repair_pressure=1.0 - homeostasis.integrity,
            waste_pressure=min(1.0, len(degradation.items) / 64.0),
        )
