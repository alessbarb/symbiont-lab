"""Evaluator-only runtime reproduction replay study for Milestone I."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.birth_authority import HabitatBirthAuthority
from symbiont.core.runtime import OrganismRuntime

from symbiont import __version__ as symbiont_version
from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.limits import KernelLimits


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
    version = tuple(int(part) for part in (symbiont_version.split(".") + ["0", "0"])[:3])
    genome = load_base_genome(kernel_limits=KernelLimits(), running_version=version)
    authority = HabitatBirthAuthority(habitat_id="runtime-study", capacity=2)
    parent = OrganismRuntime(
        organism_id="study-parent",
        genome=genome,
        birth_authority=authority,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    parent.living_body_state.growth_progress = 1.0
    child = parent.materialize_clonal_bud()
    if child is None:
        raise RuntimeError("study could not materialize child")
    child.run(ticks)
    restored = OrganismRuntime.from_checkpoint(
        child.checkpoint(),
        bootstrap_semantic_senses=False,
        discover_senses=False,
        birth_authority=authority,
    )
    left = tuple(result.metabolism for result in child.run(ticks))
    right = tuple(result.metabolism for result in restored.run(ticks))
    return RuntimeReproductionStudy(
        parent.organism_id,
        child.organism_id,
        child.generation,
        len(child.cognitive_bridge.graph.nodes)
        if child.cognitive_bridge and child.cognitive_bridge.graph
        else 0,
        left == right,
    )


__all__ = ["RuntimeReproductionStudy", "run_runtime_reproduction_study"]
