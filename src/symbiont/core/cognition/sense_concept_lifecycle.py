from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Collection, Mapping

from ...cognition.graph import CognitiveGraph
from ...cognition.limits import KernelLimits
from ...cognition.structure import Mutation, apply_mutations
from ...cognition.types import EdgeKind, NodeKind

_ACTIVITY_THRESHOLD = 0.1
_TENTATIVE_WEIGHT = 0.05
_CORE_READOUT_ID = "readout_core"
_MOTOR_READOUT_PREFIX = "readout_motor:"
_PRIMITIVE_READOUT_PREFIX = "readout_primitive:"


class RepresentationMaturity(StrEnum):
    NASCENT = "nascent"
    PROVISIONAL = "provisional"
    MATURE = "mature"
    STABLE = "stable"
    WEAKENING = "weakening"
    RETIRING = "retiring"


class RepresentationTracker:
    """Own generic developmental evidence for graph representations."""

    def __init__(self, graph: CognitiveGraph) -> None:
        self.born_tick: dict[str, int] = {
            node.node_id: 0 for node in graph.nodes
        }
        self.observation_count: dict[str, int] = {
            node.node_id: 0 for node in graph.nodes
        }
        self.active_count: dict[str, int] = {
            node.node_id: 0 for node in graph.nodes
        }

    def observe(
        self,
        activations: Mapping[str, float],
        *,
        threshold: float = _ACTIVITY_THRESHOLD,
    ) -> None:
        for node_id, value in activations.items():
            self.observation_count[node_id] = (
                self.observation_count.get(node_id, 0) + 1
            )
            if abs(value) >= threshold:
                self.active_count[node_id] = (
                    self.active_count.get(node_id, 0) + 1
                )

    def note_birth(self, node_id: str, *, tick: int) -> None:
        if not node_id:
            return
        self.born_tick.setdefault(node_id, max(0, int(tick)))
        self.observation_count.setdefault(node_id, 0)
        self.active_count.setdefault(node_id, 0)

    def remove(self, node_id: str) -> None:
        self.born_tick.pop(node_id, None)
        self.observation_count.pop(node_id, None)
        self.active_count.pop(node_id, None)

    def reconcile(self, graph: CognitiveGraph) -> None:
        node_ids = {node.node_id for node in graph.nodes}
        self.born_tick = {
            key: value
            for key, value in self.born_tick.items()
            if key in node_ids
        }
        self.observation_count = {
            key: value
            for key, value in self.observation_count.items()
            if key in node_ids
        }
        self.active_count = {
            key: value
            for key, value in self.active_count.items()
            if key in node_ids
        }
        for node_id in node_ids:
            self.born_tick.setdefault(node_id, 0)
            self.observation_count.setdefault(node_id, 0)
            self.active_count.setdefault(node_id, 0)

    def maturity(
        self,
        node_id: str,
        *,
        graph: CognitiveGraph,
        tick: int,
        orphan_since_tick: Mapping[str, int],
        retiring_predictor_ids: Collection[str],
        predictor_utility: Mapping[str, object],
        tentative_lifetime_ticks: int,
        minimum_support: int,
    ) -> RepresentationMaturity:
        node = graph.node_by_id(node_id)
        if node is None:
            return RepresentationMaturity.NASCENT
        if node.kind is NodeKind.SENSE:
            return RepresentationMaturity.STABLE
        if (
            node.kind is NodeKind.PREDICTOR
            and node_id in retiring_predictor_ids
        ):
            return RepresentationMaturity.RETIRING

        orphan_since = orphan_since_tick.get(node_id)
        if orphan_since is not None:
            orphan_age = max(0, tick - orphan_since)
            grace = max(1, tentative_lifetime_ticks)
            if orphan_age >= max(1, grace // 2):
                return RepresentationMaturity.RETIRING
            return RepresentationMaturity.WEAKENING

        born_tick = self.born_tick.get(node_id, 0)
        age = max(0, tick - born_tick)
        grace = max(1, tentative_lifetime_ticks)
        observations = self.observation_count.get(node_id, 0)
        active = self.active_count.get(node_id, 0)
        required_support = max(2, minimum_support)

        if age < grace or observations < required_support:
            return RepresentationMaturity.NASCENT

        incident = graph.incident_edges(node_id)
        integrated = any(
            edge.support >= required_support for edge in incident
        )
        if active < required_support or not integrated:
            return RepresentationMaturity.PROVISIONAL

        if node.kind is NodeKind.PREDICTOR:
            utility = predictor_utility.get(node_id)
            if not (
                utility is not None
                and getattr(utility, "samples", 0)
                >= max(8, required_support)
                and getattr(utility, "predictive_gain", 0.0) > 0.0
                and getattr(utility, "recent_gain", 0.0) > 0.0
            ):
                return RepresentationMaturity.PROVISIONAL

        if age >= 2 * grace and active >= 2 * required_support:
            return RepresentationMaturity.STABLE
        return RepresentationMaturity.MATURE


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
        existing_candidate_ids: Collection[str],
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
        if candidate_id in set(existing_candidate_ids):
            return None
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

    @staticmethod
    def orphan_latent_ids(
        *,
        graph: CognitiveGraph,
    ) -> set[str]:
        incident = {node.node_id: 0 for node in graph.nodes}
        for edge in graph.edges:
            incident[edge.source_id] = incident.get(edge.source_id, 0) + 1
            incident[edge.target_id] = incident.get(edge.target_id, 0) + 1
        return {
            node.node_id
            for node in graph.nodes
            if (
                node.kind
                in (
                    NodeKind.CONCEPT,
                    NodeKind.STATE,
                    NodeKind.GATE,
                    NodeKind.READOUT,
                )
                and incident.get(node.node_id, 0) == 0
            )
        }

    def orphan_node_mutations(
        self,
        *,
        graph: CognitiveGraph,
        tick: int,
        max_mutations: int,
        protected_node_ids: Collection[str],
        grace_ticks: int,
        develop_senses: bool,
    ) -> tuple[Mutation, ...]:
        if not develop_senses or max_mutations <= 0:
            return ()
        protected = {
            str(node_id)
            for node_id in protected_node_ids
            if str(node_id)
        }
        orphan_ids = self.orphan_latent_ids(graph=graph) - protected
        for node in graph.nodes:
            if (
                node.kind
                in (
                    NodeKind.CONCEPT,
                    NodeKind.STATE,
                    NodeKind.GATE,
                    NodeKind.READOUT,
                )
                and node.node_id not in orphan_ids
            ):
                self.orphan_since_tick.pop(node.node_id, None)

        grace = max(1, int(grace_ticks))
        mutations: list[Mutation] = []
        for node_id in sorted(orphan_ids):
            since = self.orphan_since_tick.setdefault(node_id, tick)
            if tick - since < grace:
                continue
            mutations.append(
                Mutation(kind="remove_node", payload={"node_id": node_id})
            )
            if len(mutations) >= max_mutations:
                break
        return tuple(mutations)

    def sense_eviction_mutations(
        self,
        *,
        graph: CognitiveGraph,
        tick: int,
        max_mutations: int,
        sense_node_limit: int,
        retention_ticks: int,
        develop_senses: bool,
    ) -> tuple[Mutation, ...]:
        if not develop_senses or max_mutations <= 0:
            return ()
        senses = [
            node for node in graph.nodes if node.kind is NodeKind.SENSE
        ]
        if not senses:
            return ()
        incident_ids = {
            node_id
            for edge in graph.edges
            for node_id in (edge.source_id, edge.target_id)
        }
        over_budget = max(0, len(senses) - sense_node_limit)
        retention = max(1, int(retention_ticks))
        candidates: list[tuple[bool, int, str]] = []
        for node in senses:
            if node.node_id in incident_ids:
                continue
            last_seen = self.sense_last_seen_tick.get(node.node_id, 0)
            stale = tick - last_seen >= retention
            candidates.append((stale, last_seen, node.node_id))

        candidates.sort(key=lambda item: (not item[0], item[1], item[2]))
        mutations: list[Mutation] = []
        needed_over_budget = over_budget
        for stale, _, node_id in candidates:
            if not stale and needed_over_budget <= 0:
                continue
            mutations.append(
                Mutation(kind="remove_node", payload={"node_id": node_id})
            )
            if needed_over_budget > 0:
                needed_over_budget -= 1
            if len(mutations) >= max_mutations:
                break
        return tuple(mutations)

    @staticmethod
    def has_sense_to_readout_path(
        *,
        graph: CognitiveGraph,
        minimum_support: int,
        established_only: bool = False,
    ) -> bool:
        senses = {
            node.node_id
            for node in graph.nodes
            if node.kind is NodeKind.SENSE
        }
        readouts = {
            node.node_id
            for node in graph.nodes
            if (
                node.kind is NodeKind.READOUT
                and not node.node_id.startswith(_MOTOR_READOUT_PREFIX)
                and not node.node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
            )
        }
        if _CORE_READOUT_ID in readouts:
            readouts = {_CORE_READOUT_ID}
        if not senses or not readouts:
            return False

        adjacency: dict[str, set[str]] = {}
        for edge in graph.edges:
            if established_only and edge.support < minimum_support:
                continue
            adjacency.setdefault(edge.source_id, set()).add(edge.target_id)
        frontier = list(senses)
        visited = set(senses)
        while frontier:
            source_id = frontier.pop()
            for target_id in adjacency.get(source_id, ()):
                if target_id in readouts:
                    return True
                if target_id not in visited:
                    visited.add(target_id)
                    frontier.append(target_id)
        return False

    def stale_concept_reclamation_mutations(
        self,
        *,
        graph: CognitiveGraph,
        tick: int,
        max_mutations: int,
        protected_node_ids: Collection[str],
        grace_ticks: int,
        develop_senses: bool,
    ) -> tuple[Mutation, ...]:
        if max_mutations <= 0 or not develop_senses:
            return ()
        protected = set(protected_node_ids)
        routed = self.nodes_with_path_to_core_readout(graph=graph)
        unrouted = self.update_unrouted(
            graph=graph,
            routed_ids=routed,
            tick=tick,
        )
        grace = max(1, int(grace_ticks))

        candidates: list[tuple[int, int, str, tuple[Mutation, ...]]] = []
        for node_id in sorted(unrouted):
            if node_id in protected:
                continue
            lineage = self.lineage.get(node_id)
            born_tick = lineage.born_tick if lineage is not None else 0
            if tick - born_tick < grace:
                continue
            unrouted_since = self.unrouted_since_tick.get(node_id, tick)
            if tick - unrouted_since < grace:
                continue
            last_active = self.concept_last_active_tick.get(
                node_id,
                born_tick,
            )
            if tick - last_active < grace:
                continue

            incident = [
                edge
                for edge in graph.edges
                if edge.source_id == node_id or edge.target_id == node_id
            ]
            mutations = tuple(
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
            if len(mutations) > max_mutations:
                continue
            candidates.append(
                (
                    -(tick - unrouted_since),
                    last_active,
                    node_id,
                    mutations,
                )
            )

        if not candidates:
            return ()
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        return candidates[0][3]

    @staticmethod
    def nodes_with_path_to_targets(
        target_ids: Collection[str],
        *,
        graph: CognitiveGraph,
    ) -> set[str]:
        node_ids = {node.node_id for node in graph.nodes}
        targets = set(target_ids) & node_ids
        if not targets:
            return set()
        reverse_adj: dict[str, set[str]] = {}
        for edge in graph.edges:
            reverse_adj.setdefault(edge.target_id, set()).add(edge.source_id)
        reachable = set(targets)
        frontier = list(targets)
        while frontier:
            target = frontier.pop()
            for source in reverse_adj.get(target, ()):
                if source not in reachable:
                    reachable.add(source)
                    frontier.append(source)
        return reachable

    def nodes_with_path_to_core_readout(
        self,
        *,
        graph: CognitiveGraph,
    ) -> set[str]:
        core_readouts = [
            node.node_id
            for node in graph.nodes
            if (
                node.kind is NodeKind.READOUT
                and not node.node_id.startswith(_MOTOR_READOUT_PREFIX)
                and not node.node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
            )
        ]
        targets = (
            (_CORE_READOUT_ID,)
            if _CORE_READOUT_ID in core_readouts
            else tuple(core_readouts)
        )
        return self.nodes_with_path_to_targets(targets, graph=graph)

    def propose_recycling(
        self,
        *,
        graph: CognitiveGraph,
        tick: int,
        mutation_slots: int,
        develop_senses: bool,
        kernel_limits: KernelLimits,
    ) -> tuple[tuple[Mutation, ...], dict[str, object] | None]:
        if not develop_senses or mutation_slots < 1:
            return (), None

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
        if not core_readouts:
            return (), None

        routed = self.nodes_with_path_to_core_readout(graph=graph)
        unrouted_ids = self.update_unrouted(
            graph=graph,
            routed_ids=routed,
            tick=tick,
        )
        stranded = [
            node_id
            for node_id in sorted(unrouted_ids)
            if node_id in self.concept_last_active_tick
        ]
        if not stranded:
            return (), None

        concept_id = stranded[0]
        readout_id = core_readouts[0]
        if any(
            edge.source_id == concept_id and edge.target_id == readout_id
            for edge in graph.edges
        ):
            return (), None

        mutation = Mutation(
            kind="add_edge",
            payload={
                "source_id": concept_id,
                "target_id": readout_id,
                "kind": EdgeKind.EXCITATORY,
                "weight": _TENTATIVE_WEIGHT,
                "plasticity": 0.25,
                "delay_ticks": 1,
            },
        )
        candidate_graph = apply_mutations(
            graph,
            (mutation,),
            kernel_limits,
            frozen=False,
        )
        if candidate_graph is graph:
            return (), None
        return (
            (mutation,),
            {
                "tick": tick,
                "concept_id": concept_id,
                "reason": "stranded_route_repair",
            },
        )

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
