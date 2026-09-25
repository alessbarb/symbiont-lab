from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .spec import ExperimentSpec, spec_from_payload


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
        "ablation": {"horizon_ticks"},
        "adaptation": {"horizon_ticks"},
        "output": {"save_trace", "save_summary"},
    }
    for block_name in (
        "attention",
        "evidence",
        "heritage",
        "campaign",
        "ablation",
        "adaptation",
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
