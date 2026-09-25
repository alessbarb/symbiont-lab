"""Regulatory phenotype and delayed homeostatic credit."""
from __future__ import annotations

from dataclasses import dataclass

from ...genetics.expression import (
    ExpressionRegulator,
    GeneExpressionState,
    RegulatorySignals,
)
from ...genetics.genome import Genome
from ...host.drift import DriftObservation
from ..cognition.bridge import CognitiveBridge, CognitiveBridgeResult
from ..cognition.consolidation import novelty_from_drift_kind
from ..embodiment.homeostasis import HomeostaticController
from ..embodiment.physiology import LivingBodyState


@dataclass(frozen=True, slots=True)
class RegulationServices:
    cognitive_bridge: CognitiveBridge | None
    homeostasis: HomeostaticController
    living_body_state: LivingBodyState


class RegulationDomain:
    """Own phenotype regulation and delayed intrinsic action credit."""

    def __init__(self) -> None:
        self.pending_homeostatic_action_credit: list[
            tuple[int, str, str, tuple[str, ...], float, float]
        ] = []

    def update_gene_expression(
        self,
        *,
        genome: Genome | None,
        expression_state: GeneExpressionState | None,
        expression_regulator: ExpressionRegulator,
        cognitive_bridge: CognitiveBridge | None,
        cognition: CognitiveBridgeResult | None,
        drift_observations: dict[str, DriftObservation],
        metabolic_pressure: str,
        actuator_count: int,
        active_actuator_count: int,
    ) -> GeneExpressionState | None:
        if genome is None or expression_state is None:
            return expression_state

        losses = (
            [float(error.loss) for error in cognition.prediction_errors]
            if cognition is not None
            else []
        )
        prediction_error = (
            max(0.0, min(1.0, sum(losses) / len(losses)))
            if losses
            else 0.0
        )
        novelty = max(
            (
                novelty_from_drift_kind(observation.kind)
                for observation in drift_observations.values()
            ),
            default=0.0,
        )
        controllability_loss = (
            max(
                0.0,
                min(
                    1.0,
                    1.0
                    - active_actuator_count
                    / max(1, int(actuator_count)),
                ),
            )
            if actuator_count
            else 0.0
        )
        embodiment_mismatch = max(
            prediction_error, controllability_loss
        )
        uncertainty = max(
            prediction_error, 0.5 * controllability_loss
        )
        pressure_ratio = {
            "normal": 0.0,
            "elevated": 0.33,
            "severe": 0.66,
            "unrecoverable": 1.0,
        }.get(str(metabolic_pressure), 0.0)
        signals = RegulatorySignals(
            uncertainty=uncertainty,
            novelty=max(0.0, min(1.0, novelty)),
            prediction_error=prediction_error,
            controllability_loss=controllability_loss,
            embodiment_mismatch=embodiment_mismatch,
            resource_pressure=pressure_ratio,
        )
        frozen = bool(
            cognitive_bridge is not None
            and getattr(cognitive_bridge, "_safety_state", None) is not None
            and cognitive_bridge._safety_state.frozen  # noqa: SLF001
        )
        updated = expression_regulator.update(
            genome,
            expression_state,
            signals,
            frozen=frozen,
        )
        if cognitive_bridge is not None:
            cognitive_bridge.set_expression_state(updated)
        return updated

    def schedule_homeostatic_action_credit(
        self,
        *,
        cognitive_bridge: CognitiveBridge | None,
        family: str,
        action_id: str,
        concept_ids: tuple[str, ...],
        baseline_error: float,
        tick: int,
    ) -> None:
        if cognitive_bridge is None or not concept_ids:
            return
        for horizon, discount in (
            (4, 1.0),
            (16, 0.85),
            (64, 0.65),
            (256, 0.40),
        ):
            self.pending_homeostatic_action_credit.append(
                (
                    int(tick) + horizon,
                    family,
                    str(action_id),
                    tuple(sorted(set(concept_ids))),
                    float(baseline_error),
                    float(discount),
                )
            )
        if len(self.pending_homeostatic_action_credit) > 4096:
            self.pending_homeostatic_action_credit.sort(
                key=lambda item: item[0]
            )
            self.pending_homeostatic_action_credit = (
                self.pending_homeostatic_action_credit[:4096]
            )

    def resolve_homeostatic_action_credit(
        self,
        *,
        services: RegulationServices,
        tick: int,
    ) -> None:
        pending = self.pending_homeostatic_action_credit
        if not pending:
            return
        if not services.living_body_state.alive:
            pending.clear()
            return
        current_error = services.homeostasis.deviation()
        remaining: list[
            tuple[int, str, str, tuple[str, ...], float, float]
        ] = []
        for (
            due_tick,
            family,
            action_id,
            concept_ids,
            baseline_error,
            discount,
        ) in pending:
            if due_tick > tick:
                remaining.append(
                    (
                        due_tick,
                        family,
                        action_id,
                        concept_ids,
                        baseline_error,
                        discount,
                    )
                )
                continue
            if services.cognitive_bridge is None:
                continue
            intrinsic_value = max(
                -1.0,
                min(
                    1.0,
                    (baseline_error - current_error) * discount,
                ),
            )
            services.cognitive_bridge.observe_homeostatic_action_outcome(
                family=family,
                action_id=action_id,
                concept_ids=concept_ids,
                value=intrinsic_value,
                tick=tick,
            )
        self.pending_homeostatic_action_credit = remaining
