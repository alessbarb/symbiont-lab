from __future__ import annotations

import pytest

from symbiont.core.governor import (
    ConsentRevokedError,
    GovernedOrganism,
    RateLimitedError,
    TickBudgetExhaustedError,
)
from symbiont.core.runtime import OrganismRuntime


def _runtime() -> OrganismRuntime:
    return OrganismRuntime(min_samples=1, investigate_ticks=0)


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def test_rejects_negative_min_seconds_between_ticks():
    with pytest.raises(ValueError):
        GovernedOrganism(_runtime(), min_seconds_between_ticks=-1.0)


def test_rejects_non_positive_max_ticks():
    with pytest.raises(ValueError):
        GovernedOrganism(_runtime(), max_ticks=0)


def test_is_consented_true_by_default():
    governed = GovernedOrganism(_runtime())
    assert governed.is_consented


def test_ticks_remaining_none_when_unbounded():
    governed = GovernedOrganism(_runtime())
    assert governed.ticks_remaining is None


def test_tick_delegates_to_wrapped_runtime():
    governed = GovernedOrganism(_runtime())
    result = governed.tick()

    assert result.tick == 1
    assert governed.ticks_run == 1


def test_revoke_blocks_the_next_tick():
    governed = GovernedOrganism(_runtime())
    governed.tick()
    governed.revoke()

    assert not governed.is_consented
    with pytest.raises(ConsentRevokedError):
        governed.tick()


def test_grant_after_revoke_resumes_ticking():
    governed = GovernedOrganism(_runtime())
    governed.revoke()
    governed.grant()

    result = governed.tick()
    assert result.tick == 1


def test_tick_budget_is_enforced():
    governed = GovernedOrganism(_runtime(), max_ticks=2)
    governed.tick()
    governed.tick()

    assert governed.ticks_remaining == 0
    with pytest.raises(TickBudgetExhaustedError):
        governed.tick()


def test_ticks_remaining_counts_down():
    governed = GovernedOrganism(_runtime(), max_ticks=3)
    governed.tick()
    assert governed.ticks_remaining == 2
    governed.tick()
    assert governed.ticks_remaining == 1


def test_rate_limit_blocks_a_tick_too_soon():
    clock = _FakeClock(start=0.0)
    governed = GovernedOrganism(_runtime(), min_seconds_between_ticks=5.0, clock=clock)
    governed.tick()

    clock.now = 2.0
    with pytest.raises(RateLimitedError):
        governed.tick()


def test_rate_limit_allows_a_tick_after_the_interval_elapses():
    clock = _FakeClock(start=0.0)
    governed = GovernedOrganism(_runtime(), min_seconds_between_ticks=5.0, clock=clock)
    governed.tick()

    clock.now = 5.0
    result = governed.tick()
    assert result.tick == 2


def test_zero_rate_limit_never_blocks():
    clock = _FakeClock(start=0.0)
    governed = GovernedOrganism(_runtime(), min_seconds_between_ticks=0.0, clock=clock)
    governed.tick()
    governed.tick()  # same instant, should still be allowed

    assert governed.ticks_run == 2


def test_checkpoint_delegates_to_wrapped_runtime():
    runtime = _runtime()
    governed = GovernedOrganism(runtime, max_ticks=5)
    governed.tick()

    assert governed.checkpoint() == runtime.checkpoint()


def test_failed_tick_due_to_revocation_does_not_consume_budget():
    governed = GovernedOrganism(_runtime(), max_ticks=2)
    governed.revoke()
    with pytest.raises(ConsentRevokedError):
        governed.tick()

    assert governed.ticks_run == 0
    assert governed.ticks_remaining == 2
