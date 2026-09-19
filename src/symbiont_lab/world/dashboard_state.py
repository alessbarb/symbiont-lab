"""Background-ticking world state for the read-only World dashboard
(docs/design/symbiont-world-v2.md §8, extended to a persistent server).

The world runs continuously in a daemon thread, independent of any
viewer connecting or disconnecting -- same "the display does not control
cognition" rule as the CLI view: this state exposes a snapshot, never a
way to call WorldAction or otherwise influence the tick.
"""
from __future__ import annotations

from threading import Lock, Thread
import time

from typing import Any

from .cli_view import render_world, world_snapshot
from .genesis_v1 import GENESIS_V1_METADATA, build_constitution, build_ground_truth
from .persistence import WorldStorage
from .population import PopulationGenesisRuntime, founder_placement
from symbiont_world.topology import HexTopology


class WorldDashboardState:
    def __init__(
        self,
        *,
        world_seed: int = 101,
        founders: int = 8,
        width: int = 8,
        height: int = 8,
        tick_delay_s: float = 0.5,
        storage: WorldStorage | None = None,
        checkpoint_interval: int = 100,
        population: PopulationGenesisRuntime | None = None,
    ) -> None:
        self._lock = Lock()
        self._tick_delay_s = max(tick_delay_s, 0.0)
        self._running = False
        self._error: str | None = None
        self.storage = storage
        self.checkpoint_interval = checkpoint_interval

        self.topology = HexTopology(width=width, height=height)
        self.ground_truth = build_ground_truth()
        self.constitution = build_constitution(self.ground_truth, dimensions=(width, height))

        if population is not None:
            self.population = population
            self.topology = population.topology
            self.ground_truth = population.ground_truth
        else:
            cells = founder_placement(world_seed, self.topology, founders)
            self.population = PopulationGenesisRuntime(
                organism_ids=tuple(f"founder-{i}" for i in range(founders)),
                world_seed=world_seed,
                ground_truth=self.ground_truth,
                topology=self.topology,
                start_cells=cells,
            )

        # Bounded timeline metrics (docs/design/symbiont-world-v3.md §27, §28)
        self._timeline_max = 2048
        self._history_ticks: list[int] = []
        self._history_alive: list[int] = []
        self._history_mean_integrity: list[float] = []
        self._history_mean_reserve: list[float] = []
        self._history_hazard_hits: list[int] = []
        self._history_acquisitions: list[float] = []

        self._record_metrics(self.population.state.tick, None)

    def _record_metrics(self, tick: int, record: Any | None) -> None:
        oids = self.population.organism_ids
        alive_count = sum(self.population.is_alive(o) for o in oids)
        tot = len(oids) or 1
        
        integ_sum = 0.0
        res_sum = 0.0
        for o in oids:
            rig = self.population._rigs[o]
            integ_sum += float(rig.runtime.homeostasis.integrity)
            metabolic = rig.runtime.metabolism.snapshot()
            ratios = [
                metabolic.reserve[k] / max(metabolic.capacity[k], 1e-12)
                for k in metabolic.capacity
            ]
            if not ratios:
                raise RuntimeError("metabolic snapshot unexpectedly has no reserve dimensions")
            res_sum += float(sum(ratios) / len(ratios))

        mean_integ = integ_sum / tot
        mean_res = res_sum / tot

        hits_count = 0
        acq_count = 0.0
        if record is not None and hasattr(record, "per_organism"):
            for rec in record.per_organism.values():
                hits_count += len(rec.hazard_hits)
                if rec.action and "intake" in rec.action.action_id.lower() and rec.action.executed:
                    acq_count += 1.0

        self._history_ticks.append(tick)
        self._history_alive.append(alive_count)
        self._history_mean_integrity.append(round(mean_integ, 4))
        self._history_mean_reserve.append(round(mean_res, 4))
        self._history_hazard_hits.append(hits_count)
        self._history_acquisitions.append(acq_count)

        if len(self._history_ticks) > self._timeline_max:
            self._history_ticks.pop(0)
            self._history_alive.pop(0)
            self._history_mean_integrity.pop(0)
            self._history_mean_reserve.pop(0)
            self._history_hazard_hits.pop(0)
            self._history_acquisitions.pop(0)

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    return
                if not self.population.any_alive():
                    self._running = False
                    return
                try:
                    record = self.population.run_tick()
                    if record is not None:
                        self._record_metrics(self.population.state.tick, record)
                        if (
                            self.storage is not None
                            and self.checkpoint_interval > 0
                            and self.population.state.tick % self.checkpoint_interval == 0
                        ):
                            self.storage.save_checkpoint(
                                self.population,
                                world_fingerprint=self.constitution.fingerprint(),
                                constitution=self.constitution,
                            )
                except Exception as exc:  # noqa: BLE001 -- surfaced to viewers, not raised
                    self._error = f"{type(exc).__name__}: {exc}"
                    self._running = False
                    return
            time.sleep(self._tick_delay_s)

    def payload(self) -> dict:
        with self._lock:
            text = render_world(
                self.population.state,
                self.population.environment,
                self.ground_truth,
                GENESIS_V1_METADATA,
                self.topology,
                journal=self.population.journal,
            )
            snapshot = world_snapshot(
                self.population.state,
                self.population.environment,
                self.ground_truth,
                GENESIS_V1_METADATA,
                self.topology,
                population=self.population,
            )
            events = [
                {
                    "event_id": e.event_id,
                    "tick": e.tick,
                    "kind": e.kind,
                    "actor": e.actor,
                    "position": e.position,
                    "payload": dict(e.payload),
                    "causal_parent_ids": list(e.causal_parent_ids),
                    "contributing_event_ids": list(e.contributing_event_ids),
                }
                for e in self.population.journal.replay()[-60:]
            ]
            return {
                "running": self._running,
                "error": self._error,
                "tick": self.population.state.tick,
                "alive_count": sum(self.population.is_alive(o) for o in self.population.organism_ids),
                "text": text,
                "history": {
                    "ticks": list(self._history_ticks),
                    "alive": list(self._history_alive),
                    "mean_integrity": list(self._history_mean_integrity),
                    "mean_reserve": list(self._history_mean_reserve),
                    "hazard_hits": list(self._history_hazard_hits),
                    "acquisitions": list(self._history_acquisitions),
                },
                "events": events,
                **snapshot,
            }

