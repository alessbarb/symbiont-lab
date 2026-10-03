"""Preregistered W03 run (docs/design/symbiont-world-v2.md §11):

¿8 founders sin mutación producen diferenciación ecológica (nichos)
puramente ontogenética/social?

Ground truth: genesis_v2.build_ground_truth_v2() -- two regions (north
q<4, south q>=4) with different ResourceLaw parameters for two of the
four resources; everything else identical to Genesis v1.

Preregistered metric (frozen before running): for each founder, its
dominant_resource = the resource_id with the highest INTAKE count in its
action history. Since pools are per-cell, not per-region (v2 §3's honest
correction), same-region founders share the *law* but never the *pool* --
so any within-region agreement or disagreement in dominant_resource is
informative rather than trivial.

Preregistered decision rule: reject H0 ("no differentiation beyond direct
region-law response") only if founders WITHIN THE SAME region disagree on
dominant_resource. Cross-region differences are the expected, uninteresting
case (the law itself differs) -- they say nothing about ontogenetic/social
differentiation. Within-region disagreement would be the actual candidate
signal W03 is looking for.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from symbiont_lab.world.genesis_v2 import build_ground_truth_v2, region_of
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
from symbiont_world.genesis import GroundTruth
from symbiont_world.laws import HazardLaw
from symbiont_world.topology import HexTopology

WORLD_SEED = 101
FOUNDERS = 8
TICKS = 300


def _zero_density_coupling(ground_truth: GroundTruth) -> GroundTruth:
    """Control ablation: same everything, but hazard exposure no longer
    depends on local density. Isolates whether density-coupled hazard is
    the mechanism behind within-region disagreement."""
    flat_hazards = {
        hazard_id: HazardLaw(base_probability=law.base_probability, density_coupling=0.0)
        for hazard_id, law in ground_truth.hazards.items()
    }
    return GroundTruth(
        fields=ground_truth.fields,
        resources=ground_truth.resources,
        hazards=flat_hazards,
        region_of=ground_truth.region_of,
        regional_resources=ground_truth.regional_resources,
        regional_hazards=ground_truth.regional_hazards,
    )


def dominant_resource(action_counts: dict) -> str | None:
    intake_counts = Counter()
    for action_id, count in action_counts.items():
        if action_id.startswith("intake:"):
            intake_counts[action_id.removeprefix("intake:")] += count
    if not intake_counts:
        return None
    return intake_counts.most_common(1)[0][0]


def w03(*, ground_truth: GroundTruth | None = None, id_prefix: str = "w03-founder") -> dict:
    topology = HexTopology(width=8, height=8)
    ground_truth = ground_truth if ground_truth is not None else build_ground_truth_v2()
    cells = founder_placement(WORLD_SEED, topology, FOUNDERS)
    organism_ids = tuple(f"{id_prefix}-{i}" for i in range(FOUNDERS))

    population = PopulationGenesisRuntime(
        organism_ids=organism_ids,
        world_seed=WORLD_SEED,
        ground_truth=ground_truth,
        topology=topology,
        start_cells=cells,
    )
    records = population.run(TICKS)

    per_founder = {}
    for organism_id in organism_ids:
        action_counts = Counter()
        for record in records:
            if organism_id in record.per_organism:
                action_counts[record.per_organism[organism_id].action.action_id] += 1
        cell = population.state.bodies[organism_id].occupied_cell
        per_founder[organism_id] = {
            "cell": [cell.q, cell.r],
            "region": region_of(cell),
            "action_counts": dict(action_counts),
            "dominant_resource": dominant_resource(action_counts),
            "alive": population.is_alive(organism_id),
        }

    by_region: dict[str, set] = {}
    for organism_id, data in per_founder.items():
        by_region.setdefault(data["region"], set()).add(data["dominant_resource"])

    within_region_disagreement = {
        region: sorted(resources) for region, resources in by_region.items() if len(resources) > 1
    }
    reject_h0 = len(within_region_disagreement) > 0

    return {
        "per_founder": per_founder,
        "by_region_dominant_resources": {region: sorted(r) for region, r in by_region.items()},
        "within_region_disagreement": within_region_disagreement,
        "reject_h0": reject_h0,
    }


def w03_with_control() -> dict:
    treatment = w03(id_prefix="w03-treatment")
    control_truth = _zero_density_coupling(build_ground_truth_v2())
    control = w03(ground_truth=control_truth, id_prefix="w03-control")
    return {
        "treatment": treatment,
        "control_zero_density_coupling": control,
        "mechanism_supported": treatment["reject_h0"] and not control["reject_h0"],
    }


if __name__ == "__main__":
    result = w03_with_control()
    print(json.dumps(result, indent=2))
    Path(__file__).with_name("w03_results.json").write_text(json.dumps(result, indent=2))
