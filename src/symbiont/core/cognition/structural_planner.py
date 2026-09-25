from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Collection

from ...cognition.graph import CognitiveGraph, GraphError, PlasticNode
from ...cognition.limits import KernelLimits
from ...cognition.structure import (
    EdgeLifecycleState,
    Mutation,
    StructuralPlasticity,
    apply_mutations,
    evaluate_edge_lifecycle,
)
from ...cognition.types import NodeKind
from .predictors import PredictorLifecycle
from .sense_concept_lifecycle import SenseConceptLifecycle
from .structural_candidates import StructuralCandidate, StructuralContention

_MOTOR_READOUT_PREFIX = "readout_motor:"
_PRIMITIVE_READOUT_PREFIX = "readout_primitive:"


@dataclass(slots=True)
class AdaptiveStructuralBudgets:
    node_budget: int
    edge_budget: int
    sense_budget: int
    node_ceiling: int
    edge_ceiling: int
    sense_ceiling: int
    sensitivity: float

    @classmethod
    def from_graph(
        cls,
        graph: CognitiveGraph,
        *,
        kernel_limits: KernelLimits,
        soft_node_budget: int,
        soft_edge_budget: int,
        sense_node_budget: int,
        sensitivity: float,
    ) -> "AdaptiveStructuralBudgets":
        node_ceiling = min(kernel_limits.max_nodes, soft_node_budget)
        edge_ceiling = min(kernel_limits.max_edges, soft_edge_budget)
        sense_ceiling = min(node_ceiling, sense_node_budget)
        node_budget = max(
            len(graph.nodes),
            min(node_ceiling, max(4, math.ceil(node_ceiling * 0.25))),
        )
        edge_budget = max(
            len(graph.edges),
            min(edge_ceiling, max(8, math.ceil(edge_ceiling * 0.25))),
        )
        sense_count = sum(
            1 for node in graph.nodes if node.kind.value == "sense"
        )
        sense_budget = max(
            sense_count,
            min(
                node_budget,
                sense_ceiling,
                max(2, math.ceil(sense_ceiling * 0.25)),
            ),
        )
        return cls(
            node_budget=node_budget,
            edge_budget=edge_budget,
            sense_budget=sense_budget,
            node_ceiling=node_ceiling,
            edge_ceiling=edge_ceiling,
            sense_ceiling=sense_ceiling,
            sensitivity=max(0.0, min(1.0, float(sensitivity))),
        )

    @property
    def sense_limit(self) -> int:
        return min(self.sense_budget, self.node_budget)

    def restore(self, *, nodes: int, edges: int, senses: int) -> None:
        self.node_budget = int(nodes)
        self.edge_budget = int(edges)
        self.sense_budget = int(senses)

    def expand(
        self,
        *,
        need_nodes: bool = False,
        need_edges: bool = False,
        need_senses: bool = False,
    ) -> bool:
        if self.sensitivity <= 0.0:
            return False

        def grow(current: int, ceiling: int) -> int:
            if current >= ceiling:
                return current
            remaining = ceiling - current
            step = max(
                1,
                math.ceil(remaining * self.sensitivity * 0.25),
            )
            return min(ceiling, current + step)

        changed = False
        if need_nodes:
            updated = grow(self.node_budget, self.node_ceiling)
            changed = changed or updated != self.node_budget
            self.node_budget = updated
        if need_edges:
            updated = grow(self.edge_budget, self.edge_ceiling)
            changed = changed or updated != self.edge_budget
            self.edge_budget = updated
        if need_senses:
            effective_ceiling = min(self.sense_ceiling, self.node_budget)
            updated = grow(self.sense_budget, effective_ceiling)
            changed = changed or updated != self.sense_budget
            self.sense_budget = updated
        return changed


