"""Paired causal validation of canonical Genome v2 phenotype expression.

The evaluator changes exactly one locus per pair.  Both conditions use the
same Symbiont id, RNG seed, opaque motor surface and deterministic body law.
No target action or evaluator feedback enters the organism.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from importlib import resources

from symbiont.core.orchestration.symbiont import Symbiont
from symbiont.genetics.genome import Genome, GenomeCodec, flatten_genes
from symbiont.genetics.germline import GermlineState

WORLD_LAW_ID = "opaque-linear-body-v1"


@dataclass(frozen=True, slots=True)
class GenomeCausalCondition:
    name: str
    genome_id: str
    genotype_hash: str
    locus: str
    locus_value: float
    initial_learning_rate: float
    initial_exploration_rate: float
    activation_trace: tuple[float, ...]
    prediction_error_trace: tuple[float, ...]
    final_relation_weight: float
    active_ticks: int

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["activation_trace"] = list(self.activation_trace)
        payload["prediction_error_trace"] = list(self.prediction_error_trace)
        return payload


@dataclass(frozen=True, slots=True)
class GenomeCausalPair:
    locus: str
    differing_loci: tuple[str, ...]
    low: GenomeCausalCondition
    high: GenomeCausalCondition

    @property
    def phenotype_diverged(self) -> bool:
        return (
            self.low.initial_learning_rate != self.high.initial_learning_rate
            or self.low.initial_exploration_rate != self.high.initial_exploration_rate
        )

    @property
    def trajectory_diverged(self) -> bool:
        return (
            self.low.activation_trace != self.high.activation_trace
            or self.low.prediction_error_trace != self.high.prediction_error_trace
            or abs(self.low.final_relation_weight - self.high.final_relation_weight) > 1e-12
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "locus": self.locus,
            "differing_loci": list(self.differing_loci),
            "phenotype_diverged": self.phenotype_diverged,
            "trajectory_diverged": self.trajectory_diverged,
            "low": self.low.as_dict(),
            "high": self.high.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class GenomeCausalValidationStudy:
    seed: int
    steps: int
    world_law_id: str
    exploration_pair: GenomeCausalPair
    learning_pair: GenomeCausalPair

    @property
    def passed(self) -> bool:
        pairs = (self.exploration_pair, self.learning_pair)
        return all(
            pair.differing_loci == (pair.locus,)
            and pair.phenotype_diverged
            and pair.trajectory_diverged
            for pair in pairs
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "steps": self.steps,
            "world_law_id": self.world_law_id,
            "passed": self.passed,
            "exploration_pair": self.exploration_pair.as_dict(),
            "learning_pair": self.learning_pair.as_dict(),
        }


def _base_genome(genome_id: str) -> Genome:
    payload = json.loads(
        resources.files("symbiont.genetics")
        .joinpath("defaults/base-genome-v2.json")
        .read_text(encoding="utf-8")
    )
    payload["genome_id"] = genome_id
    return GenomeCodec().load(payload)


def _differing_loci(left: Genome, right: Genome) -> tuple[str, ...]:
    left_values = flatten_genes(left)
    right_values = flatten_genes(right)
    return tuple(
        sorted(locus for locus in left_values if left_values[locus] != right_values[locus])
    )


def _exploration_genome(
    base: Genome,
    *,
    genome_id: str,
    baseline: float,
) -> Genome:
    return replace(
        base,
        genome_id=genome_id,
        sensorimotor=replace(
            base.sensorimotor,
            spontaneous_activity_baseline=float(baseline),
        ),
    )


def _learning_genome(
    base: Genome,
    *,
    genome_id: str,
    baseline: float,
) -> Genome:
    learning = replace(
        base.plasticity.learning_rate,
        baseline=float(baseline),
    )
    return replace(
        base,
        genome_id=genome_id,
        plasticity=replace(
            base.plasticity,
            learning_rate=learning,
        ),
    )


def _run_condition(
    *,
    name: str,
    genome: Genome,
    locus: str,
    locus_value: float,
    seed: int,
    steps: int,
) -> GenomeCausalCondition:
    symbiont = Symbiont(
        "symbiont.genome-causal-pair",
        seed=seed,
        genome=genome,
        germline=GermlineState.from_genome(genome),
    )
    symbiont.attach_execution_surface(
        "surface.genome-causal-v1",
        embodiment_id="embodiment.genome-causal-v1",
    )
    symbiont.register_output_channels(("out.0",))

    initial_learning_rate = symbiont.learning_rate
    initial_exploration_rate = symbiont.exploration_rate
    body_signal = 0.1
    activation_trace: list[float] = []
    prediction_error_trace: list[float] = []

    for _ in range(steps):
        activations = symbiont.step({"input.0": body_signal})
        activation = float(activations.get("out.0", 0.0))
        activation_trace.append(activation)
        prediction_error_trace.append(float(symbiont.last_prediction_error))
        # Deterministic opaque body law shared by both paired conditions.
        body_signal = max(
            0.0,
            min(1.0, 0.1 + 0.8 * activation),
        )

    return GenomeCausalCondition(
        name=name,
        genome_id=genome.genome_id,
        genotype_hash=genome.genotype_hash,
        locus=locus,
        locus_value=float(locus_value),
        initial_learning_rate=float(initial_learning_rate),
        initial_exploration_rate=float(initial_exploration_rate),
        activation_trace=tuple(activation_trace),
        prediction_error_trace=tuple(prediction_error_trace),
        final_relation_weight=symbiont.sensorimotor_model.relation_weight(
            "out.0",
            "input.0",
        ),
        active_ticks=sum(abs(value) > 1e-9 for value in activation_trace),
    )


def _pair(
    *,
    low: Genome,
    high: Genome,
    locus: str,
    low_value: float,
    high_value: float,
    seed: int,
    steps: int,
) -> GenomeCausalPair:
    differing = _differing_loci(low, high)
    if differing != (locus,):
        raise RuntimeError(
            "paired genome conditions must differ at exactly one locus; "
            f"expected {locus!r}, got {differing!r}"
        )
    return GenomeCausalPair(
        locus=locus,
        differing_loci=differing,
        low=_run_condition(
            name="low",
            genome=low,
            locus=locus,
            locus_value=low_value,
            seed=seed,
            steps=steps,
        ),
        high=_run_condition(
            name="high",
            genome=high,
            locus=locus,
            locus_value=high_value,
            seed=seed,
            steps=steps,
        ),
    )


def run_genome_causal_validation(
    *,
    seed: int = 991,
    steps: int = 96,
) -> GenomeCausalValidationStudy:
    if steps < 8:
        raise ValueError("steps must be at least 8")

    base = _base_genome("genome_causal_base")
    exploration_low_value = 0.02
    exploration_high_value = 0.65
    exploration_locus = "sensorimotor.spontaneous_activity_baseline"
    exploration_pair = _pair(
        low=_exploration_genome(
            base,
            genome_id="genome_causal_exploration_low",
            baseline=exploration_low_value,
        ),
        high=_exploration_genome(
            base,
            genome_id="genome_causal_exploration_high",
            baseline=exploration_high_value,
        ),
        locus=exploration_locus,
        low_value=exploration_low_value,
        high_value=exploration_high_value,
        seed=seed,
        steps=steps,
    )

    learning_low_value = 0.005
    learning_high_value = 0.06
    learning_locus = "plasticity.learning_rate.baseline"
    learning_pair = _pair(
        low=_learning_genome(
            base,
            genome_id="genome_causal_learning_low",
            baseline=learning_low_value,
        ),
        high=_learning_genome(
            base,
            genome_id="genome_causal_learning_high",
            baseline=learning_high_value,
        ),
        locus=learning_locus,
        low_value=learning_low_value,
        high_value=learning_high_value,
        seed=seed,
        steps=steps,
    )

    return GenomeCausalValidationStudy(
        seed=seed,
        steps=steps,
        world_law_id=WORLD_LAW_ID,
        exploration_pair=exploration_pair,
        learning_pair=learning_pair,
    )


__all__ = [
    "GenomeCausalCondition",
    "GenomeCausalPair",
    "GenomeCausalValidationStudy",
    "WORLD_LAW_ID",
    "run_genome_causal_validation",
]
