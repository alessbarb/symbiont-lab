"""Atomic multi-layer tick transaction (docs/design/symbiont-world-v3.md §4, §5).

Guarantees full commit-or-rollback across:
1. WorldState (occupancy, bodies, tick)
2. WorldEnvironment (fields, resource pools)
3. Organisms (_OrganismRig: runtime, reading_provider, habitats, policy_rng)
4. DeferredEffectQueue
5. EventJournal (staged events committed only on success)

Property guaranteed: failed_tick(state_n) == state_n.
"""

from __future__ import annotations

import copy
import copyreg
import types
from typing import Any, Mapping, Sequence

# Register pickle reducer for MappingProxyType so deepcopy works on nested runtime structures
copyreg.pickle(types.MappingProxyType, lambda mp: (types.MappingProxyType, (dict(mp),)))


from symbiont_world.events import EventJournal, WorldEvent
from symbiont_world.genesis import WorldEnvironment
from symbiont_world.state import TickAborted, WorldState

from .adapter import _OrganismRig
from .deferred import DeferredEffectQueue


class IntegratedWorldTickTransaction:
    """Context manager executing a tick with full rollback capability across
    world state, environment, all organism rigs, deferred effects, and journal."""

    def __init__(
        self,
        *,
        state: WorldState,
        environment: WorldEnvironment,
        rigs: Mapping[str, _OrganismRig],
        deferred_queue: DeferredEffectQueue | None = None,
        journal: EventJournal | None = None,
        geography: Any | None = None,
    ) -> None:
        self.state = state
        self.environment = environment
        self.rigs = rigs
        self.deferred_queue = deferred_queue
        self.journal = journal
        self.geography = geography
        self.committed: bool = False
        self._staged_events: list[WorldEvent] = []

        self._snapshot_state: dict[str, object] | None = None
        self._snapshot_environment: dict[str, object] | None = None
        self._snapshot_rigs: dict[str, _OrganismRig] | None = None
        self._snapshot_deferred: list[dict[str, object]] | None = None
        self._snapshot_geography: dict[str, object] | None = None

    def stage_event(self, event: WorldEvent) -> None:
        """Stage an event during the tick. Staged events are only appended to
        the journal if the transaction successfully commits."""
        self._staged_events.append(event)

    def stage_events(self, events: Sequence[WorldEvent]) -> None:
        self._staged_events.extend(events)

    @property
    def staged_events(self) -> tuple[WorldEvent, ...]:
        return tuple(self._staged_events)

    def __enter__(self) -> "IntegratedWorldTickTransaction":
        # 1. Snapshot WorldState
        self._snapshot_state = self.state.snapshot()
        # 2. Snapshot WorldEnvironment
        self._snapshot_environment = self.environment.snapshot()
        # 3. Snapshot all organism rigs
        # Deep-copy each rig as one object graph, not as independent fields.
        # This preserves internal identity links (runtime lifecycle -> reading
        # provider, runtime -> resource habitats) across rollback.
        # For experimental_clean organisms with an Individual, detach historical
        # records before deepcopy to avoid O(T^2) snapshot explosion, maintaining
        # the history reference and pre-tick length for rollback if needed.
        snapshot_rigs: dict[str, tuple[Any, int | None]] = {}
        for org_id, rig in self.rigs.items():
            if rig.individual is not None:
                history_ref = rig.individual.history
                history_len = len(history_ref)
                rig.individual.history = []
                try:
                    snap_rig = copy.deepcopy(rig)
                finally:
                    rig.individual.history = history_ref
                snap_rig.individual.history = history_ref
                snapshot_rigs[org_id] = (snap_rig, history_len)
            else:
                snapshot_rigs[org_id] = (copy.deepcopy(rig), None)
        self._snapshot_rigs = snapshot_rigs
        # 4. Snapshot DeferredEffectQueue
        if self.deferred_queue is not None:
            self._snapshot_deferred = self.deferred_queue.snapshot()
        # 5. Snapshot DynamicGeography
        if self.geography is not None:
            self._snapshot_geography = self.geography.snapshot()
        # 6. Reset staged events
        self._staged_events.clear()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            # COMMIT:
            self.committed = True
            self.state.tick += 1
            if self.journal is not None:
                for event in self._staged_events:
                    self.journal.append(event)
            return False

        # ROLLBACK:
        self.committed = False
        if self._snapshot_state is not None:
            self.state.restore(self._snapshot_state)
        if self._snapshot_environment is not None:
            self.environment.restore(self._snapshot_environment)
        if self._snapshot_rigs is not None:
            for org_id, snap_entry in self._snapshot_rigs.items():
                snap, saved_history_len = (
                    snap_entry if isinstance(snap_entry, tuple) else (snap_entry, None)
                )
                rig = self.rigs[org_id]
                rig.runtime = snap.runtime
                rig.reading_provider = snap.reading_provider
                rig.resource_habitats = snap.resource_habitats
                rig.policy = snap.policy
                rig.policy_rng = snap.policy_rng
                rig.actuation_adapter = snap.actuation_adapter
                rig.actuation_binding = snap.actuation_binding
                if snap.individual is not None and rig.individual is not None:
                    rig.individual = snap.individual
                    if saved_history_len is not None:
                        del rig.individual.history[saved_history_len:]
        if self.deferred_queue is not None and self._snapshot_deferred is not None:
            self.deferred_queue.restore(self._snapshot_deferred)
        if self.geography is not None and self._snapshot_geography is not None:
            self.geography.restore(self._snapshot_geography)
        self._staged_events.clear()

        if issubclass(exc_type, TickAborted):
            return True
        return False
