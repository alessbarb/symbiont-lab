from __future__ import annotations

from symbiont.cognition.generative import GenerativeMode, GenerativeScheduler


def test_scheduler_is_separate_from_target_selection_and_enforces_mode_quota():
    scheduler = GenerativeScheduler(online_quota=1)
    first = scheduler.schedule(
        mode=GenerativeMode.ONLINE,
        tick=3,
        has_target=True,
        workspace_open=True,
        model_queries_remaining=1,
    )
    second = scheduler.schedule(
        mode=GenerativeMode.ONLINE,
        tick=3,
        has_target=True,
        workspace_open=True,
        model_queries_remaining=1,
    )
    assert first.allowed is True
    assert second.reason == "mode_quota_exhausted"


def test_scheduler_fails_closed_without_target_or_budget():
    scheduler = GenerativeScheduler()
    assert (
        scheduler.schedule(
            mode=GenerativeMode.IDLE,
            tick=0,
            has_target=False,
            workspace_open=True,
            model_queries_remaining=1,
        ).reason
        == "no_target"
    )
    assert (
        scheduler.schedule(
            mode=GenerativeMode.IDLE,
            tick=0,
            has_target=True,
            workspace_open=True,
            model_queries_remaining=0,
        ).reason
        == "model_budget_exhausted"
    )
