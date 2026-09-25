"""Single causal authority for organism-owned physical action."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from ...actuation.action import ActionProposal, MotorCommand
from ...actuation.arbitration import ActionArbitrator
from ...actuation.binding import CompetenceExecutionBindingRegistry
from ...actuation.commitment import ActionCommitment, CommitmentStatus
from ...actuation.competence import CompetenceLibrary, MotorCompetence
from ...actuation.composition import CompositionEngine
from ...actuation.effects import EffectSpace
from ...actuation.evidence import CausalEvidenceLedger, SensorimotorTransition
from ...actuation.exploration import ExplorationPolicy, ExplorationSignals
from ...actuation.model import AgencyModel, CompetenceEffectModel, ControllabilityModel
from ...actuation.proposer import ActuatorProposer
from ...actuation.sensorimotor import SensorimotorLearner
from ...actuation.state import SensorimotorV2Snapshot
from ...actuation.surface import ActuatorSurface
from ...actuation.system import ActuatorSystem
from ...actuation.types import Actuation, MotorIntent


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
        legacy_proposer: ActuatorProposer | None = None,
        legacy_learner: SensorimotorLearner | None = None,
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
        self._legacy_proposer = legacy_proposer or (
            ActuatorProposer(surface, organism_id=organism_id)
            if self.enabled and surface is not None else None
        )
        self._legacy_learner = legacy_learner or (
            SensorimotorLearner(
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
        self._trace_by_command: dict[str, ActionTrace] = {}

    @property
    def legacy_proposer(self) -> ActuatorProposer | None:
        return self._legacy_proposer

    @property
    def legacy_learner(self) -> SensorimotorLearner | None:
        return self._legacy_learner

    @property
    def current_surface_fingerprint(self) -> str | None:
        return self.surface.contract_fingerprint if self.surface is not None else None

    @property
    def active_repertoire(self) -> tuple[str, ...]:
        return self._legacy_proposer.active_repertoire if self._legacy_proposer is not None else ()

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

    def snapshot(
        self,
        *,
        body_schema_sensorimotor_relations: int = 0,
    ) -> SensorimotorV2Snapshot | None:
        if not self.enabled:
            return None
        legacy = self._legacy_learner.snapshot() if self._legacy_learner is not None else None
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
