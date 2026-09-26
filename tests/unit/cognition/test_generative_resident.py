from __future__ import annotations

from dataclasses import dataclass

from symbiont.cognition.generative import (
    CompetenceEffectGenerativeAdapter,
    GeneratedFeature,
    GeneratedProposal,
    GenerativeContext,
    GenerativeMode,
    GenerativeOperation,
    GenerativeResidentSnapshot,
    GenerativeState,
    ResidentGenerativeCognition,
)


@dataclass(frozen=True)
class _Error:
    predictor_id: str = "predictor.a"
    target_id: str = "sense.a"
    error: float = 0.5
    loss: float = 0.25


@dataclass
class _Cognition:
    prediction_errors: tuple[_Error, ...] = (_Error(),)
    activations: dict[str, float] | None = None

    def __post_init__(self) -> None:
        if self.activations is None:
            self.activations = {"concept.a": 0.8, "sense.a": -0.2}


class _Model:
    model_id = "model.test"

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation is GenerativeOperation.PREDICT

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        return (
            GeneratedProposal(
                features=(GeneratedFeature("outcome.test", None, 0.8, self.model_id),),
                predicted_outcomes=("outcome.test",),
                uncertainty=0.2,
                coherence=0.9,
                model_id=self.model_id,
                support_refs=context.references,
            ),
        )


def test_prediction_error_enters_endogenous_agenda_but_waits_for_compatible_model() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    resident.register_model(_Model())

    snapshot = resident.step(
        tick=1,
        cognition=_Cognition(),
        mode=GenerativeMode.ONLINE,
    )

    assert isinstance(snapshot, GenerativeResidentSnapshot)
    assert snapshot.target_id is None
    assert snapshot.transition_count == 0
    assert snapshot.model_queries == 0
    assert snapshot.agenda_contamination_count == 0
    target = next(
        item
        for item in resident.agenda.targets
        if item.target_id == "gc.prediction.predictor.a.sense.a"
    )
    assert target.selection_count == 0
    assert target.no_progress_count == 0
    assert resident.last_workspace is not None
    assert len(resident.last_workspace.states) == 1


def test_resident_loop_abstains_when_no_model_can_answer_prospective_target() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")

    snapshot = resident.step(
        tick=1,
        cognition=None,
        prospective_candidate_ids=("competence.a",),
        mode=GenerativeMode.ONLINE,
    )

    assert snapshot.target_id == "gc.prospective.competence.a"
    assert snapshot.transition_count == 0
    assert snapshot.model_queries == 1
    assert snapshot.termination is not None
    assert snapshot.termination.value == "model_unavailable"


@dataclass(frozen=True)
class _Effect:
    effect_id: str
    confidence: float


def test_resident_loop_uses_learned_competence_effect_adapter() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    resident.register_model(
        CompetenceEffectGenerativeAdapter(
            model_id="competence-effect",
            predictor=lambda competence_id, context_id: _Effect(
                effect_id=f"effect.{competence_id}",
                confidence=0.75,
            ),
        )
    )

    snapshot = resident.step(
        tick=3,
        cognition=None,
        prospective_candidate_ids=("competence.a",),
        mode=GenerativeMode.ONLINE,
    )

    assert snapshot.target_id == "gc.prospective.competence.a"
    assert snapshot.transition_count == 1
    assert resident.last_workspace is not None
    generated = resident.last_workspace.states[-1]
    assert generated.source_model_ids == ("competence-effect",)
    assert generated.features[0].token == "effect.competence.a"
    assert generated.origin.value == "inferred"


def test_resident_checkpoint_round_trip_preserves_agenda_scheduler_and_workspace() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    resident.register_model(_Model())
    before = resident.step(
        tick=4,
        cognition=_Cognition(),
        mode=GenerativeMode.IDLE,
    )

    restored = ResidentGenerativeCognition.from_checkpoint(
        resident.checkpoint(),
        organism_id="organism.test",
    )

    after = restored.snapshot(mode=GenerativeMode.IDLE)
    assert restored.generative_tick == resident.generative_tick
    assert tuple(target.target_id for target in restored.agenda.targets) == tuple(
        target.target_id for target in resident.agenda.targets
    )
    assert after.episode_id == before.episode_id
    assert after.state_count == before.state_count
    assert after.transition_count == before.transition_count
    assert after.agenda_contamination_count == 0



def test_resident_reconciles_hypothesis_only_with_matching_factual_model_domain() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    resident.register_model(_Model())
    resident.step(
        tick=1,
        cognition=None,
        prospective_candidate_ids=("competence.a",),
        mode=GenerativeMode.ONLINE,
    )

    assert len(resident.hypotheses) == 1
    hypothesis = next(iter(resident.hypotheses.values()))
    assert hypothesis.status.value == "predicted"

    ignored = resident.note_factual_outcome(
        action_id="competence.a",
        outcome_tokens=("outcome.test",),
        evidence_refs=("evidence.other",),
        model_ids=("other-model",),
    )
    assert ignored == 0
    assert hypothesis.status.value == "predicted"

    reconciled = resident.note_factual_outcome(
        action_id="competence.a",
        outcome_tokens=("outcome.test",),
        evidence_refs=("evidence.observed",),
        model_ids=("model.test",),
    )
    assert reconciled == 1
    assert hypothesis.status.value == "supported"
    assert hypothesis.factual_support_refs == ("evidence.observed",)
    assert resident.reconciliation_count == 1


def test_resident_marks_matching_action_hypothesis_contradicted_by_factual_outcome() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    resident.register_model(_Model())
    resident.step(
        tick=1,
        cognition=None,
        prospective_candidate_ids=("competence.a",),
        mode=GenerativeMode.ONLINE,
    )

    reconciled = resident.note_factual_outcome(
        action_id="competence.a",
        outcome_tokens=("outcome.different",),
        evidence_refs=("evidence.observed",),
        model_ids=("model.test",),
    )

    hypothesis = next(iter(resident.hypotheses.values()))
    assert reconciled == 1
    assert hypothesis.status.value == "contradicted"
    assert hypothesis.factual_conflict_refs == ("evidence.observed",)



class _BranchingModel:
    def __init__(self, model_id: str, outcome: str) -> None:
        self.model_id = model_id
        self.outcome = outcome

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation in {GenerativeOperation.PREDICT, GenerativeOperation.BRANCH}

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        return (
            GeneratedProposal(
                features=(GeneratedFeature(self.outcome, None, 0.7, self.model_id),),
                predicted_outcomes=(self.outcome,),
                uncertainty=0.3,
                coherence=0.9,
                model_id=self.model_id,
                support_refs=context.references,
            ),
        )


def test_resident_preserves_model_disagreement_as_separate_branches_and_hypotheses() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    resident.register_model(_BranchingModel("model.a", "outcome.a"))
    resident.register_model(_BranchingModel("model.b", "outcome.b"))

    snapshot = resident.step(
        tick=2,
        cognition=None,
        prospective_candidate_ids=("competence.a",),
        mode=GenerativeMode.ONLINE,
    )

    assert snapshot.transition_count == 2
    assert snapshot.hypothesis_count == 2
    assert resident.last_workspace is not None
    assert {
        state.source_model_ids for state in resident.last_workspace.states if state.depth == 1
    } == {("model.a",), ("model.b",)}
    assert {
        tuple(resident._hypothesis_outcomes[hypothesis_id])
        for hypothesis_id in resident.hypotheses
    } == {("outcome.a",), ("outcome.b",)}
