from symbiont.cognition.generative import GenerativeMode, GenerativeScheduler


def test_scheduler_checkpoint_preserves_quota_usage():
    scheduler = GenerativeScheduler(online_quota=1, idle_quota=2, offline_quota=3)
    scheduler.schedule(
        mode=GenerativeMode.IDLE,
        tick=7,
        has_target=True,
        workspace_open=True,
        model_queries_remaining=1,
    )

    restored = GenerativeScheduler.from_checkpoint(scheduler.checkpoint())
    decision = restored.schedule(
        mode=GenerativeMode.IDLE,
        tick=7,
        has_target=True,
        workspace_open=True,
        model_queries_remaining=1,
    )

    assert decision.allowed
    assert (
        restored.schedule(
            mode=GenerativeMode.IDLE,
            tick=7,
            has_target=True,
            workspace_open=True,
            model_queries_remaining=1,
        ).reason
        == "mode_quota_exhausted"
    )


def test_scheduler_checkpoint_rejects_unknown_mode():
    scheduler = GenerativeScheduler()
    payload = scheduler.checkpoint()
    payload["used"] = [{"tick": 1, "mode": "unknown", "count": 1}]

    try:
        GenerativeScheduler.from_checkpoint(payload)
    except ValueError as exc:
        assert "invalid scheduler checkpoint" in str(exc)
    else:
        raise AssertionError("unknown scheduler mode was accepted")
