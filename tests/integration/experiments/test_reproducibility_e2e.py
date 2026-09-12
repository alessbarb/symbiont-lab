from __future__ import annotations

import json
from pathlib import Path

from symbiont_lab.cli.main import run_reproduce
from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.experiments.manifest import RunManifest
from symbiont_lab.experiments.runner import ExperimentRunner


def test_experiment_run_and_bitwise_reproducibility_e2e(tmp_path: Path) -> None:
    """E2E test: TOML -> ExperimentRunner -> manifest.json -> run_reproduce -> verify bitwise identity."""
    spec_path = tmp_path / "test_experiment.toml"
    spec_path.write_text(
        """schema_version = 1

[experiment]
id = "test.reproducibility.e2e"
title = "E2E Reproducibility Test"
protocol = "simulate"
protocol_version = 1
hypothesis = "Simulations with identical seed produce identical world digests."

[world]
hosts = 12
steps = 40
seed = 42
threat_rate = 0.04
poison_fraction = 0.05
heterogeneity = 0.10

[output]
save_trace = false
save_summary = true
""",
        encoding="utf-8",
    )

    spec = load_experiment_file(spec_path)
    base_dir = tmp_path / ".symbiont"
    runner = ExperimentRunner(base_dir=base_dir)
    result, manifest, run_dir = runner.run(spec)

    manifest_file = run_dir / "manifest.json"
    assert manifest_file.is_file(), f"Manifest not generated at {manifest_file}"

    # Load and inspect manifest
    loaded_manifest = RunManifest.load(manifest_file)
    assert loaded_manifest.run_id == manifest.run_id
    assert loaded_manifest.world_digest != "na"
    assert len(loaded_manifest.world_digest) == 64

    # Run reproduction
    exit_code = run_reproduce(manifest_file)
    assert exit_code == 0

    # Ensure runs directory contains the reproduced run
    runs_dir = base_dir / "runs"
    run_subdirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    assert len(run_subdirs) == 2, f"Expected 2 runs, found: {run_subdirs}"

    # Verify both manifests have identical world_digest and identical metrics
    manifests = [RunManifest.load(d / "manifest.json") for d in run_subdirs]
    assert manifests[0].world_digest == manifests[1].world_digest
    m0_res = manifests[0].metrics["result"]
    m1_res = manifests[1].metrics["result"]
    assert m0_res["pathogen_events"] == m1_res["pathogen_events"]
    assert m0_res["benign_events"] == m1_res["benign_events"]
    assert m0_res["calibration_error"] == m1_res["calibration_error"]
