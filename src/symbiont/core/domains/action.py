"""Single causal authority for organism-owned physical action."""
from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, Mapping

from ...actuation.action import (
    ActionEvaluation,
    ActionJustification,
    ActionProposal,
    ActionSource,
    MotorCommand,
)
from ...actuation.arbitration import ActionArbitrator
from ...actuation.binding import CompetenceExecutionBindingRegistry
from ...actuation.commitment import ActionCommitment, CommitmentStatus
from ...actuation.competence import CompetenceEvidence, CompetenceLibrary, MotorCompetence
from ...actuation.composition import CompositionEngine
from ...actuation.effects import EffectSpace
from ...actuation.evidence import (
    CausalEvidenceLedger,
    PredictionError,
    SensorimotorTransition,
)
from ...actuation.exploration import ExplorationPolicy, ExplorationSignals
from ...actuation.model import AgencyModel, CompetenceEffectModel, ControllabilityModel
from ...actuation.proposer import ActuatorEvidenceModel
from ...actuation.sensorimotor import CompetenceDevelopmentEngine
from ...actuation.state import SensorimotorV2Snapshot
from ...actuation.surface import ActuatorSurface
from ...actuation.system import ActuatorSystem
from ...actuation.types import Actuation, MotorIntent
from ...genetics.expression import GeneExpressionState
from ...host.percepts import Percept
from ...sensory import SensorySystem
from ..cognition.bridge import CognitiveBridge, CognitiveBridgeResult
from ..embodiment.body_schema import BodySchemaEngine
from ..embodiment.homeostasis import HomeostaticController
from ..regulation import InnateReactivity, ReactiveMemory, ReactiveState


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
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
    choose_acquired_competence: Callable[..., str | None]
    schedule_homeostatic_action_credit: Callable[..., None]


