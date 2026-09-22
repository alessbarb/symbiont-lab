from __future__ import annotations

import json

from symbiont_lab.kernel_characterization.config import BASELINE_KERNEL, KernelVariant
from symbiont_lab.kernel_characterization.runner import run_k1, run_k2, run_k3, run_k4_k5, write_run


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


def test_k1_probe_is_capacity_sensitive_and_frontier_is_variant_level():
    raw, summary, frontier = run_k1(
        [KernelVariant(max_nodes=value) for value in (64, 192, 512)],
        seeds=(101,),
        phase_ticks=2,
    )
    errors = {row["max_nodes"]: row["prediction_error"] for row in raw}
    assert errors[64] > errors[192] > errors[512]
    assert all("seed" not in row for row in frontier)
    assert summary["variants"][1]["max_nodes"] == 192


def test_write_run_contains_reproduction_artifacts(tmp_path):
    run_dir = write_run(tmp_path, [KernelVariant(max_nodes=64)], (101,), 1)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["protocol_version"] == 1
    assert manifest["kernel_baseline"]["max_nodes"] == 192
    assert manifest["genome"]["kind"] == "synthetic_capacity_probe"
    assert (run_dir / "raw.jsonl").exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "pareto.json").exists()


def test_k2_varies_edges_without_changing_canonical_nodes():
    raw, summary = run_k2(
        [KernelVariant(max_nodes=192, max_edges=value) for value in (384, 1536)],
        seeds=(101,),
        phase_ticks=2,
    )
    assert {row["max_edges"] for row in raw} == {384, 1536}
    assert [row["active_lanes"] for row in raw] == [187, 187]
    assert [row["edges_used"] for row in raw] == [384, 1536]
    assert summary["protocol"] == "K2"


def test_k3_varies_concept_ceiling():
    raw, summary = run_k3(
        [KernelVariant(max_nodes=192, max_concepts=value) for value in (8, 32, 64)],
        seeds=(101,),
        phase_ticks=2,
    )
    assert [row["concepts_used"] for row in raw] == [8, 32, 64]
    assert raw[0]["prediction_error"] > raw[-1]["prediction_error"]
    assert summary["protocol"] == "K3"


def test_k4_and_k5_exercise_structural_limits():
    k4_raw, k4_summary = run_k4_k5(
        [KernelVariant(max_nodes=192, max_structural_mutations_per_consolidation=value) for value in (1, 8)],
        seeds=(101,),
        dimension="K4",
    )
    k5_raw, k5_summary = run_k4_k5(
        [KernelVariant(max_nodes=192, max_tentative_edges=value) for value in (16, 128)],
        seeds=(101,),
        dimension="K5",
    )
    assert k4_summary["protocol"] == "K4"
    assert k5_summary["protocol"] == "K5"
    assert k4_raw[0]["accepted_mutations"] < k4_raw[1]["accepted_mutations"]
    assert k5_raw[0]["accepted_mutations"] <= k5_raw[1]["accepted_mutations"]
