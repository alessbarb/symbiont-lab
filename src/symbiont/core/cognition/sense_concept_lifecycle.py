from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Collection, Mapping

from ...cognition.graph import CognitiveGraph
from ...cognition.structure import Mutation
from ...cognition.types import EdgeKind, NodeKind

_ACTIVITY_THRESHOLD = 0.1
_TENTATIVE_WEIGHT = 0.05
_CORE_READOUT_ID = "readout_core"
_MOTOR_READOUT_PREFIX = "readout_motor:"
_PRIMITIVE_READOUT_PREFIX = "readout_primitive:"


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
        self._cached_concept_sig_rev = -1
        self._cached_concept_sig_lineage_len = -1
        self._cached_concept_sig_graph: CognitiveGraph | None = None
        self._cached_concept_signatures: list[set[str]] = []
        self._cached_concept_signature_pairs: set[tuple[str, str]] = set()

    @property
    def concept_lineage(self) -> tuple[ConceptLineage, ...]:
        return tuple(self.lineage[key] for key in sorted(self.lineage))

    def salient_concept_ids(
        self,
        activations: Mapping[str, float],
        *,
        node_kinds: Mapping[str, NodeKind],
        limit: int = 4,
    ) -> tuple[str, ...]:
        values = [
            (str(node_id), abs(float(value)))
            for node_id, value in activations.items()
            if (
                node_kinds.get(node_id) is NodeKind.CONCEPT
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                and abs(float(value)) > 1e-9
            )
        ]
        if not values:
            return ()

        absolute = sorted(
            node_id
            for node_id, magnitude in values
            if magnitude >= _ACTIVITY_THRESHOLD
        )
        if absolute:
            return tuple(absolute)

        magnitudes = sorted(magnitude for _node_id, magnitude in values)
        midpoint = len(magnitudes) // 2
        if len(magnitudes) % 2:
            median = magnitudes[midpoint]
        else:
            median = 0.5 * (
                magnitudes[midpoint - 1] + magnitudes[midpoint]
            )
        deviations = sorted(abs(value - median) for value in magnitudes)
        midpoint = len(deviations) // 2
        if len(deviations) % 2:
            mad = deviations[midpoint]
        else:
            mad = 0.5 * (
                deviations[midpoint - 1] + deviations[midpoint]
            )

        peak = magnitudes[-1]
        relative_threshold = max(
            1e-4,
            median + 1.5 * mad,
            peak * 0.35,
        )
        ranked = sorted(
            (
                (magnitude, node_id)
                for node_id, magnitude in values
                if magnitude >= relative_threshold
            ),
            key=lambda item: (-item[0], item[1]),
        )
        return tuple(
            sorted(
                node_id
                for _magnitude, node_id in ranked[: max(1, int(limit))]
            )
        )

    def concept_signature_exists(
        self,
        source_ids: tuple[str, str],
        *,
        graph: CognitiveGraph,
        live_graph: CognitiveGraph,
        topology_revision: int,
    ) -> bool:
        cacheable = graph is live_graph
        if cacheable:
            if (
                self._cached_concept_sig_rev != topology_revision
                or self._cached_concept_sig_graph is not live_graph
                or self._cached_concept_sig_lineage_len != len(self.lineage)
            ):
                signatures = [
                    set(lineage.parent_ids)
                    for lineage in self.lineage.values()
                ]
                concept_ids = {
                    node.node_id
                    for node in graph.nodes
                    if node.kind is NodeKind.CONCEPT
                }
                incoming: dict[str, set[str]] = {
                    concept_id: set() for concept_id in concept_ids
                }
                for edge in graph.edges:
                    if edge.target_id in incoming:
                        incoming[edge.target_id].add(edge.source_id)
                signatures.extend(incoming.values())
                signature_pairs: set[tuple[str, str]] = set()
                for sources in signatures:
                    ordered = sorted(sources)
                    for index, source_id in enumerate(ordered):
                        for target_id in ordered[index + 1 :]:
                            signature_pairs.add((source_id, target_id))
                self._cached_concept_signatures = signatures
                self._cached_concept_signature_pairs = signature_pairs
                self._cached_concept_sig_graph = live_graph
                self._cached_concept_sig_rev = topology_revision
                self._cached_concept_sig_lineage_len = len(self.lineage)
            signatures = self._cached_concept_signatures
        else:
            signatures = [
                set(lineage.parent_ids)
                for lineage in self.lineage.values()
            ]
            concept_ids = {
                node.node_id
                for node in graph.nodes
                if node.kind is NodeKind.CONCEPT
            }
            incoming = {
                concept_id: set()
                for concept_id in concept_ids
            }
            for edge in graph.edges:
                if edge.target_id in incoming:
                    incoming[edge.target_id].add(edge.source_id)
            signatures.extend(incoming.values())

        if len(source_ids) == 2:
            source_id, target_id = source_ids
            if cacheable:
                key = (
                    (source_id, target_id)
                    if source_id <= target_id
                    else (target_id, source_id)
                )
                return key in self._cached_concept_signature_pairs
            return any(
                source_id in sources and target_id in sources
                for sources in signatures
            )
        pair = set(source_ids)
        return any(pair.issubset(sources) for sources in signatures)

    def observe_retrospective_support(
        self,
        source_ids: Collection[str],
        *,
        support_epochs: int,
        node_kinds: Mapping[str, NodeKind],
        graph: CognitiveGraph,
        topology_revision: int,
        develop_senses: bool,
    ) -> int:
        if not develop_senses:
            return 0
        if (
            isinstance(support_epochs, bool)
            or not isinstance(support_epochs, int)
            or support_epochs <= 0
        ):
            return 0
        eligible = tuple(
            sorted(
                {
                    str(source_id)
                    for source_id in source_ids
                    if node_kinds.get(str(source_id)) is NodeKind.SENSE
                }
            )
        )
        if len(eligible) < 2:
            return 0

        gained = 0
        for index, source_id in enumerate(eligible):
            for target_id in eligible[index + 1 :]:
                key = (source_id, target_id)
                if self.concept_signature_exists(
                    key,
                    graph=graph,
                    live_graph=graph,
                    topology_revision=topology_revision,
                ):
                    self.concept_support.pop(key, None)
                    self.retrospective_support.pop(key, None)
                    continue
                previous = self.retrospective_support.get(key, 0)
                updated = max(previous, support_epochs)
                self.retrospective_support[key] = updated
                gained += max(0, updated - previous)
        return gained

    def record_concept_support(
        self,
        activations: Mapping[str, float],
        *,
        node_kinds: Mapping[str, NodeKind],
        graph: CognitiveGraph,
        topology_revision: int,
        tick: int,
        growth_threshold: float,
        develop_senses: bool,
    ) -> None:
        if not develop_senses:
            return
        for node_id in self.salient_concept_ids(
            activations,
            node_kinds=node_kinds,
        ):
            self.concept_last_active_tick[node_id] = tick

        threshold = max(_ACTIVITY_THRESHOLD, growth_threshold)
        active_senses = sorted(
            node_id
            for node_id, value in activations.items()
            if (
                node_kinds.get(node_id) is NodeKind.SENSE
                and abs(value) >= threshold
            )
        )
        for index, source_id in enumerate(active_senses):
            for target_id in active_senses[index + 1 :]:
                key = (source_id, target_id)
                if self.concept_signature_exists(
                    key,
                    graph=graph,
                    live_graph=graph,
                    topology_revision=topology_revision,
                ):
                    self.concept_support.pop(key, None)
                    self.retrospective_support.pop(key, None)
                    continue
                self.concept_support[key] = (
                    self.concept_support.get(key, 0) + 1
                )

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

    def propose_germinal_concept_candidate(
        self,
        *,
        graph: CognitiveGraph,
        live_graph: CognitiveGraph,
        topology_revision: int,
        pending_concepts: int,
        max_concepts: int,
        minimum_support: int,
        develop_senses: bool,
    ) -> tuple[str, tuple[Mutation, ...]] | None:
        if not develop_senses:
            return None
        concept_count = sum(
            1 for node in graph.nodes if node.kind is NodeKind.CONCEPT
        )
        if concept_count + pending_concepts >= max_concepts:
            return None

        support_pairs = set(self.concept_support) | set(
            self.retrospective_support
        )
        eligible = sorted(
            (
                (
                    max(
                        self.concept_support.get(pair, 0),
                        self.retrospective_support.get(pair, 0),
                    ),
                    pair,
                )
                for pair in support_pairs
                if (
                    max(
                        self.concept_support.get(pair, 0),
                        self.retrospective_support.get(pair, 0),
                    )
                    >= minimum_support
                    and not self.concept_signature_exists(
                        pair,
                        graph=graph,
                        live_graph=live_graph,
                        topology_revision=topology_revision,
                    )
                )
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not eligible:
            return None

        _, source_ids = eligible[0]
        if any(
            (node := graph.node_by_id(source_id)) is None
            or node.kind is not NodeKind.SENSE
            for source_id in source_ids
        ):
            return None

        signature = "|".join(source_ids)
        candidate_id = f"concept:{signature}"
        core_readouts = sorted(
            node.node_id
            for node in graph.nodes
            if (
                node.kind is NodeKind.READOUT
                and not node.node_id.startswith(_MOTOR_READOUT_PREFIX)
                and not node.node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
            )
        )
        if _CORE_READOUT_ID in core_readouts:
            core_readouts = [_CORE_READOUT_ID]

        concept_id = self.new_node_id("concept", graph=graph)
        mutations: list[Mutation] = [
            Mutation(
                kind="add_node",
                payload={
                    "node_id": concept_id,
                    "kind": NodeKind.CONCEPT,
                    "source_ids": source_ids,
                },
            )
        ]

        if core_readouts:
            readout_id = core_readouts[0]
        else:
            existing_ids = {node.node_id for node in graph.nodes}
            if _CORE_READOUT_ID in existing_ids:
                return None
            readout_id = _CORE_READOUT_ID
            mutations.append(
                Mutation(
                    kind="add_node",
                    payload={
                        "node_id": readout_id,
                        "kind": NodeKind.READOUT,
                    },
                )
            )

        mutations.append(
            Mutation(
                kind="add_edge",
                payload={
                    "source_id": concept_id,
                    "target_id": readout_id,
                    "kind": EdgeKind.EXCITATORY,
                    "weight": _TENTATIVE_WEIGHT,
                    "plasticity": 0.5,
                    "delay_ticks": 1,
                },
            )
        )
        return candidate_id, tuple(mutations)

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
