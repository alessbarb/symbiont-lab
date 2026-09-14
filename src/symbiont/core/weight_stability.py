"""Epoch-spaced class-stability consolidation for synaptic weights (design
docs/design/biological-memory-consolidation.md §11, owner decision
2026-09-14). Deliberately separate from ConsolidationSignal/
MemoryConsolidator: an Oja delta is an internal consequence of learning,
not a perceptual salience signal, and reinterpreting it as novelty/surprise
would mix levels the memory-kind taxonomy keeps apart.
"""

from __future__ import annotations

from collections.abc import Collection, Hashable
from dataclasses import dataclass
from typing import Mapping, Sequence

from ..cognition.checkpoint import WEIGHT_CLASSES, dequantize_signed, quantize_signed
from ..cognition.limits import KernelLimits
from ..cognition.types import WEIGHT_RANGE

EdgeKey = Hashable


@dataclass(slots=True)
class _EdgeStability:
    pending_class: int
    pending_epoch: int
    candidate_class: int | None = None
    support_epochs: int = 0


class WeightStabilityTracker:
    def __init__(self, *, kernel_limits: KernelLimits) -> None:
        self._kernel_limits = kernel_limits
        self._state: dict[EdgeKey, _EdgeStability] = {}
        self._durable: dict[EdgeKey, int] = {}

    def seed(self, edge_key: EdgeKey, construction_class: int) -> None:
        """Called once per edge at CognitiveBridge construction/restore --
        this is the durable class an edge exports until it completes its
        first real consolidation (design: construction weight until first
        real consolidation)."""
        self._durable[edge_key] = construction_class

    def reconcile(self, edge_keys: Collection[EdgeKey]) -> None:
        """Forget consolidation state for edges that no longer exist.

        Structural plasticity can prune an edge and later recreate the same
        endpoint/kind tuple. Keeping the removed edge's pending candidate in
        RAM would let the new edge inherit evidence from a previous synapse.
        Reconciliation makes edge lifetime, not identifier reuse, the memory
        boundary.
        """
        allowed = set(edge_keys)
        self._state = {key: value for key, value in self._state.items() if key in allowed}
        self._durable = {key: value for key, value in self._durable.items() if key in allowed}

    def observe(self, edge_key: EdgeKey, weight_class: int, *, tick: int) -> None:
        epoch_id = tick // self._kernel_limits.consolidation_epoch_ticks
        state = self._state.get(edge_key)
        if state is None:
            self._state[edge_key] = _EdgeStability(
                pending_class=weight_class, pending_epoch=epoch_id, candidate_class=weight_class, support_epochs=0
            )
            return
        if epoch_id == state.pending_epoch:
            # Still inside the same epoch -- P12: the latest sample this
            # epoch wins, but no support increment happens until the epoch
            # actually closes (a burst of updates counts as at most one
            # observation for this epoch).
            state.pending_class = weight_class
            return
        # An epoch boundary was crossed: finalize the just-closed epoch's
        # sampled class against the running candidate.
        finalized_class = state.pending_class
        if finalized_class == state.candidate_class:
            state.support_epochs += 1
        else:
            state.candidate_class = finalized_class
            state.support_epochs = 1
        state.pending_class = weight_class
        state.pending_epoch = epoch_id

    def candidate_class(self, edge_key: EdgeKey) -> int | None:
        state = self._state.get(edge_key)
        return state.candidate_class if state is not None else None

    def is_ready(self, edge_key: EdgeKey) -> bool:
        state = self._state.get(edge_key)
        return state is not None and state.support_epochs >= self._kernel_limits.slow_support_epochs

    def durable_class(self, edge_key: EdgeKey) -> int:
        return self._durable[edge_key]

    def consolidate_node(
        self,
        edge_keys: Sequence[EdgeKey],
        live_weights: Mapping[EdgeKey, float],
        *,
        max_incoming_norm: float,
    ) -> dict[EdgeKey, int] | None:
        """Node-atomic homeostatic commit (design §11, P13): a node commits
        only when every *changed* incoming edge (candidate class differs
        from its current durable class) is individually ready. One immature
        changed edge blocks the whole node -- no partial commits, and an
        unchanged sibling's durable weight is never rewritten."""
        changed = [key for key in edge_keys if self.candidate_class(key) != self.durable_class(key)]
        if not changed:
            return None
        if not all(self.is_ready(key) for key in changed):
            return None

        changed_set = set(changed)
        vector: dict[EdgeKey, float] = {}
        for key in edge_keys:
            if key in changed_set:
                vector[key] = live_weights[key]
            else:
                vector[key] = dequantize_signed(self.durable_class(key), WEIGHT_RANGE, WEIGHT_CLASSES)

        norm = sum(abs(value) for value in vector.values())
        scale = max_incoming_norm / norm if norm > max_incoming_norm else 1.0

        result = {key: quantize_signed(value * scale, WEIGHT_RANGE, WEIGHT_CLASSES) for key, value in vector.items()}
        for key, durable_class in result.items():
            self._durable[key] = durable_class
        return result
