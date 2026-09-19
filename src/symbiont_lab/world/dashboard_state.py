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

from .cli_view import render_world, world_snapshot
from .genesis_v1 import GENESIS_V1_METADATA, build_ground_truth
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
    ) -> None:
        self._lock = Lock()
        self._tick_delay_s = max(tick_delay_s, 0.0)
        self._running = False
        self._error: str | None = None

        self.topology = HexTopology(width=width, height=height)
        self.ground_truth = build_ground_truth()
        cells = founder_placement(world_seed, self.topology, founders)
        self.population = PopulationGenesisRuntime(
            organism_ids=tuple(f"founder-{i}" for i in range(founders)),
            world_seed=world_seed,
            ground_truth=self.ground_truth,
            topology=self.topology,
            start_cells=cells,
        )

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
                    self.population.run_tick()
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
            )
            snapshot = world_snapshot(
                self.population.state,
                self.population.environment,
                self.ground_truth,
                GENESIS_V1_METADATA,
                self.topology,
            )
            return {
                "running": self._running,
                "error": self._error,
                "tick": self.population.state.tick,
                "alive_count": sum(self.population.is_alive(o) for o in self.population.organism_ids),
                "text": text,
                **snapshot,
            }
