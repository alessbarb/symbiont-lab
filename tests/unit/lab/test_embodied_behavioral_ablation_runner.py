from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from symbiont_lab.experiments.runner import ExperimentRunner
from symbiont_lab.experiments.loader import load_experiment_file


@dataclass
class _Result:
    def as_dict(self):
        return {"ok": True}


def test_behavioral_ablation_runner_passes_preregistered_horizon(
    monkeypatch,
    tmp_path: Path,
):
    calls = {}

    def protocol(*, seeds, ticks, horizon_ticks):
        calls.update(
            seeds=tuple(seeds),
            ticks=ticks,
            horizon_ticks=horizon_ticks,
        )
        return _Result()

    monkeypatch.setattr(
        "symbiont_lab.experiments.runner.get_protocol",
        lambda _name: protocol,
    )
    monkeypatch.setattr(
        "symbiont_lab.experiments.runner.get_git_info",
        lambda: ("a" * 40, False),
    )

    spec = load_experiment_file(
        Path("experiments/learning/embodied-behavioral-ablation/experiment.toml")
    )
    ExperimentRunner(tmp_path).run(spec)

    assert calls == {
        "seeds": (101, 127, 149),
        "ticks": 3000,
        "horizon_ticks": 256,
    }
