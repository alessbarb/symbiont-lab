"""Explicit migration from the historical cognition Genome v1 to Genome v2."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
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
            "eligibility_decay": float(plasticity["eligibility_decay"]),
            "structural_plasticity": {
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
        },
        "evolvability": {
            "development_mutation_scale": sigma,
            "plasticity_mutation_scale": sigma,
            "regulation_mutation_scale": sigma,
            "sensorimotor_mutation_scale": sigma,
            "structure_mutation_scale": sigma,
            "recombination_linkage": 0.5,
        },
    }
    # Historical MotorGenes intentionally have no target in Genome v2. The
    # embodiment migration reconstructs its own actuator surface.
    return v2



def apply_legacy_heritable_payload(
    genome: Genome,
    payload: Mapping[str, object],
    *,
    kernel_limits: object,
) -> Genome:
    """Project historical HeritableGenome state into Genome v2 once.

    Only loci that still have a causal v2 meaning are migrated. Removed loci
    are deliberately not preserved as dead configuration.
    """
    genome_id = payload.get("genome_id")
    raw_loci = payload.get("loci", ())
    identity = payload.get("identity")
    if not isinstance(genome_id, str) or not isinstance(raw_loci, (list, tuple)):
        raise ValueError("malformed legacy HeritableGenome payload")

    loci: list[tuple[str, float]] = []
    seen: set[str] = set()
    allowed = {
        "initial_concepts",
        "soft_node_budget",
        "soft_edge_budget",
        "learning_rate",
        "forgetting_rate",
    }
    for item in raw_loci:
        if (
            not isinstance(item, (list, tuple))
            or len(item) != 2
            or not isinstance(item[0], str)
            or isinstance(item[1], bool)
            or not isinstance(item[1], (int, float))
        ):
            raise ValueError("malformed legacy HeritableGenome locus")
        key = item[0]
        if key not in allowed or key in seen:
            raise ValueError("unknown or duplicate legacy HeritableGenome locus")
        seen.add(key)
        loci.append((key, float(item[1])))

    legacy_material = {
        "genome_id": genome_id,
        "loci": tuple(loci),
    }
    legacy_identity = "genome_" + hashlib.sha256(
        json.dumps(
            legacy_material,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    if identity not in (None, legacy_identity):
        raise ValueError("legacy HeritableGenome identity mismatch")

    values = dict(loci)
    development = genome.development
    node_ceiling = min(
        int(kernel_limits.max_nodes),
        max(1, round(values.get("soft_node_budget", development.soft_node_budget))),
    )
    edge_ceiling = min(
        int(kernel_limits.max_edges),
        max(1, round(values.get("soft_edge_budget", development.soft_edge_budget))),
    )
    development = replace(
        development,
        soft_node_budget=node_ceiling,
        soft_edge_budget=edge_ceiling,
        sense_node_budget=min(development.sense_node_budget, node_ceiling),
    )

    plasticity = genome.plasticity
    if "learning_rate" in values:
        spec = plasticity.learning_rate
        baseline = max(spec.minimum, min(spec.maximum, values["learning_rate"]))
        plasticity = replace(
            plasticity,
            learning_rate=replace(spec, baseline=baseline),
        )

    return replace(
        genome,
        genome_id=legacy_identity,
        development=development,
        plasticity=plasticity,
    )

def migrate_v1_genome(payload: Mapping[str, object]) -> Genome:
    return GenomeCodec().load(migrate_v1_payload(payload))


__all__ = ["apply_legacy_heritable_payload", "migrate_v1_genome", "migrate_v1_payload"]
