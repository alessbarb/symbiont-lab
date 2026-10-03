"""ADR-0011: the visual apparatus samples physics deterministically and bounded."""

from __future__ import annotations

from pathlib import Path

import pytest

pybullet = pytest.importorskip("pybullet")
pybullet_data = pytest.importorskip("pybullet_data")

from environment.physics3d.environments import build_environment, environment_recipe
from lab.integration.physics3d.bodies import ANTHROPOMORPHIC_V6_VISION
from lab.physics3d.engine import run
from lab.physics3d.persistence import read_symbiont_bundle_manifest

pytestmark = pytest.mark.slow


def _eye() -> dict[str, float]:
    client = pybullet.connect(pybullet.DIRECT)
    try:
        pybullet.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=client)
        pybullet.loadURDF("plane.urdf", physicsClientId=client)
        build_environment(client, environment_recipe("vision-nursery-v1"))
        return ANTHROPOMORPHIC_V6_VISION.apparatus_factory(client).sample_receptors()
    finally:
        pybullet.disconnect(client)


def test_visual_samples_are_deterministic_bounded_and_contrasted() -> None:
    first, second = _eye(), _eye()
    assert first == second
    visual = [value for key, value in first.items() if int(key.removeprefix("rec.")) >= 107]
    assert len(visual) == 144
    assert all(0.0 <= value <= 1.0 for value in visual)
    assert max(visual) - min(visual) > 0.5  # the nursery exposes luminance structure


def test_engine_runs_vision_body_in_nursery(tmp_path: Path) -> None:
    causes: list[str] = []
    bundle = tmp_path / "o.symbiont"
    run(
        headless=True,
        ticks=3,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=True,
        fresh_body=True,
        body_kind="anthropomorphic-v6-vision",
        environment="vision-nursery-v1",
        symbiont_file=bundle,
        body_file=tmp_path / "b.json",
        telemetry_file=tmp_path / "t",
        termination_callback=causes.append,
    )
    manifest = read_symbiont_bundle_manifest(bundle)
    assert causes == ["budget_exhausted"]
    assert manifest["body_kind"] == "anthropomorphic-v6-vision"
    assert manifest["receptor_count"] == 251
