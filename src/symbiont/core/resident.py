from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import time
from typing import Callable

from .governor import GovernedOrganism
from .runtime import OrganismRuntime, RuntimeTickResult


@dataclass(slots=True, frozen=True)
class ResidentConfig:
    interval_seconds: float = 15.0
    checkpoint_every_ticks: int = 20
    max_ticks: int | None = None

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if self.checkpoint_every_ticks < 1:
            raise ValueError("checkpoint_every_ticks must be at least 1")
        if self.max_ticks is not None and self.max_ticks < 1:
            raise ValueError("max_ticks must be at least 1 when provided")


class ResidentOrganism:
    """Foreground resident lifecycle with explicit stop and durable memory.

    This class is intentionally transparent: it does not daemonize itself,
    modify startup configuration, elevate privileges or hide. A process
    supervisor such as ``systemd --user`` may keep it alive, while this loop
    remains an ordinary user process with a visible command line and a clean
    shutdown path.
    """

    def __init__(
        self,
        runtime: OrganismRuntime,
        *,
        state_file: str | Path,
        config: ResidentConfig | None = None,
        on_tick: Callable[[RuntimeTickResult], None] | None = None,
        on_checkpoint: Callable[[], None] | None = None,
    ) -> None:
        self.runtime = runtime
        self.state_file = Path(state_file).expanduser()
        self.config = config if config is not None else ResidentConfig()
        self.on_tick = on_tick
        self.on_checkpoint = on_checkpoint
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def run(self) -> int:
        governed = GovernedOrganism(self.runtime, max_ticks=self.config.max_ticks)
        ticks = 0
        try:
            while not self._stop.is_set():
                result = governed.tick()
                ticks += 1
                if self.on_tick is not None:
                    self.on_tick(result)
                if ticks % self.config.checkpoint_every_ticks == 0:
                    self.runtime.save(self.state_file)
                    if self.on_checkpoint is not None:
                        self.on_checkpoint()
                if self.config.max_ticks is not None and ticks >= self.config.max_ticks:
                    break
                self._stop.wait(self.config.interval_seconds)
        finally:
            self.runtime.save(self.state_file)
            if self.on_checkpoint is not None:
                self.on_checkpoint()
        return ticks
