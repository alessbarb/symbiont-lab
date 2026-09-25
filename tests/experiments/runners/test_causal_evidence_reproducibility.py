from __future__ import annotations

from pathlib import Path

import pytest

from symbiont_lab.cli.main import run_reproduce
from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.experiments.manifest import RunManifest
from symbiont_lab.experiments.runner import ExperimentRunner


def test_causal_evidence_toml_manifest_and_reproduction(tmp_path: Path) -> None:
    spec_path = tmp_path / "causal_evidence.toml"
    spec_path.write_text(
        """schema_version = 1

[experiment]
id = "test.evidence.causal-budget"
title = "Causal evidence reproducibility"
protocol = "evidence.causal-budget"
protocol_version = 1

[world]
hosts = 8
steps = 70
threat_rate = 0.06
poison_fraction = 0.08
heterogeneity = 0.12

[design]
seeds = [17, 23]

[evidence]
budgets_per_1000 = [15.0]
exploration_fractions = [0.0, 0.10]
sensor_noise = 0.18
""",
        encoding="utf-8",
    )

    spec = load_experiment_file(spec_path)
    base_dir = tmp_path / ".symbiont"
    result, manifest, run_dir = ExperimentRunner(base_dir=base_dir).run(spec)

    assert manifest.protocol == "evidence.causal-budget"
    assert manifest.world_digest == result.world_digest
    assert len(manifest.world_digest) == 64
    assert manifest.metrics["result"]["sensor_noise"] == 0.18
    assert manifest.metrics["result"]["paired_vs_random"]

    manifest_file = run_dir / "manifest.json"
    assert RunManifest.load(manifest_file).world_digest == result.world_digest
    assert run_reproduce(manifest_file, base_dir=base_dir) == 0


pytestmark = pytest.mark.experiment_contract
