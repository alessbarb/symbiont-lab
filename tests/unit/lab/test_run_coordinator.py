from symbiont_lab.workbench.runs import RunCoordinator


def test_run_coordinator_allows_only_one_owner() -> None:
    coordinator = RunCoordinator()

    assert coordinator.acquire("experiment") is True
    assert coordinator.active == "experiment"
    assert coordinator.acquire("study") is False

    coordinator.release("study")
    assert coordinator.active == "experiment"

    coordinator.release("experiment")
    assert coordinator.active is None
    assert coordinator.acquire("study") is True
