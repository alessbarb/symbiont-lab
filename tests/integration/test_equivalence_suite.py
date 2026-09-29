from __future__ import annotations

from pathlib import Path

from symbiont_lab.physics3d.engine import run
from symbiont_lab.physics3d.equivalence import EquivalenceRunConfig, equivalent, run_digests


def _snapshot(tmp_path: Path) -> Path:
    snapshot = tmp_path / "snapshot"
    (snapshot / "models").mkdir(parents=True)
    run(
        headless=True,
        ticks=2,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=True,
        fresh_body=True,
        body_kind="anthropomorphic-v6",
        symbiont_file=snapshot / "organism.symbiont",
        body_file=snapshot / "body.json",
        telemetry_file=tmp_path / "telemetry",
    )
    return snapshot


def test_equivalence_config_is_deterministic_without_training(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path)
    config = EquivalenceRunConfig(ticks=4, body_kind="anthropomorphic-v6")
    first = run_digests(snapshot, config=config)
    second = run_digests(snapshot, config=config)
    assert equivalent(first, second)
