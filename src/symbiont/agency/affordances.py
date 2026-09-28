"""AffordanceResolver: effect-directed and opportunity-directed affordances (§32, §37-§38).

Affordances are derived — never stored — from organism-owned knowledge:

* forward knowledge: a CompetenceEffectModel-backed predictor (competence,
  context -> effect), falling back to the competence's converged effect;
* causal knowledge: ControllabilityModel;
* current-body authority: CompetenceExecutionBindingRegistry on the current
  actuator surface and embodiment;
* effect identity: EffectSpace through EffectMatcher.

The reverse mapping ``effect -> possible competences`` is computed from those
views rather than kept as a second factual truth.  The resolver never reads
actuators, never commits and never emits commands.
"""

from __future__ import annotations

from collections.abc import Callable

from ..actuation.binding import CompetenceExecutionBindingRegistry
from ..actuation.competence import CompetenceLibrary, MotorCompetence
from ..actuation.effects import EffectMatcher, EffectSpace
from ..actuation.model import CausalSourceKind, ControllabilityModel, EffectPrediction
from .affordance import ActionAffordance, affordance_id_for


class AffordanceResolver:
    """Read-only projection over current competence, causal and binding knowledge."""

    def __init__(
        self,
        *,
        competences: CompetenceLibrary,
        predict: Callable[..., EffectPrediction | None],
        controllability_model: ControllabilityModel,
        execution_bindings: CompetenceExecutionBindingRegistry,
        executable: Callable[[MotorCompetence], bool],
        effect_space: EffectSpace,
        effect_matcher: EffectMatcher,
        surface_fingerprint: str | None,
        embodiment_id: str | None,
    ) -> None:
        self._competences = competences
        self._predict = predict
        self._controllability = controllability_model
        self._bindings = execution_bindings
        self._executable = executable
        self._effect_space = effect_space
        self._matcher = effect_matcher
        self._surface_fingerprint = surface_fingerprint
        self._embodiment_id = embodiment_id

    def _affordance(
        self,
        competence: MotorCompetence,
        *,
        context_ref: str | None,
        embodiment_id: str | None,
    ) -> ActionAffordance | None:
        if embodiment_id != self._embodiment_id:
            return None
        if not self._executable(competence):
            return None
        binding = self._bindings.get(competence.competence_id)
        if binding is None:
            return None
        prediction = self._predict(
            competence_id=competence.competence_id,
            context_id=context_ref,
        )
        if prediction is None or self._effect_space.get(prediction.effect_id) is None:
            return None
        anticipated = prediction.effect_id
        prediction_confidence = prediction.confidence
        prediction_ref = prediction.prediction_id
        control = self._controllability.estimate(
            source_kind=CausalSourceKind.COMPETENCE,
            source_ref=competence.competence_id,
            effect_id=anticipated,
            context_id=context_ref,
        )
        return ActionAffordance(
            affordance_id=affordance_id_for(
                competence_id=competence.competence_id,
                anticipated_effect_id=anticipated,
                context_ref=context_ref,
                embodiment_id=embodiment_id,
            ),
            competence_id=competence.competence_id,
            anticipated_effect_id=anticipated,
            context_ref=context_ref,
            embodiment_id=embodiment_id,
            prediction_confidence=max(0.0, min(1.0, prediction_confidence)),
            controllability=(
                control.confidence if control is not None else binding.controllability
            ),
            executability_confidence=binding.reliability,
            prediction_ref=prediction_ref,
            evidence_refs=binding.evidence_refs[-8:],
        )

    @staticmethod
    def _ranked(affordances: list[ActionAffordance]) -> tuple[ActionAffordance, ...]:
        return tuple(
            sorted(
                affordances,
                key=lambda item: (
                    -item.controllability,
                    -item.prediction_confidence,
                    -item.executability_confidence,
                    item.competence_id,
                ),
            )
        )

    def for_effect(
        self,
        *,
        effect_id: str,
        context_ref: str | None,
        embodiment_id: str | None,
    ) -> tuple[ActionAffordance, ...]:
        """Effect-directed: what can probably produce ``effect_id`` here and now?"""
        found: list[ActionAffordance] = []
        for competence in self._competences.items:
            affordance = self._affordance(
                competence, context_ref=context_ref, embodiment_id=embodiment_id
            )
            if affordance is None:
                continue
            if (
                self._matcher.match(
                    self._effect_space,
                    expected_effect_id=effect_id,
                    observed_effect_id=affordance.anticipated_effect_id,
                )
                > 0.0
            ):
                found.append(affordance)
        return self._ranked(found)

    def current(
        self,
        *,
        context_ref: str | None,
        embodiment_id: str | None,
    ) -> tuple[ActionAffordance, ...]:
        """Opportunity-directed: given the current state, what can I probably do?"""
        found = [
            affordance
            for competence in self._competences.items
            if (
                affordance := self._affordance(
                    competence, context_ref=context_ref, embodiment_id=embodiment_id
                )
            )
            is not None
        ]
        return self._ranked(found)


__all__ = ["AffordanceResolver"]
