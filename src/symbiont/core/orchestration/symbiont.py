"""Autonomous cognitive seed backed by canonical Genome v2.

The reduced Symbiont used by clean embodiment studies intentionally reuses the
same canonical sensorimotor inference components as OrganismRuntime.  It is not
an alternate BodySchema/agency architecture.
"""

from __future__ import annotations

import hashlib
import random
from typing import Mapping, Sequence

from ...actuation.acquisition import AgencyAcquisition
from ...actuation.action import (
    ActionEvaluation,
    ActionJustification,
    ActionProposal,
    ActionSource,
)
from ...actuation.binding import CompetenceExecutionBindingRegistry
from ...actuation.competence import (
    CompetenceEvidence,
    CompetenceLibrary,
    MotorCompetence,
)
from ...actuation.effects import EffectSpace
from ...actuation.evidence import CausalEvidenceLedger, PredictionError
from ...actuation.intervention import opaque_channel_ref
from ...actuation.model import (
    AgencyModel,
    CausalSourceKind,
    CompetenceEffectModel,
    ControllabilityModel,
)
from ...actuation.surface import ActuatorChannel, ActuatorSurface
from ...genetics.expression import (
    ExpressionRegulator,
    GeneExpressionState,
    RegulatorySignals,
)
from ...genetics.genome import Genome
from ...genetics.germline import GermlineState
from ..domains.action import ActionDomain
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
                GeneExpressionState.from_genome(genome, germline=germline)
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
        self._last_prediction_error: float = 0.0
        self._channel_outputs: dict[str, str] = {}
        self._signal_to_input: dict[str, str] = {}
        self.competence_library = CompetenceLibrary()
        self._reset_embodiment_state()

        # Passive compatibility telemetry only. Genome v2 never captures
        # lifetime expression into the germline unless an explicit experiment
        # invokes GermlineState.capture_acquired_variation itself.
        self.last_epigenetic_capture: tuple[str, ...] = ()
        self.epigenetic_capture_count = 0

    def _reset_embodiment_state(self) -> None:
        """Discard current-Body factual authority without touching Symbiont history."""
        self.sensorimotor_model = SensorimotorDynamicsModel(learning_rate=self.learning_rate)
        self.body_schema = BodySchemaEngine()
        self._current_surface_fingerprint: str | None = None
        for competence in self.competence_library.items:
            competence.effect_id = None
        self.last_inputs = {}
        self.last_activations = {}
        self._channel_outputs = {}
        self._signal_to_input = {}
        # The single action authority owns the shared Agency Acquisition state
        # (attempts, intervention families, effects, causal evidence,
        # controllability, agency, learned dimensions) exactly as in
        # OrganismRuntime; this reduced seed only drives it.
        self.action_domain = ActionDomain(
            organism_id=self.symbiont_id,
            enabled=False,
            surface=None,
        )
        self.action_domain.competence_library = self.competence_library

    # Canonical inference state lives in the shared acquisition component.
    @property
    def acquisition(self) -> AgencyAcquisition:
        return self.action_domain.acquisition

    @property
    def effect_space(self) -> EffectSpace:
        return self.acquisition.effect_space

    @property
    def causal_evidence(self) -> CausalEvidenceLedger:
        return self.acquisition.causal_evidence

    @property
    def competence_effect_model(self) -> CompetenceEffectModel:
        return self.acquisition.effect_model

    @property
    def controllability_model(self) -> ControllabilityModel:
        return self.acquisition.controllability_model

    @property
    def agency_model(self) -> AgencyModel:
        return self.acquisition.agency_model

    @property
    def competence_execution_bindings(self) -> CompetenceExecutionBindingRegistry:
        return self.action_domain.execution_bindings

    def _configure_action_surface(self) -> None:
        if self._current_surface_fingerprint is None or not self.current_output_channels:
            self.action_domain.enabled = False
            self.action_domain.surface = None
            self.acquisition.bind_surface(None, surface_fingerprint=None)
            return
        channels = tuple(
            ActuatorChannel(
                slot_id=f"motor_slot.{index}",
                actuator_id=actuator_id,
            )
            for index, actuator_id in enumerate(sorted(self.current_output_channels))
        )
        self.action_domain.surface = ActuatorSurface(
            channels=channels,
            contract_fingerprint=self._current_surface_fingerprint,
        )
        self.action_domain.enabled = True
        self.acquisition.bind_surface(
            tuple(sorted(self.current_output_channels)),
            surface_fingerprint=self._current_surface_fingerprint,
        )

    def begin_new_embodiment(self) -> None:
        """Withdraw all old-Body authority for a genuine Body transplant."""
        self._reset_embodiment_state()

    def attach_execution_surface(
        self,
        surface_fingerprint: str,
        *,
        embodiment_id: str | None = None,
    ) -> None:
        """Attach the opaque legal motor surface for the current embodiment."""
        if not isinstance(surface_fingerprint, str) or not surface_fingerprint:
            raise ValueError("surface_fingerprint must be non-empty")
        if embodiment_id is not None and (not isinstance(embodiment_id, str) or not embodiment_id):
            raise ValueError("embodiment_id must be non-empty when provided")
        self._current_surface_fingerprint = surface_fingerprint
        self.action_domain.embodiment_id = embodiment_id
        self._configure_action_surface()

    def refresh_phenotype_expression(self) -> dict[str, float]:
        if self.total_ticks > 0:
            raise RuntimeError(
                "phenotype birth expression cannot be refreshed after lifetime execution begins"
            )
        if self.genome is not None:
            self.gene_expression_state = GeneExpressionState.from_genome(
                self.genome,
                germline=self.germline,
            )
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
        self._channel_outputs.update(
            {opaque_channel_ref(output): output for output in self.current_output_channels}
        )
        self.historical_output_channels.update(self.current_output_channels)
        self._configure_action_surface()

    @property
    def known_output_channels(self) -> set[str]:
        return set(self.current_output_channels)

    @property
    def last_prediction_error(self) -> float:
        return self._last_prediction_error

    @property
    def body_schema_confidence(self) -> float:
        return self.body_schema.boundary_confidence

    @property
    def body_schema_disrupted(self) -> bool:
        return self.body_schema.boundary_disruption_score >= 0.5

    @property
    def body_schema_revision_count(self) -> int:
        return self.body_schema.boundary_revision_count

    def _signature_outputs(self, signature_id: str) -> tuple[str, ...]:
        signature = self.acquisition.signatures.get(signature_id)
        if signature is None:
            return ()
        return tuple(
            sorted(
                self._channel_outputs[ref]
                for ref in signature.channel_refs
                if ref in self._channel_outputs
            )
        )

    def inferred_mapping_signature(self) -> tuple[tuple[str, str], ...]:
        """Observer projection of strongest current opaque action->input mapping."""
        by_output: dict[str, tuple[str, float]] = {}
        for estimate in self.agency_model.estimates_for(CausalSourceKind.INTERVENTION):
            effect = self.effect_space.get(estimate.effect_id)
            if effect is None:
                continue
            inputs = tuple(
                sorted(
                    self._signal_to_input[feature]
                    for feature in effect.feature_refs
                    if feature in self._signal_to_input
                )
            )
            if not inputs:
                continue
            for output in self._signature_outputs(estimate.source_ref):
                candidate = (inputs[0], float(estimate.confidence))
                current = by_output.get(output)
                if current is None or candidate[1] > current[1]:
                    by_output[output] = candidate
        return tuple(
            sorted((output, input_id) for output, (input_id, _confidence) in by_output.items())
        )

    def agency_snapshot(self) -> tuple[tuple[str, str, str, float], ...]:
        return tuple(
            sorted(
                (
                    estimate.source_kind.value,
                    estimate.source_ref,
                    estimate.effect_id,
                    round(float(estimate.confidence), 12),
                )
                for estimate in self.agency_model.estimates
            )
        )

    @staticmethod
    def _signal_ref(channel: str) -> str:
        digest = hashlib.sha256(f"reduced-symbiont-signal:{channel}".encode("utf-8")).hexdigest()[
            :24
        ]
        return f"signal.{digest}"

    @staticmethod
    def _state_ref(tick: int, phase: str) -> str:
        return f"state.reduced.{phase}.{tick}"

    def _agency_confidence_for_output(self, output: str) -> float:
        channel_ref = opaque_channel_ref(output)
        values = [
            estimate.confidence
            for estimate in self.agency_model.estimates_for(CausalSourceKind.INTERVENTION)
            if channel_ref
            in (
                signature.channel_refs
                if (signature := self.acquisition.signatures.get(estimate.source_ref)) is not None
                else ()
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

        attempt = self.acquisition.pending_attempt
        if attempt is None:
            # Bodily/environmental change without an organism command is a
            # passive counterfactual window, never evidence of agency.
            self.acquisition.observe_passive_window(
                tick_start=self.total_ticks - 1,
                tick_end=self.total_ticks,
                context_ref="context.reduced",
                prior_state_ref=self._state_ref(self.total_ticks - 1, "before"),
                resulting_state_ref=self._state_ref(self.total_ticks, "after"),
                changes=effect_changes,
            )
            return
        effect = self.effect_space.observe(effect_changes)
        transition = self.acquisition.close_attempt(
            tick=self.total_ticks,
            state_before_ref=self._state_ref(self.total_ticks - 1, "before"),
            state_after_ref=self._state_ref(self.total_ticks, "after"),
            prediction_ref=(
                f"prediction.reduced.{self.total_ticks - 1}" if self.last_inputs else None
            ),
            observed_effect_id=(effect.effect_id if effect is not None else None),
            observed_changes=effect_changes,
            prediction_error=PredictionError(
                magnitude=max(0.0, float(prediction_error)),
                uncertainty=min(1.0, max(0.0, float(prediction_error))),
                novelty=min(1.0, max(0.0, float(prediction_error))),
            ),
        )
        self.acquisition.learn(transition, body_schema=self.body_schema)
        self._converge_competence(attempt.intervention_signature_id)

    @staticmethod
    def _competence_id_for_signature(signature_id: str) -> tuple[str, str]:
        digest = hashlib.sha256(
            f"reduced-symbiont-action:{signature_id}".encode("utf-8")
        ).hexdigest()[:24]
        return f"competence.{digest}", digest

    def competence_for_signature(self, signature_id: str) -> str | None:
        """The reduced competence whose controller replays this intervention family."""
        competence_id, _digest = self._competence_id_for_signature(signature_id)
        return competence_id if self.competence_library.get(competence_id) is not None else None

    def _converge_competence(self, signature_id: str) -> None:
        """Reduced controller = one recurrent intervention family (§28, §84).

        The same canonical convergence gate as ActionDomain: a recurrent
        pattern becomes a competence only on an agentic, controllable learned
        dimension whose effect is an EffectSpace effect.
        """
        command = self.action_domain.last_motor_command
        if (
            command is None
            or self._current_surface_fingerprint is None
            or self.acquisition.signatures.attempt_support(signature_id) < 2
        ):
            return
        grounding = self.acquisition.ground_competence(
            controller_seed_ref=signature_id,
            patterns=(dict(command.channels),),
        )
        if grounding is None:
            return
        competence_id, digest = self._competence_id_for_signature(signature_id)
        control = grounding.controllability
        failures = max(0, int(round(control.action_support * (1.0 - control.reliability))))
        competence = self.competence_library.get(competence_id)
        if competence is None:
            competence = MotorCompetence(
                competence_id=competence_id,
                controller_id=f"controller.{digest}",
                effect_id=grounding.effect_id,
                evidence=CompetenceEvidence(
                    controller_seed_ref=signature_id,
                    effect_evidence_refs=(grounding.effect_id,),
                    controllability_evidence_refs=grounding.evidence_refs,
                    support=control.action_support,
                    failures=failures,
                    reproducibility=control.reliability,
                    controllability=control.confidence,
                    directional_consistency=control.reliability,
                ),
                controller_strategy_ref=signature_id,
            )
            self.competence_library.add(competence)
        else:
            competence.effect_id = grounding.effect_id
            evidence = competence.evidence
            evidence.effect_evidence_refs = tuple(
                dict.fromkeys(evidence.effect_evidence_refs + (grounding.effect_id,))
            )
            evidence.controllability_evidence_refs = tuple(
                dict.fromkeys(evidence.controllability_evidence_refs + grounding.evidence_refs)
            )[-64:]
            evidence.support = max(evidence.support, control.action_support)
            evidence.failures = min(evidence.support, max(evidence.failures, failures))
            evidence.reproducibility = max(evidence.reproducibility, control.reliability)
            evidence.controllability = max(evidence.controllability, control.confidence)
            evidence.directional_consistency = max(
                evidence.directional_consistency, control.reliability
            )
        self.competence_execution_bindings.bind_from_evidence(
            competence_id=competence_id,
            surface_fingerprint=self._current_surface_fingerprint,
            effect_id=grounding.effect_id,
            evidence_refs=grounding.evidence_refs,
            reliability=control.reliability,
            controllability=control.confidence,
            tick=self.total_ticks,
        )

    def _update_body_boundary(
        self,
        current_inputs: Mapping[str, float],
        prediction_error: float,
    ) -> None:
        self_caused = {
            self._signal_to_input[feature_ref]
            for feature_ref in self.acquisition.self_caused_features(min_confidence=0.35)
            if feature_ref in self._signal_to_input
        } & set(current_inputs)

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
        current_inputs = {str(key): float(value) for key, value in opaque_inputs.items()}
        deltas = {
            channel: value - self.last_inputs.get(channel, value)
            for channel, value in current_inputs.items()
        }

        residuals = self.sensorimotor_model.observe(
            deltas,
            tick=self.total_ticks,
        )
        prediction_error = (
            sum(item.error for item in residuals) / len(residuals) if residuals else 0.0
        )
        self._last_prediction_error = prediction_error

        self._record_transition(
            deltas=deltas,
            prediction_error=prediction_error,
        )
        self._update_body_boundary(current_inputs, prediction_error)
        self.self_model.record_tick(
            schema_confidence=self.body_schema.boundary_confidence,
            prediction_error=prediction_error,
        )

        confidence_values = tuple(estimate.confidence for estimate in self.agency_model.estimates)
        mean_confidence = (
            sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        )

        # Tick t evidence changes expression for t+1. This reduced runtime
        # receives no evaluator/world semantic signal.
        if self.genome is not None and self.gene_expression_state is not None:
            bounded_error = max(0.0, min(1.0, abs(float(prediction_error))))
            signals = RegulatorySignals(
                uncertainty=max(bounded_error, 1.0 - mean_confidence),
                novelty=bounded_error,
                prediction_error=bounded_error,
                controllability_loss=max(0.0, min(1.0, 1.0 - mean_confidence)),
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
            self.learning_rate = self.gene_expression_state.effective_learning_rate
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
                    noise = self._rng.gauss(0.0, max(0.001, self.exploration_rate))
                    level = max(0.0, min(1.0, previous + noise))
            next_activations[output] = level

        if current_inputs:
            self.sensorimotor_model.predict(
                next_activations,
                tuple(sorted(current_inputs)),
            )

        delivered_activations: dict[str, float] = {}
        driven = {key: value for key, value in next_activations.items() if value > 0.0}
        if next_activations:
            if not self.action_domain.enabled or self.action_domain.surface is None:
                raise RuntimeError(
                    "Symbiont produced motor output without an attached ActionDomain surface"
                )
        if driven:
            proposal_id = (
                "proposal.reduced."
                + hashlib.sha256(
                    f"{self.symbiont_id}:{self.total_ticks}:{sorted(next_activations.items())}".encode(
                        "utf-8"
                    )
                ).hexdigest()[:24]
            )
            # §7.3: exploration never needs (nor names) a competence.
            proposal = ActionProposal(
                proposal_id=proposal_id,
                source=ActionSource.EXPLORATION,
                effect_target_id=None,
                competence_id=None,
                justification=ActionJustification(
                    originating_need_id="internal.sensorimotor-uncertainty",
                ),
                evaluation=ActionEvaluation(
                    epistemic_relevance=max(0.0, min(1.0, self.exploration_rate)),
                    effect_confidence=max(
                        (self._agency_confidence_for_output(output) for output in next_activations),
                        default=0.0,
                    ),
                    uncertainty=max(0.0, min(1.0, 1.0 - mean_confidence)),
                ),
            )
            commitment = self.action_domain.commit(
                proposal,
                tick=self.total_ticks,
                controller_id="controller.reduced-exploration",
                maximum_duration=1,
            )
            command = self.action_domain.issue_command(
                next_activations,
                tick=self.total_ticks,
            )
            actuations = self.action_domain.execute_command(command)
            delivered_activations = {
                actuation.actuator_id: float(actuation.delivered) for actuation in actuations
            }
            self.acquisition.open_attempt(
                command=command,
                commitment=commitment,
                context_ref="context.reduced",
                actuation_ref=f"actuation.{command.command_id}",
                tick=self.total_ticks,
            )
        else:
            delivered_activations = {output: 0.0 for output in next_activations}

        self.last_inputs = current_inputs
        self.last_activations = dict(delivered_activations)
        return delivered_activations


__all__ = ["Symbiont"]
