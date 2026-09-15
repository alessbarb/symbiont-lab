"""Evaluator-only runtime reproduction replay study for Milestone I."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, replace
from importlib import resources
from symbiont.cognition.genome import GenomeCodec
from symbiont.core.birth_authority import HabitatBirthAuthority
from symbiont.core.reproduction import ReproductivePressure
from symbiont.core.runtime import OrganismRuntime

@dataclass(frozen=True, slots=True)
class RuntimeReproductionStudy:
    parent_id: str
    child_id: str
    generation: int
    germinal_node_count: int
    replay_equal: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

def run_runtime_reproduction_study(*, ticks: int = 2) -> RuntimeReproductionStudy:
    if ticks < 1:
        raise ValueError("ticks must be positive")
    payload = json.loads(resources.files("symbiont.cognition").joinpath("defaults/base-genome.json").read_text())
    genome = replace(GenomeCodec().load(payload), kernel_compatibility=">=0.79")
    authority = HabitatBirthAuthority(habitat_id="runtime-study", capacity=2, resource_budget=2.0)
    parent = OrganismRuntime(
        organism_id="study-parent", genome=genome, birth_authority=authority,
        reproductive_pressure=ReproductivePressure(threshold_ticks=1),
        bootstrap_semantic_senses=False, discover_senses=False,
    )
    parent.observe_reproductive_pressure(adaptive=True, capacity_exhausted=True, blocked_growth=True)
    child = parent.materialize_clonal_bud()
    if child is None:
        raise RuntimeError("study could not materialize child")
    child.run(ticks)
    restored = OrganismRuntime.from_checkpoint(
        child.checkpoint(), bootstrap_semantic_senses=False, discover_senses=False,
        birth_authority=authority,
    )
    left = tuple(result.metabolism for result in child.run(ticks))
    right = tuple(result.metabolism for result in restored.run(ticks))
    return RuntimeReproductionStudy(parent.organism_id, child.organism_id, child.generation,
                                    len(child.cognitive_bridge.graph.nodes) if child.cognitive_bridge and child.cognitive_bridge.graph else 0,
                                    left == right)

__all__ = ["RuntimeReproductionStudy", "run_runtime_reproduction_study"]
