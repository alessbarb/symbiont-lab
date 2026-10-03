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
    assert len(first["trace_per_tick"]) == 4
    assert equivalent(first, second), [
        (tick_a, {key for key in components_a if components_a[key] != components_b.get(key)})
        for (tick_a, components_a), (_, components_b) in zip(
            first["trace_components_per_tick"], second["trace_components_per_tick"]
        )
        if components_a != components_b
    ]

    original = ModeledOrganismRuntime.record_experience

    def perturbed(self, record, **kwargs):  # drop every experience: a causal change
        return None

    monkeypatch.setattr(ModeledOrganismRuntime, "record_experience", perturbed)
    changed = run_digests(snapshot, 4, body_kind="anthropomorphic-v6")
    monkeypatch.setattr(ModeledOrganismRuntime, "record_experience", original)
    assert not equivalent(first, changed)
    assert first_divergence(first, changed) is not None


def test_harness_detects_a_per_tick_trace_divergence(tmp_path):
    snapshot = _snapshot(tmp_path)
    baseline = run_digests(snapshot, 2, body_kind="anthropomorphic-v6")
    changed = dict(baseline)
    changed["trace_per_tick"] = list(baseline["trace_per_tick"])
    tick, digest = changed["trace_per_tick"][1]
    changed["trace_per_tick"][1] = (tick, f"{digest}-perturbed")

    assert first_divergence(baseline, changed) == tick
    assert not equivalent(baseline, changed)
