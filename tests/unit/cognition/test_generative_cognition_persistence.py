from symbiont.cognition.generative import (
    GenerativeAgenda,
    GenerativeMode,
    GenerativeScheduler,
    dumps_cognition,
    loads_cognition,
    new_episode,
)
from symbiont.cognition.generative.workspace import GenerativeWorkspace


def test_cognition_checkpoint_round_trips_workspace_agenda_and_scheduler():
    workspace = GenerativeWorkspace(
        episode=new_episode(
            episode_id="e0",
            organism_id="o0",
            root_state_id="s0",
            mode=GenerativeMode.OFFLINE,
            symbiont_tick=4,
            generative_tick=2,
        )
    )
    agenda = GenerativeAgenda()
    scheduler = GenerativeScheduler(offline_quota=2)
    scheduler.schedule(
        mode=GenerativeMode.OFFLINE,
        tick=4,
        has_target=False,
        workspace_open=True,
        model_queries_remaining=1,
    )

    restored_workspace, restored_agenda, restored_scheduler = loads_cognition(
        dumps_cognition(workspace=workspace, agenda=agenda, scheduler=scheduler)
    )

    assert restored_workspace.checkpoint() == workspace.checkpoint()
    assert restored_agenda.checkpoint() == agenda.checkpoint()
    assert restored_scheduler.checkpoint() == scheduler.checkpoint()


def test_cognition_checkpoint_requires_all_domains():
    payload = {
        "schema_version": 1,
        "workspace": {},
        "agenda": {},
    }
    try:
        loads_cognition(__import__("json").dumps(payload))
    except ValueError as exc:
        assert "invalid generative cognition checkpoint" in str(exc)
    else:
        raise AssertionError("incomplete cognition checkpoint was accepted")
