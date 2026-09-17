"""Construction boundary for the Genesis biological-closure experiment.

Genesis is apparatus setup, not an organism policy.  It creates several
identical germinal organisms, finite opaque resource surfaces and one bounded
lineage authority.  The harness remains the only owner of environmental
regimes and evaluator measurements.
"""
from __future__ import annotations

from dataclasses import replace
import math

from symbiont.cognition.birth import load_base_genome, load_base_graph
from symbiont.cognition.limits import KernelLimits
from symbiont.core.birth_authority import HabitatBirthAuthority
from symbiont.core.ecology import SharedHabitat
from symbiont.core.heredity import HeritableGenome
from symbiont.core.inheritance import EpigeneticPrior
from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.reproduction import ReproductivePressure
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat

from .harness import AutonomousLifeHarness, HarnessConfig


def build_genesis_harness(
    config: HarnessConfig | None = None,
    *,
    kernel_limits: KernelLimits | None = None,
    interoception_enabled: bool = True,
    interoception_mode: str | None = None,
    reproduction_enabled: bool = True,
    social_enabled: bool = True,
    resource_profiles: tuple[tuple[float, float, float, float], ...] | None = None,
    founder_loci: tuple[tuple[str, float], ...] | None = None,
) -> AutonomousLifeHarness:
    """Build the canonical bounded Genesis run without injecting answers.

    All residents receive the same operational and heritable founder genome.
    Per-organism mutation seeds are distinct experimental seeds, not fitness or
    evaluator inputs.  The apparatus exposes only resource quantities through
    the supplied ``SharedHabitat`` instances.
    """
    selected = config or HarnessConfig()
    # The canonical environment must provide a bounded opportunity for each
    # founder to encounter a surface in the same cycle.  This is a quantity
    # scale, not an action schedule or a lineage instruction.
    selected = replace(selected, resource_scale=float(selected.population * 2 + 1))
    limits = kernel_limits or KernelLimits()
    genome = load_base_genome(kernel_limits=limits, running_version=(0, 59, 4))
    authority = HabitatBirthAuthority(
        habitat_id="genesis-lineage",
        capacity=32,
        # Initial residents consume one unit each; remaining finite units
        # allow births without giving the apparatus an offspring schedule.
        resource_budget=32.0,
    )
    # Distinct physical profiles create niches without assigning a preferred
    # resource to any organism.  Only quantities and intake consequences cross
    # the organism boundary; these positions are evaluator-side apparatus
    # metadata for later ecological analysis.
    profiles = resource_profiles or (
        (0.30, 0.50, 0.70, 0.10),
        (0.10, 1.00, 1.40, 0.35),
        (0.02, 2.00, 1.00, 0.80),
    )
    if len(profiles) < 1 or any(
        len(profile) != 4
        or any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(float(value)) for value in profile)
        or profile[0] < 0.0 or not 0.1 <= profile[1] <= 16.0
        or not 0.0 <= profile[2] <= 16.0
        or not 0.0 <= profile[3] <= 1.0
        for profile in profiles
    ):
        raise ValueError(
            "resource_profiles must contain finite (renewal, cost, usefulness, information) tuples"
        )
    habitats = {
        resource_id: SharedHabitat(
            habitat_id=resource_id,
            capacity=32,
            # Admission reserves one unit per founder on every attached
            # surface.  Keep an explicit finite abundance surplus so the
            # initial cohort can actually discover and acquire resources;
            # otherwise the admission transaction consumes the whole pool and
            # silently turns the ablation into "resource surface absent".
            resources=float(selected.resource_scale),
            renewal_rate=profiles[index % len(profiles)][0],
            acquisition_cost=profiles[index % len(profiles)][1],
            physiological_usefulness=profiles[index % len(profiles)][2],
            information_content=profiles[index % len(profiles)][3],
        )
        for index, resource_id in enumerate(selected.resource_classes)
    }
    social_habitat = (
        SocialHabitat(
            EcologicalResourcePool({
                resource_id: float(selected.population * 2)
                for resource_id in selected.resource_classes
            }),
            max_members=32,
        )
        if social_enabled else None
    )
    selected_founder_loci = (
        (("forgetting_rate", genome.plasticity.forgetting_rate.initial),
         ("learning_rate", genome.plasticity.learning_rate.initial))
        if founder_loci is None else founder_loci
    )
    if (not isinstance(selected_founder_loci, tuple)
            or len(selected_founder_loci) > 16
            or any(not isinstance(item, tuple) or len(item) != 2
                   or not isinstance(item[0], str)
                   or isinstance(item[1], bool) or not isinstance(item[1], (int, float))
                   or not math.isfinite(float(item[1]))
                   for item in selected_founder_loci)):
        raise ValueError("founder_loci must contain bounded finite key/value tuples")
    founder = HeritableGenome("genesis_founder", selected_founder_loci)
    organisms = []
    for index in range(selected.population):
        metabolic_kinds = ("observation", "cognition", "persistence", "maintenance")
        organisms.append(OrganismRuntime(
            organism_id=f"genesis_{index:02d}",
            genome=genome,
            cognitive_graph=load_base_graph(kernel_limits=limits),
            heritable_genome=founder,
            mutation_seed=selected.seed + index,
            epigenetic_priors=(EpigeneticPrior("exploration_bias", 0.25),),
            birth_authority=authority,
            social_habitat=social_habitat,
            # Founders reach reproductive readiness during the first
            # abundance window; later regime shifts then test whether their
            # descendants can persist without an apparatus birth schedule.
            reproductive_pressure=(
                ReproductivePressure(threshold_ticks=1)
                if reproduction_enabled else None
            ),
            resource_habitats=habitats,
            metabolism=MetabolicLedger(
                replenishment={kind: 0.0 for kind in metabolic_kinds},
                # Founders begin viable rather than already below the
                # elevated-pressure boundary.  Scarcity and damage then
                # create the experimental challenge instead of making every
                # first observation an artificial stress event.
                reserve={kind: 0.80 for kind in metabolic_kinds},
            ),
            explicit_metabolism=True,
            # Birth has a material maintenance cost.  Under stale external
            # supply, released residency units cannot become a perpetual
            # population-recycling loophole.
            reproduction_cost=0.05,
            autonomous_behavior=True,
            # Keep novelty available but do not let the founder's first
            # exploratory choice overwhelm a finite-resource opportunity.
            # This is an experimental prior, not a reserve-dependent policy;
            # later action outcomes can still move the local frontier.
            behavior_exploration=0.10,
            bootstrap_semantic_senses=False,
            discover_senses=False,
            interoception_enabled=interoception_enabled,
            interoception_mode=interoception_mode,
        ))
        if social_habitat is not None:
            organisms[-1].join_social_habitat(social_habitat)
    return AutonomousLifeHarness(
        organisms,
        config=selected,
        resource_habitats=habitats,
        social_habitat=social_habitat,
        birth_authority=authority,
    )


__all__ = ["build_genesis_harness"]
