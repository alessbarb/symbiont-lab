from __future__ import annotations

from dataclasses import dataclass

import pytest

from symbiont.cognition.generative import (
    AgendaSource,
    CompetenceEffectGenerativeAdapter,
    GeneratedFeature,
    GeneratedProposal,
    GenerativeContext,
    GenerativeMode,
    GenerativeOperation,
    GenerativeResidentSnapshot,
    GenerativeState,
    GenerativeTarget,
    RecombinationFragment,
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


class _CounterfactualModel:
    model_id = "model.counterfactual"

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation is GenerativeOperation.COUNTERFACTUAL

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        return (
            GeneratedProposal(
                features=(GeneratedFeature("outcome.counterfactual", None, 0.7, self.model_id),),
                predicted_outcomes=("outcome.counterfactual",),
                uncertainty=0.4,
                coherence=0.8,
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


def test_recurring_conflict_routes_to_counterfactual_without_factual_authority() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    resident.register_model(_CounterfactualModel())
    resident.agenda.add_target(
        GenerativeTarget(
            target_id="target.recurring-conflict",
            source=AgendaSource.RECURRING_CONFLICT,
            source_refs=("internal.conflict",),
            created_tick=1,
            uncertainty=0.8,
            persistence=0.5,
            recurrence=2,
            estimated_resolvability=0.7,
        )
    )

    snapshot = resident.step(tick=1, cognition=None, mode=GenerativeMode.IDLE)

    assert snapshot.target_id == "target.recurring-conflict"
    assert snapshot.transition_count == 2
    assert snapshot.transitions[0].operation == GenerativeOperation.COUNTERFACTUAL.value
    assert snapshot.states[-1].origin == "counterfactual"
    assert snapshot.factual_contamination_count == 0


def test_idle_mode_routes_prediction_error_to_a_compatible_model() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    resident.register_model(_Model())

    snapshot = resident.step(
        tick=1,
        cognition=_Cognition(),
        mode=GenerativeMode.IDLE,
    )

    assert snapshot.target_id == "gc.prediction.predictor.a.sense.a"
    assert snapshot.transition_count == 2
    assert snapshot.termination is not None
    assert snapshot.termination.value == "completed"


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
        tuple(resident._hypothesis_outcomes[hypothesis_id]) for hypothesis_id in resident.hypotheses
    } == {("outcome.a",), ("outcome.b",)}


def test_materialized_replay_preserves_factual_source_without_creating_observation() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")

    snapshot = resident.materialize_replay(
        tick=8,
        source_episode_id="episode.source",
        context_tokens=("sense.a", "concept.a"),
        action_tokens=("action.a",),
        outcome_tokens=("effect.a",),
        uncertainty=0.2,
        coherence=0.9,
    )

    assert snapshot.mode is GenerativeMode.OFFLINE
    assert snapshot.state_count == 1
    assert snapshot.transition_count == 0
    assert snapshot.hypothesis_count == 0
    assert snapshot.factual_contamination_count == 0
    assert resident.last_workspace is not None
    state = resident.last_workspace.states[0]
    assert state.origin.value == "replayed"
    assert state.source_episode_ids == ("episode.source",)
    signal = resident.consolidator.signal(
        representation_ref="sense.a",
        generative_demand=0.7,
    )
    assert signal.recurrent_activation == 1
    assert signal.source_diversity == 1


def test_replaying_same_factual_episode_does_not_manufacture_source_diversity() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")

    for tick in (8, 9, 10):
        resident.materialize_replay(
            tick=tick,
            source_episode_id="episode.same",
            context_tokens=("sense.a",),
        )

    signal = resident.consolidator.signal(
        representation_ref="sense.a",
        generative_demand=0.7,
    )
    assert signal.recurrent_activation == 3
    assert signal.independent_episode_count == 3
    assert signal.source_diversity == 1
    assert not resident.consolidator.is_mature(signal)


def test_recombination_materializes_two_compatible_sources_as_imagined() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    left = RecombinationFragment(
        source_episode_id="episode.left",
        source_state_id="state.left",
        features=(GeneratedFeature("feature.left", None, 0.9),),
        compatibility_keys=("context.shared",),
        uncertainty=0.2,
        coherence=0.9,
    )
    right = RecombinationFragment(
        source_episode_id="episode.right",
        source_state_id="state.right",
        features=(GeneratedFeature("feature.right", None, 0.8),),
        compatibility_keys=("context.shared",),
        uncertainty=0.3,
        coherence=0.7,
    )

    snapshot = resident.materialize_recombination(tick=11, left=left, right=right)

    assert snapshot.mode is GenerativeMode.OFFLINE
    assert snapshot.state_count == 1
    assert snapshot.transition_count == 0
    assert snapshot.factual_contamination_count == 0
    assert resident.last_workspace is not None
    assert resident.last_workspace.episode.source_episode_ids == (
        "episode.left",
        "episode.right",
    )
    state = resident.last_workspace.states[0]
    assert state.origin.value == "imagined"
    assert state.source_episode_ids == ("episode.left", "episode.right")
    assert state.relation_refs == ("context.shared",)
    assert (
        resident.consolidator.signal(
            representation_ref="feature.left", generative_demand=0.5
        ).source_diversity
        == 0
    )


def test_recombination_rejects_incompatible_fragments_without_workspace() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    left = RecombinationFragment(
        source_episode_id="episode.left",
        source_state_id="state.left",
        features=(GeneratedFeature("feature.left", None, 0.9),),
        compatibility_keys=("context.left",),
        uncertainty=0.2,
        coherence=0.9,
    )
    right = RecombinationFragment(
        source_episode_id="episode.right",
        source_state_id="state.right",
        features=(GeneratedFeature("feature.right", None, 0.8),),
        compatibility_keys=("context.right",),
        uncertainty=0.3,
        coherence=0.7,
    )

    with pytest.raises(ValueError, match="no organism-owned compatibility relation"):
        resident.materialize_recombination(tick=11, left=left, right=right)

    assert resident.last_workspace is None


def test_recombination_checkpoint_preserves_multi_episode_provenance() -> None:
    resident = ResidentGenerativeCognition(organism_id="organism.test")
    fragment = RecombinationFragment(
        source_episode_id="episode.left",
        source_state_id="state.left",
        features=(GeneratedFeature("feature.left", None, 0.9),),
        compatibility_keys=("context.shared",),
        uncertainty=0.2,
        coherence=0.9,
    )
    other = RecombinationFragment(
        source_episode_id="episode.right",
        source_state_id="state.right",
        features=(GeneratedFeature("feature.right", None, 0.8),),
        compatibility_keys=("context.shared",),
        uncertainty=0.3,
        coherence=0.7,
    )

    resident.materialize_recombination(tick=11, left=fragment, right=other)
    restored = ResidentGenerativeCognition.from_checkpoint(
        resident.checkpoint(), organism_id="organism.test"
    )

    assert restored.last_workspace is not None
    assert restored.last_workspace.episode.source_episode_ids == (
        "episode.left",
        "episode.right",
    )
    assert restored.last_workspace.states[0].origin.value == "imagined"
    assert restored.last_workspace.states[0].source_state_ids == (
        "state.left",
        "state.right",
    )
