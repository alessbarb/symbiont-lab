from __future__ import annotations

import time
from typing import Any, Callable

from .runtime import OrganismRuntime, RuntimeTickResult


class ConsentRevokedError(RuntimeError):
    """Raised when a tick is attempted while consent is not granted."""


class RateLimitedError(RuntimeError):
    """Raised when a tick is attempted before the minimum interval has elapsed."""


class TickBudgetExhaustedError(RuntimeError):
    """Raised when the configured maximum number of ticks has already been reached."""


class GovernedOrganism:
    """Wraps an :class:`~symbiont.core.runtime.OrganismRuntime` with explicit,
    continuously-checked consent and a bounded resource budget (roadmap
    v0.45, Milestone D #55).

    v0.44's runtime proved the cognitive cycle closes and repeats; this
    release governs *whether* and *how often* it is allowed to. Nothing
    here senses anything itself — every :meth:`tick` call first checks,
    fresh, whether the organism is currently permitted to run at all:

    - **Consent** is a live toggle, not a one-time construction argument —
      the same discipline CLAUDE.md requires for individual samples
      ("consent is checked before every sample, not just once at
      startup"), applied one level up to the whole cognitive cycle.
      :meth:`revoke` takes effect on the very next tick, not eventually.
    - **Frequency** is bounded by ``min_seconds_between_ticks``: a tick
      attempted too soon after the last one is refused, not queued,
      delayed or silently throttled — this class never sleeps or spawns a
      background loop of its own, so it introduces no durable background
      execution.
    - **Total resource use** is bounded by ``max_ticks``: once reached,
      every further tick is refused until a new ``GovernedOrganism`` (or a
      caller-provided reset) is created — there is no way to run past the
      configured budget from inside this class.

    Capability-level permission (which senses the organism may use at all)
    is deliberately not reinvented here: it already exists as
    :class:`~symbiont.host.contracts.DiscoveryPolicy`, passed to the
    wrapped ``OrganismRuntime`` at construction.
    """

    def __init__(
        self,
        runtime: OrganismRuntime,
        *,
        min_seconds_between_ticks: float = 0.0,
        max_ticks: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if min_seconds_between_ticks < 0.0:
            raise ValueError("min_seconds_between_ticks must be non-negative")
        if max_ticks is not None and max_ticks < 1:
            raise ValueError("max_ticks must be at least 1 when given")
        self._runtime = runtime
        self._min_seconds_between_ticks = min_seconds_between_ticks
        self._max_ticks = max_ticks
        self._clock = clock
        self._granted = True
        self._last_tick_at: float | None = None
        self._ticks_run = 0

    @property
    def is_consented(self) -> bool:
        return self._granted

    @property
    def ticks_run(self) -> int:
        return self._ticks_run

    @property
    def ticks_remaining(self) -> int | None:
        """``None`` when unbounded; otherwise how many ticks are left in
        the budget."""
        if self._max_ticks is None:
            return None
        return max(0, self._max_ticks - self._ticks_run)

    def grant(self) -> None:
        self._granted = True

    def revoke(self) -> None:
        self._granted = False

    def tick(self) -> RuntimeTickResult:
        if not self._granted:
            raise ConsentRevokedError("consent has been revoked; call grant() to resume")
        if self._max_ticks is not None and self._ticks_run >= self._max_ticks:
            raise TickBudgetExhaustedError(f"tick budget of {self._max_ticks} has already been reached")

        now = self._clock()
        if self._last_tick_at is not None and (now - self._last_tick_at) < self._min_seconds_between_ticks:
            waited = now - self._last_tick_at
            raise RateLimitedError(
                f"must wait at least {self._min_seconds_between_ticks}s between ticks "
                f"(only {waited:.3f}s elapsed)"
            )

        result = self._runtime.tick()
        self._last_tick_at = self._clock()
        self._ticks_run += 1
        return result

    def checkpoint(self) -> dict[str, Any]:
        return self._runtime.checkpoint()
