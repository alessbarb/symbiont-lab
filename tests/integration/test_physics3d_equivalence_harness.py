"""Simulation Throughput v1 §2: the equivalence harness is deterministic and
detects a change in the organism's causal state."""

from __future__ import annotations

from pathlib import Path

import pytest

from symbiont.modeling.runtime import ModeledOrganismRuntime
from symbiont_lab.physics3d.engine import run
from symbiont_lab.physics3d.equivalence import equivalent, first_divergence, run_digests


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


@pytest.mark.slow
def test_harness_is_deterministic_and_detects_a_causal_change(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    first = run_digests(snapshot, 4, body_kind="anthropomorphic-v6")
    second = run_digests(snapshot, 4, body_kind="anthropomorphic-v6")
    assert len(first["per_tick"]) >= 4
    assert equivalent(first, second)

    original = ModeledOrganismRuntime.record_experience

    def perturbed(self, record, **kwargs):  # drop every experience: a causal change
        return None

    monkeypatch.setattr(ModeledOrganismRuntime, "record_experience", perturbed)
    changed = run_digests(snapshot, 4, body_kind="anthropomorphic-v6")
    monkeypatch.setattr(ModeledOrganismRuntime, "record_experience", original)
    assert not equivalent(first, changed)
    assert first_divergence(first, changed) is not None
