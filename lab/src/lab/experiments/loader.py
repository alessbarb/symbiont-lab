from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from lab.experiments.spec import ExperimentSpec, spec_from_payload


def load_experiment_file(file_path: str | Path) -> ExperimentSpec:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Experiment spec file not found: {file_path}")

    with path.open("rb") as f:
        data = tomllib.load(f)

    return load_experiment_dict(data)


def load_experiment_dict(data: dict[str, Any]) -> ExperimentSpec:
    if not isinstance(data, dict):
        raise ValueError("experiment document must be an object")
    allowed = {
        "schema_version",
        "experiment",
        "world",
        "design",
        "attention",
        "evidence",
        "heritage",
        "campaign",
        "ablation",
        "adaptation",
        "consolidation",
        "body",
        "corpora",
        "vision",
        "transfer",
        "establishment",
        "retention",
        "output",
    }
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"unknown experiment sections: {sorted(unknown)}")
    if not isinstance(data.get("experiment"), dict):
        raise ValueError("experiment section is required")
    _reject_unknown_keys(
        data["experiment"],
        {"id", "title", "protocol", "protocol_version", "hypothesis", "success_criteria", "notes"},
        "experiment",
    )
    flat_payload: dict[str, Any] = {}

    schema_version = data.get("schema_version", 1)
    flat_payload["schema_version"] = schema_version

    exp_block = data["experiment"]
    if exp_block:
        flat_payload["experiment_id"] = exp_block.get("id", "custom")
        flat_payload["title"] = exp_block.get("title", "Untitled")
        flat_payload["protocol"] = exp_block.get("protocol", "simulate")
        flat_payload["protocol_version"] = exp_block.get("protocol_version", 1)
        flat_payload["hypothesis"] = exp_block.get("hypothesis", "")
        flat_payload["success_criteria"] = exp_block.get("success_criteria", "")
        flat_payload["notes"] = exp_block.get("notes", "")

    world_block = data.get("world", {})
    if not isinstance(world_block, dict):
        raise ValueError("world section must be an object")
    _reject_unknown_keys(
        world_block,
        {
            "hosts",
            "steps",
            "seed",
            "seeds",
            "threat_rate",
            "poison_fraction",
            "heterogeneity",
            "drift_step",
            "drift_fraction",
            "drift_magnitude",
            "delay",
        },
        "world",
    )
    for k, v in world_block.items():
        flat_payload[k] = v

    design_block = data.get("design", {})
    if not isinstance(design_block, dict):
        raise ValueError("design section must be an object")
    _reject_unknown_keys(design_block, {"seed", "seeds"}, "design")
    if "seeds" in design_block:
        flat_payload["seeds"] = design_block["seeds"]
    elif "seed" in design_block:
        flat_payload["seed"] = design_block["seed"]

    # Extra parameters for protocols (attention, evidence, heritage, etc.)
    extra = {}
    extension_keys = {
        "attention": {
            "budget_per_1000",
            "budgets_per_1000",
            "curve_budgets_per_1000",
            "reference_strategy",
        },
        "evidence": {
            "budget",
            "budget_per_1000",
            "budgets_per_1000",
            "exploration_fractions",
            "noise_levels",
            "sensor_noise",
            "reference_strategy",
        },
        "heritage": {
            "source_threat_rate",
            "target_threat_rates",
            "target_offset",
            "heritage_limit",
        },
        # Long-running discovery protocols keep their bounded campaign
        # controls in an extension block rather than overloading ``world``.
        "campaign": {
            "stages",
            "population_sizes",
            "multigeneration_generations",
            "replay_windows",
            "deferred_stages",
            "deferred_reason",
        },
        "ablation": {
            "horizon_ticks",
            "inert_actuator_count",
            "factorized_effects",
            "reconciliation",
            "membership",
            "binding_invalidation",
            "arm",
            "break_tick",
            "arms",
        },
        "adaptation": {"horizon_ticks"},
        "consolidation": {
            "min_support",
            "min_controllability",
            "min_agency",
            "stability_ticks",
            "max_wait_ticks",
            "min_age_ticks",
            "horizons",
            "primary_horizon",
        },
        "body": {"actuator_count", "receptors_per_actuator", "drifting_receptor_count"},
        # Private Model Learnability v1 §8: frozen checkpoint inputs.
        "corpora": {"c1", "c2"},
        # Visual Acquisition v1 §5-§6: horizons, late window, and whether
        # predictive performance may be computed (only at a frozen H).
        "vision": {
            "late_window",
            "horizons",
            "report_performance",
            "sample_every",
            "environment",
        },
        # Re-embodiment Functional Transfer v1: frozen design and decision
        # constants, checked against the study module by a contract test.
        "transfer": {
            "development_seeds",
            "arms",
            "relations",
            "shared_pairs",
            "sham_shared_pairs",
            "swap_unrelated_source_on_alternate_seeds",
            "naive_arm_is_restored",
            "private_model_bridge",
            "actuators",
            "development_ticks_rule",
            "measurement_ticks_rule",
            "max_body_difficulty_spread",
            "primary_metric",
            "min_seeds_improved",
            "min_median_paired_reduction",
            "practical_null_margin",
            "max_activity_rate_ratio",
            "max_contaminated_seeds",
        },
        # Competence Establishment Evidence v1: frozen design and decision
        # constants, checked against the study module by a contract test.
        "establishment": {
            "selection_seeds",
            "supports",
            "consistencies",
            "current_gate",
            "actuators",
            "horizon",
            "stable_window",
            "primary_metric",
            "selection_rule",
            "min_seeds_improved",
            "min_median_paired_reduction",
        },
        # Metabolic Retention Price Calibration v1: frozen design and decision
        # constants, checked against the study module by a contract test.
        "retention": {
            "pilot_seeds",
            "selection_seeds",
            "baseline_prices",
            "node_prices",
            "dormancy_factors",
            "current_prices",
            "horizon",
            "body_energy",
            "support_rule",
            "coherence_rule",
            "selection_rule",
            "min_alive_seeds",
            "min_seeds_not_worse",
            "min_t_stable_reduction",
            "max_retained_growth",
        },
        "output": {"save_trace", "save_summary"},
    }
    for block_name in (
        "attention",
        "evidence",
        "heritage",
        "campaign",
        "ablation",
        "adaptation",
        "consolidation",
        "body",
        "corpora",
        "vision",
        "transfer",
        "establishment",
        "retention",
        "output",
    ):
        if block_name in data:
            if not isinstance(data[block_name], dict):
                raise ValueError(f"{block_name} section must be an object")
            _reject_unknown_keys(data[block_name], extension_keys[block_name], block_name)
            extra[block_name] = data[block_name]
    flat_payload["extra_params"] = extra

    return spec_from_payload(flat_payload)


def _reject_unknown_keys(block: dict[str, Any], allowed: set[str], name: str) -> None:
    unknown = set(block) - allowed
    if unknown:
        raise ValueError(f"unknown keys in {name} section: {sorted(unknown)}")
