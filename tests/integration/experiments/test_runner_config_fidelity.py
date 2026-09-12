from __future__ import annotations

import json
from pathlib import Path

import pytest

from symbiont_lab.experiments.spec import spec_from_payload
from symbiont_lab.experiments.runner import ExperimentRunner


def test_generic_fallback_protocol_uses_declared_seeds_not_defaults(tmp_path: Path) -> None:
    """A protocol reached only through the generic fallback branch (evidence.replicated
    has no `seed` kwarg, only `seeds`) must run on the spec's declared design, not
    silently fall back to the protocol's own hardcoded defaults."""
    spec = spec_from_payload(
        {
            "id": "test.fidelity",
            "protocol": "evidence.replicated",
            "hosts": 20,
            "steps": 30,
            "seeds": [1, 2],
        }
    )
    runner = ExperimentRunner(base_dir=tmp_path / ".symbiont")
    result, manifest, run_dir = runner.run(spec)

    raw_metrics = json.loads((run_dir / "metrics.json").read_text())
    assert raw_metrics["seeds"] == [1, 2]
    assert manifest.config["seeds"] == [1, 2]


def test_protocol_with_unsuppliable_required_params_fails_loudly(tmp_path: Path) -> None:
    """campaign.comparative requires base_spec/parameter/baseline_value/variant_value,
    which a declarative TOML spec cannot express. This must raise a clear error
    instead of silently running with mismatched/default arguments."""
    spec = spec_from_payload({"id": "test.unsupported", "protocol": "campaign.comparative"})
    runner = ExperimentRunner(base_dir=tmp_path / ".symbiont")

    with pytest.raises(ValueError, match="campaign.comparative"):
        runner.run(spec)
