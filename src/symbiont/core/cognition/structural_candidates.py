from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Collection

from ...cognition.graph import CognitiveGraph
from ...cognition.structure import Mutation, apply_mutations


@dataclass(slots=True)
class StructuralCandidate:
    candidate_id: str
    family: str
    producer_id: str
    eligible_tick: int
    mutations: tuple[Mutation, ...]
    contention_losses: int = 0

    @property
    def required_nodes(self) -> int:
        return sum(1 for mutation in self.mutations if mutation.kind == "add_node")

    @property
    def required_edges(self) -> int:
        return sum(1 for mutation in self.mutations if mutation.kind == "add_edge")

    def checkpoint(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "producer_id": self.producer_id,
            "eligible_tick": self.eligible_tick,
            "contention_losses": 0,
            "mutations": [
                {"kind": mutation.kind, "payload": dict(mutation.payload)}
                for mutation in self.mutations
            ],
        }


class StructuralContention:
    """Own producer-neutral structural admission arbitration.

    This component does not own maintenance, repair or generic structural
    growth. It only manages admission candidates and deterministic/fair
    selection among producers.
    """

    def __init__(self, *, kernel_limits, identity: str) -> None:
        self._kernel_limits = kernel_limits
        self.candidates: dict[str, StructuralCandidate] = {}
        self.consolidation_generation = 0
        self.last_consolidated_producer_id: str | None = None
        self._identity = str(identity)

    @staticmethod
    def producer_id_for_family(family: str) -> str:
        normalized = str(family).strip().replace("_", "-")
        return f"producer.{normalized}" if normalized else "producer.unknown"

    def bind_identity(self, identity: str) -> None:
        value = str(identity)
        if value:
            self._identity = value

    def register(
        self,
        *,
        candidate_id: str,
        family: str,
        mutations: tuple[Mutation, ...],
        eligible_tick: int,
        producer_id: str | None = None,
    ) -> bool:
        if not candidate_id or not mutations:
            return False
        resolved_producer = (
            str(producer_id).strip()
            if producer_id is not None and str(producer_id).strip()
            else self.producer_id_for_family(family)
        )
        existing = self.candidates.get(candidate_id)
        if existing is not None:
            existing.mutations = mutations
            existing.eligible_tick = min(
                existing.eligible_tick,
                max(0, int(eligible_tick)),
            )
            return True
        if any(
            candidate.producer_id == resolved_producer for candidate in self.candidates.values()
        ):
            return False
        if len(self.candidates) >= self._kernel_limits.max_consolidation_candidates:
            return False
        self.candidates[candidate_id] = StructuralCandidate(
            candidate_id=candidate_id,
            family=family,
            producer_id=resolved_producer,
            eligible_tick=max(0, int(eligible_tick)),
            mutations=mutations,
        )
        return True

    def drop(self, candidate_id: str) -> None:
        self.candidates.pop(candidate_id, None)

    def _producer_rank(self, producer_id: str) -> int:
        material = f"{self._identity}|producer-order|{producer_id}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")

    def candidate_tiebreak(self, candidate_id: str) -> int:
        material = (f"{self._identity}|{self.consolidation_generation}|{candidate_id}").encode(
            "utf-8"
        )
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")

    def select(
        self,
        *,
        graph: CognitiveGraph,
        mutation_slots: int,
        node_slots: int,
        edge_slots: int,
        frozen: bool,
    ) -> tuple[str | None, tuple[Mutation, ...], tuple[str, ...]]:
        if mutation_slots <= 0:
            return None, (), ()

        valid = [
            candidate
            for candidate in self.candidates.values()
            if (
                candidate.required_nodes <= node_slots
                and candidate.required_edges <= edge_slots
                and len(candidate.mutations) <= mutation_slots
            )
        ]
        if not valid:
            return None, (), ()

        nominees: dict[str, StructuralCandidate] = {}
        for candidate in valid:
            current = nominees.get(candidate.producer_id)
            if current is None or (
                candidate.eligible_tick,
                self.candidate_tiebreak(candidate.candidate_id),
                candidate.candidate_id,
            ) < (
                current.eligible_tick,
                self.candidate_tiebreak(current.candidate_id),
                current.candidate_id,
            ):
                nominees[candidate.producer_id] = candidate
        if not nominees:
            return None, (), ()

        oldest_tick = min(candidate.eligible_tick for candidate in nominees.values())
        eligible_producers = [
            producer_id
            for producer_id, candidate in nominees.items()
            if candidate.eligible_tick == oldest_tick
        ]
        producer_order = sorted(
            eligible_producers,
            key=lambda producer_id: (self._producer_rank(producer_id), producer_id),
        )
        if self.last_consolidated_producer_id is not None:
            cursor_key = (
                self._producer_rank(self.last_consolidated_producer_id),
                self.last_consolidated_producer_id,
            )
            after_cursor = [
                producer_id
                for producer_id in producer_order
                if (self._producer_rank(producer_id), producer_id) > cursor_key
            ]
            before_or_at_cursor = [
                producer_id
                for producer_id in producer_order
                if (self._producer_rank(producer_id), producer_id) <= cursor_key
            ]
            producer_order = after_cursor + before_or_at_cursor

        winner = nominees[producer_order[0]]
        candidate_graph = apply_mutations(
            graph,
            winner.mutations,
            self._kernel_limits,
            frozen=frozen,
        )
        if candidate_graph is graph:
            self.candidates.pop(winner.candidate_id, None)
            return None, (), ()
        return winner.candidate_id, winner.mutations, ()

    def commit(
        self,
        *,
        winner_id: str | None,
        loser_ids: Collection[str],
    ) -> None:
        if winner_id is None:
            return
        winner = self.candidates.get(winner_id)
        if winner is not None:
            self.last_consolidated_producer_id = winner.producer_id
        self.candidates.pop(winner_id, None)
        _ = loser_ids
