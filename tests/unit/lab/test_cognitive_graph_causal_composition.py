from __future__ import annotations

import pytest

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.experiments.runner import ExperimentRunner
from symbiont_lab.studies.learning.cognitive_graph_causal_composition import (
    run_cognitive_graph_causal_composition_study,
)


def test_cognitive_graph_protocol_is_deterministic_and_falsifies_full_claim():
    result = run_cognitive_graph_causal_composition_study(seeds=(101, 127, 149), ticks=200)
    replay = run_cognitive_graph_causal_composition_study(seeds=(101, 127, 149), ticks=200)

    assert result == replay
    assert result.replay_deterministic
    assert result.local_chain_discovery_rate == 1.0
    assert result.distant_composition_rate == 0.0
    assert result.intervention_discrimination_rate < 0.70
    assert result.contradiction_revision_rate == 0.0
    assert result.temporal_lag_discovery_rate == 1.0
    assert result.composed_discovery_rate == 1.0
    assert result.composed_context_reuse_rate == 1.0
    assert result.composed_revision_rate == 1.0
    assert result.context_reuse_rate == 1.0
    assert not result.full_capability_supported


def test_cognitive_graph_protocol_is_registered():
    protocol = get_protocol("learning.cognitive-graph-causal-composition")
    result = protocol(seeds=(101,), ticks=64)
    assert result.seeds == (101,)
    assert not result.full_capability_supported


def test_cognitive_graph_protocol_rejects_invalid_ticks():
    with pytest.raises(ValueError):
        run_cognitive_graph_causal_composition_study(seeds=(101,), ticks=31)


def test_declared_experiment_runs_through_runner(tmp_path):
    spec = load_experiment_file(
        "experiments/learning/cognitive-graph-causal-composition/experiment.toml"
    )
    result, _manifest, run_dir = ExperimentRunner(tmp_path).run(spec)
    assert result.full_capability_supported is False
    assert (run_dir / "summary.json").exists()