@dataclass(frozen=True, slots=True)
class ActionTrace:
    proposal_id: str
    commitment_id: str
    command_id: str


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
            if self.enabled and surface is not None else None
        )
        self._competence_development = competence_development or (
            CompetenceDevelopmentEngine(
                surface.actuator_ids,
                organism_id=organism_id,
                max_concurrent=None,
                embodiment_fingerprint=surface.contract_fingerprint,
            )
            if self.enabled and surface is not None else None
        )
        self._actuator_system = actuator_system or ActuatorSystem()

        self.arbitrator = ActionArbitrator()
        self.effect_space = EffectSpace()
        self.causal_evidence = CausalEvidenceLedger()
        self.competence_library = CompetenceLibrary()
        self.execution_bindings = CompetenceExecutionBindingRegistry()
        self.effect_model = CompetenceEffectModel()
        self.controllability_model = ControllabilityModel()
        self.agency_model = AgencyModel()
        self.exploration_policy = ExplorationPolicy()
        self.composition_engine = CompositionEngine()

        self.active_commitment: ActionCommitment | None = None
        self.last_proposal: ActionProposal | None = None
        self.last_motor_command: MotorCommand | None = None
        self.last_transition: SensorimotorTransition | None = None
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
        self.pending_motor_observation: tuple[
            tuple[str, float, dict[str, float] | None], ...
        ] = ()
        self.pending_proprioception: dict[str, float] = {}
        self.pending_reactive_credit: tuple[str, str, float] | None = None
        self.last_reactive_state: ReactiveState | None = None
        self._trace_by_command: dict[str, ActionTrace] = {}

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
        return self._actuator_evidence.active_repertoire if self._actuator_evidence is not None else ()

    def competence_is_executable(self, competence: MotorCompetence) -> bool:
        return self.execution_bindings.is_executable(
            competence,
            surface_fingerprint=self.current_surface_fingerprint,
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
        material = "|".join(
            f"{key}:{float(value):.12g}" for key, value in sorted(channels.items())
        )
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

    def motor_percept_snapshot(self, percepts: tuple[Percept, ...], *, sensory_system: SensorySystem) -> dict[str, float]:
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
    ) -> None:
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
        if (
            self.active_composition_children
            and self.active_composition_index + 1
            < len(self.active_composition_children)
        ):
            self.active_composition_index += 1
            child_id = self.active_composition_children[
                self.active_composition_index
            ]
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
                controllability_potential=(
                    None if activations == 0 else strength
                ),
                physiological_cost=physiological_cost,
                risk=risk,
            )
            opportunities.append((state.actuator_id, signals))
        self.exploration_strength_memory.update(current_strengths)
        self.last_exploration_signals = dict(opportunities)
        chosen = self.exploration_policy.choose(tuple(opportunities))
        return (chosen,) if chosen is not None else ()

    def _refresh_competence_library(self) -> None:
        """Project sequence evidence into the v2 competence repertoire.

        A sequence supplies a controller seed and evidence only.  No effect
        binding is fabricated: that remains unresolved until EffectSpace
        correspondence is learned.
        """
        if self._competence_development is None or self.surface is None:
            return
        for primitive in self._competence_development.primitives:
            if not primitive.established:
                continue
            existing = self.competence_library.get(primitive.primitive_id)
            if existing is None:
                self.competence_library.add(
                    MotorCompetence(
                        competence_id=primitive.primitive_id,
                        controller_id=f"controller.{primitive.primitive_id}",
                        effect_id=None,
                        evidence=primitive.competence_evidence,
                        controller_strategy_ref=primitive.primitive_id,
                    )
                )
            else:
                existing.evidence = primitive.competence_evidence

    def step(
        self,
        cognition: CognitiveBridgeResult | None,
        percepts: tuple[Percept, ...],
        *,
        tick: int,
        signal_references: dict[str, str] | None = None,
        services: ActionServices,
    ) -> None:
        baseline = self.motor_percept_snapshot(percepts, sensory_system=services.sensory_system)
        sensorimotor_body_state = self.sensorimotor_body_snapshot(percepts, sensory_system=services.sensory_system)

        # Complete t-1 -> t only when the bodily consequence is actually
        # observable.  A command is never credited with a same-tick effect.
        self.last_transition = None
        if self.pending_transition is not None:
            previous = self.pending_transition
            before_state = previous["state_before"]
            raw_changes = {
                name: float(sensorimotor_body_state[name]) - float(before_state[name])
                for name in sorted(set(before_state) & set(sensorimotor_body_state))
            }
            references = signal_references or {}
            opaque_changes: dict[str, float] = {}
            for name, delta in raw_changes.items():
                opaque = references.get(name)
                if opaque is None and name.startswith(
                    ("signal.", "latent.", "part.", "channel.", "internal.", "effect.")
                ):
                    opaque = name
                if opaque is not None:
                    opaque_changes[str(opaque)] = delta
            observed_effect = self.effect_space.observe(opaque_changes)

            predicted_effect_id = previous.get("predicted_effect_id")
            prediction_confidence = float(
                previous.get("prediction_confidence", 0.0)
            )
            observed_effect_id = (
                observed_effect.effect_id
                if observed_effect is not None
                else None
            )
            prediction_error = None
            if predicted_effect_id is not None:
                matched = predicted_effect_id == observed_effect_id
                prediction_error = PredictionError(
                    magnitude=0.0 if matched else 1.0,
                    uncertainty=max(
                        0.0,
                        min(1.0, 1.0 - prediction_confidence),
                    ),
                    novelty=0.0 if matched else 1.0,
                )

            transition = SensorimotorTransition(
                transition_id="transition." + hashlib.sha256(
                    f"{self.organism_id}:{previous['tick']}:{tick}:{previous['motor_command_ref']}".encode("utf-8")
                ).hexdigest()[:24],
                tick_start=int(previous["tick"]),
                tick_end=tick,
                context_ref=str(previous["context_ref"]),
                commitment_id=str(previous["commitment_id"]),
                controller_id=str(previous["controller_id"]),
                competence_id=(
                    str(previous["competence_id"])
                    if previous.get("competence_id") is not None
                    else None
                ),
                state_before_ref=str(previous["state_before_ref"]),
                motor_command_ref=str(previous["motor_command_ref"]),
                actuation_ref=str(previous["actuation_ref"]),
                prediction_ref=(
                    str(previous["prediction_id"])
                    if previous.get("prediction_id") is not None
                    else None
                ),
                state_after_ref="state." + _canonical_hash(
                    {"values": dict(sorted(sensorimotor_body_state.items()))}
                )[:24],
                observed_effect_id=observed_effect_id,
                prediction_error=prediction_error,
                physiological_delta_ref=None,
            )
            causal = self.causal_evidence.observe(transition)
            self.effect_model.observe(causal)
            if observed_effect is not None:
                self.effect_by_commitment[
                    transition.commitment_id
                ] = observed_effect.effect_id

            if transition.competence_id is not None and observed_effect is not None:
                services.body_schema.observe_sensorimotor_evidence(
                    competence_id=transition.competence_id,
                    effect_id=observed_effect.effect_id,
                    tick=tick,
                )
                competence = self.competence_library.get(transition.competence_id)
                if competence is not None:
                    current_surface = self.current_surface_fingerprint
                    control_estimate = self.controllability_model.update_from_ledger(
                        self.causal_evidence,
                        effect_id=observed_effect.effect_id,
                        competence_id=transition.competence_id,
                        context_id=transition.context_ref,
                        tick=tick,
                    )
                    if competence.effect_id is None:
                        competence.effect_id = observed_effect.effect_id
                    if current_surface is not None:
                        self.execution_bindings.bind_from_evidence(
                            competence_id=transition.competence_id,
                            surface_fingerprint=current_surface,
                            effect_id=observed_effect.effect_id,
                            evidence_refs=(causal.evidence_id,),
                            reliability=control_estimate.reliability,
                            controllability=max(
                                control_estimate.confidence,
                                competence.evidence.controllability,
                            ),
                            tick=tick,
                        )
                    self.agency_model.update_from_ledger(
                        self.causal_evidence,
                        effect_id=observed_effect.effect_id,
                        competence_id=transition.competence_id,
                        context_id=transition.context_ref,
                        tick=tick,
                        prediction_match=(
                            None
                            if prediction_error is None
                            else 1.0 - prediction_error.magnitude
                        ),
                    )

                    # Embodiment v2 body-boundary inference is reconstructed
                    # from organism-owned causal effects and agency only.
                    # Controllability alone never makes a channel part of Body.
                    observed_features = {
                        feature
                        for effect in self.effect_space.effects
                        for feature in effect.feature_refs
                    }
                    self_caused_features: set[str] = set()
                    for estimate in self.agency_model.estimates:
                        if estimate.confidence < 0.35:
                            continue
                        agentic_effect = self.effect_space.get(
                            estimate.effect_id
                        )
                        if agentic_effect is not None:
                            self_caused_features.update(
                                agentic_effect.feature_refs
                            )
                    if observed_features:
                        services.body_schema.observe_agency_boundary(
                            observed_channels=observed_features,
                            self_caused_channels=self_caused_features,
                            # Somatic membership requires independent evidence;
                            # correlation/controllability is not sufficient.
                            somatic_correlated_channels=(),
                            prediction_error=(
                                prediction_error.magnitude
                                if prediction_error is not None
                                else 0.0
                            ),
                        )
            self.last_transition = transition
            self.pending_transition = None

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
            return

        self.last_action_source = "none"
        intents: tuple[MotorIntent, ...] = ()
        pending: list[tuple[str, float, dict[str, float] | None]] = []
        primitive_selected_now = False

        if self._competence_development is None:
            raise RuntimeError("actuation requires sensorimotor learner")

        # Advance an internal composed controller or close one completed
        # competence before opening deliberation again.
        self._advance_or_complete_competence(tick=tick)

        self._refresh_competence_library()
        candidate_ids = tuple(
            competence.competence_id
            for competence in self.competence_library.items
            if self.competence_is_executable(competence)
        )
        proposals: list[ActionProposal] = []

        # Innate reactivity contributes urgency and a learned response candidate;
        # it never writes a motor command itself.
        reactive_candidate = services.reactive_memory.best(
            signature=reactive_state.signature,
            candidates=candidate_ids,
        )
        if reactive_state.withdrawal >= 0.55 and reactive_candidate is not None:
            proposal_id = "proposal." + hashlib.sha256(
                f"{self.organism_id}:{tick}:protection:{reactive_candidate}".encode("utf-8")
            ).hexdigest()[:24]
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

        # Prospective agency proposes an already acquired competence.  It does
        # not activate it; final ownership belongs to the universal arbitrator.
        prospective_id: str | None = None
        if cognition is not None and candidate_ids:
            prospective_id = services.choose_acquired_competence(
                cognition=cognition,
                percepts=percepts,
                candidate_ids=candidate_ids,
                signal_references=signal_references or {},
                tick=tick,
            )
        if prospective_id is not None and prospective_id in candidate_ids:
            proposal_id = "proposal." + hashlib.sha256(
                f"{self.organism_id}:{tick}:prospection:{prospective_id}".encode("utf-8")
            ).hexdigest()[:24]
            proposals.append(
                ActionProposal(
                    proposal_id=proposal_id,
                    source=ActionSource.PROSPECTION,
                    effect_target_id=None,
                    competence_id=prospective_id,
                    justification=ActionJustification(
                        competence_id=prospective_id,
                    ),
                    evaluation=ActionEvaluation(
                        effect_confidence=0.75,
                        controllability=0.75,
                        uncertainty=0.25,
                    ),
                )
            )

        # Cognitive motor reuse is competence-level only.  The historical
        # cognition->individual-actuator path is intentionally gone.
        if cognition is not None and candidate_ids:
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
                    proposal_id = "proposal." + hashlib.sha256(
                        f"{self.organism_id}:{tick}:competence:{primitive_id}".encode("utf-8")
                    ).hexdigest()[:24]
                    proposals.append(
                        ActionProposal(
                            proposal_id=proposal_id,
                            source=ActionSource.COMPETENCE,
                            effect_target_id=None,
                            competence_id=primitive_id,
                            justification=ActionJustification(
                                competence_id=primitive_id,
                            ),
                            evaluation=ActionEvaluation(
                                effect_confidence=strength,
                                controllability=strength,
                                uncertainty=1.0 - strength,
                            ),
                        )
                    )

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
            proposal_id = "proposal." + hashlib.sha256(
                f"{self.organism_id}:{tick}:exploration:{preferred_id}".encode("utf-8")
            ).hexdigest()[:24]
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
                ranked_exploration
                if selected.source is ActionSource.EXPLORATION
                else ()
            )
            self.active_commitment = self.commit(
                selected,
                tick=tick,
                controller_id=controller_id,
                maximum_duration=(
                    8 if selected.source is ActionSource.EXPLORATION else None
                ),
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
        if not intents:
            self.pending_proprioception = {}
            if self._competence_development is not None:
                self._competence_development.observe(
                    tick=tick,
                    body_state=sensorimotor_body_state,
                    motor_vector={},
                    discovery_eligible=False,
                    execution_primitive_id=None,
                )
            return

        # Low-level feedback/control commands inherit the selected commitment;
        # they are not new deliberative actions.
        if self.active_commitment is None or not self.active_commitment.active:
            raise RuntimeError("motor output has no active organism-owned commitment")
        self.last_motor_command = self.issue_command(
            {
                intent.actuator_id: float(intent.activation)
                for intent in intents
            },
            tick=tick,
        )

        proprioception: dict[str, float] = {}
        actuations = list(
            self.execute_command(self.last_motor_command)
        )
        for actuation in actuations:
            aid = actuation.actuator_id
            proprioception.update({
                f"motor.requested_activation.{aid}": actuation.requested,
                f"motor.delivered_activation.{aid}": actuation.delivered,
            })

        self.last_motor_intents = tuple(intents)
        self.last_actuations = tuple(actuations)
        self.last_motor_intent = self.last_motor_intents[0]
        self.last_actuation = self.last_actuations[0]
        self.pending_proprioception = proprioception

        if self.last_motor_command is not None and self.active_commitment is not None:
            context_ref = "context." + hashlib.sha256(
                (
                    (
                        self.surface.contract_fingerprint
                        if self.surface is not None
                        else "no-surface"
                    )
                    + "|"
                    + ("|".join(active_concepts) or "opaque")
                ).encode("utf-8")
            ).hexdigest()[:24]
            prediction = (
                self.effect_model.predict(
                    competence_id=self.active_commitment.competence_id,
                    context_id=context_ref,
                )
                if self.active_commitment.competence_id is not None
                else None
            )
            command_payload = {
                "channels": [
                    [actuator_id, activation]
                    for actuator_id, activation in self.last_motor_command.channels
                ]
            }
            actuation_payload = {
                "delivered": [
                    [item.actuator_id, float(item.delivered)]
                    for item in self.last_actuations
                ]
            }
            self.pending_transition = {
                "tick": tick,
                "commitment_id": self.active_commitment.commitment_id,
                "controller_id": self.active_commitment.controller_id,
                "competence_id": self.active_commitment.competence_id,
                "context_ref": context_ref,
                "prediction_id": (
                    prediction.prediction_id if prediction is not None else None
                ),
                "predicted_effect_id": (
                    prediction.effect_id if prediction is not None else None
                ),
                "prediction_confidence": (
                    prediction.confidence if prediction is not None else 0.0
                ),
                "state_before": dict(sensorimotor_body_state),
                "state_before_ref": "state." + _canonical_hash(
                    {"values": dict(sorted(sensorimotor_body_state.items()))}
                )[:24],
                "motor_command_ref": "command." + _canonical_hash(command_payload)[:24],
                "actuation_ref": "actuation." + _canonical_hash(actuation_payload)[:24],
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


    def snapshot(
        self,
        *,
        body_schema_sensorimotor_relations: int = 0,
    ) -> SensorimotorV2Snapshot | None:
        if not self.enabled:
            return None
        legacy = self._competence_development.snapshot() if self._competence_development is not None else None
        progress = [
            max(0.0, float(item.learning_progress))
            for item in self.last_exploration_signals.values()
        ]
        active = self.active_commitment
        return SensorimotorV2Snapshot(
            effect_count=len(self.effect_space.effects),
            causal_evidence_count=len(self.causal_evidence.evidence),
            competence_count=len(self.competence_library.items),
            established_competence_count=sum(
                1 for item in self.competence_library.items
                if self.competence_is_executable(item)
            ),
            competence_candidate_count=legacy.competence_candidates if legacy is not None else 0,
            controllability_estimate_count=len(self.controllability_model.estimates),
            predictive_context_count=self.effect_model.context_count,
            agency_estimate_count=len(self.agency_model.estimates),
            composition_evidence_count=len(self.composition_engine.evidence),
            established_composition_count=len(self.composition_engine.established),
            body_schema_sensorimotor_relations=int(body_schema_sensorimotor_relations),
            active_commitment_id=active.commitment_id if active is not None and active.active else None,
            active_competence_id=active.competence_id if active is not None and active.active else None,
            action_source=self.last_action_source,
            exploration_preference=self.active_exploration_preference,
            mean_learning_progress=sum(progress) / len(progress) if progress else 0.0,
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
        and 3 restore the explicit execution-binding registry. Schema 3 also
        carries current Embodiment identity. All body-specific authority is
        validated against the currently attached actuator surface.
        """
        schema = int(payload.get("schema_version") or 0)
        if schema not in {1, 2, 3}:
            raise ValueError("unsupported sensorimotor v2 checkpoint schema")

        if schema == 3:
            raw_surface_binding = payload.get("surface_binding")
            if not isinstance(raw_surface_binding, Mapping):
                raise ValueError("sensorimotor v3 surface binding is missing")
            stored_fingerprint = raw_surface_binding.get("contract_fingerprint")
            if (
                isinstance(stored_fingerprint, str)
                and fingerprint_migration is not None
                and stored_fingerprint == fingerprint_migration[0]
            ):
                stored_fingerprint = fingerprint_migration[1]
            if (
                self.surface is not None
                and stored_fingerprint != self.surface.contract_fingerprint
            ):
                raise ValueError(
                    "sensorimotor v3 state belongs to another actuator surface"
                )
            raw_embodiment_id = raw_surface_binding.get("embodiment_id")
            if raw_embodiment_id is not None:
                if not isinstance(raw_embodiment_id, str) or not raw_embodiment_id:
                    raise ValueError("invalid action-domain embodiment id")
                self.embodiment_id = raw_embodiment_id

        raw_effects = payload.get("effect_space")
        raw_evidence = payload.get("causal_evidence")
        if isinstance(raw_effects, Mapping):
            self.effect_space = EffectSpace.restore(raw_effects)
        if isinstance(raw_evidence, Mapping):
            self.causal_evidence = CausalEvidenceLedger.restore(raw_evidence)
            body_schema.rebuild_sensorimotor_view(self.causal_evidence.evidence)
            self.effect_model.rebuild(self.causal_evidence)
            self.controllability_model.rebuild(self.causal_evidence)
            self.agency_model.rebuild(self.causal_evidence)

        known_channels = set(
            self.surface.actuator_ids if self.surface is not None else ()
        )
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
                    str(value)
                    for value in raw_preference
                    if str(value) in known_channels
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
            if not isinstance(competence_id, str) or not isinstance(
                controller_id, str
            ):
                raise ValueError("invalid competence checkpoint identifiers")
            restored_library.add(
                MotorCompetence(
                    competence_id=competence_id,
                    controller_id=controller_id,
                    effect_id=(
                        str(item["effect_id"])
                        if item.get("effect_id") is not None
                        else None
                    ),
                    evidence=CompetenceEvidence(
                        controller_seed_ref=str(
                            item.get("controller_strategy_ref") or competence_id
                        ),
                        support=int(item.get("support", 0)),
                        failures=int(item.get("failures", 0)),
                        reproducibility=float(
                            item.get("reproducibility", 0.0)
                        ),
                        controllability=float(
                            item.get("controllability", 0.0)
                        ),
                        directional_consistency=float(
                            item.get("directional_consistency", 0.0)
                        ),
                    ),
                    controller_strategy_ref=(
                        str(item["controller_strategy_ref"])
                        if item.get("controller_strategy_ref") is not None
                        else None
                    ),
                    parent_competence_ids=tuple(
                        str(value)
                        for value in item.get("parent_competence_ids", [])
                    ),
                )
            )
        self.competence_library = restored_library

        if schema in {2, 3}:
            raw_bindings = payload.get("execution_bindings")
            binding_payload = (
                deepcopy(raw_bindings)
                if isinstance(raw_bindings, Mapping)
                else None
            )
            if binding_payload is not None and fingerprint_migration is not None:
                old_fp, new_fp = fingerprint_migration
                raw_items = binding_payload.get("items")
                if isinstance(raw_items, list):
                    for item in raw_items:
                        if (
                            isinstance(item, dict)
                            and item.get("surface_fingerprint") == old_fp
                        ):
                            item["surface_fingerprint"] = new_fp
            self.execution_bindings = (
                CompetenceExecutionBindingRegistry.restore(binding_payload)
            )
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
                    if evidence.competence_id == competence_id
                    and evidence.effect_id == effect_id
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
                            competence.evidence.reproducibility
                            if competence is not None
                            else 0.0
                        ),
                        controllability=(
                            competence.evidence.controllability
                            if competence is not None
                            else 0.0
                        ),
                        tick=max(
                            (
                                evidence.observation_tick
                                for evidence in matching
                            ),
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
            self.composition_predecessor_id = (
                str(predecessor) if predecessor is not None else None
            )
            children = raw_composition.get("active_children", [])
            if isinstance(children, list):
                self.active_composition_children = tuple(
                    str(value) for value in children
                )
            self.active_composition_index = int(
                raw_composition.get("active_index", 0)
            )

        known_competences = {
            item.competence_id for item in self.competence_library.items
        }
        if (
            self.active_commitment is None
            or not self.active_commitment.active
            or not self.active_composition_children
            or any(
                child not in known_competences
                for child in self.active_composition_children
            )
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

    def checkpoint_v2(self) -> dict[str, object]:
        if self.surface is None:
            raise RuntimeError("cannot checkpoint enabled action domain without surface")
        return {
            "schema_version": 3,
            "surface_binding": {
                "contract_fingerprint": self.surface.contract_fingerprint,
                "known_channel_ids": list(self.surface.actuator_ids),
                "embodiment_id": self.embodiment_id,
            },
            "effect_space": self.effect_space.checkpoint(),
            "causal_evidence": self.causal_evidence.checkpoint(),
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
