"""Experience & World Gates H and I at engine level (ADR-0009, ADR-0010, ADR-0042).

Gate H: resuming the same immutable State X (organism + body) with the same
seed and rates reproduces the causal organism state exactly.
Gate I: observer density (observation every tick vs. almost never) does not
change that causal state.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("pybullet")

from symbiont_lab.physics3d.engine import run
from symbiont_lab.physics3d.persistence import read_symbiont_bundle_runtime

pytestmark = pytest.mark.slow

TICKS = 24


# The vision body in the moving-source nursery adds TinyRenderer sampling and
# a kinematic source as new causal inputs (Vision Acquisition v1 §2).
CONFIGS = {
    "v6-flat": {"body_kind": "anthropomorphic-v6", "environment": None},
    "vision-d1": {"body_kind": "anthropomorphic-v6-vision", "environment": "vision-nursery-d1-v1"},
}


@pytest.fixture(scope="module", params=sorted(CONFIGS))
def state_x(request, tmp_path_factory) -> tuple[Path, Path, dict]:
    config = CONFIGS[request.param]
    root = tmp_path_factory.mktemp("x")
    bundle, body = root / "x.symbiont", root / "x.json"
    run(
        headless=True,
        ticks=4,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=True,
        fresh_body=True,
        symbiont_file=bundle,
        body_file=body,
        telemetry_file=root / "t",
        **config,
    )
    return bundle, body, config


def _resume(state_x: tuple[Path, Path, dict], root: Path, **kwargs) -> dict:
    root.mkdir()
    bundle, body = root / "o.symbiont", root / "b.json"
    shutil.copy(state_x[0], bundle)
    shutil.copy(state_x[1], body)
    run(
        headless=True,
        ticks=TICKS,
        seed=7,
        show_monitor=False,
        enable_slm=False,
        symbiont_file=bundle,
        body_file=body,
        telemetry_file=root / "t",
        **state_x[2],
        **kwargs,
    )
    payload = read_symbiont_bundle_runtime(bundle)
    assert int(payload["saved_at_tick"]) > TICKS
    return payload


def test_gate_h_same_state_x_reproduces_causal_state(state_x, tmp_path) -> None:
    first = _resume(state_x, tmp_path / "a")
    second = _resume(state_x, tmp_path / "b")
    assert first == second


def test_gate_i_observer_density_does_not_change_causal_state(state_x, tmp_path) -> None:
    dense = _resume(state_x, tmp_path / "dense", observation_hz=24)
    sparse = _resume(state_x, tmp_path / "sparse", observation_hz=1)
    assert dense == sparse
