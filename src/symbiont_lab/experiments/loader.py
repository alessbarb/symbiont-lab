from __future__ import annotations

from pathlib import Path
import tomllib
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
    flat_payload: dict[str, Any] = {}

    schema_version = data.get("schema_version", 1)
    flat_payload["schema_version"] = schema_version

    exp_block = data.get("experiment", {})
    if exp_block:
        flat_payload["experiment_id"] = exp_block.get("id", "custom")
        flat_payload["title"] = exp_block.get("title", "Untitled")
        flat_payload["protocol"] = exp_block.get("protocol", "simulate")
        flat_payload["protocol_version"] = exp_block.get("protocol_version", 1)
        flat_payload["hypothesis"] = exp_block.get("hypothesis", "")
        flat_payload["success_criteria"] = exp_block.get("success_criteria", "")
        flat_payload["notes"] = exp_block.get("notes", "")

    world_block = data.get("world", {})
    for k, v in world_block.items():
        flat_payload[k] = v

    design_block = data.get("design", {})
    if "seeds" in design_block:
        flat_payload["seeds"] = design_block["seeds"]
    elif "seed" in design_block:
        flat_payload["seed"] = design_block["seed"]

    # Extra parameters for protocols (attention, evidence, heritage, etc.)
    extra = {}
    for block_name in ("attention", "evidence", "heritage", "campaign", "output"):
        if block_name in data:
            extra[block_name] = data[block_name]
    flat_payload["extra_params"] = extra

    return spec_from_payload(flat_payload)
