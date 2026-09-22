from __future__ import annotations

import json

from symbiont_lab.kernel_characterization.config import BASELINE_KERNEL, KernelVariant
from symbiont_lab.kernel_characterization.runner import run_k1, write_run


def test_variant_does_not_change_canonical_defaults():
    variant = KernelVariant(max_nodes=64)
    assert variant.limits().max_nodes == 64
    assert BASELINE_KERNEL.max_nodes == 192
    assert BASELINE_KERNEL.max_edges == 1536


def test_k1_is_deterministic_and_includes_control():
    variants = [KernelVariant(max_nodes=value) for value in (64, 192)]
    first = run_k1(variants, seeds=(101,), phase_ticks=2)
    second = run_k1(variants, seeds=(101,), phase_ticks=2)
    stable_fields = ("seed", "max_nodes", "prediction_error", "predictive_gain", "nodes_used", "concepts_used", "edges_used")
    assert [tuple(row.get(field) for field in stable_fields) for row in first[0]] == [
        tuple(row.get(field) for field in stable_fields) for row in second[0]
    ]
    assert {row["max_nodes"] for row in first[0]} == {64, 192}
    assert first[1]["protocol"] == "K1-A"


def test_write_run_contains_reproduction_artifacts(tmp_path):
    run_dir = write_run(tmp_path, [KernelVariant(max_nodes=64)], (101,), 1)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["protocol_version"] == 1
    assert manifest["kernel_baseline"]["max_nodes"] == 192
    assert manifest["genome"]["kind"] == "synthetic_capacity_probe"
    assert (run_dir / "raw.jsonl").exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "pareto.json").exists()
