"""Resident orchestration for Generative Cognition v1.

This module composes the bounded generative substrate inside the organism
without acquiring factual-evidence or motor authority.  It deliberately owns
only temporary generative state, endogenous agenda state, model routing and
scheduler state.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .agenda import (
    AgendaCandidate,
    AgendaProgress,
    AgendaSource,
    GenerativeAgenda,
    GenerativeTarget,
    TargetStatus,
)
from .branch import BranchEngine
from .budget import GenerativeBudget
from .calibration import PredictionCalibration
from .consolidation import GenerativeConsolidator, GenerativeUseTracker
from .episode import new_episode
from .execution import GenerativeExecutionCoordinator, GenerativeExecutionResult
from .epistemic_value import EpistemicValue, EpistemicValueEstimator
from .hypothesis import GenerativeHypothesis, HypothesisStatus
from .model import GenerativeContext, GenerativeModel
from .registry import GenerativeModelRegistry
from .reconciliation import GenerativeReconciler
from .replay import ReplayEngine, ReplayFragment
from .persistence import GENERATIVE_COGNITION_SCHEMA_VERSION, restore as restore_workspace
from .rollout import RolloutEngine, RolloutResult
from .scheduler import GenerativeScheduler
from .types import (
    EpistemicOrigin,
    GeneratedFeature,
    GenerativeMode,
    GenerativeOperation,
    GenerativeState,
    GenerativeTermination,
)
from .workspace import GenerativeWorkspace


@dataclass(frozen=True, slots=True)
class GenerativeStateSnapshot:
    state_id: str
    parent_state_id: str | None
    origin: str
    depth: int
    model_ids: tuple[str, ...]
    uncertainty: float
    coherence: float


@dataclass(frozen=True, slots=True)
class GenerativeTransitionSnapshot:
    transition_id: str
    source_state_id: str
    target_state_id: str
    operation: str
    model_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GenerativeHypothesisSnapshot:
    hypothesis_id: str
    target_id: str
    status: str
    model_ids: tuple[str, ...]
    uncertainty: float


@dataclass(frozen=True, slots=True)
class GenerativeResidentSnapshot:
    """Bounded passive view of the most recent resident generative pass."""

    mode: GenerativeMode
    target_id: str | None
    episode_id: str | None
    state_count: int
    transition_count: int
    branch_count: int
    max_depth: int
    model_queries: int
    termination: GenerativeTermination | None
    agenda_candidate_count: int
    agenda_contamination_count: int
    factual_contamination_count: int
    hypothesis_count: int
    reconciliation_count: int
    consolidation_signal_count: int
    states: tuple[GenerativeStateSnapshot, ...]
    transitions: tuple[GenerativeTransitionSnapshot, ...]
    hypotheses: tuple[GenerativeHypothesisSnapshot, ...]


class ResidentGenerativeCognition:
    """Compose agenda, scheduling, models and rollout inside one Symbiont.

    The class receives only organism-owned cognitive state and opaque action
    candidates.  It cannot execute actions or write factual evidence.
    """

    def __init__(
        self,
        *,
        organism_id: str,
        budget: GenerativeBudget | None = None,
        agenda: GenerativeAgenda | None = None,
        scheduler: GenerativeScheduler | None = None,
        registry: GenerativeModelRegistry | None = None,
    ) -> None:
        if not isinstance(organism_id, str) or not organism_id:
            raise ValueError("organism_id must be non-empty")
        self.organism_id = organism_id
        self.budget = budget or GenerativeBudget()
        self.agenda = agenda or GenerativeAgenda()
        self.scheduler = scheduler or GenerativeScheduler()
        self.registry = registry or GenerativeModelRegistry()
        self.execution = GenerativeExecutionCoordinator(
            agenda=self.agenda,
            scheduler=self.scheduler,
        )
        self.generative_tick = 0
        self.last_workspace: GenerativeWorkspace | None = None
        self.last_execution: GenerativeExecutionResult | None = None
        self.last_rollout: RolloutResult | None = None
        self.hypotheses: dict[str, GenerativeHypothesis] = {}
        self._hypothesis_target: dict[str, str] = {}
        self._hypothesis_outcomes: dict[str, tuple[str, ...]] = {}
        self._hypothesis_representations: dict[str, tuple[str, ...]] = {}
        self._hypothesis_calibration: dict[
            str, tuple[str, GenerativeOperation, int, float]
        ] = {}
        self.reconciler = GenerativeReconciler()
        self.calibration = PredictionCalibration()
        self.consolidator = GenerativeConsolidator()
        self.reconciliation_count = 0
        self.factual_contamination_count = 0

    def register_model(self, model: GenerativeModel) -> None:
        self.registry.register(model)

    def checkpoint(self) -> dict[str, object]:
        """Persist durable resident GC state without persisting model owners."""
        return {
            "schema_version": GENERATIVE_COGNITION_SCHEMA_VERSION,
            "generative_tick": self.generative_tick,
            "agenda": self.agenda.checkpoint(),
            "scheduler": self.scheduler.checkpoint(),
            "workspace": (
                self.last_workspace.checkpoint()
                if self.last_workspace is not None
                else None
            ),
            "hypotheses": [
                {
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "source_episode_ids": list(hypothesis.source_episode_ids),
                    "source_model_ids": list(hypothesis.source_model_ids),
                    "uncertainty": hypothesis.uncertainty,
                    "status": hypothesis.status.value,
                    "factual_support_refs": list(hypothesis.factual_support_refs),
                    "factual_conflict_refs": list(hypothesis.factual_conflict_refs),
                    "target_id": self._hypothesis_target[hypothesis.hypothesis_id],
                    "predicted_outcomes": list(
                        self._hypothesis_outcomes.get(hypothesis.hypothesis_id, ())
                    ),
                    "representation_refs": list(
                        self._hypothesis_representations.get(hypothesis.hypothesis_id, ())
                    ),
                    "calibration": (
                        {
                            "model_id": self._hypothesis_calibration[hypothesis.hypothesis_id][0],
                            "operation": self._hypothesis_calibration[hypothesis.hypothesis_id][1].value,
                            "depth": self._hypothesis_calibration[hypothesis.hypothesis_id][2],
                            "uncertainty": self._hypothesis_calibration[hypothesis.hypothesis_id][3],
                        }
                        if hypothesis.hypothesis_id in self._hypothesis_calibration
                        else None
                    ),
                }
                for hypothesis in sorted(
                    self.hypotheses.values(), key=lambda item: item.hypothesis_id
                )
            ],
            "calibration": self.calibration.checkpoint(),
            "generative_use": self.consolidator.tracker.checkpoint(),
            "reconciliation_count": self.reconciliation_count,
            "factual_contamination_count": self.factual_contamination_count,
        }

    @classmethod
    def from_checkpoint(
        cls,
        payload: object,
        *,
        organism_id: str,
        budget: GenerativeBudget | None = None,
        registry: GenerativeModelRegistry | None = None,
    ) -> "ResidentGenerativeCognition":
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != GENERATIVE_COGNITION_SCHEMA_VERSION
        ):
            raise ValueError("invalid resident generative cognition checkpoint")
        try:
            agenda = GenerativeAgenda.from_checkpoint(payload["agenda"])
            scheduler = GenerativeScheduler.from_checkpoint(payload["scheduler"])
            tick = payload["generative_tick"]
            if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
                raise ValueError("invalid generative_tick")
            resident = cls(
                organism_id=organism_id,
                budget=budget,
                agenda=agenda,
                scheduler=scheduler,
                registry=registry,
            )
            resident.generative_tick = tick
            raw_workspace = payload.get("workspace")
            if raw_workspace is not None:
                resident.last_workspace = restore_workspace(
                    {
                        "schema_version": GENERATIVE_COGNITION_SCHEMA_VERSION,
                        "workspace": raw_workspace,
                    }
                )
                if resident.last_workspace.episode.organism_id != organism_id:
                    raise ValueError("generative workspace belongs to another organism")

            resident.calibration = PredictionCalibration.from_checkpoint(
                payload.get("calibration", {"buckets": []})
            )
            resident.consolidator = GenerativeConsolidator(
                tracker=GenerativeUseTracker.from_checkpoint(
                    payload.get("generative_use", {"representations": []})
                )
            )
            raw_reconciliations = payload.get("reconciliation_count", 0)
            raw_contamination = payload.get("factual_contamination_count", 0)
            for name, value in (
                ("reconciliation_count", raw_reconciliations),
                ("factual_contamination_count", raw_contamination),
            ):
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"invalid {name}")
            resident.reconciliation_count = raw_reconciliations
            resident.factual_contamination_count = raw_contamination

            raw_hypotheses = payload.get("hypotheses", [])
            if not isinstance(raw_hypotheses, list) or len(raw_hypotheses) > 128:
                raise ValueError("invalid generative hypothesis collection")
            for item in raw_hypotheses:
                if not isinstance(item, dict):
                    raise ValueError("invalid generative hypothesis")
                hypothesis = GenerativeHypothesis(
                    hypothesis_id=item["hypothesis_id"],
                    source_episode_ids=tuple(item.get("source_episode_ids", ())),
                    source_model_ids=tuple(item.get("source_model_ids", ())),
                    uncertainty=item["uncertainty"],
                    status=HypothesisStatus(item.get("status", HypothesisStatus.HYPOTHESIZED.value)),
                    factual_support_refs=tuple(item.get("factual_support_refs", ())),
                    factual_conflict_refs=tuple(item.get("factual_conflict_refs", ())),
                )
                resident.hypotheses[hypothesis.hypothesis_id] = hypothesis
                target_id = item["target_id"]
                if not isinstance(target_id, str) or not target_id:
                    raise ValueError("hypothesis target_id must be non-empty")
                resident._hypothesis_target[hypothesis.hypothesis_id] = target_id
                resident._hypothesis_outcomes[hypothesis.hypothesis_id] = tuple(
                    item.get("predicted_outcomes", ())
                )
                resident._hypothesis_representations[hypothesis.hypothesis_id] = tuple(
                    item.get("representation_refs", ())
                )
                raw_calibration = item.get("calibration")
                if raw_calibration is not None:
                    if not isinstance(raw_calibration, dict):
                        raise ValueError("invalid hypothesis calibration metadata")
                    resident._hypothesis_calibration[hypothesis.hypothesis_id] = (
                        str(raw_calibration["model_id"]),
                        GenerativeOperation(raw_calibration["operation"]),
                        int(raw_calibration["depth"]),
                        float(raw_calibration["uncertainty"]),
                    )
            return resident
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid resident generative cognition checkpoint") from exc

    def step(
        self,
        *,
        tick: int,
        cognition: object | None,
        prospective_candidate_ids: tuple[str, ...] = (),
        mode: GenerativeMode = GenerativeMode.ONLINE,
    ) -> GenerativeResidentSnapshot:
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be a non-negative integer")
        if not isinstance(prospective_candidate_ids, tuple):
            raise ValueError("prospective_candidate_ids must be a tuple")
        if not isinstance(mode, GenerativeMode):
            raise ValueError("mode must be a GenerativeMode")

        self._ingest_prediction_errors(cognition, tick=tick)
        self._ingest_prospective_candidates(prospective_candidate_ids, tick=tick)

        root_uncertainty = self._root_uncertainty(cognition)
        episode_id = f"generative.{tick}.{self.generative_tick}"
        root_state_id = f"{episode_id}.root"
        episode = new_episode(
            episode_id=episode_id,
            organism_id=self.organism_id,
            root_state_id=root_state_id,
            mode=mode,
            symbiont_tick=tick,
            generative_tick=self.generative_tick,
        )
        workspace = GenerativeWorkspace(episode=episode, budget=self.budget)
        root = GenerativeState(
            state_id=root_state_id,
            episode_id=episode_id,
            origin=EpistemicOrigin.INFERRED,
            parent_state_id=None,
            depth=0,
            features=self._root_features(cognition),
            active_concept_ids=(),
            relation_refs=(),
            source_episode_ids=(),
            source_model_ids=(),
            source_state_ids=(),
            uncertainty=root_uncertainty,
            coherence=1.0,
            generative_tick=self.generative_tick,
        )
        workspace.add_state(root)
        self.last_workspace = workspace
        self.last_rollout = None

        def run_target(candidate: AgendaCandidate, selected_mode: GenerativeMode) -> AgendaProgress:
            workspace.episode.target_id = candidate.target.target_id
            # v1 runtime adapters currently understand prospective competence
            # queries.  Other endogenous agenda sources remain valid targets,
            # but they must wait for a compatible model instead of being
            # reinterpreted as competence identifiers.
            if candidate.target.source is not AgendaSource.PROSPECTIVE_DECISION:
                return AgendaProgress()
            context = GenerativeContext(
                tokens=candidate.target.source_refs,
                references=candidate.target.source_refs,
            )
            depth = {
                GenerativeMode.ONLINE: 1,
                GenerativeMode.IDLE: min(2, workspace.budget.max_depth),
                GenerativeMode.OFFLINE: min(4, workspace.budget.max_depth),
            }[selected_mode]
            branching_models = self.registry.available(
                operation=GenerativeOperation.BRANCH,
                state=root,
            )
            if len(branching_models) > 1:
                result = BranchEngine(
                    registry=self.registry,
                    workspace=workspace,
                ).branch(
                    root_state_id=root_state_id,
                    context=context,
                    max_branches=min(
                        len(branching_models),
                        workspace.budget.max_branches,
                    ),
                )
            else:
                result = RolloutEngine(
                    registry=self.registry,
                    workspace=workspace,
                ).rollout(
                    root_state_id=root_state_id,
                    context=context,
                    operation=GenerativeOperation.PREDICT,
                    max_depth=depth,
                )
            self.last_rollout = result
            if result.states:
                self.generative_tick = max(
                    self.generative_tick,
                    max(state.generative_tick for state in result.states),
                )
            for transition in result.transitions:
                for model_id in transition.model_ids:
                    self.calibration.record_prediction(
                        model_id=model_id,
                        operation=transition.operation,
                        depth=max(
                            0,
                            next(
                                (
                                    state.depth
                                    for state in result.states
                                    if state.state_id == transition.target_state_id
                                ),
                                0,
                            ),
                        ),
                        uncertainty=transition.uncertainty_after,
                    )
            hypotheses_by_state: dict[str, GenerativeHypothesis] = {}
            if result.transitions:
                states_by_id = {state.state_id: state for state in result.states}
                for transition in result.transitions:
                    final_state = states_by_id.get(transition.target_state_id)
                    if final_state is None:
                        continue
                    hypothesis = self._ensure_hypothesis(
                        target_id=candidate.target.target_id,
                        episode_id=workspace.episode.episode_id,
                        transition=transition,
                        final_state=final_state,
                    )
                    if hypothesis is not None:
                        hypotheses_by_state[final_state.state_id] = hypothesis
                for state in result.states:
                    hypothesis = hypotheses_by_state.get(state.state_id)
                    for feature in state.features:
                        self.consolidator.tracker.record(
                            representation_ref=feature.token,
                            episode_id=workspace.episode.episode_id,
                            state_id=state.state_id,
                            model_ids=state.source_model_ids,
                            hypothesis_ref=(
                                hypothesis.hypothesis_id if hypothesis is not None else None
                            ),
                            model_disagreement=(
                                1.0
                                if len(
                                    {
                                        item.predicted_outcomes
                                        for item in result.transitions
                                    }
                                ) > 1
                                else 0.0
                            ),
                        )
            hypothesis_changed = bool(hypotheses_by_state)
            return AgendaProgress(
                new_branch=False,
                uncertainty_changed=any(
                    transition.uncertainty_after != transition.uncertainty_before
                    for transition in result.transitions
                ),
                disagreement_changed=(
                    len({item.predicted_outcomes for item in result.transitions}) > 1
                ),
                hypothesis_changed=hypothesis_changed,
                discriminating_consequence=bool(result.transitions),
                reconciliation=False,
            )

        self.last_execution = self.execution.run(
            mode=mode,
            tick=tick,
            workspace=workspace,
            run_target=run_target,
            eligible_sources=frozenset({AgendaSource.PROSPECTIVE_DECISION}),
        )

        target_id = self.last_execution.target_id
        if target_id is None:
            episode.termination_reason = GenerativeTermination.COMPLETED
        elif self.last_rollout is not None:
            episode.termination_reason = self.last_rollout.termination

        return self.snapshot(mode=mode)

    def _ensure_hypothesis(
        self,
        *,
        target_id: str,
        episode_id: str,
        transition,
        final_state: GenerativeState,
    ) -> GenerativeHypothesis | None:
        active = next(
            (
                hypothesis
                for hypothesis_id, hypothesis in self.hypotheses.items()
                if self._hypothesis_target.get(hypothesis_id) == target_id
                and hypothesis.source_model_ids == transition.model_ids
                and hypothesis.status in {
                    HypothesisStatus.HYPOTHESIZED,
                    HypothesisStatus.PREDICTED,
                }
            ),
            None,
        )
        if active is not None:
            return active
        if len(self.hypotheses) >= 128:
            return None
        digest = hashlib.sha256(
            f"{self.organism_id}|{target_id}|{episode_id}|{transition.model_ids}".encode("utf-8")
        ).hexdigest()[:24]
        hypothesis = GenerativeHypothesis(
            hypothesis_id=f"hypothesis.{digest}",
            source_episode_ids=(episode_id,),
            source_model_ids=transition.model_ids,
            uncertainty=final_state.uncertainty,
        )
        hypothesis.mark_predicted()
        self.hypotheses[hypothesis.hypothesis_id] = hypothesis
        self._hypothesis_target[hypothesis.hypothesis_id] = target_id
        self._hypothesis_outcomes[hypothesis.hypothesis_id] = transition.predicted_outcomes
        self._hypothesis_representations[hypothesis.hypothesis_id] = tuple(
            sorted({feature.token for feature in final_state.features})
        )
        if transition.model_ids:
            self._hypothesis_calibration[hypothesis.hypothesis_id] = (
                transition.model_ids[0],
                transition.operation,
                final_state.depth,
                transition.uncertainty_after,
            )
        return hypothesis

    def note_factual_outcome(
        self,
        *,
        action_id: str,
        outcome_tokens: tuple[str, ...],
        evidence_refs: tuple[str, ...],
        model_ids: tuple[str, ...] | None = None,
    ) -> int:
        """Reconcile only hypotheses for the action that actually occurred.

        All values supplied here must originate from the canonical factual
        experience path. Generated output is never accepted as evidence.
        """
        if not isinstance(action_id, str) or not action_id:
            raise ValueError("action_id must be non-empty")
        if not isinstance(outcome_tokens, tuple) or not isinstance(evidence_refs, tuple):
            raise ValueError("factual outcome inputs must be tuples")
        if not evidence_refs:
            raise ValueError("factual reconciliation requires evidence refs")
        target_id = f"gc.prospective.{action_id}"
        reconciled = 0
        for hypothesis_id, hypothesis in tuple(self.hypotheses.items()):
            if (
                self._hypothesis_target.get(hypothesis_id) != target_id
                or hypothesis.status not in {
                    HypothesisStatus.HYPOTHESIZED,
                    HypothesisStatus.PREDICTED,
                }
                or (
                    model_ids is not None
                    and not set(hypothesis.source_model_ids).intersection(model_ids)
                )
            ):
                continue
            predicted = set(self._hypothesis_outcomes.get(hypothesis_id, ()))
            supported = bool(predicted.intersection(outcome_tokens))
            self.reconciler.reconcile(
                hypothesis,
                evidence_ref=evidence_refs[0],
                supported=supported,
            )
            for representation_ref in self._hypothesis_representations.get(
                hypothesis_id, ()
            ):
                self.consolidator.tracker.note_factual_sources(
                    representation_ref=representation_ref,
                    source_refs=evidence_refs,
                )
            calibration = self._hypothesis_calibration.get(hypothesis_id)
            if calibration is not None:
                model_id, operation, depth, uncertainty = calibration
                self.calibration.record_comparison(
                    model_id=model_id,
                    operation=operation,
                    depth=depth,
                    uncertainty=uncertainty,
                    observed_error=0.0 if supported else 1.0,
                )
            self.agenda.resolve(target_id)
            reconciled += 1
        self.reconciliation_count += reconciled
        return reconciled

    def consolidation_signals(self) -> dict[str, object]:
        """Return bounded durable non-factual cognitive-use signals.

        Signals are derived from the bounded persistent tracker rather than
        only the most recent workspace, so source-diverse cognitive demand can
        survive ordinary tick changes and checkpoint restoration.
        """
        return {
            ref: self.consolidator.signal(
                representation_ref=ref,
                generative_demand=0.5,
            )
            for ref in self.consolidator.tracker.representation_refs[:64]
        }


    def materialize_replay(
        self,
        *,
        tick: int,
        source_episode_id: str,
        context_tokens: tuple[str, ...],
        action_tokens: tuple[str, ...] = (),
        outcome_tokens: tuple[str, ...] = (),
        uncertainty: float = 0.25,
        coherence: float = 1.0,
    ) -> GenerativeResidentSnapshot:
        """Materialize factual episodic provenance as non-factual replay.

        The replay is a new internal episode, not a new ExperienceRecord.  Its
        source episode id is retained so repeated replay cannot masquerade as
        independent factual evidence.
        """
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be a non-negative integer")
        if not isinstance(context_tokens, tuple):
            raise ValueError("context_tokens must be a tuple")
        episode_id = f"generative.replay.{tick}.{self.generative_tick}"
        root_state_id = f"{episode_id}.root"
        episode = new_episode(
            episode_id=episode_id,
            organism_id=self.organism_id,
            root_state_id=root_state_id,
            mode=GenerativeMode.OFFLINE,
            symbiont_tick=tick,
            generative_tick=self.generative_tick,
        )
        workspace = GenerativeWorkspace(episode=episode, budget=self.budget)
        features = tuple(
            GeneratedFeature(
                token=token,
                value_class=None,
                confidence=1.0,
                source_model_id=None,
            )
            for token in tuple(dict.fromkeys((*context_tokens, *action_tokens, *outcome_tokens)))[:32]
            if isinstance(token, str) and token
        )
        state = ReplayEngine(workspace=workspace).materialize(
            ReplayFragment(
                source_episode_id=source_episode_id,
                source_state_id=source_episode_id,
                features=features,
                uncertainty=uncertainty,
                coherence=coherence,
            )
        )
        episode.termination_reason = GenerativeTermination.COMPLETED
        self.last_workspace = workspace
        self.last_rollout = RolloutResult(
            states=(state,),
            transitions=(),
            termination=GenerativeTermination.COMPLETED,
        )
        self.last_execution = None
        for feature in state.features:
            self.consolidator.tracker.record(
                representation_ref=feature.token,
                episode_id=episode_id,
                state_id=state.state_id,
                source_refs=(source_episode_id,),
            )
        self.generative_tick += 1
        return self.snapshot(mode=GenerativeMode.OFFLINE)

    def epistemic_value_for(self, candidate_id: str) -> EpistemicValue | None:
        """Return a comparison-only epistemic signal for one opaque competence.

        The signal is derived exclusively from the endogenous prospective
        agenda target.  It cannot execute an action and does not alter factual
        outcome value.
        """
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("candidate_id must be non-empty")
        target_id = f"gc.prospective.{candidate_id}"
        target = next(
            (item for item in self.agenda.targets if item.target_id == target_id),
            None,
        )
        if target is None or target.status in {TargetStatus.RESOLVED, TargetStatus.RETIRED}:
            return None
        resolvability = target.estimated_resolvability or 0.0
        expected_uncertainty = target.uncertainty * (1.0 - resolvability)
        return EpistemicValueEstimator.estimate(
            candidate_ref=candidate_id,
            current_uncertainty=target.uncertainty,
            expected_uncertainty=expected_uncertainty,
            expected_hypothesis_discrimination=0.0,
            model_disagreement=(
                1.0
                if target.source in {
                    AgendaSource.MODEL_DISAGREEMENT,
                    AgendaSource.RECURRING_CONFLICT,
                }
                else 0.0
            ),
        )

    def snapshot(self, *, mode: GenerativeMode) -> GenerativeResidentSnapshot:
        workspace = self.last_workspace
        episode = workspace.episode if workspace is not None else None
        eligible = sum(
            1
            for target in self.agenda.targets
            if target.status in {TargetStatus.ELIGIBLE, TargetStatus.SUPPRESSED}
        )
        return GenerativeResidentSnapshot(
            mode=mode,
            target_id=(self.last_execution.target_id if self.last_execution is not None else None),
            episode_id=(episode.episode_id if episode is not None else None),
            state_count=(len(workspace.states) if workspace is not None else 0),
            transition_count=(len(workspace.transitions) if workspace is not None else 0),
            branch_count=(episode.branch_count if episode is not None else 0),
            max_depth=(episode.max_depth_reached if episode is not None else 0),
            model_queries=(workspace.model_queries if workspace is not None else 0),
            termination=(episode.termination_reason if episode is not None else None),
            agenda_candidate_count=eligible,
            agenda_contamination_count=self.agenda.agenda_contamination_count,
            factual_contamination_count=self.factual_contamination_count,
            hypothesis_count=len(self.hypotheses),
            reconciliation_count=self.reconciliation_count,
            consolidation_signal_count=len(self.consolidation_signals()),
            states=tuple(
                GenerativeStateSnapshot(
                    state_id=state.state_id,
                    parent_state_id=state.parent_state_id,
                    origin=state.origin.value,
                    depth=state.depth,
                    model_ids=state.source_model_ids,
                    uncertainty=state.uncertainty,
                    coherence=state.coherence,
                )
                for state in (workspace.states if workspace is not None else ())[:64]
            ),
            transitions=tuple(
                GenerativeTransitionSnapshot(
                    transition_id=transition.transition_id,
                    source_state_id=transition.source_state_id,
                    target_state_id=transition.target_state_id,
                    operation=transition.operation.value,
                    model_ids=transition.model_ids,
                )
                for transition in (workspace.transitions if workspace is not None else ())[:64]
            ),
            hypotheses=tuple(
                GenerativeHypothesisSnapshot(
                    hypothesis_id=hypothesis.hypothesis_id,
                    target_id=self._hypothesis_target.get(hypothesis.hypothesis_id, ""),
                    status=hypothesis.status.value,
                    model_ids=hypothesis.source_model_ids,
                    uncertainty=hypothesis.uncertainty,
                )
                for hypothesis in sorted(
                    self.hypotheses.values(),
                    key=lambda item: item.hypothesis_id,
                )[:128]
            ),
        )

    def _ingest_prediction_errors(self, cognition: object | None, *, tick: int) -> None:
        errors = tuple(getattr(cognition, "prediction_errors", ()) or ())
        for error in errors:
            predictor_id = str(getattr(error, "predictor_id", ""))
            target_id = str(getattr(error, "target_id", ""))
            if not predictor_id or not target_id:
                continue
            identifier = f"gc.prediction.{predictor_id}.{target_id}"
            loss = getattr(error, "loss", 0.0)
            try:
                uncertainty = max(0.0, min(1.0, float(loss)))
            except (TypeError, ValueError):
                uncertainty = 0.0
            self.agenda.observe_target(
                GenerativeTarget(
                    target_id=identifier,
                    source=AgendaSource.PREDICTION_ERROR,
                    source_refs=(predictor_id, target_id),
                    created_tick=tick,
                    uncertainty=uncertainty,
                    persistence=0.5,
                    recurrence=1,
                    estimated_resolvability=max(0.0, 1.0 - uncertainty),
                )
            )

    def _ingest_prospective_candidates(
        self,
        candidate_ids: tuple[str, ...],
        *,
        tick: int,
    ) -> None:
        for candidate_id in candidate_ids:
            if not isinstance(candidate_id, str) or not candidate_id:
                continue
            identifier = f"gc.prospective.{candidate_id}"
            self.agenda.observe_target(
                GenerativeTarget(
                    target_id=identifier,
                    source=AgendaSource.PROSPECTIVE_DECISION,
                    source_refs=(candidate_id,),
                    created_tick=tick,
                    uncertainty=0.5,
                    persistence=0.5,
                    recurrence=1,
                    estimated_resolvability=0.5,
                )
            )

    @staticmethod
    def _root_uncertainty(cognition: object | None) -> float:
        errors = tuple(getattr(cognition, "prediction_errors", ()) or ())
        losses: list[float] = []
        for error in errors:
            try:
                losses.append(max(0.0, min(1.0, float(getattr(error, "loss", 0.0)))))
            except (TypeError, ValueError):
                continue
        return sum(losses) / len(losses) if losses else 0.5

    @staticmethod
    def _root_features(cognition: object | None) -> tuple[GeneratedFeature, ...]:
        activations = getattr(cognition, "activations", None)
        if not isinstance(activations, Mapping):
            return ()
        ranked = sorted(
            (
                (str(node_id), float(value))
                for node_id, value in activations.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ),
            key=lambda item: (-abs(item[1]), item[0]),
        )[:16]
        return tuple(
            GeneratedFeature(
                token=node_id,
                value_class=value,
                confidence=max(0.0, min(1.0, abs(value))),
                source_model_id=None,
            )
            for node_id, value in ranked
        )


__all__ = [
    "GenerativeHypothesisSnapshot",
    "GenerativeResidentSnapshot",
    "GenerativeStateSnapshot",
    "GenerativeTransitionSnapshot",
    "ResidentGenerativeCognition",
]
