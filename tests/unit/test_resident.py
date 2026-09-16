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


def test_resident_stops_cleanly_on_death(tmp_path) -> None:
    from types import SimpleNamespace
    from symbiont.core.physiology import VitalState

    class DyingRuntime(FakeRuntime):
        def tick(self):
            self.ticks += 1
            state = VitalState.DEAD if self.ticks >= 2 else VitalState.ACTIVE
            return SimpleNamespace(physiology=SimpleNamespace(state=state))

    runtime = DyingRuntime()
    target = tmp_path / "dead_state.json"
    resident = ResidentOrganism(
        runtime,  # type: ignore[arg-type]
        state_file=target,
        config=ResidentConfig(interval_seconds=0.001, max_ticks=10),
    )
    ticks = resident.run()
    assert ticks == 2
    assert target in runtime.saved


def test_resident_publishes_capsule_to_local_habitat(tmp_path) -> None:
    from symbiont.core.capsule import CapsuleKeyPair
    from symbiont.core.local_habitat import LocalHabitat
    from symbiont.core.runtime import OrganismRuntime

    habitat = LocalHabitat(tmp_path / "habitat")
    keypair = CapsuleKeyPair.generate()

    runtime = OrganismRuntime(
        bootstrap_semantic_senses=True,
        discover_senses=False,
        min_samples=1,
    )
    runtime.tick()

    state_file = tmp_path / "resident.json"
    resident = ResidentOrganism(
        runtime,
        state_file=state_file,
        config=ResidentConfig(interval_seconds=0.001, checkpoint_every_ticks=1, max_ticks=1),
        habitat=habitat,
        keypair=keypair,
    )
    ticks = resident.run()
    assert ticks == 1
    caps = habitat.poll_capsules()
    assert len(caps) == 1
    assert caps[0].signer_public_key == keypair.public_bytes


