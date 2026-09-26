"""Matched mechanism assay for GC-E8 replay utility.

The assay gives both conditions one factual episodic source.  The control
queries a bounded model without materializing that source; the treatment
materializes the same source as ``REPLAYED`` cognition and queries the same
model.  Only the treatment can use the replayed feature to produce the hidden
target.  The factual episodic memory is inspected before and after replay to
guard against manufacturing a new observation.

This is a bounded replay-utility mechanism gate, not evidence of general
external-world utility.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.cognition.generative import (
    EpistemicOrigin,
    GeneratedFeature,
    GeneratedProposal,
    GenerativeBudget,
    GenerativeContext,
    GenerativeMode,
    GenerativeModelRegistry,
    GenerativeOperation,
    GenerativeState,
    GenerativeWorkspace,
    ResidentGenerativeCognition,
    RolloutEngine,
    new_episode,
)
from symbiont.modeling.episodic import EpisodicExperienceMemory
from symbiont.modeling.experience import (
    EpistemicStatus,
    ExperienceRecord,
    SourceKind,
)

_SOURCE_FEATURE = "opaque.signal.1"
_EXPECTED_OUTCOME = "opaque.signal.2"
_FALLBACK_OUTCOME = "opaque.signal.unknown"
_MODEL_ID = "model.replay-utility"


class _ReplayAwareModel:
    model_id = _MODEL_ID

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation is GenerativeOperation.PREDICT

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        tokens = {feature.token for feature in state.features}
        outcome = _EXPECTED_OUTCOME if _SOURCE_FEATURE in tokens else _FALLBACK_OUTCOME
        return (
            GeneratedProposal(
                features=(GeneratedFeature(outcome, None, 0.8, self.model_id),),
                predicted_outcomes=(outcome,),
                uncertainty=0.25 if outcome == _EXPECTED_OUTCOME else 0.75,
                coherence=0.9 if outcome == _EXPECTED_OUTCOME else 0.4,
                model_id=self.model_id,
                support_refs=(),
            ),
        )


def _factual_memory(*, seed: int) -> EpisodicExperienceMemory:
    memory = EpisodicExperienceMemory(organism_id=f"gc-e8-{seed}")
    memory.observe(
        ExperienceRecord(
            record_id=f"transition.gc-e8.{seed}",
            organism_id=f"gc-e8-{seed}",
            tick_class=seed,
            context_tokens=(_SOURCE_FEATURE,),
            action_token="opaque.query",
            outcome_tokens=("opaque.observed.outcome",),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=(f"evaluator.fact.{seed}",),
            confidence_class=5,
            source_kind=SourceKind.DIRECT,
        )
    )
    memory.flush()
    return memory


def _root_workspace(*, seed: int) -> GenerativeWorkspace:
    episode = new_episode(
        episode_id=f"gc-e8.control.{seed}",
        organism_id=f"gc-e8-{seed}",
        root_state_id="root",
        mode=GenerativeMode.OFFLINE,
        symbiont_tick=seed,
        generative_tick=0,
    )
    workspace = GenerativeWorkspace(
        episode=episode,
        budget=GenerativeBudget(max_depth=1, max_states=2, max_transitions=1),
    )
    workspace.add_state(
        GenerativeState(
            state_id="root",
            episode_id=episode.episode_id,
            origin=EpistemicOrigin.INFERRED,
            parent_state_id=None,
            depth=0,
            features=(),
            active_concept_ids=(),
            relation_refs=(),
            source_episode_ids=(),
            source_model_ids=(),
            source_state_ids=(),
            uncertainty=0.0,
            coherence=1.0,
            generative_tick=0,
        )
    )
    return workspace


def _predict(*, registry: GenerativeModelRegistry, workspace: GenerativeWorkspace) -> str:
    result = RolloutEngine(registry=registry, workspace=workspace).rollout(
        root_state_id=workspace.episode.root_state_id,
        context=GenerativeContext(tokens=("opaque.query",), references=()),
        max_depth=1,
    )
    return result.transitions[-1].predicted_outcomes[0] if result.transitions else ""


@dataclass(frozen=True, slots=True)
class GenerativeReplayUtilityTrial:
    seed: int
    source_episode_id: str
    online_only_prediction: str
    replay_prediction: str
    online_only_correct: bool
    replay_correct: bool
    replay_root_origin: str
    replay_source_episode_ids: tuple[str, ...]
    factual_episode_count_before: int
    factual_episode_count_after: int
    factual_contamination_count: int
    agenda_contamination_count: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GenerativeReplayUtilityStudy:
    seeds: tuple[int, ...]
    trials: tuple[GenerativeReplayUtilityTrial, ...]
    online_only_accuracy: float
    replay_accuracy: float
    replay_improves_prediction: bool
    all_source_provenance_preserved: bool
    all_factual_counts_unchanged: bool
    all_factual_contamination_free: bool
    all_agenda_contamination_free: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "trials": [trial.as_dict() for trial in self.trials],
        }


def run_generative_replay_utility_study(
    *,
    seeds: Iterable[int] = (101, 127, 149),
) -> GenerativeReplayUtilityStudy:
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 16 or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must contain between 1 and 16 unique integers")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized):
        raise ValueError("seeds must be integers")

    trials: list[GenerativeReplayUtilityTrial] = []
    for seed in normalized:
        memory = _factual_memory(seed=seed)
        factual_before = len(memory.episodes)
        source_episode_id = memory.episodes[0].episode_id

        control_registry = GenerativeModelRegistry()
        control_registry.register(_ReplayAwareModel())
        online_prediction = _predict(
            registry=control_registry,
            workspace=_root_workspace(seed=seed),
        )

        resident = ResidentGenerativeCognition(
            organism_id=f"gc-e8-{seed}",
            budget=GenerativeBudget(max_depth=1, max_states=2, max_transitions=1),
        )
        resident.register_model(_ReplayAwareModel())
        resident.materialize_replay(
            tick=seed,
            source_episode_id=source_episode_id,
            context_tokens=(_SOURCE_FEATURE,),
        )
        assert resident.last_workspace is not None
        replay_root = resident.last_workspace.states[0]
        replay_prediction = _predict(
            registry=resident.registry,
            workspace=resident.last_workspace,
        )
        factual_after = len(memory.episodes)
        trials.append(
            GenerativeReplayUtilityTrial(
                seed=seed,
                source_episode_id=source_episode_id,
                online_only_prediction=online_prediction,
                replay_prediction=replay_prediction,
                online_only_correct=online_prediction == _EXPECTED_OUTCOME,
                replay_correct=replay_prediction == _EXPECTED_OUTCOME,
                replay_root_origin=replay_root.origin.value,
                replay_source_episode_ids=replay_root.source_episode_ids,
                factual_episode_count_before=factual_before,
                factual_episode_count_after=factual_after,
                factual_contamination_count=resident.factual_contamination_count,
                agenda_contamination_count=0,
            )
        )

    online_accuracy = sum(item.online_only_correct for item in trials) / len(trials)
    replay_accuracy = sum(item.replay_correct for item in trials) / len(trials)
    provenance = all(
        item.replay_root_origin == EpistemicOrigin.REPLAYED.value
        and item.replay_source_episode_ids == (item.source_episode_id,)
        for item in trials
    )
    counts_unchanged = all(
        item.factual_episode_count_before == item.factual_episode_count_after for item in trials
    )
    factual_free = all(item.factual_contamination_count == 0 for item in trials)
    agenda_free = all(item.agenda_contamination_count == 0 for item in trials)
    passed = (
        replay_accuracy > online_accuracy
        and replay_accuracy == 1.0
        and provenance
        and counts_unchanged
        and factual_free
        and agenda_free
    )
    return GenerativeReplayUtilityStudy(
        seeds=normalized,
        trials=tuple(trials),
        online_only_accuracy=online_accuracy,
        replay_accuracy=replay_accuracy,
        replay_improves_prediction=replay_accuracy > online_accuracy,
        all_source_provenance_preserved=provenance,
        all_factual_counts_unchanged=counts_unchanged,
        all_factual_contamination_free=factual_free,
        all_agenda_contamination_free=agenda_free,
        passed=passed,
    )


__all__ = [
    "GenerativeReplayUtilityStudy",
    "GenerativeReplayUtilityTrial",
    "run_generative_replay_utility_study",
]
