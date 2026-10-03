from symbiont.cognition.generative import (
    AgendaProgress,
    AgendaSource,
    GenerativeAgenda,
    GenerativeBudget,
    GenerativeExecutionCoordinator,
    GenerativeMode,
    GenerativeScheduler,
    GenerativeTarget,
    GenerativeWorkspace,
    new_episode,
)


def _workspace() -> GenerativeWorkspace:
    return GenerativeWorkspace(
        episode=new_episode(
            episode_id="e0",
            organism_id="o0",
            root_state_id="s0",
            mode=GenerativeMode.IDLE,
            symbiont_tick=1,
            generative_tick=1,
        ),
        budget=GenerativeBudget(max_model_queries=1),
    )


def _agenda() -> GenerativeAgenda:
    agenda = GenerativeAgenda()
    agenda.add_target(
        GenerativeTarget(
            target_id="target-0",
            source=AgendaSource.UNCERTAINTY,
            source_refs=("organism-ref",),
            created_tick=1,
            uncertainty=0.8,
            persistence=0.4,
            recurrence=1,
        )
    )
    return agenda


def test_coordinator_runs_one_eligible_target_and_records_progress():
    calls = []
    coordinator = GenerativeExecutionCoordinator(agenda=_agenda(), scheduler=GenerativeScheduler())

    result = coordinator.run(
        mode=GenerativeMode.IDLE,
        tick=2,
        workspace=_workspace(),
        run_target=lambda candidate, mode: (
            calls.append((candidate.target.target_id, mode)) or AgendaProgress(new_branch=True)
        ),
    )

    assert result.decision.allowed
    assert result.target_id == "target-0"
    assert result.progress == AgendaProgress(new_branch=True)
    assert calls == [("target-0", GenerativeMode.IDLE)]


def test_coordinator_does_not_call_target_when_workspace_is_closed():
    workspace = _workspace()
    workspace.close(reason=None)
    calls = []
    coordinator = GenerativeExecutionCoordinator(agenda=_agenda(), scheduler=GenerativeScheduler())

    result = coordinator.run(
        mode=GenerativeMode.OFFLINE,
        tick=2,
        workspace=workspace,
        run_target=lambda candidate, mode: calls.append(candidate) or AgendaProgress(),
    )

    assert not result.decision.allowed
    assert result.decision.reason == "workspace_closed"
    assert result.target_id is None
    assert calls == []


def test_coordinator_reports_no_target_without_invoking_callback():
    calls = []
    coordinator = GenerativeExecutionCoordinator(
        agenda=GenerativeAgenda(), scheduler=GenerativeScheduler()
    )

    result = coordinator.run(
        mode=GenerativeMode.ONLINE,
        tick=2,
        workspace=_workspace(),
        run_target=lambda candidate, mode: calls.append(candidate) or AgendaProgress(),
    )

    assert result.decision.reason == "no_target"
    assert calls == []
