"""Autonomous cognitive seed backed by canonical Genome v2.

The reduced Symbiont used by clean embodiment studies intentionally reuses the
same canonical sensorimotor inference components as OrganismRuntime.  It is not
an alternate BodySchema/agency architecture.
"""
from __future__ import annotations

import hashlib
import random
from typing import Mapping, Sequence

from ...actuation.effects import EffectSpace
from ...actuation.evidence import CausalEvidenceLedger, PredictionError, SensorimotorTransition
from ...actuation.model import AgencyModel, CompetenceEffectModel, ControllabilityModel
from ...genetics.expression import (
    ExpressionRegulator,
    GeneExpressionState,
    RegulatorySignals,
)
from ...genetics.genome import Genome
from ...genetics.germline import GermlineState
from ..embodiment.body_schema import BodySchemaEngine
from ..embodiment.dynamics import SensorimotorDynamicsModel
from .continuity import SymbiontContinuityModel


class Symbiont:
    """Minimal autonomous seed used by clean embodiment studies.

    Body-specific state is canonical Embodiment state: low-level dynamics,
    causal evidence, effect grounding, controllability, agency and BodySchema.
    A transplant resets those facts while preserving Symbiont identity,
    historical time, genotype and gene-expression continuity.
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
            else (
                GeneExpressionState.from_genome(genome)
                if genome is not None
                else None
            )
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

        self.self_model = SymbiontContinuityModel(symbiont_id)
        self.total_ticks = 0
        self.current_output_channels: set[str] = set()
        self.historical_output_channels: set[str] = set()
        self.last_inputs: dict[str, float] = {}
        self.last_activations: dict[str, float] = {}
        self._last_action_competence_id: str | None = None
        self._competence_outputs: dict[str, tuple[str, ...]] = {}
        self._signal_to_input: dict[str, str] = {}
        self._reset_embodiment_state()

        # Passive compatibility telemetry only. Genome v2 never captures
        # lifetime expression into the germline unless an explicit experiment
        # invokes GermlineState.capture_acquired_variation itself.
        self.last_epigenetic_capture: tuple[str, ...] = ()
        self.epigenetic_capture_count = 0

    def _reset_embodiment_state(self) -> None:
        """Discard current-Body factual authority without touching Symbiont history."""
        self.sensorimotor_model = SensorimotorDynamicsModel(
            learning_rate=self.learning_rate
        )
        self.effect_space = EffectSpace()
        self.causal_evidence = CausalEvidenceLedger()
        self.competence_effect_model = CompetenceEffectModel()
        self.controllability_model = ControllabilityModel()
        self.agency_model = AgencyModel()
        self.body_schema = BodySchemaEngine()
        self.last_inputs = {}
        self.last_activations = {}
        self._last_action_competence_id = None
        self._competence_outputs = {}
        self._signal_to_input = {}

    def begin_new_embodiment(self) -> None:
        """Withdraw all old-Body authority for a genuine Body transplant."""
        self._reset_embodiment_state()

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
        self.current_output_channels = {str(value) for value in channels}
        self.historical_output_channels.update(self.current_output_channels)

    @property
    def known_output_channels(self) -> set[str]:
        return set(self.current_output_channels)

    @staticmethod
    def _signal_ref(channel: str) -> str:
        digest = hashlib.sha256(
            f"reduced-symbiont-signal:{channel}".encode("utf-8")
        ).hexdigest()[:24]
        return f"signal.{digest}"

    @staticmethod
    def _state_ref(tick: int, phase: str) -> str:
        return f"state.reduced.{phase}.{tick}"

    def _action_competence_id(
        self,
        activations: Mapping[str, float],
    ) -> str | None:
        active = tuple(
            sorted(
                channel
                for channel, value in activations.items()
                if abs(float(value)) > 0.05
            )
        )
        if not active:
            return None
        material = "|".join(active)
        digest = hashlib.sha256(
            f"reduced-symbiont-action:{material}".encode("utf-8")
        ).hexdigest()[:24]
        competence_id = f"competence.{digest}"
        self._competence_outputs[competence_id] = active
        return competence_id

    def _agency_confidence_for_output(self, output: str) -> float:
        values = [
            estimate.confidence
            for estimate in self.agency_model.estimates
            if output in self._competence_outputs.get(
                estimate.competence_id, ()
            )
        ]
        return max(values, default=0.0)

    def _record_transition(
        self,
        *,
        deltas: Mapping[str, float],
        prediction_error: float,
    ) -> None:
        if self.total_ticks <= 1:
            return
        effect_changes: dict[str, float] = {}
        for input_id, delta in deltas.items():
            signal_ref = self._signal_ref(input_id)
            self._signal_to_input[signal_ref] = input_id
            effect_changes[signal_ref] = float(delta)
        effect = self.effect_space.observe(effect_changes)

        competence_id = self._last_action_competence_id
        controller_id = (
            f"controller.{competence_id.removeprefix('competence.')}"
            if competence_id is not None
            else "controller.passive"
        )
        transition = SensorimotorTransition(
            transition_id=f"transition.reduced.{self.total_ticks}",
            tick_start=max(0, self.total_ticks - 1),
            tick_end=self.total_ticks,
            context_ref="context.reduced",
            commitment_id=f"commitment.reduced.{self.total_ticks - 1}",
            controller_id=controller_id,
            competence_id=competence_id,
            state_before_ref=self._state_ref(self.total_ticks - 1, "before"),
            motor_command_ref=f"command.reduced.{self.total_ticks - 1}",
            actuation_ref=f"actuation.reduced.{self.total_ticks - 1}",
            prediction_ref=(
                f"prediction.reduced.{self.total_ticks - 1}"
                if self.last_inputs
                else None
            ),
            state_after_ref=self._state_ref(self.total_ticks, "after"),
            observed_effect_id=(effect.effect_id if effect is not None else None),
            prediction_error=PredictionError(
                magnitude=max(0.0, float(prediction_error)),
                uncertainty=min(1.0, max(0.0, float(prediction_error))),
                novelty=min(1.0, max(0.0, float(prediction_error))),
            ),
        )
        evidence = self.causal_evidence.observe(transition)
        self.competence_effect_model.observe(evidence)

        if competence_id is not None and effect is not None:
            control = self.controllability_model.update_from_ledger(
                self.causal_evidence,
                effect_id=effect.effect_id,
                competence_id=competence_id,
                context_id=None,
                tick=self.total_ticks,
            )
            prediction_match = 1.0 - min(1.0, max(0.0, prediction_error))
            self.agency_model.update_from_ledger(
                self.causal_evidence,
                effect_id=effect.effect_id,
                competence_id=competence_id,
                context_id=None,
                tick=self.total_ticks,
                prediction_match=prediction_match,
            )

    def _update_body_boundary(
        self,
        current_inputs: Mapping[str, float],
        prediction_error: float,
    ) -> None:
        self_caused: set[str] = set()
        for estimate in self.agency_model.estimates:
            if estimate.confidence < 0.35:
                continue
            effect = self.effect_space.get(estimate.effect_id)
            if effect is None:
                continue
            for feature_ref in effect.feature_refs:
                input_id = self._signal_to_input.get(feature_ref)
                if input_id is not None:
                    self_caused.add(input_id)

        self.body_schema.observe_agency_boundary(
            observed_channels=set(current_inputs),
            self_caused_channels=self_caused,
            # Somatic extension requires separate evidence. The reduced runtime
            # deliberately does not infer it from mere correlation.
            somatic_correlated_channels=(),
            prediction_error=prediction_error,
        )

    def step(self, opaque_inputs: Mapping[str, float]) -> dict[str, float]:
        self.total_ticks += 1
        current_inputs = {
            str(key): float(value) for key, value in opaque_inputs.items()
        }
        deltas = {
            channel: value - self.last_inputs.get(channel, value)
            for channel, value in current_inputs.items()
        }

        residuals = self.sensorimotor_model.observe(
            deltas,
            tick=self.total_ticks,
        )
        prediction_error = (
            sum(item.error for item in residuals) / len(residuals)
            if residuals
            else 0.0
        )

        self._record_transition(
            deltas=deltas,
            prediction_error=prediction_error,
        )
        self._update_body_boundary(current_inputs, prediction_error)
        self.self_model.record_tick(
            schema_confidence=self.body_schema.boundary_confidence,
            prediction_error=prediction_error,
        )

        confidence_values = tuple(
            estimate.confidence for estimate in self.agency_model.estimates
        )
        mean_confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.0
        )

        # Tick t evidence changes expression for t+1. This reduced runtime
        # receives no evaluator/world semantic signal.
        if self.genome is not None and self.gene_expression_state is not None:
            bounded_error = max(0.0, min(1.0, abs(float(prediction_error))))
            signals = RegulatorySignals(
                uncertainty=max(bounded_error, 1.0 - mean_confidence),
                novelty=bounded_error,
                prediction_error=bounded_error,
                controllability_loss=max(
                    0.0, min(1.0, 1.0 - mean_confidence)
                ),
                embodiment_mismatch=max(
                    bounded_error,
                    self.body_schema.boundary_disruption_score,
                ),
                resource_pressure=0.0,
            )
            self.gene_expression_state = self._expression_regulator.update(
                self.genome,
                self.gene_expression_state,
                signals,
            )
            self.learning_rate = (
                self.gene_expression_state.effective_learning_rate
            )
            self.exploration_rate = self.gene_expression_state.exploration_drive
            self.sensorimotor_model.learning_rate = self.learning_rate
            self.expressed_loci = {
                "learning_rate": self.learning_rate,
                "exploration_rate": self.exploration_rate,
            }

        outputs = sorted(self.current_output_channels)
        if not outputs and self.last_activations:
            outputs = sorted(self.last_activations)

        next_activations: dict[str, float] = {}
        disruption = self.body_schema.boundary_disruption_score >= 0.5
        for output in outputs:
            if self._rng.random() >= self.exploration_rate:
                level = 0.0
            else:
                confidence = self._agency_confidence_for_output(output)
                if disruption or confidence < 0.4:
                    level = self._rng.uniform(0.05, 1.0)
                else:
                    previous = self.last_activations.get(output, 0.5)
                    noise = self._rng.gauss(
                        0.0, max(0.001, self.exploration_rate)
                    )
                    level = max(0.0, min(1.0, previous + noise))
            next_activations[output] = level

        if current_inputs:
            self.sensorimotor_model.predict(
                next_activations,
                tuple(sorted(current_inputs)),
            )

        self.last_inputs = current_inputs
        self.last_activations = dict(next_activations)
        self._last_action_competence_id = self._action_competence_id(
            next_activations
        )
        return next_activations


__all__ = ["Symbiont"]
