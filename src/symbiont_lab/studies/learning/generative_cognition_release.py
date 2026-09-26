"""Release-gate study for Generative Cognition v1.

The apparatus exercises the canonical generative substrate without feeding
laboratory labels or scores back into an organism.  It focuses on the three
release-blocking invariants:

GC-E5  generated cognition never becomes factual evidence;
GC-E10 agenda selection and stopping are endogenous;
GC-E13 consolidation cannot defeat anti-rumination and monopolise agenda.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.cognition.generative import (
    AgendaProgress,
    AgendaSource,
    GeneratedFeature,
    GeneratedProposal,
    GenerativeAgenda,
    GenerativeContext,
    GenerativeMode,
    GenerativeOperation,
    GenerativeState,
    GenerativeTarget,
    ResidentGenerativeCognition,
)
from symbiont.cognition.generative.consolidation import GenerativeConsolidator


class _FalsePredictionModel:
    model_id = "study.false-model"

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation in {GenerativeOperation.PREDICT, GenerativeOperation.BRANCH}

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        action = context.tokens[0] if context.tokens else "unknown"
        predicted = f"outcome.predicted.{action}"
        return (
            GeneratedProposal(
                features=(
                    GeneratedFeature(
                        token=predicted,
                        value_class=None,
                        confidence=0.8,
                        source_model_id=self.model_id,
                    ),
                ),
                predicted_outcomes=(predicted,),
                uncertainty=0.2,
                coherence=0.9,
                model_id=self.model_id,
                support_refs=context.references,
            ),
        )


@dataclass(frozen=True, slots=True)
class FactualContaminationGate:
    generated_episodes: int
    reconciliations: int
    contradicted_hypotheses: int
    factual_contamination_count: int
    all_generated_origins_non_observed: bool

    @property
    def passed(self) -> bool:
        return (
            self.generated_episodes > 0
            and self.reconciliations == self.generated_episodes
            and self.contradicted_hypotheses == self.generated_episodes
            and self.factual_contamination_count == 0
            and self.all_generated_origins_non_observed
        )


@dataclass(frozen=True, slots=True)
class EndogenousAgendaGate:
    productive_selected: bool
    productive_resolved: bool
    stagnant_suppressed: bool
    alternate_selected_after_suppression: bool
    agenda_contamination_count: int

    @property
    def passed(self) -> bool:
        return (
            self.productive_selected
            and self.productive_resolved
            and self.stagnant_suppressed
            and self.alternate_selected_after_suppression
            and self.agenda_contamination_count == 0
        )


@dataclass(frozen=True, slots=True)
class AgendaConsolidationGate:
    mature_consolidation_signal: bool
    stagnant_target_suppressed: bool
    productive_target_selected: bool
    source_diversity: int
    cross_episode_reuse: int

    @property
    def passed(self) -> bool:
        return (
            self.mature_consolidation_signal
            and self.stagnant_target_suppressed
            and self.productive_target_selected
            and self.source_diversity >= 2
            and self.cross_episode_reuse >= 1
        )


@dataclass(frozen=True, slots=True)
class GenerativeCognitionReleaseGateReport:
    gc_e5: FactualContaminationGate
    gc_e10: EndogenousAgendaGate
    gc_e13: AgendaConsolidationGate

    @property
    def passed(self) -> bool:
        return self.gc_e5.passed and self.gc_e10.passed and self.gc_e13.passed

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "gc_e5": {**asdict(self.gc_e5), "passed": self.gc_e5.passed},
            "gc_e10": {**asdict(self.gc_e10), "passed": self.gc_e10.passed},
            "gc_e13": {**asdict(self.gc_e13), "passed": self.gc_e13.passed},
        }


def _run_gc_e5(*, episodes: int) -> FactualContaminationGate:
    resident = ResidentGenerativeCognition(organism_id="gc-release-e5")
    resident.register_model(_FalsePredictionModel())
    all_non_observed = True

    for index in range(episodes):
        action_id = f"competence.{index}"
        snapshot = resident.step(
            tick=index * 2,
            cognition=None,
            prospective_candidate_ids=(action_id,),
            mode=GenerativeMode.ONLINE,
        )
        all_non_observed = all_non_observed and all(
            state.origin != "observed" for state in snapshot.states
        )
        resident.note_factual_outcome(
            action_id=action_id,
            outcome_tokens=(f"outcome.actual.{index}",),
            evidence_refs=(f"evidence.gc-e5.{index}",),
            model_ids=(_FalsePredictionModel.model_id,),
        )

    return FactualContaminationGate(
        generated_episodes=episodes,
        reconciliations=resident.reconciliation_count,
        contradicted_hypotheses=resident.contradicted_hypothesis_count,
        factual_contamination_count=resident.factual_contamination_count,
        all_generated_origins_non_observed=all_non_observed,
    )


def _target(
    target_id: str,
    *,
    source: AgendaSource,
    uncertainty: float,
    resolvability: float,
    tick: int = 0,
) -> GenerativeTarget:
    return GenerativeTarget(
        target_id=target_id,
        source=source,
        source_refs=(f"internal.{target_id}",),
        created_tick=tick,
        uncertainty=uncertainty,
        persistence=0.5,
        recurrence=1,
        estimated_resolvability=resolvability,
    )


def _run_gc_e10() -> EndogenousAgendaGate:
    agenda = GenerativeAgenda(
        max_reselection_without_progress=2,
        suppression_duration=8,
    )
    productive = _target(
        "target.productive",
        source=AgendaSource.ACTIVE_HYPOTHESIS,
        uncertainty=0.8,
        resolvability=0.9,
    )
    stagnant = _target(
        "target.stagnant",
        source=AgendaSource.UNCERTAINTY,
        uncertainty=1.0,
        resolvability=0.0,
    )
    alternate = _target(
        "target.alternate",
        source=AgendaSource.PREDICTION_ERROR,
        uncertainty=0.4,
        resolvability=0.8,
    )
    for item in (productive, stagnant, alternate):
        agenda.add_target(item)

    first = agenda.select(
        tick=1,
        limit=1,
        sources=frozenset({AgendaSource.ACTIVE_HYPOTHESIS}),
    )
    productive_selected = bool(first and first[0].target.target_id == productive.target_id)
    if productive_selected:
        agenda.record_progress(
            productive.target_id,
            tick=1,
            progress=AgendaProgress(hypothesis_changed=True),
        )
        agenda.resolve(productive.target_id)

    for tick in (2, 3):
        selected = agenda.select(
            tick=tick,
            limit=1,
            sources=frozenset({AgendaSource.UNCERTAINTY}),
        )
        if selected:
            agenda.record_progress(
                stagnant.target_id,
                tick=tick,
                progress=AgendaProgress(),
            )

    stagnant_state = next(item for item in agenda.targets if item.target_id == stagnant.target_id)
    selected_after = agenda.select(
        tick=4,
        limit=1,
        sources=frozenset({AgendaSource.PREDICTION_ERROR, AgendaSource.UNCERTAINTY}),
    )
    return EndogenousAgendaGate(
        productive_selected=productive_selected,
        productive_resolved=any(
            item.target_id == productive.target_id and item.status.value == "resolved"
            for item in agenda.targets
        ),
        stagnant_suppressed=stagnant_state.status.value == "suppressed",
        alternate_selected_after_suppression=bool(
            selected_after and selected_after[0].target.target_id == alternate.target_id
        ),
        agenda_contamination_count=agenda.agenda_contamination_count,
    )


def _run_gc_e13() -> AgendaConsolidationGate:
    agenda = GenerativeAgenda(
        max_reselection_without_progress=2,
        suppression_duration=16,
    )
    sticky = _target(
        "target.sticky",
        source=AgendaSource.ACTIVE_HYPOTHESIS,
        uncertainty=0.9,
        resolvability=0.9,
    )
    productive = _target(
        "target.new",
        source=AgendaSource.PREDICTION_ERROR,
        uncertainty=0.6,
        resolvability=0.9,
    )
    agenda.add_target(sticky)
    agenda.add_target(productive)

    consolidator = GenerativeConsolidator()
    for episode_id, evidence_ref in (
        ("episode.1", "evidence.1"),
        ("episode.2", "evidence.2"),
        ("episode.3", "evidence.3"),
    ):
        consolidator.tracker.record(
            representation_ref="representation.sticky",
            episode_id=episode_id,
            state_id=f"{episode_id}.state",
            model_ids=("model.a",),
            hypothesis_ref="hypothesis.sticky",
        )
        consolidator.tracker.note_factual_sources(
            representation_ref="representation.sticky",
            source_refs=(evidence_ref,),
        )
    signal = consolidator.signal(
        representation_ref="representation.sticky",
        generative_demand=0.9,
    )

    # Even a mature, source-diverse consolidation signal does not feed agenda
    # priority.  With no cognitive progress, anti-rumination must still win.
    for tick in (1, 2):
        selected = agenda.select(
            tick=tick,
            limit=1,
            sources=frozenset({AgendaSource.ACTIVE_HYPOTHESIS}),
        )
        if selected:
            agenda.record_progress(
                sticky.target_id,
                tick=tick,
                progress=AgendaProgress(),
            )

    sticky_state = next(item for item in agenda.targets if item.target_id == sticky.target_id)
    next_selected = agenda.select(
        tick=3,
        limit=1,
        sources=frozenset({AgendaSource.ACTIVE_HYPOTHESIS, AgendaSource.PREDICTION_ERROR}),
    )
    return AgendaConsolidationGate(
        mature_consolidation_signal=consolidator.is_mature(signal),
        stagnant_target_suppressed=sticky_state.status.value == "suppressed",
        productive_target_selected=bool(
            next_selected and next_selected[0].target.target_id == productive.target_id
        ),
        source_diversity=signal.source_diversity,
        cross_episode_reuse=signal.cross_episode_reuse,
    )


def run_generative_cognition_release_gates(
    *,
    episodes: int = 16,
) -> GenerativeCognitionReleaseGateReport:
    if isinstance(episodes, bool) or not isinstance(episodes, int) or episodes < 4:
        raise ValueError("episodes must be an integer >= 4")
    return GenerativeCognitionReleaseGateReport(
        gc_e5=_run_gc_e5(episodes=episodes),
        gc_e10=_run_gc_e10(),
        gc_e13=_run_gc_e13(),
    )


__all__ = [
    "AgendaConsolidationGate",
    "EndogenousAgendaGate",
    "FactualContaminationGate",
    "GenerativeCognitionReleaseGateReport",
    "run_generative_cognition_release_gates",
]
