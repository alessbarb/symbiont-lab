from __future__ import annotations

from .candidate import ActuatorCandidateState
from .constitution import ActuatorConstitution
from .types import ActuatorId


class ActuatorEvidenceModel:
    """Track naturally observed actuator/effect evidence.

    This model never proposes or authorizes an action.  It only summarizes
    evidence about opaque channels already present on the current actuator
    surface; ActionDomain owns exploration and every physical commitment.

    Only ``constitution.actuator_ids`` are ever considered — this never
    invents an actuator_id that isn't already part of the body. Promotion to
    ``active_repertoire`` is exclusively evidence-driven
    (``consider_natural_evidence``): no scheduled probing protocol lives
    here (L6.2) — that apparatus moved to
    ``symbiont_lab.studies.common.actuator_probing_calendar`` for explicit,
    Lab-run matched intervention/control studies.
    """

    def __init__(
        self,
        constitution: ActuatorConstitution,
        *,
        organism_id: str,
        effect_threshold: float = 0.5,
    ) -> None:
        if not 0.0 <= effect_threshold <= 1.0:
            raise ValueError("effect_threshold must be within [0.0, 1.0]")

        self._constitution = constitution
        self._organism_id = organism_id
        self._effect_threshold = effect_threshold
        self._states: dict[ActuatorId, ActuatorCandidateState] = {
            actuator_id: ActuatorCandidateState(actuator_id=actuator_id)
            for actuator_id in constitution.actuator_ids
        }

    @property
    def states(self) -> tuple[ActuatorCandidateState, ...]:
        return tuple(sorted(self._states.values(), key=lambda state: state.actuator_id))

    @property
    def active_repertoire(self) -> tuple[ActuatorId, ...]:
        return tuple(state.actuator_id for state in self.states if state.probing_state == "active")

    def record_effect(
        self,
        actuator_id: ActuatorId,
        percept_id: str,
        *,
        activation: float,
        delta_percept: float,
        tick: int,
    ) -> None:
        state = self._states[actuator_id]
        state.observe_effect(percept_id, activation=activation, delta_percept=delta_percept)
        state.last_seen_tick = tick

    def consider_natural_evidence(self, actuator_id: ActuatorId, *, min_samples: int = 12) -> bool:
        """Promote an actuator from passive, naturally occurring covariance.

        This is the canonical clean World's only promotion path: causal
        competence may be learned, but exploration is never a scheduled
        experimenter-authored ON/OFF protocol.
        """
        if min_samples < 3:
            raise ValueError("min_samples must be at least 3")
        state = self._states[actuator_id]
        strongest_count = max(
            (relation.count for relation in state.effect_relations.values()),
            default=0,
        )
        if strongest_count < min_samples or state.effect_strength < self._effect_threshold:
            return False
        state.probing_state = "active"
        state.natural_promotion_samples = int(min_samples)
        return True


__all__ = ["ActuatorEvidenceModel"]
