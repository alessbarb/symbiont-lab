"""Standing-variation selection under reversible pressure (refutation #3).

`genesis-multigenerational-followup.md` found that a single fixed value of the
`behavior_exploration` locus produces a real, reproducible outcome
differential under `default` regime pressure, but that differential vanishes
under `stale_resources`.  Every founder in every existing Genesis study shares
one identical genome, so none of that evidence shows selection acting on
standing variation -- only that changing a fixed parameter changes outcomes.

This module founds a population with genuinely mixed `behavior_exploration`
alleles (half low, half high), lets pressure apply and then reverse mid-run,
and asks whether the population's live mean allele value shifts one way under
the first regime, then shifts back when pressure reverses again -- the actual
signature of selection acting on standing variation, not a parameter sweep.

Apparatus-only: the harness and this module never expose regime labels,
fitness, or allele composition to any organism.  `_mean_live_behavior_exploration`
is a read of already-heritable, already-public state (`OrganismRuntime.heritable_genome`)
for evaluator-side descriptive statistics only; it is never written back.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import math
import time

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

LOW_ALLELE = 0.0
HIGH_ALLELE = 0.1
CONTROL_ALLELE = 0.05
SIGNIFICANCE_ALPHA = 0.01

# Same opaque (renewal, cost, usefulness, information) niches genesis.py uses;
# reused verbatim so this study inherits the same known-viable resource shape
# rather than inventing an untested one.
_RESOURCE_PROFILES = (
    (0.30, 0.50, 0.70, 0.10),
    (0.10, 1.00, 1.40, 0.35),
    (0.02, 2.00, 1.00, 0.80),
)


def _build_population(config: HarnessConfig, *, founder_values: tuple[float, ...]) -> AutonomousLifeHarness:
    """Build a population where founder ``i`` inherits ``behavior_exploration=founder_values[i]``."""
    if len(founder_values) != config.population:
        raise ValueError("founder_values must supply exactly one value per founder")
    limits = KernelLimits()
    genome = load_base_genome(kernel_limits=limits, running_version=(0, 59, 4))
    authority = HabitatBirthAuthority(
        habitat_id="reversible-selection-lineage", capacity=32, resource_budget=32.0,
    )
    habitats = {
        resource_id: SharedHabitat(
            habitat_id=resource_id,
            capacity=32,
            resources=float(config.resource_scale),
            renewal_rate=_RESOURCE_PROFILES[index % len(_RESOURCE_PROFILES)][0],
            acquisition_cost=_RESOURCE_PROFILES[index % len(_RESOURCE_PROFILES)][1],
            physiological_usefulness=_RESOURCE_PROFILES[index % len(_RESOURCE_PROFILES)][2],
            information_content=_RESOURCE_PROFILES[index % len(_RESOURCE_PROFILES)][3],
        )
        for index, resource_id in enumerate(config.resource_classes)
    }
    social_habitat = SocialHabitat(
        EcologicalResourcePool({
            resource_id: float(config.population * 2) for resource_id in config.resource_classes
        }),
        max_members=32,
    )
    metabolic_kinds = ("observation", "cognition", "persistence", "maintenance")
    organisms = []
    for index, value in enumerate(founder_values):
        clamped = max(0.0, min(1.0, float(value)))
        founder = HeritableGenome(
            f"reversible_founder_{index:02d}", (("behavior_exploration", clamped),)
        )
        organism = OrganismRuntime(
            organism_id=f"reversible_{index:02d}",
            genome=genome,
            cognitive_graph=load_base_graph(kernel_limits=limits),
            heritable_genome=founder,
            mutation_seed=config.seed + index,
            epigenetic_priors=(EpigeneticPrior("exploration_bias", 0.25),),
            birth_authority=authority,
            social_habitat=social_habitat,
            reproductive_pressure=ReproductivePressure(threshold_ticks=1),
            resource_habitats=habitats,
            metabolism=MetabolicLedger(
                replenishment={kind: 0.0 for kind in metabolic_kinds},
                reserve={kind: 0.80 for kind in metabolic_kinds},
            ),
            explicit_metabolism=True,
            reproduction_cost=0.05,
            autonomous_behavior=True,
            behavior_exploration=clamped,
            bootstrap_semantic_senses=False,
            discover_senses=False,
            interoception_enabled=True,
        )
        organism.join_social_habitat(social_habitat)
        organisms.append(organism)
    return AutonomousLifeHarness(
        organisms, config=config, resource_habitats=habitats,
        social_habitat=social_habitat, birth_authority=authority,
    )


def _mean_live_behavior_exploration(harness: AutonomousLifeHarness) -> float | None:
    """Evaluator-side mean of live organisms' inherited ``behavior_exploration``.

    Reads the harness's live-organism list directly: no public inspection API
    for this exists, and this module lives in the same package as the harness
    it reads.  The result is a descriptive population statistic only -- it is
    never written back into any organism's tick.
    """
    values = [
        float(dict(organism.heritable_genome.loci)["behavior_exploration"])
        for organism in harness._organisms  # noqa: SLF001 -- intra-package apparatus read
        if organism.heritable_genome is not None
        and "behavior_exploration" in dict(organism.heritable_genome.loci)
    ]
    return (sum(values) / len(values)) if values else None


def _sign(value: float) -> int:
    if value > 1e-9:
        return 1
    if value < -1e-9:
        return -1
    return 0


@dataclass(frozen=True, slots=True)
class ReversibleSelectionSeedResult:
    seed: int
    condition: str
    baseline_mean: float | None
    mid1_mean: float | None
    mid2_mean: float | None
    final_mean: float | None
    shift_a: float | None
    shift_b: float | None
    reversal_observed: bool
    final_population: int
    deaths: int


def _run_one_seed(seed: int, *, condition: str, population: int, ticks_per_segment: int) -> dict[str, object]:
    """Top-level, picklable worker: build, run three segments, sample, return plain data.

    Segments follow ``regimes=("scarcity", "abundance", "scarcity")``: pressure
    applies (scarcity), reverses (abundance), then reverses again back to the
    original pressure (scarcity) -- two reversals in one run, so a genuine
    selection signal must flip sign twice, not once by coincidence.
    """
    half = population // 2
    if condition == "mixed":
        founder_values = tuple([LOW_ALLELE] * half + [HIGH_ALLELE] * (population - half))
    elif condition == "control":
        founder_values = tuple([CONTROL_ALLELE] * population)
    else:
        raise ValueError("unknown condition")
    config = HarnessConfig(
        population=population,
        generations=1,
        ticks=ticks_per_segment * 3,
        checkpoint_interval=ticks_per_segment * 3,
        random_checkpoint_count=0,
        seed=seed,
        regimes=("scarcity", "abundance", "scarcity"),
        resource_scale=float(population * 2 + 1),
    )
    harness = _build_population(config, founder_values=founder_values)
    baseline = _mean_live_behavior_exploration(harness)
    harness.run(max_ticks=ticks_per_segment)
    mid1 = _mean_live_behavior_exploration(harness)
    harness.run(max_ticks=ticks_per_segment)
    mid2 = _mean_live_behavior_exploration(harness)
    trace3 = harness.run(max_ticks=ticks_per_segment)
    final = _mean_live_behavior_exploration(harness)
    shift_a = (mid2 - mid1) if (mid1 is not None and mid2 is not None) else None
    shift_b = (final - mid2) if (mid2 is not None and final is not None) else None
    reversal = bool(
        shift_a is not None and shift_b is not None
        and _sign(shift_a) != 0 and _sign(shift_b) != 0
        and _sign(shift_a) != _sign(shift_b)
    )
    final_population = trace3.population[-1][1] if trace3.population else 0
    deaths = len(harness._birth_authority.death_records) if harness._birth_authority is not None else 0  # noqa: SLF001
    return {
        "seed": seed, "condition": condition,
        "baseline_mean": baseline, "mid1_mean": mid1, "mid2_mean": mid2, "final_mean": final,
        "shift_a": shift_a, "shift_b": shift_b, "reversal_observed": reversal,
        "final_population": final_population, "deaths": deaths,
    }


def _to_result(payload: dict[str, object]) -> ReversibleSelectionSeedResult:
    return ReversibleSelectionSeedResult(
        seed=int(payload["seed"]), condition=str(payload["condition"]),
        baseline_mean=payload["baseline_mean"], mid1_mean=payload["mid1_mean"],
        mid2_mean=payload["mid2_mean"], final_mean=payload["final_mean"],
        shift_a=payload["shift_a"], shift_b=payload["shift_b"],
        reversal_observed=bool(payload["reversal_observed"]),
        final_population=int(payload["final_population"]), deaths=int(payload["deaths"]),
    )


def _binomial_sf(n: int, k: int, p: float) -> float:
    """Exact one-sided P(X >= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


@dataclass(frozen=True, slots=True)
class ReversibleSelectionStudy:
    seeds: tuple[int, ...]
    ticks_per_segment: int
    population: int
    mixed_results: tuple[ReversibleSelectionSeedResult, ...]
    control_results: tuple[ReversibleSelectionSeedResult, ...]
    mixed_reversals: int
    control_reversals: int
    mixed_reversal_p_value: float
    control_reversal_p_value: float
    rs1_mixed_reversal_significant: bool
    rs2_control_not_significant: bool
    replay_deterministic: bool
    all_gates_pass: bool
    wall_clock_seconds: float


def run_reversible_selection_study(
    *,
    seeds: tuple[int, ...] = tuple(range(1, 201)),
    ticks_per_segment: int = 90,
    population: int = 8,
    max_workers: int | None = None,
) -> ReversibleSelectionStudy:
    """Run the mixed-founder and uniform-control conditions across many seeds in parallel."""
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be unique")
    if any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds):
        raise ValueError("seeds must be non-negative integers")
    if not 8 <= population <= 32 or population % 2:
        raise ValueError("population must be an even value within [8, 32]")
    if ticks_per_segment < 1:
        raise ValueError("ticks_per_segment must be positive")

    start = time.monotonic()
    jobs = [(seed, condition) for condition in ("mixed", "control") for seed in seeds]
    results: dict[tuple[int, str], dict[str, object]] = {}
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _run_one_seed, seed, condition=condition,
                population=population, ticks_per_segment=ticks_per_segment,
            ): (seed, condition)
            for seed, condition in jobs
        }
        for future, key in futures.items():
            results[key] = future.result()
    wall_clock = time.monotonic() - start

    mixed = tuple(_to_result(results[(seed, "mixed")]) for seed in seeds)
    control = tuple(_to_result(results[(seed, "control")]) for seed in seeds)
    mixed_reversals = sum(item.reversal_observed for item in mixed)
    control_reversals = sum(item.reversal_observed for item in control)
    n = len(seeds)
    mixed_p = _binomial_sf(n, mixed_reversals, 0.5)
    control_p = _binomial_sf(n, control_reversals, 0.5)
    rs1 = mixed_p < SIGNIFICANCE_ALPHA
    rs2 = control_p >= SIGNIFICANCE_ALPHA

    replay_ok = True
    for seed in seeds[:3]:
        first = results[(seed, "mixed")]
        second = _run_one_seed(
            seed, condition="mixed", population=population, ticks_per_segment=ticks_per_segment,
        )
        if first != second:
            replay_ok = False
            break

    return ReversibleSelectionStudy(
        seeds=tuple(seeds), ticks_per_segment=ticks_per_segment, population=population,
        mixed_results=mixed, control_results=control,
        mixed_reversals=mixed_reversals, control_reversals=control_reversals,
        mixed_reversal_p_value=round(mixed_p, 10), control_reversal_p_value=round(control_p, 10),
        rs1_mixed_reversal_significant=rs1, rs2_control_not_significant=rs2,
        replay_deterministic=replay_ok,
        all_gates_pass=bool(rs1 and rs2 and replay_ok),
        wall_clock_seconds=round(wall_clock, 3),
    )


__all__ = [
    "ReversibleSelectionSeedResult", "ReversibleSelectionStudy",
    "run_reversible_selection_study",
]
