from __future__ import annotations

from dataclasses import dataclass
from typing import Collection

from ...cognition.graph import CognitiveGraph
from ...cognition.types import NodeKind


@dataclass(slots=True, frozen=True)
class ConceptLineage:
    concept_id: str
    parent_ids: tuple[str, ...]
    born_tick: int


class SenseConceptLifecycle:
    """Own mutable sensory/concept developmental bookkeeping."""

    def __init__(self) -> None:
        self.concept_support: dict[tuple[str, str], int] = {}
        self.retrospective_support: dict[tuple[str, str], int] = {}
        self.lineage: dict[str, ConceptLineage] = {}
        self.sense_last_seen_tick: dict[str, int] = {}
        self.orphan_since_tick: dict[str, int] = {}
        self.unrouted_since_tick: dict[str, int] = {}
        self.concept_last_active_tick: dict[str, int] = {}
        self.next_concept_index = 1

    @property
    def concept_lineage(self) -> tuple[ConceptLineage, ...]:
        return tuple(self.lineage[key] for key in sorted(self.lineage))

    def consume_concept_support(self, parent_ids: Collection[str]) -> None:
        parents = sorted(set(parent_ids))
        for index, source_id in enumerate(parents):
            for target_id in parents[index + 1 :]:
                key = (source_id, target_id)
                self.concept_support.pop(key, None)
                self.retrospective_support.pop(key, None)

    def extract_max_concept_index(
        self,
        graph: CognitiveGraph,
    ) -> int:
        max_idx = 0
        all_ids = {node.node_id for node in graph.nodes} | set(self.lineage)
        for node_id in all_ids:
            if not node_id.startswith("concept_"):
                continue
            try:
                value = int(node_id.split("_", 1)[1], 16)
            except ValueError:
                continue
            max_idx = max(max_idx, value)
        return max_idx

    def new_node_id(
        self,
        prefix: str,
        *,
        graph: CognitiveGraph,
    ) -> str:
        existing = {node.node_id for node in graph.nodes} | set(self.lineage)
        if prefix == "concept":
            while True:
                candidate = f"concept_{self.next_concept_index:016x}"
                self.next_concept_index += 1
                if candidate not in existing:
                    return candidate
        index = 1
        while True:
            candidate = f"{prefix}_{index:016x}"
            if candidate not in existing:
                return candidate
            index += 1

    def update_unrouted(
        self,
        *,
        graph: CognitiveGraph,
        routed_ids: Collection[str],
        tick: int,
    ) -> set[str]:
        concept_ids = {
            node.node_id
            for node in graph.nodes
            if node.kind is NodeKind.CONCEPT
        }
        unrouted = concept_ids - set(routed_ids)
        for node_id in concept_ids:
            if node_id in unrouted:
                self.unrouted_since_tick.setdefault(node_id, tick)
            else:
                self.unrouted_since_tick.pop(node_id, None)
        return unrouted
