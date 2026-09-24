"""Campaign-wide integrity gates for embodiment falsification v1.

These gates validate apparatus isolation. They do not score scientific H1/H0.
A failed gate invalidates interpretation of the corresponding campaign run.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import inspect
from typing import Sequence

from symbiont.genetics.genome import flatten_genes
from symbiont.genetics.germline import GermlineState
from symbiont.core.symbiont import Symbiont
from symbiont_lab.world.adapter import _construct_organism
from symbiont_lab.world.genesis_v1 import build_ground_truth


@dataclass(frozen=True, slots=True)
class EmbodimentIntegrityGates:
    clean_runtime_boundary: bool
    clean_actuation_boundary: bool
    symbiont_step_surface_clean: bool
    germline_surface_clean: bool
    genome_germline_present: bool
    no_world_identity_in_genome: bool

    @property
    def all_pass(self) -> bool:
        return all(asdict(self).values())

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["all_pass"] = self.all_pass
        return data


def run_embodiment_integrity_gates(
    *,
    organism_id: str = "integrity-subject",
    world_seed: int = 918273,
) -> EmbodimentIntegrityGates:
    """Run reusable architecture/non-interference gates.

    Stronger dynamic invariance gates (label/world paired replay) live in E8;
    these gates cover the common prerequisites shared by every E1-E8 result.
    """
    truth = build_ground_truth()
    rig = _construct_organism(
        organism_id=organism_id,
        world_id="integrity-world-display-label",
        world_seed=world_seed,
        organism_seed=world_seed + 1,
        ground_truth=truth,
        policy="cognitive",
        sensory_plasticity=True,
        discover_senses=True,
        actuation_enabled=True,
        experimental_clean=True,
    )

    individual = rig.individual
    genome = individual.genome if individual is not None else None
    germline = individual.germline if individual is not None else None

    step_params = tuple(inspect.signature(Symbiont.step).parameters)
    forbidden_step_tokens = (
        "condition", "phase", "world", "body_id", "embodiment",
        "truth", "label", "resource", "hazard", "schedule",
    )
    step_clean = (
        step_params == ("self", "opaque_inputs")
        and not any(
            token in name.lower()
            for name in step_params
            for token in forbidden_step_tokens
        )
    )

    germline_methods = (
        GermlineState.capture_acquired_variation,
        GermlineState.effective_value,
    )
    germline_param_names = {
        name.lower()
        for method in germline_methods
        for name in inspect.signature(method).parameters
    }
    forbidden_germline_tokens = {
        "world", "condition", "phase", "resource", "hazard",
        "body", "embodiment", "concept", "signal", "schedule",
    }
    germline_clean = not any(
        token in param
        for param in germline_param_names
        for token in forbidden_germline_tokens
    )

    genome_values = flatten_genes(genome) if genome is not None else {}
    genome_text = repr(sorted(genome_values.items())).lower()
    identity_tokens = (
        "world", "resource", "hazard", "body", "embodiment",
        "signal", "condition", "schedule", "intervention",
    )
    no_world_identity = not any(token in genome_text for token in identity_tokens)

    return EmbodimentIntegrityGates(
        clean_runtime_boundary=(rig.runtime is None and individual is not None),
        clean_actuation_boundary=(
            rig.actuation_adapter is None
            and rig.actuation_binding is None
            and rig.resource_habitats == {}
        ),
        symbiont_step_surface_clean=step_clean,
        germline_surface_clean=germline_clean,
        genome_germline_present=(genome is not None and germline is not None),
        no_world_identity_in_genome=no_world_identity,
    )


__all__ = [
    "EmbodimentIntegrityGates",
    "run_embodiment_integrity_gates",
]
