"""Evaluator-only parent/child population lifecycle study for Milestone I."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json
from dataclasses import replace
from importlib import resources
from symbiont.cognition.genome import GenomeCodec
from symbiont.core.birth_authority import HabitatBirthAuthority
from symbiont.core.reproduction import ReproductivePressure
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.metabolism import MetabolicLedger

@dataclass(frozen=True, slots=True)
class RuntimePopulationStudy:
    parent_id: str
    child_id: str
    child_died: bool
    live_after_death: int
    released_budget: float
    duplicate_release_prevented: bool
    capacity_blocked_birth: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

def run_runtime_population_study() -> RuntimePopulationStudy:
    payload = json.loads(resources.files("symbiont.cognition").joinpath("defaults/base-genome.json").read_text())
    genome = replace(GenomeCodec().load(payload), kernel_compatibility=">=0.79")
    authority = HabitatBirthAuthority(habitat_id="population-study", capacity=2, resource_budget=2.0)
    zero = {kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    parent = OrganismRuntime(organism_id="parent", genome=genome, birth_authority=authority,
                             reproductive_pressure=ReproductivePressure(threshold_ticks=1),
                             metabolism=MetabolicLedger(replenishment=zero), explicit_metabolism=True,
                             bootstrap_semantic_senses=False, discover_senses=False)
    parent.observe_reproductive_pressure(adaptive=True, capacity_exhausted=True, blocked_growth=True)
    child = parent.materialize_clonal_bud()
    if child is None:
        raise RuntimeError("population study could not materialize child")
    parent.observe_reproductive_pressure(adaptive=True, capacity_exhausted=True, blocked_growth=True)
    capacity_blocked_birth = parent.materialize_clonal_bud() is None
    child.metabolism.charge("maintenance", 2.0)
    result = child.tick()
    child_died = result.physiology is not None and result.physiology.state.value == "dead"
    released_budget = authority.resource_budget
    # A second tick is rejected before any second release can occur.
    duplicate_release_prevented = False
    try:
        child.tick()
    except RuntimeError:
        duplicate_release_prevented = True
    return RuntimePopulationStudy(parent.organism_id, child.organism_id, child_died,
                                  len(authority.live_ids), released_budget,
                                  duplicate_release_prevented, capacity_blocked_birth)

__all__ = ["RuntimePopulationStudy", "run_runtime_population_study"]
