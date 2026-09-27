"""Single causal authority for organism-owned physical action."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any, Mapping

from ...actuation.acquisition import AgencyAcquisition, CausalUpdate
from ...actuation.action import (
    ActionEvaluation,
    ActionJustification,
    ActionProposal,
    ActionSource,
    MotorCommand,
)
from ...actuation.arbitration import ActionArbitrator
from ...actuation.binding import CompetenceExecutionBindingRegistry
from ...actuation.checkpoint import export_actuation_state
from ...actuation.commitment import ActionCommitment, CommitmentStatus
from ...actuation.competence import CompetenceEvidence, CompetenceLibrary, MotorCompetence
from ...actuation.composition import CompositionEngine
from ...actuation.controller import ControllerFrame
from ...actuation.dimension import ActionDimensionDiscoveryPolicy, ActionDimensionRegistry
from ...actuation.effects import EffectSpace
from ...actuation.evidence import (
    CausalEvidenceLedger,
    PredictionError,
    SensorimotorTransition,
)
from ...actuation.exploration import ExplorationPolicy, ExplorationSignals
from ...actuation.intervention import InterventionSignatureRegistry, opaque_channel_ref
from ...actuation.model import (
    AgencyModel,
    CausalSourceKind,
    CompetenceEffectModel,
    ControllabilityModel,
    EffectPrediction,
)
from ...actuation.proposer import ActuatorEvidenceModel
from ...actuation.sensorimotor import CompetenceDevelopmentEngine
from ...actuation.state import SensorimotorV2Snapshot
from ...actuation.surface import ActuatorSurface
from ...actuation.system import ActuatorSystem
from ...actuation.types import Actuation, MotorIntent
from ...agency.affordance import ActionAffordance
from ...agency.affordances import AffordanceResolver
from ...agency.executive_outcome import CausalRevisionState, ExecutiveKey, ExecutiveModulation
from ...agency.intention import ActionIntent, AdmissionRoute, IntentStatus
from ...agency.prospective import ProspectiveDecision
from ...genetics.expression import GeneExpressionState
from ...host.percepts import Percept
from ...sensory import SensorySystem
from ..cognition.bridge import CognitiveBridge, CognitiveBridgeResult
from ..embodiment.body_schema import BodySchemaEngine
from ..embodiment.homeostasis import HomeostaticController
from ..regulation import InnateReactivity, ReactiveMemory, ReactiveState
from .context import TickContext
from .intention import (
    CAUSAL_BINDING_INVALIDATED,
    EMBODIMENT_CHANGED,
    HOMEOSTATIC_EMERGENCY,
    NEW_MOTOR_AUTHORITY,
    PROPOSAL_NOT_SELECTED,
    PROTECTION_TAKES_PRIORITY,
    RECONSIDERED,
    SUPERSEDED_BY_OTHER_ACTION,
    SUPERSEDED_BY_PROTECTION,
    ExecutiveMode,
    IntentionDomain,
    IntentionPolicy,
)

_BODY_BOUNDARY_AGENCY = 0.35


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ActionServices:
    """Explicit collaborators for one action-domain tick.

    These are observation/feedback services, never alternative action
    authorities.  The only route across the body boundary remains
    ActionDomain.issue_command() -> execute_command().
    """

    sensory_system: SensorySystem
    homeostasis: HomeostaticController
    innate_reactivity: InnateReactivity
    reactive_memory: ReactiveMemory
    body_schema: BodySchemaEngine
    cognitive_bridge: CognitiveBridge | None
    gene_expression_state: GeneExpressionState | None
    choose_acquired_action: Callable[..., ProspectiveDecision | None]
    schedule_homeostatic_action_credit: Callable[..., None]


@dataclass(frozen=True, slots=True)
class ActionTrace:
    proposal_id: str
    commitment_id: str
    command_id: str


@dataclass(frozen=True, slots=True)
class ActionCognitionProjection:
    active_motor_actuator_ids: tuple[str, ...]
    motor_effect_actuator_ids: tuple[str, ...]
    active_competence_ids: tuple[str, ...]
    # Executive state already reconciled this tick (T3), visible to T4 cognition.
    active_intent_id: str | None = None
    active_intent_status: str | None = None
    intent_outcomes: tuple[tuple[str, str, str, str | None], ...] = ()
    # Every competence/controller structure that still exists (known or not
    # currently usable); lets cognition retire demand about vanished ones.
    known_competence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionDevelopmentProjection:
    actuator_count: int
    active_actuator_count: int


@dataclass(frozen=True, slots=True)
class ActionObservation:
    """Consequences observed at the start of a tick (T0-T3).

    Produced before new cognition runs and consumed by the act phase of the
    same tick.  Snapshots are ephemeral and never persisted.
    """

    tick: int
    baseline: dict[str, float]
    body_state: dict[str, float]


@dataclass(frozen=True, slots=True)
class ActionStepResult:
    """Passive report that a committed command crossed the body boundary."""

    action_id: str
    executed: bool
    result: object | None = None
    reason: str | None = None


class ActionDomain:
    """Canonical causal owner of the Sensorimotor v2 action path."""

    def __init__(
        self,
        *,
        organism_id: str,
        enabled: bool,
        surface: ActuatorSurface | None,
        selection_threshold: float = 0.1,
        actuator_evidence: ActuatorEvidenceModel | None = None,
        competence_development: CompetenceDevelopmentEngine | None = None,
        actuator_system: ActuatorSystem | None = None,
        embodiment_id: str | None = None,
        acquisition: AgencyAcquisition | None = None,
        dimension_policy: ActionDimensionDiscoveryPolicy | None = None,
        executive_mode: ExecutiveMode = ExecutiveMode.FULL,
        intention_policy: IntentionPolicy | None = None,
    ) -> None:
        if not organism_id:
            raise ValueError("organism_id must not be empty")
        if not 0.0 <= float(selection_threshold) <= 1.0:
            raise ValueError("selection_threshold must be within [0,1]")
        if enabled and surface is None:
            raise ValueError("enabled ActionDomain requires an actuator surface")
        self.organism_id = organism_id
        self.enabled = bool(enabled)
        self.surface = surface
        self.embodiment_id = embodiment_id
        self.selection_threshold = float(selection_threshold)
        self._actuator_evidence = actuator_evidence or (
            ActuatorEvidenceModel(surface, organism_id=organism_id)
            if self.enabled and surface is not None
            else None
        )
        self._competence_development = competence_development or (
            CompetenceDevelopmentEngine(
                surface.actuator_ids,
                organism_id=organism_id,
                max_concurrent=None,
                embodiment_fingerprint=surface.contract_fingerprint,
            )
            if self.enabled and surface is not None
            else None
        )
        self._actuator_system = actuator_system or ActuatorSystem()

        self.arbitrator = ActionArbitrator()
        # Attempts, intervention families, effects, causal evidence,
        # controllability, agency and learned ActionDimensions.  Dimensions are
        # never bootstrapped from the actuator surface: a fresh organism knows
        # 0 of its N physical motor opportunities as dimensions.
        self.acquisition = acquisition or AgencyAcquisition(dimension_policy=dimension_policy)
        self.acquisition.bind_surface(
            surface.actuator_ids if self.enabled and surface is not None else None,
            surface_fingerprint=(
                surface.contract_fingerprint if self.enabled and surface is not None else None
            ),
        )
        self.competence_library = CompetenceLibrary()
        self.execution_bindings = CompetenceExecutionBindingRegistry()
        self.exploration_policy = ExplorationPolicy()
        # Executive loop: persistent cognitive commitment to a consequence.
        # Only E2/E3/E5 control arms change the mode; the organism default is FULL.
        self.executive_mode = ExecutiveMode(executive_mode)
        self.intention = IntentionDomain(organism_id=organism_id, policy=intention_policy)
        self.intention.revision_probe = self.causal_revision_state
        self.intention.provenance = self.acquisition.provenance
        self.last_affordances: tuple[ActionAffordance, ...] = ()
        self.last_intent_proposal_id: str | None = None
        self.composition_engine = CompositionEngine()

        self.active_commitment: ActionCommitment | None = None
        self.last_proposal: ActionProposal | None = None
        self.last_motor_command: MotorCommand | None = None
        self.last_transition: SensorimotorTransition | None = None
        self.last_causal_update: CausalUpdate | None = None
        self.last_action_source = "none"
        self.last_motor_intent: MotorIntent | None = None
        self.last_actuation: Actuation | None = None
        self.last_motor_intents: tuple[MotorIntent, ...] = ()
        self.last_actuations: tuple[Actuation, ...] = ()
        self.last_executed_controller_seed_id: str | None = None

        self.exploration_strength_memory: dict[str, float] = {}
        self.active_exploration_preference: tuple[str, ...] = ()
        self.last_exploration_signals: dict[str, ExplorationSignals] = {}
        self.composition_predecessor_id: str | None = None
        self.active_composition_children: tuple[str, ...] = ()
        self.active_composition_index = 0
        self.effect_by_commitment: dict[str, str] = {}
        self.pending_transition: dict[str, Any] | None = None
        self.pending_motor_observation: tuple[tuple[str, float, dict[str, float] | None], ...] = ()
        self.pending_proprioception: dict[str, float] = {}
        self.pending_reactive_credit: tuple[str, str, float] | None = None
        self.last_reactive_state: ReactiveState | None = None
        self._trace_by_command: dict[str, ActionTrace] = {}

    # Canonical causal state is owned by the shared acquisition component.
    @property
    def effect_space(self) -> EffectSpace:
        return self.acquisition.effect_space

    @property
    def causal_evidence(self) -> CausalEvidenceLedger:
        return self.acquisition.causal_evidence

    @property
    def effect_model(self) -> CompetenceEffectModel:
        return self.acquisition.effect_model

    @property
    def controllability_model(self) -> ControllabilityModel:
        return self.acquisition.controllability_model

    @property
    def agency_model(self) -> AgencyModel:
        return self.acquisition.agency_model

    @property
    def action_dimensions(self) -> ActionDimensionRegistry:
        return self.acquisition.action_dimensions

    @property
    def intervention_signatures(self) -> InterventionSignatureRegistry:
        return self.acquisition.signatures

    @property
    def actuator_evidence(self) -> ActuatorEvidenceModel | None:
        return self._actuator_evidence

    @property
    def competence_development(self) -> CompetenceDevelopmentEngine | None:
        return self._competence_development

    @property
    def current_surface_fingerprint(self) -> str | None:
        return self.surface.contract_fingerprint if self.surface is not None else None

    @property
    def active_repertoire(self) -> tuple[str, ...]:
        return (
            self._actuator_evidence.active_repertoire if self._actuator_evidence is not None else ()
        )

    def predict_competence_effect(
        self,
        *,
        competence_id: str,
        context_id: str | None,
    ) -> EffectPrediction | None:
        """Forward expectation of a competence from organism-owned knowledge only.

        Competence-level experience wins; a converged but never-executed
        competence is expected to produce the EffectSpace effect its grounding
        dimension reliably caused on this body.
        """
        competence = self.competence_library.get(competence_id)
        footprint_effect = (
            competence is not None
            and competence.effect_id is not None
            and self.acquisition.footprint_effects
            and self.effect_space.footprint_atoms(competence.effect_id) is not None
        )
        if not footprint_effect:
            # Whole-state mode: competence-level experience wins.
            prediction = self.effect_model.predict(
                competence_id=competence_id, context_id=context_id
            )
            if prediction is not None:
                return prediction
        binding = self.execution_bindings.get(competence_id)
        if (
            competence is None
            or competence.effect_id is None
            or binding is None
            or self.effect_space.get(competence.effect_id) is None
        ):
            return None
        material = f"grounding|{competence_id}|{competence.effect_id}|{len(binding.evidence_refs)}"
        return EffectPrediction(
            prediction_id="prediction." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24],
            competence_id=competence_id,
            context_id=context_id,
            effect_id=competence.effect_id,
            confidence=binding.reliability,
            support=len(binding.evidence_refs),
        )

    def causal_revision_state(self, key: ExecutiveKey) -> CausalRevisionState:
        """Material causal/binding state of one relation (EOL §7), read-only.

        Estimate revisions advance only when the competence itself acts, so
        activity of other competences never changes this state.  Competence
        estimates are context-specific; the relation's revision is the latest
        across its contexts.
        """
        competence_id, effect_id = key
        competence = self.competence_library.get(competence_id)
        binding = self.execution_bindings.get(competence_id)

        def latest(model) -> int | None:
            return max(
                (
                    estimate.last_updated_tick
                    for estimate in model.for_source(CausalSourceKind.COMPETENCE, competence_id)
                    if estimate.effect_id == effect_id
                ),
                default=None,
            )

        return CausalRevisionState(
            binding_fingerprint=(
                f"{binding.surface_fingerprint}|{binding.effect_id}|{binding.last_evidence_tick}"
                if binding is not None
                else None
            ),
            executable=competence is not None and self.competence_is_executable(competence),
            controllability_revision=latest(self.acquisition.controllability_model),
            agency_revision=latest(self.acquisition.agency_model),
        )

    def executive_modulation(self, affordance: ActionAffordance) -> ExecutiveModulation:
        """Executive history of one afforded candidate, for admission only."""
        return self.intention.admission_modulation(
            competence_id=affordance.competence_id,
            anticipated_effect_id=affordance.anticipated_effect_id,
        )

    def competence_is_executable(self, competence: MotorCompetence) -> bool:
        """Bound on this surface, mature, and its controller can actually run.

        A library competence can outlive its controller seed (the development
        engine's primitive pool is bounded); admitting it would fail the
        controller on every attempt and loop, so it is not executable.
        """
        if not self.execution_bindings.is_executable(
            competence,
            surface_fingerprint=self.current_surface_fingerprint,
        ):
            return False
        if self._competence_development is None:
            return True
        return all(
            self._competence_development.can_activate(leaf)
            for leaf in self._flatten_competence_controller(competence.competence_id)
        )

    def begin_embodiment(
        self,
        *,
        surface: ActuatorSurface,
        embodiment_id: str | None,
        tick: int,
    ) -> None:
        if self.active_commitment is not None and self.active_commitment.active:
            self.active_commitment.terminate(
                tick=tick,
                status=CommitmentStatus.INVALIDATED,
                reason="embodiment_changed",
            )
        self.surface = surface
        self.embodiment_id = embodiment_id
        self.active_exploration_preference = ()
        self.pending_transition = None
        # §80: the open attempt belongs to the old body; learned dimensions stay
        # known but their current availability is re-derived for this surface.
        self.acquisition.discard_pending_attempt()
        self.acquisition.bind_surface(
            surface.actuator_ids, surface_fingerprint=surface.contract_fingerprint
        )
        held = self.intention.active
        if held is not None and not held.terminal:
            self.intention.invalidate(held.intent_id, reason=EMBODIMENT_CHANGED, tick=tick)
        self.last_affordances = ()
        self.pending_motor_observation = ()
        self.pending_proprioception = {}
        self.execution_bindings = CompetenceExecutionBindingRegistry()

    def commit(
        self,
        proposal: ActionProposal,
        *,
        tick: int,
        controller_id: str,
        maximum_duration: int | None = None,
    ) -> ActionCommitment:
        if not self.enabled or self.surface is None:
            raise RuntimeError("action domain has no executable surface")
        if self.active_commitment is not None and self.active_commitment.active:
            self.active_commitment.terminate(
                tick=tick,
                status=CommitmentStatus.INTERRUPTED,
                reason="superseded_by_new_proposal",
            )
        digest = hashlib.sha256(
            f"{proposal.proposal_id}:{tick}:{self.surface.contract_fingerprint}".encode("utf-8")
        ).hexdigest()[:24]
        commitment = ActionCommitment(
            commitment_id=f"commitment.{digest}",
            proposal_id=proposal.proposal_id,
            effect_target_id=proposal.effect_target_id,
            competence_id=proposal.competence_id,
            started_tick=tick,
            controller_id=controller_id,
            surface_fingerprint=self.surface.contract_fingerprint,
            embodiment_id=self.embodiment_id,
            intent_id=proposal.intent_id,
            maximum_duration=maximum_duration,
        )
        self.last_proposal = proposal
        self.active_commitment = commitment
        self.last_action_source = proposal.source.value
        return commitment

    def issue_command(self, channels: Mapping[str, float], *, tick: int) -> MotorCommand:
        commitment = self.active_commitment
        surface = self.surface
        if commitment is None or not commitment.active:
            raise RuntimeError("motor output has no active organism-owned commitment")
        if surface is None:
            raise RuntimeError("motor output has no actuator surface")
        if not commitment.compatible_with(
            surface.contract_fingerprint,
            embodiment_id=self.embodiment_id,
        ):
            commitment.terminate(
                tick=tick,
                status=CommitmentStatus.INVALIDATED,
                reason="commitment_surface_or_embodiment_changed",
            )
            raise RuntimeError("active commitment does not belong to current embodiment")
        material = "|".join(f"{key}:{float(value):.12g}" for key, value in sorted(channels.items()))
        digest = hashlib.sha256(
            f"{commitment.commitment_id}:{tick}:{material}".encode("utf-8")
        ).hexdigest()[:24]
        command = MotorCommand.from_mapping(
            command_id=f"command.{digest}",
            commitment_id=commitment.commitment_id,
            controller_id=commitment.controller_id,
            competence_id=commitment.competence_id,
            surface_fingerprint=surface.contract_fingerprint,
            channels=channels,
            issued_at_tick=tick,
            embodiment_id=self.embodiment_id,
        )
        self.last_motor_command = command
        self._trace_by_command[command.command_id] = ActionTrace(
            proposal_id=commitment.proposal_id,
            commitment_id=commitment.commitment_id,
            command_id=command.command_id,
        )
        if len(self._trace_by_command) > 4096:
            del self._trace_by_command[next(iter(self._trace_by_command))]
        return command

    def issue_controller_frame(
        self,
        frame: ControllerFrame,
        *,
        context: TickContext,
    ) -> MotorCommand:
        commitment = self.active_commitment
        if commitment is None or not commitment.active:
            raise RuntimeError("controller frame has no active commitment")
        if frame.controller_id != commitment.controller_id:
            raise RuntimeError("controller frame belongs to another commitment controller")
        if frame.competence_id != commitment.competence_id:
            raise RuntimeError("controller frame competence does not match commitment")
        channels = dict(frame.channels)
        if len(channels) != len(frame.channels):
            raise RuntimeError("controller frame contains duplicate actuator channels")
        return self.issue_command(
            channels,
            tick=context.symbiont_tick,
        )

    def execute_command(self, command: MotorCommand) -> tuple[Actuation, ...]:
        commitment = self.active_commitment
        if commitment is None or command.commitment_id != commitment.commitment_id:
            raise RuntimeError("motor command is not owned by the active commitment")
        if self.surface is None:
            raise RuntimeError("action domain has no actuator surface")
        if command.command_id not in self._trace_by_command:
            raise RuntimeError("motor command has no action trace")
        actuations = self._actuator_system.execute_command(command, self.surface)
        self.last_actuations = actuations
        return actuations

    def trace_action(self, command_id: str) -> ActionTrace | None:
        return self._trace_by_command.get(command_id)

    def motor_percept_snapshot(
        self, percepts: tuple[Percept, ...], *, sensory_system: SensorySystem
    ) -> dict[str, float]:
        # Never let the motor-discovery statistic "discover" an actuator
        # merely because requested/delivered proprioception echoes the command
        # itself. Those channels are for body/cognition, not controllability.
        proprioceptive_names = {
            sensor.cognitive_name
            for sensor in sensory_system.sensors
            if any(source_id.startswith("motor.") for source_id in sensor.source_ids)
        }
        values = {
            percept.name: float(percept.value)
            for percept in percepts
            if (
                percept.name not in proprioceptive_names
                and percept.value is not None
                and math.isfinite(float(percept.value))
            )
        }
        # Direct actuator-effect learning must see the same complete
        # currently perceived non-command body surface as the temporal learner.
        # Lexicographic truncation over opaque ids would make later channels
        # causally invisible for reasons unrelated to the body or organism.
        return dict(sorted(values.items()))

    def sensorimotor_body_snapshot(
        self,
        percepts: tuple[Percept, ...],
        *,
        sensory_system: SensorySystem,
    ) -> dict[str, float]:
        """Richer opaque state for learned body dynamics.

        Motor command echoes remain excluded so the learner must model bodily
        consequences rather than trivially reading its own requested vector.
        """
        proprioceptive_names = {
            sensor.cognitive_name
            for sensor in sensory_system.sensors
            if any(source_id.startswith("motor.") for source_id in sensor.source_ids)
        }
        values = {
            percept.name: float(percept.value)
            for percept in percepts
            if (
                percept.name not in proprioceptive_names
                and percept.value is not None
                and math.isfinite(float(percept.value))
            )
        }
        # Preserve the complete currently perceived bodily state.  A
        # lexicographic slice over opaque sensor ids silently changes which
        # physical consequences are learnable and biases motor discovery.
        return dict(sorted(values.items()))

    def complete_pending_motor_observation(
        self, percepts: tuple[Percept, ...], *, tick: int, sensory_system: SensorySystem
    ) -> tuple[str, ...]:
        pending = self.pending_motor_observation
        if not pending or self._actuator_evidence is None:
            return ()
        after = self.motor_percept_snapshot(percepts, sensory_system=sensory_system)
        promoted: list[str] = []
        for actuator_id, activation, before in pending:
            if before is not None:
                for percept_id in sorted(set(before) & set(after)):
                    self._actuator_evidence.record_effect(
                        actuator_id,
                        percept_id,
                        activation=activation,
                        delta_percept=after[percept_id] - before[percept_id],
                        tick=tick,
                    )
                self._actuator_evidence.consider_natural_evidence(actuator_id)
            if actuator_id in self._actuator_evidence.active_repertoire:
                promoted.append(actuator_id)
        self.pending_motor_observation = ()
        return tuple(dict.fromkeys(promoted))

    def development_projection(self) -> ActionDevelopmentProjection:
        return ActionDevelopmentProjection(
            actuator_count=(len(self.surface.actuator_ids) if self.surface is not None else 0),
            active_actuator_count=(
                len(self._actuator_evidence.active_repertoire)
                if self._actuator_evidence is not None
                else 0
            ),
        )

    def prepare_cognition(
        self,
        percepts: tuple[Percept, ...],
        *,
        context: TickContext,
        sensory_system: SensorySystem,
    ) -> ActionCognitionProjection:
        newly_confirmed = self.complete_pending_motor_observation(
            percepts,
            tick=context.symbiont_tick,
            sensory_system=sensory_system,
        )
        established = (
            self._actuator_evidence.active_repertoire if self._actuator_evidence is not None else ()
        )
        motor_effect_actuator_ids = tuple(sorted(set((*newly_confirmed, *established))))
        active_competence_ids = (
            tuple(
                primitive.primitive_id
                for primitive in self._competence_development.cognitive_primitives
            )
            if self._competence_development is not None
            else ()
        )
        intent = self.intention.active
        return ActionCognitionProjection(
            active_motor_actuator_ids=tuple(established),
            motor_effect_actuator_ids=motor_effect_actuator_ids,
            active_competence_ids=active_competence_ids,
            active_intent_id=intent.intent_id if intent is not None else None,
            active_intent_status=intent.status.value if intent is not None else None,
            intent_outcomes=tuple(
                (outcome.intent_id, outcome.competence_id, outcome.status.value, outcome.reason)
                for outcome in self.intention.last_outcomes
            ),
            known_competence_ids=tuple(
                sorted(
                    {item.competence_id for item in self.competence_library.items}
                    | {
                        primitive.primitive_id
                        for primitive in (
                            self._competence_development.primitives
                            if self._competence_development is not None
                            else ()
                        )
                    }
                )
            ),
        )

    def _flatten_competence_controller(
        self,
        competence_id: str,
        *,
        seen: frozenset[str] = frozenset(),
    ) -> tuple[str, ...]:
        if competence_id in seen:
            raise RuntimeError("cyclic competence composition")
        competence = self.competence_library.get(competence_id)
        if competence is None or not competence.parent_competence_ids:
            return (competence_id,)
        next_seen = seen | {competence_id}
        flattened: list[str] = []
        for child_id in competence.parent_competence_ids:
            flattened.extend(
                self._flatten_competence_controller(
                    child_id,
                    seen=next_seen,
                )
            )
        return tuple(flattened)

    def _activate_competence_controller(self, competence_id: str) -> bool:
        if self._competence_development is None:
            return False
        leaves = self._flatten_competence_controller(competence_id)
        if not leaves:
            return False
        first_leaf = leaves[0]
        self.active_composition_children = leaves if len(leaves) > 1 else ()
        self.active_composition_index = 0
        return self._competence_development.activate_primitive(first_leaf)

    def _materialize_composition(
        self,
        evidence,
    ) -> MotorCompetence | None:
        if not evidence.established or self.surface is None:
            return None
        digest = hashlib.sha256(
            (
                f"{evidence.first_competence_id}>"
                f"{evidence.second_competence_id}>"
                f"{evidence.effect_id}"
            ).encode("utf-8")
        ).hexdigest()[:24]
        competence_id = f"competence.composed.{digest}"
        existing = self.competence_library.get(competence_id)
        evidence_ref = f"composition.{digest}"
        derived = CompetenceEvidence(
            controller_seed_ref=f"sequence:{evidence.first_competence_id}>{evidence.second_competence_id}",
            effect_evidence_refs=(evidence.effect_id,),
            controllability_evidence_refs=(evidence_ref,),
            support=evidence.support,
            failures=evidence.failures,
            reproducibility=evidence.reproducibility,
            controllability=evidence.reproducibility,
            directional_consistency=1.0,
        )
        if existing is not None:
            existing.evidence = derived
            return existing
        competence = MotorCompetence(
            competence_id=competence_id,
            controller_id=f"controller.{competence_id}",
            effect_id=evidence.effect_id,
            evidence=derived,
            parent_competence_ids=(
                evidence.first_competence_id,
                evidence.second_competence_id,
            ),
            controller_strategy_ref=derived.controller_seed_ref,
        )
        self.competence_library.add(competence)
        self.execution_bindings.bind_from_evidence(
            competence_id=competence.competence_id,
            surface_fingerprint=self.surface.contract_fingerprint,
            effect_id=evidence.effect_id,
            evidence_refs=(evidence_ref,),
            reliability=evidence.reproducibility,
            controllability=evidence.reproducibility,
            tick=max(0, int(getattr(evidence, "last_tick", 0) or 0)),
        )
        return competence

    def _record_competence_completion(
        self,
        competence_id: str,
        *,
        commitment_id: str,
        tick: int,
    ) -> None:
        self.acquisition.record_commitment_pattern(
            commitment_id=commitment_id,
            controller_seed_ref=competence_id,
            tick=tick,
        )
        effect_id = self.effect_by_commitment.pop(commitment_id, None)
        predecessor = self.composition_predecessor_id
        if predecessor is not None and predecessor != competence_id:
            if effect_id is None:
                self.composition_engine.observe_absence(
                    predecessor,
                    competence_id,
                )
            else:
                evidence = self.composition_engine.observe(
                    predecessor,
                    competence_id,
                    effect_id,
                    success=True,
                )
                self._materialize_composition(evidence)
        self.composition_predecessor_id = competence_id

    def _advance_or_complete_competence(
        self,
        *,
        tick: int,
    ) -> None:
        commitment = self.active_commitment
        if (
            commitment is None
            or not commitment.active
            or commitment.competence_id is None
            or self._competence_development is None
            or self._competence_development.active_primitive_id is not None
        ):
            return
        if self.active_composition_children and self.active_composition_index + 1 < len(
            self.active_composition_children
        ):
            self.active_composition_index += 1
            child_id = self.active_composition_children[self.active_composition_index]
            if self._competence_development.activate_primitive(child_id):
                return
            commitment.terminate(
                tick=tick,
                status=CommitmentStatus.FAILED,
                reason="composed_child_unavailable",
            )
            self.active_composition_children = ()
            self.active_composition_index = 0
            return

        completed_id = commitment.competence_id
        completed_commitment_id = commitment.commitment_id
        commitment.terminate(
            tick=tick,
            status=CommitmentStatus.COMPLETED,
            reason="competence_completed",
        )
        self._record_competence_completion(
            completed_id,
            commitment_id=completed_commitment_id,
            tick=tick,
        )
        self.active_composition_children = ()
        self.active_composition_index = 0

    def _rank_exploration_opportunities(
        self,
        *,
        exploration_drive: float,
        reactive_state: ReactiveState,
        services: ActionServices,
    ) -> tuple[str, ...]:
        """Choose an opaque local opportunity from organism-owned evidence only."""
        if self._actuator_evidence is None:
            self.last_exploration_signals = {}
            return ()
        opportunities: list[tuple[str, ExplorationSignals]] = []
        current_strengths: dict[str, float] = {}
        physiological_cost = max(
            0.0,
            min(1.0, 1.0 - float(services.homeostasis.activity_scale)),
        )
        risk = max(0.0, min(1.0, float(reactive_state.withdrawal)))
        for state in self._actuator_evidence.states:
            activations = max(0, int(state.activations))
            strength = max(0.0, min(1.0, float(state.effect_strength)))
            previous = self.exploration_strength_memory.get(
                state.actuator_id,
                strength,
            )
            progress = max(0.0, strength - previous)
            current_strengths[state.actuator_id] = strength
            signals = ExplorationSignals(
                uncertainty=max(0.0, 1.0 - min(1.0, activations / 12.0)),
                novelty=1.0 / (1.0 + activations),
                learning_progress=progress,
                effect_relevance=max(0.0, min(1.0, exploration_drive)),
                controllability_potential=(None if activations == 0 else strength),
                physiological_cost=physiological_cost,
                risk=risk,
                causal_information_gain=self.acquisition.causal_information_gain(
                    (opaque_channel_ref(state.actuator_id),)
                ),
            )
            opportunities.append((state.actuator_id, signals))
        self.exploration_strength_memory.update(current_strengths)
        self.last_exploration_signals = dict(opportunities)
        chosen = self.exploration_policy.choose(tuple(opportunities))
        return (chosen,) if chosen is not None else ()

    def _refresh_competence_library(self, *, tick: int) -> None:
        """Converge recurrent controllers with causal knowledge (§28, Wave 4).

        A recurrent, reproducible temporal motor pattern is only a controller
        seed.  It becomes a MotorCompetence when its steps lie on a learned,
        available, controllable and agentic ActionDimension; the competence
        effect is that dimension's EffectSpace effect and its execution
        authority on this body is grounded in the same factual evidence.
        """
        if self._competence_development is None or self.surface is None:
            return
        if self.acquisition.footprint_effects:
            # Footprint effects follow current footprints: a competence
            # grounded on a provisional union is revised as its channels'
            # (or its own) footprints change (Factorized Effects §14.1).
            for competence in self.competence_library.items:
                if competence.effect_id is not None:
                    self.acquisition.revise_footprint_effect(competence.effect_id, tick=tick)
        for primitive in self._competence_development.primitives:
            existing = self.competence_library.get(primitive.primitive_id)
            if existing is not None:
                # Maturity is a projection of the controller's current
                # evidence; a competence whose controller lost reproducibility
                # must stop being executable rather than keep stale authority.
                existing.evidence = replace(
                    primitive.competence_evidence,
                    effect_evidence_refs=existing.evidence.effect_evidence_refs,
                    controllability_evidence_refs=existing.evidence.controllability_evidence_refs,
                )
                continue
            if not primitive.established:
                continue
            grounding = self.acquisition.ground_competence(
                controller_seed_ref=primitive.primitive_id,
                patterns=tuple(
                    {actuator_id: level / 7.0 for actuator_id, level in pattern if level > 0}
                    for pattern in primitive.sequence
                ),
                tick=tick,
            )
            if grounding is None:
                continue
            evidence = replace(
                primitive.competence_evidence,
                effect_evidence_refs=(grounding.effect_id,),
                controllability_evidence_refs=grounding.evidence_refs,
            )
            self.competence_library.add(
                MotorCompetence(
                    competence_id=primitive.primitive_id,
                    controller_id=f"controller.{primitive.primitive_id}",
                    effect_id=grounding.effect_id,
                    evidence=evidence,
                    controller_strategy_ref=primitive.primitive_id,
                )
            )
            self.execution_bindings.bind_from_evidence(
                competence_id=primitive.primitive_id,
                surface_fingerprint=self.surface.contract_fingerprint,
                effect_id=grounding.effect_id,
                evidence_refs=grounding.evidence_refs,
                reliability=grounding.controllability.reliability,
                controllability=grounding.controllability.confidence,
                tick=tick,
            )

    def _context_ref(self, active_concepts: tuple[str, ...]) -> str:
        surface = self.surface.contract_fingerprint if self.surface is not None else "no-surface"
        material = surface + "|" + ("|".join(active_concepts) or "opaque")
        return "context." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _opaque_changes(
        before_state: Mapping[str, float],
        after_state: Mapping[str, float],
        references: Mapping[str, str],
    ) -> dict[str, float]:
        opaque_changes: dict[str, float] = {}
        for name in sorted(set(before_state) & set(after_state)):
            opaque = references.get(name)
            if opaque is None and name.startswith(
                ("signal.", "latent.", "part.", "channel.", "internal.", "effect.")
            ):
                opaque = name
            if opaque is not None:
                opaque_changes[str(opaque)] = float(after_state[name]) - float(before_state[name])
        return opaque_changes

    def _close_attempt(
        self,
        previous: Mapping[str, Any],
        *,
        opaque_changes: Mapping[str, float],
        state_after_ref: str,
        tick: int,
        services: ActionServices,
    ) -> None:
        """T1-T2 for one motor-caused transition: effect, evidence, causal learning."""
        observed_effect = self.effect_space.observe(opaque_changes)
        observed_effect_id = observed_effect.effect_id if observed_effect is not None else None
        predicted_effect_id = previous.get("predicted_effect_id")
        prediction_error = None
        prediction_match = None
        if predicted_effect_id is not None:
            prediction_match = self.acquisition.effect_matcher.match(
                self.effect_space,
                expected_effect_id=str(predicted_effect_id),
                observed_effect_id=observed_effect_id,
            )
            prediction_error = PredictionError(
                magnitude=1.0 - prediction_match,
                uncertainty=max(
                    0.0, min(1.0, 1.0 - float(previous.get("prediction_confidence", 0.0)))
                ),
                novelty=1.0 - prediction_match,
            )
        transition = self.acquisition.close_attempt(
            tick=tick,
            state_before_ref=str(previous["state_before_ref"]),
            state_after_ref=state_after_ref,
            prediction_ref=(
                str(previous["prediction_id"])
                if previous.get("prediction_id") is not None
                else None
            ),
            observed_effect_id=observed_effect_id,
            prediction_error=prediction_error,
            observed_changes=opaque_changes,
        )
        update = self.acquisition.learn(
            transition,
            body_schema=services.body_schema,
            competence_prediction_match=prediction_match,
        )
        self.last_transition = transition
        self.last_causal_update = update
        if observed_effect_id is None:
            return
        self.effect_by_commitment[transition.commitment_id] = observed_effect_id

        # Execution authority on this body is re-grounded from the competence's
        # own real consequences; its effect identity stays the EffectSpace
        # effect established by convergence (never the first thing observed).
        competence = (
            self.competence_library.get(transition.competence_id)
            if transition.competence_id is not None
            else None
        )
        control = update.competence_controllability
        surface_fingerprint = self.current_surface_fingerprint
        if (
            competence is not None
            and control is not None
            and surface_fingerprint is not None
            and competence.effect_id is not None
            and self.acquisition.effect_matcher.match(
                self.effect_space,
                expected_effect_id=competence.effect_id,
                observed_effect_id=observed_effect_id,
            )
            > 0.0
        ):
            self.execution_bindings.bind_from_evidence(
                competence_id=competence.competence_id,
                surface_fingerprint=surface_fingerprint,
                effect_id=competence.effect_id,
                evidence_refs=(update.evidence.evidence_id,),
                reliability=control.reliability,
                controllability=max(control.confidence, competence.evidence.controllability),
                tick=tick,
            )

        # Embodiment v2 body-boundary inference is reconstructed from
        # organism-owned causal effects and agency only, from any causal
        # source — body ownership does not wait for a motor competence.
        # Controllability alone never makes a channel part of Body.
        observed_features = {
            feature
            for effect in self.effect_space.effects
            for feature in effect.feature_refs
            if not feature.startswith("channel.")
        }
        if observed_features:
            services.body_schema.observe_agency_boundary(
                observed_channels=observed_features,
                self_caused_channels=self.acquisition.self_caused_features(
                    min_confidence=_BODY_BOUNDARY_AGENCY
                )
                & observed_features,
                # Somatic membership requires independent evidence;
                # correlation/controllability is not sufficient.
                somatic_correlated_channels=(),
                prediction_error=(
                    prediction_error.magnitude if prediction_error is not None else 0.0
                ),
            )

    # -- executive loop (Agency Acquisition v1 §39-§71) ------------------------
    def affordance_resolver(self) -> AffordanceResolver:
        """A fresh read-only resolver over the current state (§36: never stored)."""
        return AffordanceResolver(
            competences=self.competence_library,
            predict=self.predict_competence_effect,
            controllability_model=self.controllability_model,
            execution_bindings=self.execution_bindings,
            effect_space=self.effect_space,
            effect_matcher=self.acquisition.effect_matcher,
            surface_fingerprint=self.current_surface_fingerprint,
            embodiment_id=self.embodiment_id,
        )

    def _stop_controller(self) -> None:
        if self._competence_development is not None:
            self._competence_development.interrupt_active_competence()
        self.active_composition_children = ()
        self.active_composition_index = 0

    def _reconcile_intent(self, *, tick: int) -> None:
        """T3: did what I was trying to produce actually happen? (§64-§70)."""
        intent = self.intention.active
        if intent is None or intent.status is not IntentStatus.ACTIVE:
            return
        commitment = self.active_commitment
        own_commitment = (
            commitment
            if commitment is not None
            and commitment.commitment_id == self.intention.active_commitment_id
            else None
        )
        transition = self.last_transition
        competence = self.competence_library.get(intent.competence_id)
        outcome = self.intention.observe_effect(
            observed_effect_id=transition.observed_effect_id if transition is not None else None,
            prediction_error=transition.prediction_error if transition is not None else None,
            effect_similarity=(
                self.acquisition.effect_matcher.match(
                    self.effect_space,
                    expected_effect_id=intent.anticipated_effect_id,
                    observed_effect_id=transition.observed_effect_id,
                )
                if transition is not None
                else None
            ),
            tick=tick,
            commitment_id=transition.commitment_id if transition is not None else None,
            commitment_status=(
                own_commitment.status
                if own_commitment is not None
                else (CommitmentStatus.INVALIDATED if commitment is None else None)
            ),
            competence_executable=(
                competence is not None and self.competence_is_executable(competence)
            ),
            embodiment_id=self.embodiment_id,
            observed_atoms=(
                self.acquisition.change_keys(transition.observed_effect_atoms)
                if transition is not None
                else ()
            ),
        )
        if outcome is None or own_commitment is None or not own_commitment.active:
            return
        # The intent owns WHAT; its commitment ends when that question is closed.
        if outcome.status is IntentStatus.SATISFIED:
            competence_id = own_commitment.competence_id
            own_commitment.terminate(
                tick=tick, status=CommitmentStatus.COMPLETED, reason="intent_satisfied"
            )
            self._stop_controller()
            if competence_id is not None:
                self._record_competence_completion(
                    competence_id, commitment_id=own_commitment.commitment_id, tick=tick
                )
        else:
            own_commitment.terminate(
                tick=tick,
                status=(
                    CommitmentStatus.INVALIDATED
                    if outcome.status is IntentStatus.INVALIDATED
                    else CommitmentStatus.FAILED
                ),
                reason=f"intent_{outcome.reason}",
            )
            self._stop_controller()

    def _intent_proposal(self, intent: ActionIntent, *, tick: int) -> ActionProposal:
        affordance = next(
            (
                item
                for item in self.last_affordances
                if item.affordance_id == intent.supporting_affordance_id
            ),
            None,
        )
        source = (
            ActionSource.COMPETENCE
            if intent.admission is AdmissionRoute.COGNITIVE
            else ActionSource.PROSPECTION
        )
        proposal_id = (
            "proposal."
            + hashlib.sha256(
                f"{self.organism_id}:{tick}:intent:{intent.intent_id}".encode("utf-8")
            ).hexdigest()[:24]
        )
        return ActionProposal(
            proposal_id=proposal_id,
            source=source,
            effect_target_id=intent.anticipated_effect_id,
            competence_id=intent.competence_id,
            intent_id=intent.intent_id,
            justification=ActionJustification(
                effect_target_id=intent.anticipated_effect_id,
                competence_id=intent.competence_id,
                prediction_id=intent.prediction_ref,
                evidence_refs=tuple(
                    ref
                    for ref in (*intent.origin_refs, intent.supporting_affordance_id)
                    if ref is not None
                ),
            ),
            evaluation=ActionEvaluation(
                epistemic_relevance=intent.epistemic_relevance,
                homeostatic_relevance=intent.homeostatic_relevance,
                effect_confidence=intent.confidence,
                controllability=(affordance.controllability if affordance is not None else None),
                uncertainty=max(0.0, 1.0 - intent.confidence),
            ),
        )

    def _executive_proposal(
        self,
        cognition: CognitiveBridgeResult | None,
        percepts: tuple[Percept, ...],
        *,
        context_ref: str,
        resolver: AffordanceResolver,
        signal_references: dict[str, str],
        services: ActionServices,
        tick: int,
    ) -> ActionProposal | None:
        """T6-T7: deliberate only without a valid held intent; propose a PENDING intent."""
        held = self.intention.active
        if (
            self.executive_mode is ExecutiveMode.REDECIDE_EACH_TICK
            and held is not None
            and held.status is IntentStatus.ACTIVE
        ):
            # E3 control: no persistence -- the intent and its commitment are
            # abandoned and the decision is taken again from scratch.
            commitment = self.active_commitment
            self.intention.interrupt(held.intent_id, reason=RECONSIDERED, tick=tick)
            if commitment is not None and commitment.active:
                commitment.terminate(
                    tick=tick, status=CommitmentStatus.INTERRUPTED, reason="intent_reconsidered"
                )
                self._stop_controller()
        held = self.intention.active
        if held is not None and not held.terminal:
            # §71: an ACTIVE intent keeps its identity; its commitment continues.
            return None
        if cognition is None or not self.last_affordances:
            return None
        decision = services.choose_acquired_action(
            cognition=cognition,
            percepts=percepts,
            affordances=self.last_affordances,
            resolver=resolver,
            context_ref=context_ref,
            signal_references=signal_references,
            tick=tick,
        )
        if decision is None:
            return None
        if decision.competence_id not in {
            affordance.competence_id for affordance in self.last_affordances
        }:
            raise RuntimeError("executive decision names a competence that is not afforded")
        intent = self.intention.form(
            decision,
            context_ref=context_ref,
            embodiment_id=self.embodiment_id,
            tick=tick,
        )
        if decision.anticipated_effect_id is not None:
            # Snapshot of the footprint the intent pursues (Factorized Effects
            # §14.1): reconciliation never depends on later registry changes.
            expected = self.effect_space.footprint_change_keys(decision.anticipated_effect_id)
            if expected:
                self.intention.expect_atoms(expected)
        proposal = self._intent_proposal(intent, tick=tick)
        self.last_intent_proposal_id = proposal.proposal_id
        return proposal

    def _settle_intent_arbitration(
        self,
        selected: ActionProposal | None,
        *,
        intent_proposal: ActionProposal | None,
        tick: int,
    ) -> None:
        """REJECTED if authority was never granted; INTERRUPTED if it was lost (§41)."""
        held = self.intention.active
        if held is None or held.terminal:
            return
        if held.status is IntentStatus.PENDING:
            if (
                intent_proposal is not None
                and selected is not None
                and selected.proposal_id == intent_proposal.proposal_id
            ):
                return
            if selected is None:
                reason = PROPOSAL_NOT_SELECTED
            elif selected.source is ActionSource.PROTECTION:
                reason = SUPERSEDED_BY_PROTECTION
            else:
                reason = SUPERSEDED_BY_OTHER_ACTION
            self.intention.reject(held.intent_id, reason=reason, tick=tick)
            return
        if held.status is IntentStatus.ACTIVE and selected is not None:
            if selected.source is ActionSource.PROTECTION:
                reason = PROTECTION_TAKES_PRIORITY
            elif selected.source is ActionSource.REGULATION:
                reason = HOMEOSTATIC_EMERGENCY
            else:
                reason = NEW_MOTOR_AUTHORITY
            self.intention.interrupt(held.intent_id, reason=reason, tick=tick)

    def _direct_cognitive_proposals(
        self,
        cognition: CognitiveBridgeResult | None,
        percepts: tuple[Percept, ...],
        *,
        candidate_ids: tuple[str, ...],
        context_ref: str,
        resolver: AffordanceResolver,
        signal_references: dict[str, str],
        services: ActionServices,
        tick: int,
    ) -> list[ActionProposal]:
        """E2/E5 control arm A only: activation becomes a proposal with no intent."""
        proposals: list[ActionProposal] = []
        if cognition is None or not candidate_ids:
            return proposals
        decision = (
            services.choose_acquired_action(
                cognition=cognition,
                percepts=percepts,
                affordances=self.last_affordances,
                resolver=resolver,
                context_ref=context_ref,
                signal_references=signal_references,
                tick=tick,
            )
            if self.last_affordances
            else None
        )
        if decision is not None and decision.competence_id in candidate_ids:
            proposals.append(
                ActionProposal(
                    proposal_id="proposal."
                    + hashlib.sha256(
                        f"{self.organism_id}:{tick}:prospection:{decision.competence_id}".encode(
                            "utf-8"
                        )
                    ).hexdigest()[:24],
                    source=ActionSource.PROSPECTION,
                    effect_target_id=None,
                    competence_id=decision.competence_id,
                    justification=ActionJustification(competence_id=decision.competence_id),
                    evaluation=ActionEvaluation(
                        effect_confidence=decision.confidence,
                        uncertainty=max(0.0, 1.0 - decision.confidence),
                    ),
                )
            )
        primitive_readouts = cognition.readouts_for_family("primitive")
        for primitive_id in candidate_ids:
            raw = primitive_readouts.get(primitive_id)
            if (
                isinstance(raw, (int, float))
                and not isinstance(raw, bool)
                and math.isfinite(float(raw))
                and float(raw) >= self.selection_threshold
            ):
                strength = max(0.0, min(1.0, float(raw)))
                proposals.append(
                    ActionProposal(
                        proposal_id="proposal."
                        + hashlib.sha256(
                            f"{self.organism_id}:{tick}:competence:{primitive_id}".encode("utf-8")
                        ).hexdigest()[:24],
                        source=ActionSource.COMPETENCE,
                        effect_target_id=None,
                        competence_id=primitive_id,
                        justification=ActionJustification(competence_id=primitive_id),
                        evaluation=ActionEvaluation(
                            effect_confidence=strength,
                            controllability=strength,
                            uncertainty=1.0 - strength,
                        ),
                    )
                )
        return proposals

    def step(
        self,
        cognition: CognitiveBridgeResult | None,
        percepts: tuple[Percept, ...],
        *,
        context: TickContext,
        signal_references: dict[str, str] | None = None,
        services: ActionServices,
    ) -> ActionStepResult | None:
        """Observe the previous action's consequences, then act in one call."""
        observation = self.observe_consequences(
            percepts,
            context=context,
            signal_references=signal_references,
            services=services,
        )
        return self.act(
            cognition,
            percepts,
            observation,
            context=context,
            signal_references=signal_references,
            services=services,
        )

    def observe_consequences(
        self,
        percepts: tuple[Percept, ...],
        *,
        context: TickContext,
        signal_references: dict[str, str] | None = None,
        services: ActionServices,
    ) -> ActionObservation:
        """T0-T3: close the previous transition and settle commitment status.

        Uses only percepts and organism-owned causal state; it never reads
        cognition, so it can run before the tick's new cognition.
        """
        if context.symbiont_id != self.organism_id:
            raise ValueError("action context belongs to another Symbiont")
        if self.embodiment_id is not None and context.embodiment_id != self.embodiment_id:
            raise ValueError("action context belongs to another EmbodimentEpisode")
        tick = context.symbiont_tick
        baseline = self.motor_percept_snapshot(percepts, sensory_system=services.sensory_system)
        sensorimotor_body_state = self.sensorimotor_body_snapshot(
            percepts, sensory_system=services.sensory_system
        )

        self.intention.begin_tick()
        # T1: close the previous ActionAttempt (or passive window) only when its
        # bodily consequence is actually observable.  A command is never
        # credited with a same-tick effect.
        self.last_transition = None
        self.last_causal_update = None
        if self.pending_transition is not None:
            previous = self.pending_transition
            self.pending_transition = None
            opaque_changes = self._opaque_changes(
                previous["state_before"],
                sensorimotor_body_state,
                signal_references or {},
            )
            state_after_ref = (
                "state."
                + _canonical_hash({"values": dict(sorted(sensorimotor_body_state.items()))})[:24]
            )
            if previous["kind"] == "passive":
                self.acquisition.observe_passive_window(
                    tick_start=int(previous["tick"]),
                    tick_end=tick,
                    context_ref=str(previous["context_ref"]),
                    prior_state_ref=str(previous["state_before_ref"]),
                    resulting_state_ref=state_after_ref,
                    changes=opaque_changes,
                )
            elif self.acquisition.pending_attempt is not None:
                self._close_attempt(
                    previous,
                    opaque_changes=opaque_changes,
                    state_after_ref=state_after_ref,
                    tick=tick,
                    services=services,
                )

        if (
            self.enabled
            and self._actuator_evidence is not None
            and self._competence_development is not None
            and self.surface is not None
        ):
            # Advance an internal composed controller or close one completed
            # competence so this tick's reconciliation sees its terminal status.
            self._advance_or_complete_competence(tick=tick)
        # T3: reconcile the active intent with reality before new cognition.
        self._reconcile_intent(tick=tick)
        return ActionObservation(
            tick=tick,
            baseline=baseline,
            body_state=sensorimotor_body_state,
        )

    def act(
        self,
        cognition: CognitiveBridgeResult | None,
        percepts: tuple[Percept, ...],
        observation: ActionObservation,
        *,
        context: TickContext,
        signal_references: dict[str, str] | None = None,
        services: ActionServices,
    ) -> ActionStepResult | None:
        """T5-T11: deliberate, arbitrate, control, execute and open the next attempt."""
        tick = observation.tick
        if tick != context.symbiont_tick:
            raise ValueError("action observation belongs to another tick")
        baseline = observation.baseline
        sensorimotor_body_state = observation.body_state
        homeostatic_baseline = services.homeostasis.deviation()
        reactive_state = services.innate_reactivity.evaluate(
            percepts=baseline,
            homeostatic_deviation=homeostatic_baseline,
        )
        self.last_reactive_state = reactive_state
        if self.pending_reactive_credit is not None:
            signature, primitive_id, pressure_before = self.pending_reactive_credit
            services.reactive_memory.observe(
                signature=signature,
                primitive_id=primitive_id,
                relief=pressure_before - homeostatic_baseline,
            )
            self.pending_reactive_credit = None
        active_concepts = (
            tuple(sorted(getattr(cognition, "active_concept_ids", ())))
            if cognition is not None
            else ()
        )

        # A competence may have crossed its evidence gate on the previous
        # natural exploration window. By this tick its readout can have been
        # admitted normally; record the causal context without scheduling or
        # forcing any replay.
        if (
            cognition is not None
            and services.cognitive_bridge is not None
            and self._competence_development is not None
        ):
            for primitive_id in self._competence_development.last_natural_competence_ids:
                services.cognitive_bridge.observe_primitive_execution(
                    primitive_id,
                    concept_ids=active_concepts,
                    tick=tick,
                )

        self.last_motor_intent = None
        self.last_actuation = None
        self.last_motor_intents = ()
        self.last_actuations = ()
        self.last_executed_controller_seed_id = None
        if (
            not self.enabled
            or self._actuator_evidence is None
            or self._competence_development is None
            or self.surface is None
        ):
            return None

        self.last_action_source = "none"
        intents: tuple[MotorIntent, ...] = ()
        pending: list[tuple[str, float, dict[str, float] | None]] = []
        primitive_selected_now = False

        if self._competence_development is None:
            raise RuntimeError("actuation requires sensorimotor learner")

        self._refresh_competence_library(tick=tick)
        candidate_ids = tuple(
            competence.competence_id
            for competence in self.competence_library.items
            if self.competence_is_executable(competence)
        )
        context_ref = self._context_ref(active_concepts)
        resolver = self.affordance_resolver()
        # T5: "given this situation, what can I probably do?" -- derived, never stored.
        self.last_affordances = resolver.current(
            context_ref=context_ref,
            embodiment_id=self.embodiment_id,
        )
        self.last_intent_proposal_id = None
        proposals: list[ActionProposal] = []

        # Innate reactivity contributes urgency and a learned response candidate;
        # it never writes a motor command itself.
        reactive_candidate = services.reactive_memory.best(
            signature=reactive_state.signature,
            candidates=candidate_ids,
        )
        if reactive_state.withdrawal >= 0.55 and reactive_candidate is not None:
            proposal_id = (
                "proposal."
                + hashlib.sha256(
                    f"{self.organism_id}:{tick}:protection:{reactive_candidate}".encode("utf-8")
                ).hexdigest()[:24]
            )
            proposals.append(
                ActionProposal(
                    proposal_id=proposal_id,
                    source=ActionSource.PROTECTION,
                    effect_target_id=None,
                    competence_id=reactive_candidate,
                    justification=ActionJustification(
                        originating_need_id=f"internal.{reactive_state.signature}",
                        competence_id=reactive_candidate,
                    ),
                    evaluation=ActionEvaluation(
                        homeostatic_relevance=reactive_state.withdrawal,
                        protective_relevance=reactive_state.withdrawal,
                        effect_confidence=min(1.0, reactive_state.withdrawal),
                        uncertainty=max(0.0, 1.0 - reactive_state.withdrawal),
                    ),
                )
            )

        # T5-T7: cognition reaches motor authority only through a persistent
        # ActionIntent formed from an afforded, admitted competence.  Protection
        # and exploration need no intent (§7.6).
        intent_proposal: ActionProposal | None = None
        if self.executive_mode is ExecutiveMode.DIRECT_PROPOSAL:
            proposals.extend(
                self._direct_cognitive_proposals(
                    cognition,
                    percepts,
                    candidate_ids=candidate_ids,
                    context_ref=context_ref,
                    resolver=resolver,
                    signal_references=signal_references or {},
                    services=services,
                    tick=tick,
                )
            )
        else:
            intent_proposal = self._executive_proposal(
                cognition,
                percepts,
                context_ref=context_ref,
                resolver=resolver,
                signal_references=signal_references or {},
                services=services,
                tick=tick,
            )
            if intent_proposal is not None:
                proposals.append(intent_proposal)
            if any(
                proposal.intent_id is None
                for proposal in proposals
                if proposal.source in {ActionSource.COMPETENCE, ActionSource.PROSPECTION}
            ):
                raise RuntimeError("cognitive motor proposals require an ActionIntent")

        # Exploration is permanently available, but its pressure is organism
        # owned and can become very small.  There is no developmental mode.
        exploration_drive = (
            services.gene_expression_state.exploration_drive
            if services.gene_expression_state is not None
            else 0.25
        )
        exploration_drive = max(0.0, min(1.0, float(exploration_drive)))
        ranked_exploration = self._rank_exploration_opportunities(
            services=services,
            exploration_drive=exploration_drive,
            reactive_state=reactive_state,
        )
        if exploration_drive > 0.0 and ranked_exploration:
            preferred_id = ranked_exploration[0]
            signals = self.last_exploration_signals[preferred_id]
            proposal_id = (
                "proposal."
                + hashlib.sha256(
                    f"{self.organism_id}:{tick}:exploration:{preferred_id}".encode("utf-8")
                ).hexdigest()[:24]
            )
            proposals.append(
                ActionProposal(
                    proposal_id=proposal_id,
                    source=ActionSource.EXPLORATION,
                    effect_target_id=None,
                    competence_id=None,
                    justification=ActionJustification(
                        originating_need_id="internal.sensorimotor-uncertainty",
                        evidence_refs=(f"channel.{preferred_id}",),
                    ),
                    evaluation=ActionEvaluation(
                        epistemic_relevance=max(
                            exploration_drive,
                            max(0.0, signals.learning_progress),
                        ),
                        effect_confidence=(
                            signals.controllability_potential
                            if signals.controllability_potential is not None
                            else 0.0
                        ),
                        controllability=signals.controllability_potential,
                        uncertainty=max(0.0, min(1.0, signals.uncertainty)),
                        estimated_cost=signals.physiological_cost,
                        estimated_risk=signals.risk,
                    ),
                )
            )

        decision = self.arbitrator.choose(
            proposals=tuple(proposals),
            current=self.active_commitment,
            tick=tick,
        )
        # T8: settle the intent against the single motor authority.
        self._settle_intent_arbitration(
            decision.proposal,
            intent_proposal=intent_proposal,
            tick=tick,
        )

        selected = decision.proposal
        if selected is not None:
            if self.active_commitment is not None and self.active_commitment.active:
                self.active_commitment.terminate(
                    tick=tick,
                    status=CommitmentStatus.INTERRUPTED,
                    reason=decision.reason,
                )
                self._competence_development.interrupt_active_competence()
                self.active_composition_children = ()
                self.active_composition_index = 0

            controller_id = (
                f"controller.{selected.competence_id}"
                if selected.competence_id is not None
                else "controller.sensorimotor-exploration"
            )
            self.last_proposal = selected
            self.active_exploration_preference = (
                ranked_exploration if selected.source is ActionSource.EXPLORATION else ()
            )
            self.active_commitment = self.commit(
                selected,
                tick=tick,
                controller_id=controller_id,
                maximum_duration=(8 if selected.source is ActionSource.EXPLORATION else None),
            )
            if selected.intent_id is not None:
                # §59: motor authority granted -> PENDING becomes ACTIVE.
                granted = (
                    self.competence_library.get(selected.competence_id)
                    if selected.competence_id is not None
                    else None
                )
                self.intention.activate(
                    selected.intent_id,
                    commitment_id=self.active_commitment.commitment_id,
                    tick=tick,
                    binding_valid=(granted is not None and self.competence_is_executable(granted)),
                )

            if selected.competence_id is not None:
                if self._activate_competence_controller(selected.competence_id):
                    primitive_selected_now = True
                    intents = self._competence_development.motor_intents(tick)
                    self.last_executed_controller_seed_id = (
                        self._competence_development.last_output_primitive_id
                    )
                else:
                    self.active_commitment.terminate(
                        tick=tick,
                        status=CommitmentStatus.FAILED,
                        reason="competence_controller_unavailable",
                    )
                    intents = ()
            else:
                intents = self._competence_development.motor_intents(
                    tick,
                    exploration_preference=self.active_exploration_preference,
                )

            self.last_action_source = selected.source.value

        elif decision.keep_current and self.active_commitment is not None:
            source_value = "competence" if self.active_commitment.competence_id else "exploration"
            if self.last_proposal is not None:
                source_value = self.last_proposal.source.value
            if self.active_commitment.competence_id is not None:
                if self._competence_development.active_primitive_id is not None:
                    intents = self._competence_development.motor_intents(tick)
                    self.last_executed_controller_seed_id = (
                        self._competence_development.last_output_primitive_id
                    )
            else:
                intents = self._competence_development.motor_intents(
                    tick,
                    exploration_preference=self.active_exploration_preference,
                )
            self.last_action_source = source_value

        if self.last_action_source == "exploration" and len(intents) == 1:
            isolated = intents[0]
            pending.append(
                (
                    isolated.actuator_id,
                    float(isolated.activation),
                    baseline,
                )
            )

        if self._competence_development is not None and intents:
            intents = self._competence_development.constrain_intents(intents)
            surviving_ids = {intent.actuator_id for intent in intents}
            pending = [item for item in pending if item[0] in surviving_ids]

        activity_scale = services.homeostasis.activity_scale
        if activity_scale < 1.0:
            intents = tuple(
                MotorIntent(
                    actuator_id=intent.actuator_id,
                    activation=float(intent.activation) * activity_scale,
                )
                for intent in intents
            )
            pending = [
                (
                    actuator_id,
                    float(activation) * activity_scale,
                    before,
                )
                for actuator_id, activation, before in pending
            ]

        self.pending_motor_observation = tuple(pending)
        state_before_ref = (
            "state."
            + _canonical_hash({"values": dict(sorted(sensorimotor_body_state.items()))})[:24]
        )
        context_ref = self._context_ref(active_concepts)
        if not intents:
            # §16: nothing crosses the body boundary this tick, so the next
            # observation is a passive (no-intervention) counterfactual window.
            self.pending_transition = {
                "kind": "passive",
                "tick": tick,
                "context_ref": context_ref,
                "state_before": dict(sensorimotor_body_state),
                "state_before_ref": state_before_ref,
            }
            self.pending_proprioception = {}
            if self._competence_development is not None:
                self._competence_development.observe(
                    tick=tick,
                    body_state=sensorimotor_body_state,
                    motor_vector={},
                    discovery_eligible=False,
                    execution_primitive_id=None,
                )
            return None

        # Low-level feedback/control commands inherit the selected commitment;
        # they are not new deliberative actions.
        if self.active_commitment is None or not self.active_commitment.active:
            raise RuntimeError("motor output has no active organism-owned commitment")
        self.last_motor_command = self.issue_command(
            {intent.actuator_id: float(intent.activation) for intent in intents},
            tick=tick,
        )

        proprioception: dict[str, float] = {}
        actuations = list(self.execute_command(self.last_motor_command))
        for actuation in actuations:
            aid = actuation.actuator_id
            proprioception.update(
                {
                    f"motor.requested_activation.{aid}": actuation.requested,
                    f"motor.delivered_activation.{aid}": actuation.delivered,
                }
            )

        self.last_motor_intents = tuple(intents)
        self.last_actuations = tuple(actuations)
        self.last_motor_intent = self.last_motor_intents[0]
        self.last_actuation = self.last_actuations[0]
        self.pending_proprioception = proprioception

        if self.last_motor_command is not None and self.active_commitment is not None:
            prediction = (
                self.predict_competence_effect(
                    competence_id=self.active_commitment.competence_id,
                    context_id=context_ref,
                )
                if self.active_commitment.competence_id is not None
                else None
            )
            actuation_payload = {
                "delivered": [
                    [item.actuator_id, float(item.delivered)] for item in self.last_actuations
                ]
            }
            # T11: open the ActionAttempt for this issued command.  Its
            # consequence is attached only on a later observation.
            self.acquisition.open_attempt(
                command=self.last_motor_command,
                commitment=self.active_commitment,
                context_ref=context_ref,
                actuation_ref="actuation." + _canonical_hash(actuation_payload)[:24],
                tick=tick,
            )
            self.pending_transition = {
                "kind": "attempt",
                "tick": tick,
                "context_ref": context_ref,
                "prediction_id": (prediction.prediction_id if prediction is not None else None),
                "predicted_effect_id": (prediction.effect_id if prediction is not None else None),
                "prediction_confidence": (prediction.confidence if prediction is not None else 0.0),
                "state_before": dict(sensorimotor_body_state),
                "state_before_ref": state_before_ref,
            }

        if (
            primitive_selected_now
            and self.last_executed_controller_seed_id is not None
            and cognition is not None
            and services.cognitive_bridge is not None
            and self._competence_development is not None
            and any(
                primitive.primitive_id == self.last_executed_controller_seed_id
                for primitive in self._competence_development.cognitive_primitives
            )
        ):
            services.cognitive_bridge.observe_primitive_execution(
                self.last_executed_controller_seed_id,
                concept_ids=cognition.active_concept_ids,
                tick=tick,
            )
            services.schedule_homeostatic_action_credit(
                family="primitive",
                action_id=self.last_executed_controller_seed_id,
                concept_ids=active_concepts,
                baseline_error=homeostatic_baseline,
                tick=tick,
            )
        if self._competence_development is not None:
            self._competence_development.observe(
                tick=tick,
                body_state=sensorimotor_body_state,
                motor_vector={
                    actuation.actuator_id: float(actuation.delivered)
                    for actuation in self.last_actuations
                    if actuation.delivered > 0.0
                },
                discovery_eligible=(self.last_executed_controller_seed_id is None),
                execution_primitive_id=self.last_executed_controller_seed_id,
            )

            # Natural recurrence is the missing non-circular path from a
            # learned bodily competence into cognition. No scheduler asks for
            # this movement: it must have just occurred in ordinary behavior.
            if cognition is not None and services.cognitive_bridge is not None:
                for primitive_id in self._competence_development.last_natural_competence_ids:
                    services.cognitive_bridge.observe_primitive_execution(
                        primitive_id,
                        concept_ids=active_concepts,
                        tick=tick,
                    )
                    services.schedule_homeostatic_action_credit(
                        family="primitive",
                        action_id=primitive_id,
                        concept_ids=active_concepts,
                        baseline_error=homeostatic_baseline,
                        tick=tick,
                    )

        if self.last_motor_command is None:
            return None
        return ActionStepResult(
            action_id=self.last_motor_command.command_id,
            executed=True,
            result=None,
            reason=None,
        )

    def snapshot(
        self,
        *,
        body_schema_sensorimotor_relations: int = 0,
        tick: int = 0,
    ) -> SensorimotorV2Snapshot | None:
        if not self.enabled:
            return None
        intent = self.intention.active if self.intention.holds_intent else None
        legacy = (
            self._competence_development.snapshot()
            if self._competence_development is not None
            else None
        )
        progress = [
            max(0.0, float(item.learning_progress))
            for item in self.last_exploration_signals.values()
        ]
        active = self.active_commitment
        return SensorimotorV2Snapshot(
            effect_count=len(self.effect_space.effects),
            causal_evidence_count=len(self.causal_evidence),
            competence_count=len(self.competence_library.items),
            established_competence_count=sum(
                1 for item in self.competence_library.items if self.competence_is_executable(item)
            ),
            competence_candidate_count=legacy.competence_candidates if legacy is not None else 0,
            controllability_estimate_count=len(self.controllability_model),
            predictive_context_count=self.effect_model.context_count,
            agency_estimate_count=len(self.agency_model),
            composition_evidence_count=len(self.composition_engine.evidence),
            established_composition_count=len(self.composition_engine.established),
            body_schema_sensorimotor_relations=int(body_schema_sensorimotor_relations),
            active_commitment_id=active.commitment_id
            if active is not None and active.active
            else None,
            active_competence_id=active.competence_id
            if active is not None and active.active
            else None,
            action_source=self.last_action_source,
            exploration_preference=self.active_exploration_preference,
            mean_learning_progress=sum(progress) / len(progress) if progress else 0.0,
            physical_motor_opportunity_count=(
                len(self.surface.actuator_ids) if self.surface is not None else 0
            ),
            action_attempt_count=self.acquisition.attempt_count,
            intervention_signature_count=len(self.intervention_signatures),
            recurring_intervention_signature_count=self.intervention_signatures.recurring_count,
            action_dimension_count=len(self.action_dimensions.items),
            agentic_action_dimension_count=len(self.acquisition.agentic_dimension_ids()),
            affordance_count=len(self.last_affordances),
            active_intent_id=intent.intent_id if intent is not None else None,
            active_intent_status=intent.status.value if intent is not None else None,
            active_intent_age=self.intention.age(tick) if intent is not None else None,
            active_intent_last_progress_age=(
                self.intention.last_progress_age(tick) if intent is not None else None
            ),
            intent_satisfied_count=self.intention.counts[IntentStatus.SATISFIED],
            intent_failed_count=self.intention.counts[IntentStatus.FAILED],
            intent_rejected_count=self.intention.counts[IntentStatus.REJECTED],
            intent_interrupted_count=self.intention.counts[IntentStatus.INTERRUPTED],
            intent_invalidated_count=self.intention.counts[IntentStatus.INVALIDATED],
            intent_prediction_match=self.intention.last_prediction_match,
        )

    def restore_v2(
        self,
        payload: Mapping[str, object],
        *,
        body_schema: BodySchemaEngine,
        fingerprint_migration: tuple[str, str] | None = None,
    ) -> None:
        """Restore canonical Sensorimotor v2 state into this domain.

        Schema 1 is migrated from competence-local surface bindings. Schemas 2
        to 4 restore the explicit execution-binding registry. Schemas 3 and 4
        carry current Embodiment identity. Schema 4 adds acquired intervention
        families and learned ActionDimensions. All body-specific authority is
        validated against the currently attached actuator surface.
        """
        schema = int(payload.get("schema_version") or 0)
        if schema not in {1, 2, 3, 4}:
            raise ValueError("unsupported sensorimotor v2 checkpoint schema")

        if schema in {3, 4}:
            raw_surface_binding = payload.get("surface_binding")
            if not isinstance(raw_surface_binding, Mapping):
                raise ValueError("sensorimotor surface binding is missing")
            stored_fingerprint = raw_surface_binding.get("contract_fingerprint")
            if (
                isinstance(stored_fingerprint, str)
                and fingerprint_migration is not None
                and stored_fingerprint == fingerprint_migration[0]
            ):
                stored_fingerprint = fingerprint_migration[1]
            if self.surface is not None and stored_fingerprint != self.surface.contract_fingerprint:
                raise ValueError("sensorimotor state belongs to another actuator surface")
            raw_embodiment_id = raw_surface_binding.get("embodiment_id")
            if raw_embodiment_id is not None:
                if not isinstance(raw_embodiment_id, str) or not raw_embodiment_id:
                    raise ValueError("invalid action-domain embodiment id")
                self.embodiment_id = raw_embodiment_id

        raw_effects = payload.get("effect_space")
        raw_evidence = payload.get("causal_evidence")
        raw_acquisition = payload.get("agency_acquisition") if schema == 4 else None
        if schema == 4 and not isinstance(raw_acquisition, Mapping):
            raise ValueError("sensorimotor v4 agency acquisition state is missing")
        # Sensorimotor v3 and older never acquired dimensions; the migration
        # starts with none rather than regenerating them from the surface.
        self.acquisition.restore_causal_state(
            effect_space=raw_effects if isinstance(raw_effects, Mapping) else None,
            causal_evidence=raw_evidence if isinstance(raw_evidence, Mapping) else None,
            acquisition=raw_acquisition if isinstance(raw_acquisition, Mapping) else None,
            body_schema=body_schema,
        )
        self.acquisition.bind_surface(
            self.surface.actuator_ids if self.enabled and self.surface is not None else None,
            surface_fingerprint=(
                self.surface.contract_fingerprint
                if self.enabled and self.surface is not None
                else None
            ),
        )

        known_channels = set(self.surface.actuator_ids if self.surface is not None else ())
        raw_exploration = payload.get("exploration")
        if isinstance(raw_exploration, Mapping):
            raw_strength = raw_exploration.get("strength_memory", {})
            if isinstance(raw_strength, Mapping):
                self.exploration_strength_memory = {
                    str(key): max(0.0, min(1.0, float(value)))
                    for key, value in raw_strength.items()
                    if str(key) in known_channels
                }
            raw_preference = raw_exploration.get("active_preference", [])
            if isinstance(raw_preference, list):
                self.active_exploration_preference = tuple(
                    str(value) for value in raw_preference if str(value) in known_channels
                )

        raw_competences = payload.get("competences", [])
        if not isinstance(raw_competences, list):
            raise ValueError("invalid competence checkpoint collection")
        restored_library = CompetenceLibrary()
        for item in raw_competences:
            if not isinstance(item, Mapping):
                raise ValueError("invalid competence checkpoint item")
            competence_id = item.get("competence_id")
            controller_id = item.get("controller_id")
            if not isinstance(competence_id, str) or not isinstance(controller_id, str):
                raise ValueError("invalid competence checkpoint identifiers")
            restored_library.add(
                MotorCompetence(
                    competence_id=competence_id,
                    controller_id=controller_id,
                    effect_id=(
                        str(item["effect_id"]) if item.get("effect_id") is not None else None
                    ),
                    evidence=CompetenceEvidence(
                        controller_seed_ref=str(
                            item.get("controller_strategy_ref") or competence_id
                        ),
                        support=int(item.get("support", 0)),
                        failures=int(item.get("failures", 0)),
                        reproducibility=float(item.get("reproducibility", 0.0)),
                        controllability=float(item.get("controllability", 0.0)),
                        directional_consistency=float(item.get("directional_consistency", 0.0)),
                    ),
                    controller_strategy_ref=(
                        str(item["controller_strategy_ref"])
                        if item.get("controller_strategy_ref") is not None
                        else None
                    ),
                    parent_competence_ids=tuple(
                        str(value) for value in item.get("parent_competence_ids", [])
                    ),
                )
            )
        self.competence_library = restored_library

        if schema in {2, 3, 4}:
            raw_bindings = payload.get("execution_bindings")
            binding_payload = deepcopy(raw_bindings) if isinstance(raw_bindings, Mapping) else None
            if binding_payload is not None and fingerprint_migration is not None:
                old_fp, new_fp = fingerprint_migration
                raw_items = binding_payload.get("items")
                if isinstance(raw_items, list):
                    for item in raw_items:
                        if isinstance(item, dict) and item.get("surface_fingerprint") == old_fp:
                            item["surface_fingerprint"] = new_fp
            self.execution_bindings = CompetenceExecutionBindingRegistry.restore(binding_payload)
        else:
            migrated = CompetenceExecutionBindingRegistry()
            for legacy_item in raw_competences:
                if not isinstance(legacy_item, Mapping):
                    continue
                competence_id = str(legacy_item.get("competence_id") or "")
                surface = legacy_item.get("surface_binding")
                if (
                    isinstance(surface, str)
                    and fingerprint_migration is not None
                    and surface == fingerprint_migration[0]
                ):
                    surface = fingerprint_migration[1]
                effect_id = legacy_item.get("effect_id")
                matching = tuple(
                    evidence
                    for evidence in self.causal_evidence.evidence
                    if evidence.competence_id == competence_id and evidence.effect_id == effect_id
                )
                refs = tuple(evidence.evidence_id for evidence in matching)
                if (
                    competence_id
                    and isinstance(surface, str)
                    and surface
                    and isinstance(effect_id, str)
                    and effect_id
                    and refs
                ):
                    competence = restored_library.get(competence_id)
                    migrated.bind_from_evidence(
                        competence_id=competence_id,
                        surface_fingerprint=surface,
                        effect_id=effect_id,
                        evidence_refs=refs,
                        reliability=(
                            competence.evidence.reproducibility if competence is not None else 0.0
                        ),
                        controllability=(
                            competence.evidence.controllability if competence is not None else 0.0
                        ),
                        tick=max(
                            (evidence.observation_tick for evidence in matching),
                            default=0,
                        ),
                    )
            self.execution_bindings = migrated

        raw_composition = payload.get("composition")
        if isinstance(raw_composition, Mapping):
            raw_engine = raw_composition.get("engine")
            if isinstance(raw_engine, Mapping):
                self.composition_engine = CompositionEngine.restore(raw_engine)
            predecessor = raw_composition.get("predecessor_id")
            self.composition_predecessor_id = str(predecessor) if predecessor is not None else None
            children = raw_composition.get("active_children", [])
            if isinstance(children, list):
                self.active_composition_children = tuple(str(value) for value in children)
            self.active_composition_index = int(raw_composition.get("active_index", 0))

        known_competences = {item.competence_id for item in self.competence_library.items}
        if (
            self.active_commitment is None
            or not self.active_commitment.active
            or not self.active_composition_children
            or any(child not in known_competences for child in self.active_composition_children)
            or self.active_composition_index < 0
            or self.active_composition_index >= len(self.active_composition_children)
        ):
            self.active_composition_children = ()
            self.active_composition_index = 0
        if (
            self.composition_predecessor_id is not None
            and self.composition_predecessor_id not in known_competences
        ):
            self.composition_predecessor_id = None

    def action_trace(self) -> dict[str, Any] | None:
        """Why did the body move? Causal chain of the latest observed attempt (§62-§63, §86-§87).

        Reconstructed only from organism-owned records; nothing is narrated.
        """
        attempt = self.acquisition.last_attempt
        if attempt is None:
            return None
        trace = self.trace_action(attempt.motor_command_ref)
        held = self.intention.active
        intent = (
            held
            if held is not None and self.intention.active_commitment_id == attempt.commitment_id
            else None
        )
        outcome = next(
            (
                item
                for item in reversed(self.intention.recent_outcomes)
                if item.commitment_id == attempt.commitment_id
            ),
            None,
        )
        intent_id = (
            intent.intent_id
            if intent is not None
            else (outcome.intent_id if outcome is not None else None)
        )
        transition = self.last_transition
        observed = (
            transition
            if transition is not None and transition.attempt_id == attempt.attempt_id
            else None
        )
        return {
            "intent_id": intent_id,
            "intent_status": (
                intent.status.value
                if intent is not None
                else (outcome.status.value if outcome is not None else None)
            ),
            "origin_refs": list(intent.origin_refs) if intent is not None else [],
            "affordance_id": intent.supporting_affordance_id if intent is not None else None,
            "source": "cognitive_intent" if intent_id is not None else "no_intent",
            "proposal_id": trace.proposal_id if trace is not None else None,
            "commitment_id": attempt.commitment_id,
            "competence_id": attempt.competence_id,
            "command_id": attempt.motor_command_ref,
            "attempt_id": attempt.attempt_id,
            "intervention_signature_id": attempt.intervention_signature_id,
            "transition_id": observed.transition_id if observed is not None else None,
            "observed_effect_id": observed.observed_effect_id if observed is not None else None,
            "match": outcome.effect_similarity if outcome is not None else None,
            "result": outcome.status.value if outcome is not None else None,
        }

    def observation_view(self, *, tick: int) -> dict[str, Any]:
        """Bounded passive projection for Observatory; never read back by cognition."""
        agentic = set(self.acquisition.agentic_dimension_ids())
        intent = self.intention.active if self.intention.holds_intent else None
        signatures = sorted(
            self.intervention_signatures.items,
            key=lambda item: (
                -self.intervention_signatures.attempt_support(item.signature_id),
                item.signature_id,
            ),
        )[:64]
        return {
            "physical_motor_opportunities": (
                len(self.surface.actuator_ids) if self.surface is not None else 0
            ),
            "action_attempt_count": self.acquisition.attempt_count,
            "recent_attempts": [
                {
                    "attempt_id": item.attempt_id,
                    "commitment_id": item.commitment_id,
                    "competence_id": item.competence_id,
                    "intervention_signature_id": item.intervention_signature_id,
                    "motor_command_ref": item.motor_command_ref,
                    "started_tick": item.started_tick,
                    "completed_tick": item.completed_tick,
                }
                for item in list(self.acquisition.recent_attempts)[-16:]
            ],
            "intervention_signatures": [
                {
                    "signature_id": item.signature_id,
                    "dimensionality": item.dimensionality,
                    "temporal": item.temporal_pattern_ref is not None,
                    "attempts": self.intervention_signatures.attempt_support(item.signature_id),
                }
                for item in signatures
            ],
            "intervention_signature_count": len(self.intervention_signatures),
            "recurring_intervention_signature_count": (
                self.intervention_signatures.recurring_count
            ),
            "action_dimensions": [
                {
                    "dimension_id": item.dimension_id,
                    "intervention_signature_count": len(item.intervention_signature_refs),
                    "channel_count": len(self.action_dimensions.channel_refs(item.dimension_id)),
                    "availability": item.availability,
                    "controllability": item.controllability,
                    "confidence": item.confidence,
                    "usage_count": item.usage_count,
                    "embodiment_bound": item.embodiment_bound,
                    "agentic": item.dimension_id in agentic,
                }
                for item in self.action_dimensions.items
            ],
            "causal_relation_count": len(self.controllability_model),
            "causal_evidence_count": len(self.causal_evidence.intervention_evidence),
            "passive_window_count": len(self.causal_evidence.passive_evidence),
            "affordances": [
                {
                    "affordance_id": item.affordance_id,
                    "competence_id": item.competence_id,
                    "anticipated_effect_id": item.anticipated_effect_id,
                    "prediction_confidence": item.prediction_confidence,
                    "controllability": item.controllability,
                    "executability_confidence": item.executability_confidence,
                }
                for item in self.last_affordances
            ],
            "executive": {
                "active": (
                    {
                        **intent.checkpoint(),
                        "age": self.intention.age(tick),
                        "last_progress_age": self.intention.last_progress_age(tick),
                        "commitment_id": self.intention.active_commitment_id,
                    }
                    if intent is not None
                    else None
                ),
                "outcomes": [
                    {
                        "intent_id": item.intent_id,
                        "competence_id": item.competence_id,
                        "anticipated_effect_id": item.anticipated_effect_id,
                        "status": item.status.value,
                        "reason": item.reason,
                        "tick": item.tick,
                        "commitment_id": item.commitment_id,
                        "observed_effect_id": item.observed_effect_id,
                        "effect_similarity": item.effect_similarity,
                    }
                    for item in self.intention.recent_outcomes
                ],
                "counts": {status.value: count for status, count in self.intention.counts.items()},
                "prediction_match": self.intention.last_prediction_match,
                "outcome_learning": {
                    "enabled": self.intention.policy.executive_outcome_learning,
                    **self.intention.outcome_ledger.metrics(),
                },
            },
            "trace": self.action_trace(),
        }

    def restore_intention(self, payload: Mapping[str, Any] | None, *, tick: int) -> None:
        """Restore the live intent; one whose commitment did not survive is invalidated."""
        self.intention = IntentionDomain.restore(
            payload,
            organism_id=self.organism_id,
            policy=self.intention.policy,
        )
        self.intention.revision_probe = self.causal_revision_state
        self.intention.provenance = self.acquisition.provenance
        held = self.intention.active
        if held is None or held.status is not IntentStatus.ACTIVE:
            return
        commitment = self.active_commitment
        if (
            commitment is None
            or commitment.commitment_id != self.intention.active_commitment_id
            or commitment.intent_id != held.intent_id
        ):
            self.intention.invalidate(held.intent_id, reason=CAUSAL_BINDING_INVALIDATED, tick=tick)

    def checkpoint_state(self) -> dict[str, object]:
        """Serialize the complete canonical action domain.

        Raw percept baselines are intentionally not persisted.  They are
        embodiment-local observations and are re-established after restore.
        """
        if self.enabled and (
            self.surface is None
            or self._actuator_evidence is None
            or self._competence_development is None
        ):
            raise RuntimeError("enabled action domain is missing canonical motor state")
        return {
            "schema_version": 1,
            "selection_threshold": self.selection_threshold,
            "actuator_evidence": (
                export_actuation_state(self._actuator_evidence)
                if self._actuator_evidence is not None
                else None
            ),
            "competence_development": (
                self._competence_development.checkpoint()
                if self._competence_development is not None
                else None
            ),
            "pending_motor_observation": [
                {
                    "actuator_id": actuator_id,
                    "activation": activation,
                }
                for actuator_id, activation, _baseline in self.pending_motor_observation
            ],
            "pending_proprioception": dict(sorted(self.pending_proprioception.items())),
            "last_executed_controller_seed_id": (self.last_executed_controller_seed_id),
            "active_commitment": (
                self.active_commitment.checkpoint() if self.active_commitment is not None else None
            ),
            "sensorimotor_v2": self.checkpoint_v2(),
        }

    def checkpoint_v2(self) -> dict[str, object]:
        if self.surface is None:
            raise RuntimeError("cannot checkpoint enabled action domain without surface")
        return {
            "schema_version": 4,
            "surface_binding": {
                "contract_fingerprint": self.surface.contract_fingerprint,
                "known_channel_ids": list(self.surface.actuator_ids),
                "embodiment_id": self.embodiment_id,
            },
            "effect_space": self.effect_space.checkpoint(),
            "causal_evidence": self.causal_evidence.checkpoint(),
            "agency_acquisition": self.acquisition.checkpoint(),
            "exploration": {
                "strength_memory": dict(sorted(self.exploration_strength_memory.items())),
                "active_preference": list(self.active_exploration_preference),
            },
            "competences": [
                {
                    "competence_id": item.competence_id,
                    "controller_id": item.controller_id,
                    "effect_id": item.effect_id,
                    "controller_strategy_ref": item.controller_strategy_ref,
                    "parent_competence_ids": list(item.parent_competence_ids),
                    "support": item.evidence.support,
                    "failures": item.evidence.failures,
                    "reproducibility": item.evidence.reproducibility,
                    "controllability": item.evidence.controllability,
                    "directional_consistency": item.evidence.directional_consistency,
                }
                for item in self.competence_library.items
            ],
            "execution_bindings": self.execution_bindings.checkpoint(),
            "composition": {
                "engine": self.composition_engine.checkpoint(),
                "predecessor_id": self.composition_predecessor_id,
                "active_children": list(self.active_composition_children),
                "active_index": self.active_composition_index,
            },
        }
