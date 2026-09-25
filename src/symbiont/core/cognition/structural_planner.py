from __future__ import annotations

from dataclasses import dataclass, field

from ...cognition.graph import CognitiveGraph
from ...cognition.limits import KernelLimits
from ...cognition.structure import Mutation, apply_mutations


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
