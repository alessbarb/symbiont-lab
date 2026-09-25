from __future__ import annotations

from typing import Collection

from ...cognition.graph import CognitiveGraph
from ...cognition.learning import ShadowPrediction
from ...cognition.limits import KernelLimits
from ...cognition.structure import Mutation
from .bridge_checkpoint import (
    restore_concept_lineage,
    restore_nonnegative_tick_map,
    restore_predictor_retirement,
    restore_predictor_utility,
    restore_shadow_predictions,
    restore_structural_candidates,
)
from .predictors import PredictorRetirement, PredictorUtility
from .sense_concept_lifecycle import ConceptLineage
from .structural_candidates import StructuralCandidate


class CognitiveBridgeCompatibility:
    """Private compatibility surface retained for repository tests/studies.

    New cognition code should use collaborator/public APIs instead. This mixin
    deliberately owns no state; every member delegates to CognitiveBridge's
    collaborators.
    """

    @property
    def _structural_candidates(self) -> dict[str, StructuralCandidate]:
        return self._contention.candidates

    @_structural_candidates.setter
    def _structural_candidates(
        self,
        value: dict[str, StructuralCandidate],
    ) -> None:
        self._contention.candidates = value

    @property
    def _predictor_utility(self) -> dict[str, PredictorUtility]:
        return self._predictors.utility

    @_predictor_utility.setter
    def _predictor_utility(
        self,
        value: dict[str, PredictorUtility],
    ) -> None:
        self._predictors.utility = value

    @property
    def _predictor_retirement(self) -> dict[str, PredictorRetirement]:
        return self._predictors.retirement

    @_predictor_retirement.setter
    def _predictor_retirement(
        self,
        value: dict[str, PredictorRetirement],
    ) -> None:
        self._predictors.retirement = value

    @property
    def _concept_support(self) -> dict[tuple[str, str], int]:
        return self._lifecycle.concept_support

    @_concept_support.setter
    def _concept_support(
        self,
        value: dict[tuple[str, str], int],
    ) -> None:
        self._lifecycle.concept_support = value

    @property
    def _retrospective_concept_support(self) -> dict[tuple[str, str], int]:
        return self._lifecycle.retrospective_support

    @_retrospective_concept_support.setter
    def _retrospective_concept_support(
        self,
        value: dict[tuple[str, str], int],
    ) -> None:
        self._lifecycle.retrospective_support = value

    @property
    def _concept_lineage(self) -> dict[str, ConceptLineage]:
        return self._lifecycle.lineage

    @_concept_lineage.setter
    def _concept_lineage(self, value: dict[str, ConceptLineage]) -> None:
        self._lifecycle.lineage = value

    @property
    def _sense_last_seen_tick(self) -> dict[str, int]:
        return self._lifecycle.sense_last_seen_tick

    @_sense_last_seen_tick.setter
    def _sense_last_seen_tick(self, value: dict[str, int]) -> None:
        self._lifecycle.sense_last_seen_tick = value

    @property
    def _orphan_since_tick(self) -> dict[str, int]:
        return self._lifecycle.orphan_since_tick

    @_orphan_since_tick.setter
    def _orphan_since_tick(self, value: dict[str, int]) -> None:
        self._lifecycle.orphan_since_tick = value

    @property
    def _unrouted_since_tick(self) -> dict[str, int]:
        return self._lifecycle.unrouted_since_tick

    @_unrouted_since_tick.setter
    def _unrouted_since_tick(self, value: dict[str, int]) -> None:
        self._lifecycle.unrouted_since_tick = value

    @property
    def _concept_last_active_tick(self) -> dict[str, int]:
        return self._lifecycle.concept_last_active_tick

    @_concept_last_active_tick.setter
    def _concept_last_active_tick(self, value: dict[str, int]) -> None:
        self._lifecycle.concept_last_active_tick = value

    @property
    def _next_concept_index(self) -> int:
        return self._lifecycle.next_concept_index

    @_next_concept_index.setter
    def _next_concept_index(self, value: int) -> None:
        self._lifecycle.next_concept_index = value

    @property
    def _node_born_tick(self) -> dict[str, int]:
        return self._representations.born_tick

    @_node_born_tick.setter
    def _node_born_tick(self, value: dict[str, int]) -> None:
        self._representations.born_tick = value

    @property
    def _node_observation_count(self) -> dict[str, int]:
        return self._representations.observation_count

    @_node_observation_count.setter
    def _node_observation_count(self, value: dict[str, int]) -> None:
        self._representations.observation_count = value

    @property
    def _node_active_count(self) -> dict[str, int]:
        return self._representations.active_count

    @_node_active_count.setter
    def _node_active_count(self, value: dict[str, int]) -> None:
        self._representations.active_count = value

    @property
    def _adaptive_node_budget(self) -> int:
        return self._budgets.node_budget

    @_adaptive_node_budget.setter
    def _adaptive_node_budget(self, value: int) -> None:
        self._budgets.node_budget = int(value)

    @property
    def _adaptive_edge_budget(self) -> int:
        return self._budgets.edge_budget

    @_adaptive_edge_budget.setter
    def _adaptive_edge_budget(self, value: int) -> None:
        self._budgets.edge_budget = int(value)

    @property
    def _adaptive_sense_budget(self) -> int:
        return self._budgets.sense_budget

    @_adaptive_sense_budget.setter
    def _adaptive_sense_budget(self, value: int) -> None:
        self._budgets.sense_budget = int(value)

    def _register_structural_candidate(
        self,
        *,
        candidate_id: str,
        family: str,
        mutations: tuple[Mutation, ...],
        eligible_tick: int,
        producer_id: str | None = None,
    ) -> bool:
        return self._contention.register(
            candidate_id=candidate_id,
            family=family,
            mutations=mutations,
            eligible_tick=eligible_tick,
            producer_id=producer_id,
        )

    def _drop_structural_candidate(self, candidate_id: str) -> None:
        self._contention.drop(candidate_id)

    def _select_structural_candidate(
        self,
        *,
        graph: CognitiveGraph,
        mutation_slots: int,
        node_slots: int,
        edge_slots: int,
    ) -> tuple[str | None, tuple[Mutation, ...], tuple[str, ...]]:
        return self._contention.select(
            graph=graph,
            mutation_slots=mutation_slots,
            node_slots=node_slots,
            edge_slots=edge_slots,
            frozen=self._safety_state.frozen,
        )

    def _commit_contention_result(
        self,
        *,
        winner_id: str | None,
        loser_ids: Collection[str],
    ) -> None:
        self._contention.commit(
            winner_id=winner_id,
            loser_ids=loser_ids,
        )

    def _valid_candidate(
        self,
        candidate: StructuralCandidate,
        *,
        graph: CognitiveGraph,
        active_motor_ids: Collection[str],
        active_primitive_ids: Collection[str],
    ) -> bool:
        return self._planner.valid_candidate(
            candidate,
            graph=graph,
            active_motor_ids=active_motor_ids,
            active_primitive_ids=active_primitive_ids,
            predictors=self._predictors,
            lifecycle=self._lifecycle,
            live_graph=self._graph,
            topology_revision=self._topology_revision,
        )

    def _prune_invalid_structural_proposals(
        self,
        *,
        graph: CognitiveGraph,
        active_motor_ids: Collection[str],
        active_primitive_ids: Collection[str],
    ) -> None:
        self._planner.prune_invalid_candidates(
            graph=graph,
            live_graph=self._graph,
            contention=self._contention,
            predictors=self._predictors,
            lifecycle=self._lifecycle,
            topology_revision=self._topology_revision,
            active_motor_ids=active_motor_ids,
            active_primitive_ids=active_primitive_ids,
        )

    def _retirement_edge_decay(self, edge, *, tick: int) -> None:
        self._plasticity.decay_retiring_edge(
            edge,
            tick=tick,
            retiring_predictors={
                predictor_id: retirement.entered_tick
                for predictor_id, retirement in self._predictors.retirement.items()
            },
            structural_wait=self._oldest_blocked_structural_wait(tick=tick),
            tentative_lifetime_ticks=(self._genome.structure.tentative_lifetime_ticks),
        )

    def _retirement_edge_gc_mutations(
        self,
        *,
        tick: int,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        return self._planner.retirement_edge_gc(
            graph=self._graph if graph is None else graph,
            pressure_graph=self._graph,
            predictors=self._predictors,
            contention=self._contention,
            tick=tick,
            max_mutations=max_mutations,
            lifetime_ticks=self._genome.structure.tentative_lifetime_ticks,
        )

    def _retirement_node_gc_mutations(
        self,
        *,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        return self._planner.retirement_node_gc(
            graph=self._graph if graph is None else graph,
            predictors=self._predictors,
            max_mutations=max_mutations,
        )

    def _stale_concept_reclamation_mutations(
        self,
        *,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
        protected_node_ids: Collection[str] = (),
    ) -> tuple[Mutation, ...]:
        return self._lifecycle.stale_concept_reclamation_mutations(
            graph=self._graph if graph is None else graph,
            tick=self._tick,
            max_mutations=max_mutations,
            protected_node_ids=protected_node_ids,
            grace_ticks=self._genome.structure.tentative_lifetime_ticks,
            develop_senses=self._develop_senses,
        )

    def _capacity_reclamation_mutations(
        self,
        *,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
        protected_node_ids: Collection[str] = (),
    ) -> tuple[Mutation, ...]:
        return self._stale_concept_reclamation_mutations(
            max_mutations=max_mutations,
            graph=graph,
            protected_node_ids=protected_node_ids,
        )

    def _invalidate_shadow_predictions_cache(self) -> None:
        self._predictors.invalidate_shadow_cache()

    @property
    def _live_shadow_limit(self) -> int:
        return self._predictors.live_shadow_limit(self._kernel_limits.max_nodes)

    @property
    def _preliminary_shadow_limit(self) -> int:
        return self._predictors.preliminary_shadow_limit(self._kernel_limits.max_nodes)

    def _prune_preliminary_shadow_support(self) -> None:
        node_kinds, _ = self._topology_cache()
        self._predictors.prune_preliminary(
            node_kinds=node_kinds,
            max_nodes=self._kernel_limits.max_nodes,
        )

    def _weight_class_overrides(
        self,
    ) -> dict[tuple[str, str, str], int]:
        return self._plasticity.weight_class_overrides(self._graph)

    @staticmethod
    def _restore_nonnegative_tick_map(
        payload: object,
        *,
        allowed_ids: Collection[str],
        field: str,
    ) -> dict[str, int]:
        return restore_nonnegative_tick_map(
            payload,
            allowed_ids=allowed_ids,
            field=field,
        )

    @staticmethod
    def _restore_shadow_predictions(
        payload: object,
        *,
        max_predictions: int = 16384,
    ) -> dict[tuple[str, str], ShadowPrediction]:
        return restore_shadow_predictions(
            payload,
            max_predictions=max_predictions,
        )

    @staticmethod
    def _restore_predictor_utility(
        payload: object,
        *,
        allowed_predictor_ids: Collection[str],
    ) -> dict[str, PredictorUtility]:
        return restore_predictor_utility(
            payload,
            allowed_predictor_ids=allowed_predictor_ids,
        )

    @staticmethod
    def _restore_predictor_retirement(
        payload: object,
        *,
        allowed_predictor_ids: Collection[str],
    ) -> dict[str, PredictorRetirement]:
        return restore_predictor_retirement(
            payload,
            allowed_predictor_ids=allowed_predictor_ids,
        )

    @staticmethod
    def _restore_structural_candidates(
        payload: object,
        *,
        kernel_limits: KernelLimits,
    ) -> dict[str, StructuralCandidate]:
        return restore_structural_candidates(
            payload,
            kernel_limits=kernel_limits,
        )

    @classmethod
    def _restore_concept_lineage(
        cls,
        payload: object,
        *,
        graph: CognitiveGraph,
        kernel_limits: KernelLimits,
    ) -> dict[str, ConceptLineage]:
        return restore_concept_lineage(
            payload,
            graph=graph,
            kernel_limits=kernel_limits,
        )
