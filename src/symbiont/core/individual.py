"""Individual emergence from Symbiont, Body, EmbodimentSession and History.

Under the design doc:
    Symbiont + Body + EmbodimentSession + History = Individual

'No nace un individuo completo. Nace un germen. El individuo se forma.'
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .body import ActivationConsequence, Body
from .embodiment import EmbodimentSession, implant
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
    """An emergent individual: Symbiont coupled to Body in a temporal EmbodimentSession."""

    def __init__(
        self,
        symbiont: Symbiont,
        body: Body,
        session: EmbodimentSession,
        *,
        genome: Any | None = None,
        germline: Any | None = None,
    ) -> None:
        self.symbiont = symbiont
        self.body = body
        self.session = session
        self.genome = genome if genome is not None else getattr(symbiont, "genome", None)
        self.germline = germline if germline is not None else getattr(symbiont, "germline", None)
        self.history: list[IndividualTickRecord] = []
        self._current_tick: int = session.started_at

        # Register known outputs with the cognitive seed
        self.symbiont.register_output_channels(list(session.output_bindings.keys()))

    @property
    def symbiont_id(self) -> str:
        return self.symbiont.symbiont_id

    @property
    def body_id(self) -> str:
        return self.body.body_id

    @property
    def embodiment_id(self) -> str:
        return self.session.embodiment_id

    @property
    def current_tick(self) -> int:
        return self._current_tick

    @property
    def is_alive(self) -> bool:
        return self.body.is_viable and self.session.is_active

    def step(
        self, external_stimuli: Mapping[str, float] | None = None
    ) -> IndividualTickRecord:
        """Advance one embodiment step across physical and cognitive layers."""
        self._current_tick += 1

        # 1. Physical transduction at the Body
        physical_readings = self.body.transduce_signals(external_stimuli)

        # 2. Opaque conversion at the EmbodimentSession
        opaque_inputs = self.session.transduce_to_symbiont(physical_readings)

        # 3. Cognitive step in the Symbiont (no external embodiment ID leakage, AUD-013)
        opaque_activations = self.symbiont.step(opaque_inputs)

        # 4. Routing to physical body commands
        physical_commands = self.session.route_to_body(opaque_activations)

        # 5. Physical execution & metabolic consequence on the Body
        consequences = self.body.apply_activations(physical_commands)

        # 6. Physical basal decay & wear
        self.body.tick_physics()

        # 7. Record historical trajectory
        record = IndividualTickRecord(
            tick=self._current_tick,
            symbiont_id=self.symbiont_id,
            body_id=self.body_id,
            embodiment_id=self.embodiment_id,
            opaque_inputs=dict(opaque_inputs),
            opaque_activations=dict(opaque_activations),
            physical_consequences=consequences,
            body_viable=self.body.is_viable,
            schema_confidence=self.symbiont.body_schema.overall_confidence,
            disruption_detected=self.symbiont.body_schema.disruption_detected,
        )
        self.history.append(record)
        return record

    def transplant_to(self, new_body: Body) -> EmbodimentSession:
        """Transplant the cognitive seed into a new physical body (Section 39).

        The previous embodiment session is severed. A new session is created.
        The Symbiont's cognitive continuity is preserved while its body schema
        encounters the new causal reality.
        """
        self.session.sever(self._current_tick)
        new_session = implant(
            symbiont_id=self.symbiont.symbiont_id,
            body_id=new_body.body_id,
            receptor_ids=new_body.receptor_ids,
            effector_ids=new_body.effector_ids,
            started_at=self._current_tick,
        )
        self.body = new_body
        self.session = new_session
        self.symbiont.register_output_channels(list(new_session.output_bindings.keys()))
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
    """Helper to create a complete Individual with a standard body and cognitive seed."""
    from .body import create_standard_body

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
        receptor_ids=body.receptor_ids,
        effector_ids=body.effector_ids,
        started_at=started_at,
    )
    return Individual(symbiont=symbiont, body=body, session=session)


__all__ = [
    "Individual",
    "IndividualTickRecord",
    "create_individual",
]
