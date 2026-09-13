from pathlib import Path

from symbiont.core.resident import ResidentConfig, ResidentOrganism


class FakeRuntime:
    def __init__(self) -> None:
        self.ticks = 0
        self.saved: list[Path] = []

    def tick(self):
        self.ticks += 1
        return self.ticks

    def checkpoint(self):
        return {"ticks": self.ticks}

    def save(self, path):
        self.saved.append(Path(path))


def test_resident_stops_at_explicit_budget_and_saves_on_exit(tmp_path) -> None:
    runtime = FakeRuntime()
    seen = []
    target = tmp_path / "state.json"
    resident = ResidentOrganism(
        runtime,  # type: ignore[arg-type]
        state_file=target,
        config=ResidentConfig(interval_seconds=0.001, checkpoint_every_ticks=2, max_ticks=3),
        on_tick=seen.append,
    )
    assert resident.run() == 3
    assert runtime.ticks == 3
    assert seen == [1, 2, 3]
    assert target in runtime.saved
