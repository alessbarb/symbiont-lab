"""Individual emergence from Symbiont, Body, EmbodimentEpisode and apparatus session.

Canonical ontology:
    Symbiont + Body + EmbodimentEpisode + History = Individual

EmbodimentSession is only the opaque transduction/routing adapter for the
current coupling. EmbodimentEpisode is the persistent domain entity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ...actuation.surface import ActuatorSurface
from ..embodiment.body import ActivationConsequence, Body
from ..embodiment.contract import EmbodimentContract, PerceptualSurface
from ..embodiment.episode import (
    EmbodimentEndReason,
    EmbodimentEpisode,
    EmbodimentState,
)
from ..embodiment.memory import EmbodimentArchive, archive_episode_checkpoint
from ..embodiment.session import EmbodimentSession, implant
from ...genetics.genome import Genome
from ...genetics.germline import GermlineState
from .symbiont import Symbiont


@dataclass(frozen=True, slots=True)
class IndividualTickRecord:
    """Historical record of one embodiment interaction tick."""

    tick: int
    symbiont_id: str
    body_id: str
    embodiment_id: str
    opaque_inputs: dict[str, float]
    opaque_activations: dict[str, float]
    physical_consequences: dict[str, ActivationConsequence]
    body_viable: bool
    schema_confidence: float
    disruption_detected: bool


class Individual:
    """One Symbiont physically coupled to one Body through an Embodiment."""

    def __init__(
        self,
        symbiont: Symbiont,
        body: Body,
        session: EmbodimentSession,
        *,
        genome: Genome | None = None,
        germline: GermlineState | None = None,
        embodiment_archive: EmbodimentArchive | None = None,
        embodiment_epoch: int = 1,
    ) -> None:
        if session.symbiont_id != symbiont.symbiont_id:
            raise ValueError("embodiment session belongs to another Symbiont")
        if session.body_id != body.body_id:
            raise ValueError("embodiment session belongs to another Body")
        self.symbiont = symbiont
        self.body = body
        self.session = session
        self.genome = genome if genome is not None else getattr(symbiont, "genome", None)
        self.germline = germline if germline is not None else getattr(symbiont, "germline", None)
        self.history: list[IndividualTickRecord] = []
        self._current_tick: int = session.started_at
        self.embodiment_archive = (
            embodiment_archive if embodiment_archive is not None else EmbodimentArchive()
        )
        self.embodiment = self._begin_episode(
            session=session,
            body=body,
            epoch=embodiment_epoch,
        )

        # Register only opaque output channels with the cognitive seed.
        self.symbiont.register_output_channels(list(session.output_bindings.keys()))

    @staticmethod
    def _contract_for(session: EmbodimentSession) -> EmbodimentContract:
        # Counts/opaque channel ordinals define the exposed interface. Physical
        # port labels deliberately do not enter the contract fingerprint.
        return EmbodimentContract(
            perceptual_surface=PerceptualSurface.from_count(
                len(session.input_bindings)
            ),
            actuator_surface=ActuatorSurface.from_count(
                len(session.output_bindings)
            ),
        )

    def _begin_episode(
        self,
        *,
        session: EmbodimentSession,
        body: Body,
        epoch: int,
    ) -> EmbodimentEpisode:
        contract = self._contract_for(session)
        self.symbiont.attach_execution_surface(
            contract.actuator_surface.contract_fingerprint
        )
        prior = self.embodiment_archive.prior_for(
            body_id=body.body_id,
            contract_fingerprint=contract.contract_fingerprint,
        )
        episode = EmbodimentEpisode.begin(
            symbiont_id=self.symbiont.symbiont_id,
            body_id=body.body_id,
            epoch=epoch,
            start_symbiont_tick=self._current_tick,
            contract=contract,
            embodiment_id=session.embodiment_id,
            prior=prior,
        )
        # One source of truth: Episode references the exact inference services
        # already used by the Symbiont, never copies them.
        episode.body_schema = self.symbiont.body_schema
        episode.dynamics_model = self.symbiont.sensorimotor_model
        episode.causal_evidence = self.symbiont.causal_evidence
        episode.effect_model = self.symbiont.competence_effect_model
        episode.controllability_model = self.symbiont.controllability_model
        episode.agency_model = self.symbiont.agency_model
        episode.execution_bindings = (
            self.symbiont.competence_execution_bindings
        )
        return episode

    def _archive_current_episode(
        self,
        *,
        reason: EmbodimentEndReason,
    ) -> None:
        if self.embodiment.state is not EmbodimentState.CLOSED:
            self.embodiment.close(
                symbiont_tick=self._current_tick,
                reason=reason,
            )
        archive_episode_checkpoint(
            self.embodiment_archive,
            self.embodiment.checkpoint(current_tick=self._current_tick),
            body_schema_prior=self.symbiont.body_schema.export(
                current_tick=self._current_tick
            ),
            living_body=self.body.physiology.checkpoint(),
            symbiont_tick=self._current_tick,
            end_reason=reason.value,
        )

    @property
    def symbiont_id(self) -> str:
        return self.symbiont.symbiont_id

    @property
    def body_id(self) -> str:
        return self.body.body_id

    @property
    def embodiment_id(self) -> str:
        return self.embodiment.embodiment_id

    @property
    def embodiment_tick(self) -> int:
        return self.embodiment.embodiment_tick

    @property
    def current_tick(self) -> int:
        return self._current_tick

    @property
    def is_alive(self) -> bool:
        return (
            self.body.is_viable
            and self.session.is_active
            and self.embodiment.state is not EmbodimentState.CLOSED
        )

    def step(
        self, external_stimuli: Mapping[str, float] | None = None
    ) -> IndividualTickRecord:
        """Advance one physical/cognitive Embodiment step."""
        if self.embodiment.state is not EmbodimentState.ACTIVE:
            raise RuntimeError("only an active embodiment can advance")
        self._current_tick += 1

        physical_readings = self.body.transduce_signals(external_stimuli)
        opaque_inputs = self.session.transduce_to_symbiont(physical_readings)
        opaque_activations = self.symbiont.step(opaque_inputs)
        physical_commands = self.session.route_to_body(opaque_activations)
        consequences = self.body.apply_activations(physical_commands)
        self.body.tick_physics()

        self.embodiment.advance()
        agency_values = tuple(
            item.confidence for item in self.symbiont.agency_model.estimates
        )
        controllability_values = tuple(
            item.confidence
            for item in self.symbiont.controllability_model.estimates
        )
        current_surface = (
            self.embodiment.contract.actuator_surface.contract_fingerprint
        )
        general_competences = self.symbiont.competence_library.items
        revalidated = sum(
            1
            for competence in general_competences
            if self.symbiont.competence_execution_bindings.is_executable(
                competence,
                surface_fingerprint=current_surface,
            )
        )
        self.embodiment.adaptation.observe(
            tick=self.embodiment_tick,
            prediction_error=self.symbiont.last_prediction_error,
            schema_confidence=self.symbiont.body_schema_confidence,
            causal_confidence=(
                sum(agency_values) / len(agency_values)
                if agency_values else 0.0
            ),
            controllability_confidence=(
                sum(controllability_values) / len(controllability_values)
                if controllability_values else 0.0
            ),
            revalidated_competences=revalidated,
            candidate_competences=len(general_competences),
            schema_revised=self.symbiont.body_schema_disrupted,
        )

        if self.symbiont.causal_evidence.evidence:
            latest = self.symbiont.causal_evidence.evidence[-1]
            if latest.competence_id is not None and latest.effect_id is not None:
                control = self.symbiont.controllability_model.estimate(
                    latest.effect_id,
                    latest.competence_id,
                    None,
                )
                self.embodiment.reachability.observe(
                    latest.effect_id,
                    latest.competence_id,
                    tick=self.embodiment_tick,
                    success=bool(
                        control is not None
                        and control.confidence >= 0.20
                        and control.reliability >= 0.50
                    ),
                )

        if not self.body.is_viable:
            self.session.sever(self._current_tick)
            self._archive_current_episode(reason=EmbodimentEndReason.BODY_DEATH)

        record = IndividualTickRecord(
            tick=self._current_tick,
            symbiont_id=self.symbiont_id,
            body_id=self.body_id,
            embodiment_id=self.embodiment_id,
            opaque_inputs=dict(opaque_inputs),
            opaque_activations=dict(opaque_activations),
            physical_consequences=consequences,
            body_viable=self.body.is_viable,
            schema_confidence=self.symbiont.body_schema_confidence,
            disruption_detected=self.symbiont.body_schema_disrupted,
        )
        self.history.append(record)
        return record

    def transplant_to(self, new_body: Body) -> EmbodimentSession:
        """Close one Embodiment and begin another on a distinct Body."""
        self._archive_current_episode(reason=EmbodimentEndReason.BODY_REPLACED)
        self.session.sever(self._current_tick)

        new_session = implant(
            symbiont_id=self.symbiont.symbiont_id,
            body_id=new_body.body_id,
            receptor_ids=new_body.ordered_receptors,
            effector_ids=new_body.ordered_effectors,
            started_at=self._current_tick,
        )

        previous_epoch = self.embodiment.epoch
        self.body = new_body
        self.session = new_session
        self.symbiont.begin_new_embodiment()
        self.symbiont.register_output_channels(
            list(new_session.output_bindings.keys())
        )
        self.embodiment = self._begin_episode(
            session=new_session,
            body=new_body,
            epoch=previous_epoch + 1,
        )
        return new_session


def create_individual(
    symbiont_id: str,
    body_id: str,
    *,
    morphology: str = "standard",
    num_receptors: int = 4,
    num_effectors: int = 2,
    started_at: int = 0,
) -> Individual:
    """Create a canonical Individual with a fresh Body and Embodiment."""
    from ..embodiment.body import create_standard_body

    body = create_standard_body(
        body_id=body_id,
        num_receptors=num_receptors,
        num_effectors=num_effectors,
        morphology=morphology,
    )
    symbiont = Symbiont(symbiont_id=symbiont_id)
    session = implant(
        symbiont_id=symbiont_id,
        body_id=body_id,
        receptor_ids=body.ordered_receptors,
        effector_ids=body.ordered_effectors,
        started_at=started_at,
    )
    return Individual(symbiont=symbiont, body=body, session=session)


__all__ = [
    "Individual",
    "IndividualTickRecord",
    "create_individual",
]
