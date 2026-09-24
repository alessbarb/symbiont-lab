"""Autonomous cognitive seed backed by canonical Genome v2."""
from __future__ import annotations

import random
from typing import Mapping, Sequence

from ...genetics.expression import (
    ExpressionRegulator,
    GeneExpressionState,
    RegulatorySignals,
)
from ...genetics.genome import Genome
from ...genetics.germline import GermlineState
from ..embodiment.agency import (
    AgencyModel,
    InferredBodySchema,
    InferredSelfModel,
    PerceptualStructure,
    SensorimotorModel,
)


class Symbiont:
    """Minimal autonomous seed used by clean embodiment studies.

    The same Genome object used by the full OrganismRuntime governs this
    reduced runtime. No independent genetic representation exists here.
    """

    def __init__(
        self,
        symbiont_id: str,
        *,
        learning_rate: float = 0.1,
        exploration_rate: float = 0.2,
        seed: int = 42,
        genome: Genome | None = None,
        germline: GermlineState | None = None,
        gene_expression_state: GeneExpressionState | None = None,
    ) -> None:
        if not symbiont_id:
            raise ValueError("symbiont_id must not be empty")
        self.symbiont_id = symbiont_id
        self._rng = random.Random(seed)
        self.genome = genome
        self.germline = germline
        self._expression_regulator = ExpressionRegulator()
        self.gene_expression_state = (
            gene_expression_state
            if gene_expression_state is not None
            else (GeneExpressionState.from_genome(genome) if genome is not None else None)
        )

        self.learning_rate = (
            self.gene_expression_state.effective_learning_rate
            if self.gene_expression_state is not None
            else float(learning_rate)
        )
        self.exploration_rate = (
            self.gene_expression_state.exploration_drive
            if self.gene_expression_state is not None
            else float(exploration_rate)
        )
        self.expressed_loci = {
            "learning_rate": self.learning_rate,
            "exploration_rate": self.exploration_rate,
        }

        self.perceptual_structure = PerceptualStructure()
        self.sensorimotor_model = SensorimotorModel(learning_rate=self.learning_rate)
        self.agency_model = AgencyModel()
        self.body_schema = InferredBodySchema()
        self.self_model = InferredSelfModel(symbiont_id)

        self.last_inputs: dict[str, float] = {}
        self.last_activations: dict[str, float] = {}
        self.total_ticks = 0
        self.current_output_channels: set[str] = set()
        self.historical_output_channels: set[str] = set()

        # Kept as passive compatibility telemetry. Genome v2 never captures
        # lifetime expression into the germline unless an explicit experiment
        # invokes GermlineState.capture_acquired_variation itself.
        self.last_epigenetic_capture: tuple[str, ...] = ()
        self.epigenetic_capture_count = 0

    def refresh_phenotype_expression(self) -> dict[str, float]:
        if self.total_ticks > 0:
            raise RuntimeError(
                "phenotype birth expression cannot be refreshed after lifetime execution begins"
            )
        if self.genome is not None:
            self.gene_expression_state = GeneExpressionState.from_genome(self.genome)
            self.learning_rate = self.gene_expression_state.effective_learning_rate
            self.exploration_rate = self.gene_expression_state.exploration_drive
            self.sensorimotor_model.learning_rate = self.learning_rate
        self.expressed_loci = {
            "learning_rate": self.learning_rate,
            "exploration_rate": self.exploration_rate,
        }
        return dict(self.expressed_loci)

    def register_output_channels(self, channels: Sequence[str]) -> None:
        self.current_output_channels = set(channels)
        self.historical_output_channels.update(channels)

    @property
    def known_output_channels(self) -> set[str]:
        return set(self.current_output_channels)

    def step(self, opaque_inputs: Mapping[str, float]) -> dict[str, float]:
        self.total_ticks += 1
        current_inputs = {key: float(value) for key, value in opaque_inputs.items()}
        self.perceptual_structure.observe(current_inputs)

        deltas: dict[str, float] = {}
        for channel, value in current_inputs.items():
            previous = self.last_inputs.get(channel, value)
            deltas[channel] = value - previous

        prediction_error = 0.0
        if self.last_activations and deltas:
            errors = self.sensorimotor_model.update(deltas, self.last_activations)
            if errors:
                prediction_error = sum(abs(value) for value in errors.values()) / len(errors)
            self.agency_model.record_step(self.last_activations, deltas)

        self.body_schema.update_from_agency(
            self.agency_model,
            self.perceptual_structure,
            prediction_error=prediction_error,
        )
        self.self_model.record_tick(
            body_schema_confidence=self.body_schema.overall_confidence,
            prediction_error=prediction_error,
        )

        # Tick t evidence changes expression for t+1. The reduced runtime has
        # no evaluator/world signal: body disruption is internally inferred.
        if self.genome is not None and self.gene_expression_state is not None:
            confidence_values = tuple(self.agency_model.agency_confidence.values())
            mean_confidence = (
                sum(confidence_values) / len(confidence_values)
                if confidence_values
                else 0.0
            )
            bounded_error = max(0.0, min(1.0, abs(float(prediction_error))))
            signals = RegulatorySignals(
                uncertainty=max(bounded_error, 1.0 - mean_confidence),
                novelty=bounded_error,
                prediction_error=bounded_error,
                controllability_loss=max(0.0, min(1.0, 1.0 - mean_confidence)),
                embodiment_mismatch=max(
                    bounded_error,
                    1.0 if self.body_schema.disruption_detected else 0.0,
                ),
                resource_pressure=0.0,
            )
            self.gene_expression_state = self._expression_regulator.update(
                self.genome,
                self.gene_expression_state,
                signals,
            )
            self.learning_rate = self.gene_expression_state.effective_learning_rate
            self.exploration_rate = self.gene_expression_state.exploration_drive
            self.sensorimotor_model.learning_rate = self.learning_rate
            self.expressed_loci = {
                "learning_rate": self.learning_rate,
                "exploration_rate": self.exploration_rate,
            }

        outputs = list(self.current_output_channels)
        if not outputs and self.last_activations:
            outputs = list(self.last_activations)

        next_activations: dict[str, float] = {}
        for output in outputs:
            # Passive samples remain possible for causal contrast, but the
            # probability of active variation is now genotype/expression-owned.
            if self._rng.random() >= self.exploration_rate:
                level = 0.0
            else:
                confidence = self.agency_model.agency_confidence.get(output, 0.0)
                if self.body_schema.disruption_detected or confidence < 0.4:
                    level = self._rng.uniform(0.05, 1.0)
                else:
                    previous = self.last_activations.get(output, 0.5)
                    noise = self._rng.gauss(0.0, max(0.001, self.exploration_rate))
                    level = max(0.0, min(1.0, previous + noise))
            next_activations[output] = level

        if current_inputs:
            self.sensorimotor_model.predict_deltas(
                next_activations,
                list(current_inputs.keys()),
            )

        self.last_inputs = current_inputs
        self.last_activations = dict(next_activations)
        return next_activations


__all__ = ["Symbiont"]