@dataclass(slots=True)
class StructuralPlan:
    """Sequential planning over an immutable live graph with atomic final commit.

    Staged mutations are validated against the graph produced by prior stages,
    but none become externally visible until commit_candidate reapplies the
    complete ordered batch to base_graph. This preserves CognitiveBridge's
    existing planning/commit semantics.
    """

    base_graph: CognitiveGraph
    graph: CognitiveGraph
    kernel_limits: KernelLimits
    frozen: bool
    mutation_cap: int
    mutations: list[Mutation] = field(default_factory=list)

    @classmethod
    def begin(
        cls,
        graph: CognitiveGraph,
        *,
        kernel_limits: KernelLimits,
        frozen: bool,
        mutation_cap: int,
    ) -> "StructuralPlan":
        return cls(
            base_graph=graph,
            graph=graph,
            kernel_limits=kernel_limits,
            frozen=frozen,
            mutation_cap=max(0, int(mutation_cap)),
        )

    @property
    def remaining(self) -> int:
        return max(0, self.mutation_cap - len(self.mutations))

    def stage(self, mutations: tuple[Mutation, ...]) -> bool:
        """Validate and expose a stage only to later planning phases."""
        if not mutations:
            return True
        if len(mutations) > self.remaining:
            return False
        candidate = apply_mutations(
            self.graph,
            mutations,
            self.kernel_limits,
            frozen=self.frozen,
        )
        if candidate is self.graph:
            return False
        self.graph = candidate
        self.mutations.extend(mutations)
        return True

    def append_unvalidated(self, mutations: tuple[Mutation, ...]) -> bool:
        """Append the terminal proposal without changing the planning graph.

        CognitiveBridge historically does not pre-apply the final generic
        growth proposal. If that proposal is invalid, the final atomic commit
        rejects the complete transaction, including earlier maintenance.
        """
        if not mutations:
            return True
        if len(mutations) > self.remaining:
            return False
        self.mutations.extend(mutations)
        return True

    def ordered_mutations(self) -> tuple[Mutation, ...]:
        return tuple(self.mutations)

    def commit_candidate(self) -> CognitiveGraph:
        return apply_mutations(
            self.base_graph,
            self.ordered_mutations(),
            self.kernel_limits,
            frozen=self.frozen,
        )



@dataclass(slots=True, frozen=True)
class StructuralPlanningResult:
    mutations: tuple[Mutation, ...]
    candidate_graph: CognitiveGraph
    winner_id: str | None
    loser_ids: tuple[str, ...]
    recycling_events: tuple[dict[str, object], ...]


