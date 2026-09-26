"""Resident orchestration for Generative Cognition v1.

This module composes the bounded generative substrate inside the organism
without acquiring factual-evidence or motor authority.  It deliberately owns
only temporary generative state, endogenous agenda state, model routing and
scheduler state.
"""

from __future__ import annotations

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
from .budget import GenerativeBudget
from .episode import new_episode
from .execution import GenerativeExecutionCoordinator, GenerativeExecutionResult
from .epistemic_value import EpistemicValue, EpistemicValueEstimator
from .model import GenerativeContext, GenerativeModel
from .registry import GenerativeModelRegistry
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
class GenerativeResidentSnapshot:
    """Bounded passive view of the most recent resident generative pass."""

    mode: GenerativeMode
    target_id: str | None
    episode_id: str | None
    state_count: int
    transition_count: int
    max_depth: int
    model_queries: int
    termination: GenerativeTermination | None
    agenda_candidate_count: int
    agenda_contamination_count: int


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
            context = GenerativeContext(
                tokens=candidate.target.source_refs,
                references=candidate.target.source_refs,
            )
            depth = {
                GenerativeMode.ONLINE: 1,
                GenerativeMode.IDLE: min(2, workspace.budget.max_depth),
                GenerativeMode.OFFLINE: min(4, workspace.budget.max_depth),
            }[selected_mode]
            result = RolloutEngine(registry=self.registry, workspace=workspace).rollout(
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
            return AgendaProgress(
                new_branch=False,
                uncertainty_changed=any(
                    transition.uncertainty_after != transition.uncertainty_before
                    for transition in result.transitions
                ),
                disagreement_changed=False,
                hypothesis_changed=False,
                discriminating_consequence=bool(result.transitions),
                reconciliation=False,
            )

        self.last_execution = self.execution.run(
            mode=mode,
            tick=tick,
            workspace=workspace,
            run_target=run_target,
        )

        target_id = self.last_execution.target_id
        if target_id is None:
            episode.termination_reason = GenerativeTermination.COMPLETED
        elif self.last_rollout is not None:
            episode.termination_reason = self.last_rollout.termination

        return self.snapshot(mode=mode)

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
            max_depth=(episode.max_depth_reached if episode is not None else 0),
            model_queries=(workspace.model_queries if workspace is not None else 0),
            termination=(episode.termination_reason if episode is not None else None),
            agenda_candidate_count=eligible,
            agenda_contamination_count=self.agenda.agenda_contamination_count,
        )

    def _ingest_prediction_errors(self, cognition: object | None, *, tick: int) -> None:
        errors = tuple(getattr(cognition, "prediction_errors", ()) or ())
        known = {target.target_id for target in self.agenda.targets}
        for error in errors:
            predictor_id = str(getattr(error, "predictor_id", ""))
            target_id = str(getattr(error, "target_id", ""))
            if not predictor_id or not target_id:
                continue
            identifier = f"gc.prediction.{predictor_id}.{target_id}"
            if identifier in known:
                continue
            loss = getattr(error, "loss", 0.0)
            try:
                uncertainty = max(0.0, min(1.0, float(loss)))
            except (TypeError, ValueError):
                uncertainty = 0.0
            self.agenda.add_target(
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
            known.add(identifier)

    def _ingest_prospective_candidates(
        self,
        candidate_ids: tuple[str, ...],
        *,
        tick: int,
    ) -> None:
        known = {target.target_id for target in self.agenda.targets}
        for candidate_id in candidate_ids:
            if not isinstance(candidate_id, str) or not candidate_id:
                continue
            identifier = f"gc.prospective.{candidate_id}"
            if identifier in known:
                continue
            self.agenda.add_target(
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
            known.add(identifier)

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


__all__ = ["GenerativeResidentSnapshot", "ResidentGenerativeCognition"]
