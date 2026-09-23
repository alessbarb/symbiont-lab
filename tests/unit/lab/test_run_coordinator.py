from symbiont_lab.experiments.spec import ExperimentSpec
from symbiont_lab.workbench.runs import (
    ExperimentRunState,
    RunCoordinator,
    StudyRunState,
    start_experiment,
)


def test_run_coordinator_allows_only_one_owner() -> None:
    coordinator = RunCoordinator()

    assert coordinator.acquire("experiment") is True
    assert coordinator.active == "experiment"
    assert coordinator.acquire("study") is False

    coordinator.release("study")
    assert coordinator.active == "experiment"

    coordinator.release("experiment")
    assert coordinator.active is None
    assert coordinator.acquire("physics3d") is True
    assert coordinator.acquire("study") is False
    coordinator.release("physics3d")
    assert coordinator.acquire("study") is True


def test_start_experiment_respects_preexisting_study_state() -> None:
    coordinator = RunCoordinator()
    experiment = ExperimentRunState()
    study = StudyRunState()
    assert study.start({}, 1) is True

    started = start_experiment(
        experiment,
        study,
        ExperimentSpec(),
        coordinator=coordinator,
    )

    assert started is False
    assert coordinator.active is None
    assert experiment.running is False