class StructuralPlanner:
    """Plan one consolidation transaction without publishing graph state."""

    def __init__(
        self,
        *,
        kernel_limits: KernelLimits,
        structural_plasticity: StructuralPlasticity,
        budgets: AdaptiveStructuralBudgets,
    ) -> None:
        self._kernel_limits = kernel_limits
        self._structural_plasticity = structural_plasticity
        self.budgets = budgets

    @staticmethod
    def motor_readout_id(actuator_id: str) -> str:
        return f"{_MOTOR_READOUT_PREFIX}{actuator_id}"

    @staticmethod
    def primitive_readout_id(primitive_id: str) -> str:
        return f"{_PRIMITIVE_READOUT_PREFIX}{primitive_id}"

    def sync_motor_readouts(
        self,
        *,
        graph: CognitiveGraph,
        contention: StructuralContention,
        actuator_ids: Collection[str],
        tick: int,
    ) -> None:
        requested = sorted({
            str(value) for value in actuator_ids if str(value)
        })
        existing = {node.node_id for node in graph.nodes}
        requested_set = set(requested)
        for candidate_id, candidate in list(contention.candidates.items()):
            if (
                candidate.family == "motor_readout"
                and candidate_id.removeprefix("motor:") not in requested_set
            ):
                contention.drop(candidate_id)

        for actuator_id in requested:
            node_id = self.motor_readout_id(actuator_id)
            if node_id in existing:
                contention.drop(f"motor:{actuator_id}")
                continue
            contention.register(
                candidate_id=f"motor:{actuator_id}",
                family="motor_readout",
                mutations=(
                    Mutation(
                        kind="add_node",
                        payload={
                            "node_id": node_id,
                            "kind": NodeKind.READOUT,
                        },
                    ),
                ),
                eligible_tick=tick,
            )

    def sync_primitive_readouts(
        self,
        *,
        graph: CognitiveGraph,
        contention: StructuralContention,
        primitive_ids: Collection[str],
        tick: int,
        frozen: bool,
    ) -> tuple[CognitiveGraph, tuple[Mutation, ...]]:
        requested = sorted({
            str(value) for value in primitive_ids if str(value)
        })
        requested_set = set(requested)
        requested_nodes = {
            self.primitive_readout_id(primitive_id)
            for primitive_id in requested
        }
        existing_nodes = {node.node_id for node in graph.nodes}
        existing_primitive_nodes = {
            node_id
            for node_id in existing_nodes
            if node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
        }

        for candidate_id, candidate in list(contention.candidates.items()):
            if (
                candidate.family == "primitive_readout"
                and candidate_id.removeprefix("primitive:")
                not in requested_set
            ):
                contention.drop(candidate_id)

        mutation_cap = (
            self._kernel_limits.max_structural_mutations_per_consolidation
        )
        mutations: list[Mutation] = []
        planning_graph = graph
        for node_id in sorted(existing_primitive_nodes - requested_nodes):
            incident = [
                edge
                for edge in planning_graph.edges
                if edge.source_id == node_id or edge.target_id == node_id
            ]
            stale_mutations = tuple(
                Mutation(
                    kind="remove_edge",
                    payload={
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "kind": edge.kind.value,
                    },
                )
                for edge in incident
            ) + (
                Mutation(
                    kind="remove_node",
                    payload={"node_id": node_id},
                ),
            )
            if len(mutations) + len(stale_mutations) > mutation_cap:
                break
            candidate_graph = apply_mutations(
                planning_graph,
                stale_mutations,
                self._kernel_limits,
                frozen=frozen,
            )
            if candidate_graph is planning_graph:
                continue
            mutations.extend(stale_mutations)
            planning_graph = candidate_graph

        live_graph = graph
        mutation_tuple = tuple(mutations)
        if mutation_tuple:
            candidate_graph = apply_mutations(
                graph,
                mutation_tuple,
                self._kernel_limits,
                frozen=frozen,
            )
            if candidate_graph is not graph:
                live_graph = candidate_graph
            else:
                mutation_tuple = ()

        existing_nodes = {node.node_id for node in live_graph.nodes}
        for primitive_id in requested:
            node_id = self.primitive_readout_id(primitive_id)
            candidate_id = f"primitive:{primitive_id}"
            if node_id in existing_nodes:
                contention.drop(candidate_id)
                continue
            contention.register(
                candidate_id=candidate_id,
                family="primitive_readout",
                mutations=(
                    Mutation(
                        kind="add_node",
                        payload={
                            "node_id": node_id,
                            "kind": NodeKind.READOUT,
                        },
                    ),
                ),
                eligible_tick=tick,
            )
        return live_graph, mutation_tuple

    def admit_senses(
        self,
        *,
        graph: CognitiveGraph,
        sense_values: Collection[str],
        lifecycle: SenseConceptLifecycle,
        tick: int,
        develop_senses: bool,
    ) -> tuple[CognitiveGraph, int]:
        if not develop_senses:
            return graph, 0

        existing_ids = {node.node_id for node in graph.nodes}
        existing_senses = {
            node.node_id
            for node in graph.nodes
            if node.kind is NodeKind.SENSE
        }
        observed_ids = set(sense_values)
        for sense_id in observed_ids & existing_senses:
            lifecycle.sense_last_seen_tick[sense_id] = tick

        candidates = sorted(observed_ids - existing_ids)
        if not candidates:
            return graph, 0

        admitted = 0
        sense_count = len(existing_senses)
        if (
            len(graph.nodes) >= self.budgets.node_budget
            or sense_count >= self.budgets.sense_limit
        ):
            self.budgets.expand(
                need_nodes=len(graph.nodes) >= self.budgets.node_budget,
                need_senses=sense_count >= self.budgets.sense_limit,
            )

        candidate_graph = graph
        for sense_id in candidates:
            if (
                len(candidate_graph.nodes) >= self.budgets.node_budget
                or sense_count >= self.budgets.sense_limit
            ):
                break
            try:
                candidate_graph = CognitiveGraph(
                    nodes=(
                        *candidate_graph.nodes,
                        PlasticNode(
                            node_id=sense_id,
                            kind=NodeKind.SENSE,
                        ),
                    ),
                    edges=candidate_graph.edges,
                    kernel_limits=self._kernel_limits,
                )
            except GraphError:
                continue
            admitted += 1
            sense_count += 1
            lifecycle.sense_last_seen_tick[sense_id] = tick

        return candidate_graph, admitted

    def oldest_blocked_wait(
        self,
        *,
        graph: CognitiveGraph,
        contention: StructuralContention,
        tick: int,
    ) -> int:
        if len(graph.nodes) < self.budgets.node_budget:
            return 0
        blocked = [
            candidate
            for candidate in contention.candidates.values()
            if candidate.required_nodes > 0
        ]
        if not blocked:
            return 0
        oldest = min(candidate.eligible_tick for candidate in blocked)
        return max(0, int(tick) - int(oldest))

    def retirement_edge_gc(
        self,
        *,
        graph: CognitiveGraph,
        pressure_graph: CognitiveGraph,
        predictors: PredictorLifecycle,
        contention: StructuralContention,
        tick: int,
        max_mutations: int,
        lifetime_ticks: int,
    ) -> tuple[Mutation, ...]:
        if max_mutations <= 0:
            return ()
        lifetime = max(1, int(lifetime_ticks))
        if (
            self.oldest_blocked_wait(
                graph=pressure_graph,
                contention=contention,
                tick=tick,
            )
            < 2 * lifetime
        ):
            return ()
        for predictor_id in sorted(predictors.retirement):
            retirement = predictors.retirement[predictor_id]
            if tick - retirement.entered_tick < lifetime:
                continue
            incident = sorted(
                (
                    edge
                    for edge in graph.edges
                    if edge.source_id == predictor_id
                    or edge.target_id == predictor_id
                ),
                key=lambda edge: (
                    edge.source_id,
                    edge.target_id,
                    edge.kind.value,
                ),
            )
            if not incident:
                continue
            edge = incident[0]
            return (
                Mutation(
                    kind="remove_edge",
                    payload={
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "kind": edge.kind.value,
                    },
                ),
            )
        return ()

    @staticmethod
    def retirement_node_gc(
        *,
        graph: CognitiveGraph,
        predictors: PredictorLifecycle,
        max_mutations: int,
    ) -> tuple[Mutation, ...]:
        if max_mutations <= 0:
            return ()
        incident_ids = {
            node_id
            for edge in graph.edges
            for node_id in (edge.source_id, edge.target_id)
        }
        candidates = sorted(
            predictor_id
            for predictor_id in predictors.retirement
            if predictor_id not in incident_ids
            and any(
                node.node_id == predictor_id
                and node.kind is NodeKind.PREDICTOR
                for node in graph.nodes
            )
        )
        if not candidates:
            return ()
        return (
            Mutation(
                kind="remove_node",
                payload={"node_id": candidates[0]},
            ),
        )

    @staticmethod
    def valid_candidate(
        candidate: StructuralCandidate,
        *,
        graph: CognitiveGraph,
        active_motor_ids: Collection[str],
        active_primitive_ids: Collection[str],
        predictors: PredictorLifecycle,
        lifecycle: SenseConceptLifecycle,
        live_graph: CognitiveGraph,
        topology_revision: int,
    ) -> bool:
        existing_ids = {node.node_id for node in graph.nodes}
        if any(
            mutation.kind == "add_node"
            and str(mutation.payload.get("node_id", "")) in existing_ids
            for mutation in candidate.mutations
        ):
            return False
        if candidate.family == "motor_readout":
            return candidate.candidate_id.removeprefix("motor:") in set(
                active_motor_ids
            )
        if candidate.family == "primitive_readout":
            return candidate.candidate_id.removeprefix("primitive:") in set(
                active_primitive_ids
            )
        if candidate.family == "predictor":
            add_edge = next(
                (
                    mutation
                    for mutation in candidate.mutations
                    if mutation.kind == "add_edge"
                ),
                None,
            )
            add_node = next(
                (
                    mutation
                    for mutation in candidate.mutations
                    if mutation.kind == "add_node"
                ),
                None,
            )
            if add_edge is None or add_node is None:
                return False
            source_id = str(add_edge.payload.get("source_id", ""))
            target_id = str(add_node.payload.get("predicts_node_id", ""))
            shadow = predictors.shadows.get((source_id, target_id))
            return bool(shadow is not None and shadow.promotable)
        if candidate.family == "concept":
            add_nodes = [
                mutation
                for mutation in candidate.mutations
                if mutation.kind == "add_node"
            ]
            if not add_nodes:
                return False
            raw_sources = add_nodes[0].payload.get("source_ids", ())
            if not isinstance(raw_sources, (list, tuple, set)):
                return False
            source_ids = tuple(sorted(str(value) for value in raw_sources))
            return (
                len(source_ids) >= 2
                and not lifecycle.concept_signature_exists(
                    source_ids[:2],
                    graph=graph,
                    live_graph=live_graph,
                    topology_revision=topology_revision,
                )
            )
        return True

    def prune_invalid_candidates(
        self,
        *,
        graph: CognitiveGraph,
        live_graph: CognitiveGraph,
        contention: StructuralContention,
        predictors: PredictorLifecycle,
        lifecycle: SenseConceptLifecycle,
        topology_revision: int,
        active_motor_ids: Collection[str],
        active_primitive_ids: Collection[str],
    ) -> None:
        for candidate_id, candidate in list(contention.candidates.items()):
            if not self.valid_candidate(
                candidate,
                graph=graph,
                active_motor_ids=active_motor_ids,
                active_primitive_ids=active_primitive_ids,
                predictors=predictors,
                lifecycle=lifecycle,
                live_graph=live_graph,
                topology_revision=topology_revision,
            ):
                contention.candidates.pop(candidate_id, None)

    def plan_consolidation(
        self,
        *,
        graph: CognitiveGraph,
        tick: int,
        frozen: bool,
        predictors: PredictorLifecycle,
        lifecycle: SenseConceptLifecycle,
        contention: StructuralContention,
        develop_senses: bool,
        topology_revision: int,
        active_motor_ids: Collection[str],
        active_primitive_ids: Collection[str],
        pruning_threshold: float,
        minimum_support: int,
        lifetime_ticks: int,
        sense_retention_ticks: int,
        max_concepts: int,
    ) -> StructuralPlanningResult:
        plan = StructuralPlan.begin(
            graph,
            kernel_limits=self._kernel_limits,
            frozen=frozen,
            mutation_cap=(
                self._kernel_limits.max_structural_mutations_per_consolidation
            ),
        )

        retirement_gc = self.retirement_node_gc(
            graph=plan.graph,
            predictors=predictors,
            max_mutations=min(1, plan.remaining),
        )
        if retirement_gc:
            plan.stage(retirement_gc)

        retirement_edge_gc = self.retirement_edge_gc(
            graph=plan.graph,
            pressure_graph=graph,
            predictors=predictors,
            contention=contention,
            tick=tick,
            max_mutations=min(1, plan.remaining),
            lifetime_ticks=lifetime_ticks,
        )
        if retirement_edge_gc:
            plan.stage(retirement_edge_gc)

        prune_candidates = tuple(
            Mutation(
                kind="remove_edge",
                payload={
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "kind": edge.kind,
                },
            )
            for edge in plan.graph.edges
            if evaluate_edge_lifecycle(
                edge,
                current_tick=tick,
                prune_threshold=pruning_threshold,
                minimum_support=minimum_support,
                quarantine_window_ticks=lifetime_ticks,
                tentative_lifetime_ticks=lifetime_ticks,
            )
            is EdgeLifecycleState.REMOVED
        )
        prune_mutations = prune_candidates[: plan.remaining]
        if prune_mutations:
            plan.stage(prune_mutations)

        protected_action_readouts = {
            *(
                f"{_MOTOR_READOUT_PREFIX}{str(actuator_id)}"
                for actuator_id in active_motor_ids
                if str(actuator_id)
            ),
            *(
                f"{_PRIMITIVE_READOUT_PREFIX}{str(primitive_id)}"
                for primitive_id in active_primitive_ids
                if str(primitive_id)
            ),
        }
        orphan_mutations = lifecycle.orphan_node_mutations(
            graph=plan.graph,
            tick=tick,
            max_mutations=plan.remaining,
            protected_node_ids=protected_action_readouts,
            grace_ticks=lifetime_ticks,
            develop_senses=develop_senses,
        )
        if orphan_mutations:
            plan.stage(orphan_mutations)

        sense_evictions = lifecycle.sense_eviction_mutations(
            graph=plan.graph,
            tick=tick,
            max_mutations=plan.remaining,
            sense_node_limit=self.budgets.sense_limit,
            retention_ticks=sense_retention_ticks,
            develop_senses=develop_senses,
        )
        if sense_evictions:
            plan.stage(sense_evictions)

        pending_concepts = sum(
            1
            for candidate in contention.candidates.values()
            if candidate.family == "concept"
        )
        concept_proposal = lifecycle.propose_germinal_concept_candidate(
            graph=graph,
            live_graph=graph,
            topology_revision=topology_revision,
            pending_concepts=pending_concepts,
            existing_candidate_ids=contention.candidates,
            max_concepts=max_concepts,
            minimum_support=minimum_support,
            develop_senses=develop_senses,
        )
        if concept_proposal is not None:
            candidate_id, mutations = concept_proposal
            contention.register(
                candidate_id=candidate_id,
                family="concept",
                eligible_tick=tick,
                mutations=mutations,
            )

        self.prune_invalid_candidates(
            graph=plan.graph,
            live_graph=graph,
            contention=contention,
            predictors=predictors,
            lifecycle=lifecycle,
            topology_revision=topology_revision,
            active_motor_ids=active_motor_ids,
            active_primitive_ids=active_primitive_ids,
        )

        frozen_candidate_ids = tuple(sorted(contention.candidates))
        contention.consolidation_generation += 1

        routed = lifecycle.nodes_with_path_to_core_readout(graph=plan.graph)
        lifecycle.update_unrouted(
            graph=plan.graph,
            routed_ids=routed,
            tick=tick,
        )
        repair_mutations, event = lifecycle.propose_recycling(
            graph=plan.graph,
            tick=tick,
            mutation_slots=plan.remaining,
            develop_senses=develop_senses,
            kernel_limits=self._kernel_limits,
        )
        recycling_events: tuple[dict[str, object], ...] = ()
        if repair_mutations and plan.stage(repair_mutations):
            recycling_events = (event,) if event is not None else ()

        pending_node_demand = any(
            candidate.required_nodes > 0
            for candidate in contention.candidates.values()
        )
        pending_edge_demand = any(
            candidate.required_edges > 0
            for candidate in contention.candidates.values()
        ) or bool(predictors.shadows)
        self.budgets.expand(
            need_nodes=(
                pending_node_demand
                and len(plan.graph.nodes) >= self.budgets.node_budget
            ),
            need_edges=(
                pending_edge_demand
                and len(plan.graph.edges) >= self.budgets.edge_budget
            ),
        )
        edge_slots = max(
            0,
            self.budgets.edge_budget - len(plan.graph.edges),
        )
        node_slots = max(
            0,
            self.budgets.node_budget - len(plan.graph.nodes),
        )

        original_registry = contention.candidates
        contention.candidates = {
            candidate_id: original_registry[candidate_id]
            for candidate_id in frozen_candidate_ids
            if candidate_id in original_registry
        }
        winner_id, admission_mutations, loser_ids = contention.select(
            graph=plan.graph,
            mutation_slots=plan.remaining,
            node_slots=node_slots,
            edge_slots=edge_slots,
            frozen=frozen,
        )
        frozen_registry_after = contention.candidates
        contention.candidates = {
            **{
                candidate_id: candidate
                for candidate_id, candidate in original_registry.items()
                if candidate_id not in frozen_candidate_ids
            },
            **frozen_registry_after,
        }

        if admission_mutations and not plan.stage(admission_mutations):
            plan.append_unvalidated(admission_mutations)

        edge_slots = max(
            0,
            self.budgets.edge_budget - len(plan.graph.edges),
        )
        proposed = self._structural_plasticity.propose(
            plan.graph,
            kernel_limits=self._kernel_limits,
            tick=tick,
            max_mutations=min(plan.remaining, edge_slots),
        )
        proposed = tuple(
            mutation
            for mutation in proposed
            if not (
                mutation.kind == "add_edge"
                and (
                    str(mutation.payload.get("source_id", ""))
                    in predictors.retirement
                    or str(mutation.payload.get("target_id", ""))
                    in predictors.retirement
                )
            )
        )
        plan.append_unvalidated(proposed)

        mutations = plan.ordered_mutations()
        candidate_graph = (
            plan.commit_candidate()
            if mutations
            else graph
        )
        return StructuralPlanningResult(
            mutations=mutations,
            candidate_graph=candidate_graph,
            winner_id=winner_id,
            loser_ids=loser_ids,
            recycling_events=recycling_events,
        )
