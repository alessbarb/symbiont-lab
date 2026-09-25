"""Genetic expression and developmental prior dynamics."""
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
from ..lineage.inheritance import EpigeneticPrior


class DevelopmentDomain:
    """Own genotype-to-operating-phenotype development.

    This domain receives regulatory evidence from other domains but remains
    responsible for expression state and inherited developmental priors.
    """

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
            prediction_error,
            controllability_loss,
        )
        uncertainty = max(
            prediction_error,
            0.5 * controllability_loss,
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
            and cognitive_bridge.safety_state.frozen
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

    @staticmethod
    def decay_epigenetic_priors(
        priors: tuple[EpigeneticPrior, ...],
        *,
        decay: float,
    ) -> tuple[EpigeneticPrior, ...]:
        if not priors or decay <= 0.0:
            return priors
        factor = 1.0 - decay
        return tuple(
            EpigeneticPrior(
                item.key,
                round(item.value * factor, 12),
            )
            for item in priors
            if item.value * factor > 1e-12
        )
