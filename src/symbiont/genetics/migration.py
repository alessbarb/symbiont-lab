"""Explicit migration from the historical cognition Genome v1 to Genome v2."""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .genome import Genome, GenomeCodec


def migrate_v1_payload(payload: Mapping[str, object]) -> dict[str, Any]:
    if payload.get("schema_version") != 1:
        raise ValueError("migrate_v1_payload requires schema_version == 1")

    development = payload.get("development")
    plasticity = payload.get("plasticity")
    structure = payload.get("structure")
    mutation = payload.get("mutation_policy")
    if not all(isinstance(value, Mapping) for value in (development, plasticity, structure, mutation)):
        raise ValueError("malformed Genome v1 payload")

    lr = plasticity["learning_rate"]
    fr = plasticity["forgetting_rate"]
    if not isinstance(lr, Mapping) or not isinstance(fr, Mapping):
        raise ValueError("malformed Genome v1 plasticity ranges")

    grow = float(structure["grow_threshold"])
    prune = float(structure["prune_threshold"])
    sigma = float(mutation["continuous_sigma"])

    v2: dict[str, Any] = {
        "schema_version": 2,
        "genome_id": str(payload["genome_id"]).replace("genome_", "genome_v2_", 1),
        "parent_ids": [str(payload["genome_id"])],
        "kernel_compatibility": ">=0.80,<0.90",
        "development": {
            "soft_node_budget": int(development["soft_node_budget"]),
            "soft_edge_budget": int(development["soft_edge_budget"]),
            "sense_node_budget": int(
                development.get(
                    "sense_node_budget",
                    min(32, int(development["soft_node_budget"])),
                )
            ),
            "capacity_growth_sensitivity": 0.5,
            "consolidation_interval_ticks": int(development["consolidation_interval_ticks"]),
        },
        "plasticity": {
            "learning_rate": {
                "baseline": float(lr["initial"]),
                "min": float(lr["min"]),
                "max": float(lr["max"]),
                "adaptation_rate": 0.002,
            },
            "forgetting_rate": {
                "baseline": float(fr["initial"]),
                "min": float(fr["min"]),
                "max": float(fr["max"]),
                "adaptation_rate": 0.0001,
            },
            "eligibility_decay": float(plasticity["eligibility_decay"]),
            "structural_plasticity": {
                "baseline": 0.5,
                "min": 0.05,
                "max": 1.0,
                "adaptation_rate": 0.01,
            },
            "consolidation_sensitivity": {
                "baseline": 0.5,
                "min": 0.05,
                "max": 1.0,
                "adaptation_rate": 0.01,
            },
        },
        "regulation": {
            "uncertainty_gain": 0.5,
            "novelty_gain": 0.4,
            "prediction_error_gain": 0.5,
            "controllability_loss_gain": 0.5,
            "embodiment_mismatch_gain": 0.7,
            "regulation_smoothing": 0.1,
            "regulation_decay": 0.02,
        },
        "sensorimotor": {
            "spontaneous_activity_baseline": 0.1,
            "uncertainty_exploration_gain": 0.5,
            "prediction_error_exploration_gain": 0.5,
            "exploration_habituation": 0.01,
            "contingency_sensitivity": 0.5,
            "contingency_window_ticks": 8,
            "controllability_sensitivity": 0.5,
            "body_schema_adaptation_rate": 0.1,
            "reacclimation_sensitivity": 0.7,
        },
        "structure": {
            "growth_threshold": {
                "baseline": grow,
                "min": 0.0,
                "max": max(grow, min(1.0, grow + 0.4)),
                "adaptation_rate": 0.01,
            },
            "pruning_threshold": {
                "baseline": prune,
                "min": 0.0,
                "max": max(prune, min(1.0, prune + 0.2)),
                "adaptation_rate": 0.005,
            },
            "minimum_support": int(structure["minimum_support"]),
            "tentative_lifetime_ticks": int(structure["tentative_lifetime_ticks"]),
            "complexity_pressure": {
                "baseline": 0.5,
                "min": 0.0,
                "max": 1.0,
                "adaptation_rate": 0.01,
            },
        },
        "evolvability": {
            "development_mutation_scale": sigma,
            "plasticity_mutation_scale": sigma,
            "regulation_mutation_scale": sigma,
            "sensorimotor_mutation_scale": sigma,
            "structure_mutation_scale": sigma,
            "recombination_linkage": 0.5,
        },
        "inheritance": {
            "epigenetic_decay": 0.2,
            "max_epigenetic_marks": 8,
        },
    }
    # Historical MotorGenes intentionally have no target in Genome v2. The
    # embodiment migration reconstructs its own actuator surface.
    return v2


def migrate_v1_genome(payload: Mapping[str, object]) -> Genome:
    return GenomeCodec().load(migrate_v1_payload(payload))


__all__ = ["migrate_v1_genome", "migrate_v1_payload"]
