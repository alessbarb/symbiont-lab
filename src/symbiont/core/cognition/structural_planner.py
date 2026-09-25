from __future__ import annotations

import math
from dataclasses import dataclass, field

from ...cognition.graph import CognitiveGraph
from ...cognition.limits import KernelLimits
from ...cognition.structure import Mutation, apply_mutations


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
