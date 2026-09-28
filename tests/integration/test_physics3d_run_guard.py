"""ADR-0008 engine termination: the Lab guard ends a run; it never alters it."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pybullet")

from symbiont_lab.physics3d.engine import run
from symbiont_lab.physics3d.persistence import read_symbiont_bundle_runtime

pytestmark = pytest.mark.slow


def _run(tmp_path: Path, name: str, **kwargs) -> tuple[list[str], dict]:
    causes: list[str] = []
    symbiont_file = tmp_path / f"{name}.symbiont"
    run(
        headless=True,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=True,
        fresh_body=True,
        symbiont_file=symbiont_file,
        body_file=tmp_path / f"{name}.body.json",
        telemetry_file=tmp_path / f"{name}.telemetry",
        termination_callback=causes.append,
        **kwargs,
    )
    return causes, read_symbiont_bundle_runtime(symbiont_file)


def test_budget_exit_is_reported_once(tmp_path: Path) -> None:
    causes, payload = _run(tmp_path, "budget", ticks=3)
    assert causes == ["budget_exhausted"]
    assert int(payload["saved_at_tick"]) == 3


def test_guard_ends_run_with_coherent_dormant_checkpoint(tmp_path: Path) -> None:
    seen: list[tuple[object, object]] = []

    def guard(alive, vital_state):
        seen.append((alive, vital_state))
        return "guard:protected_recovery" if len(seen) == 2 else None

    causes, payload = _run(tmp_path, "guarded", ticks=10, run_guard=guard)
    assert causes == ["guard:protected_recovery"]
    # Only primitives cross the boundary; the organism object never does.
    assert all(isinstance(a, bool) and isinstance(v, str) for a, v in seen)
    assert int(payload["saved_at_tick"]) == 2
    assert payload["embodiment_lifecycle"]["state"] == "dormant"
