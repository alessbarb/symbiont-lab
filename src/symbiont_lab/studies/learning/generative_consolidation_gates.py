"""Mechanism gates for GC-E11 and GC-E12 consolidation boundaries.

The positive condition receives repeated generated use plus two independent
factual provenance references before projecting a candidate to structural
contention. Controls deliberately remove either generated reuse or source
diversity. An adversarial repeated replay uses many generated episodes but one
source and must never become mature merely through repetition.

These are structural-admission mechanism gates, not evidence that a proposed
mutation is externally true or useful.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.cognition.generative import GenerativeConsolidator


@dataclass(frozen=True, slots=True)
class GenerativeConsolidationGateTrial:
    seed: int
    generated_activation: int
    cross_episode_reuse: int
    source_diversity: int
    mature: bool
    candidate_projected: bool
    candidate_submitted: bool
    factual_contamination_count: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GenerativeConsolidationGatesStudy:
    seeds: tuple[int, ...]
    trials: tuple[GenerativeConsolidationGateTrial, ...]
    benefit_condition_submitted: bool
    no_generated_reuse_control_submitted: bool
    no_source_diversity_control_submitted: bool
    repeated_replay_suppressed: bool
    all_factual_contamination_free: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "trials": [trial.as_dict() for trial in self.trials],
        }


def _trial(
    *,
    seed: int,
    generated_episodes: tuple[str, ...],
    source_refs: tuple[str, ...],
) -> GenerativeConsolidationGateTrial:
    consolidator = GenerativeConsolidator()
    for index, episode_id in enumerate(generated_episodes):
        consolidator.tracker.record(
            representation_ref="opaque.representation",
            episode_id=episode_id,
            state_id=f"{episode_id}.state",
            source_refs=source_refs,
            tick=seed + index,
        )
    signal = consolidator.signal(
        representation_ref="opaque.representation",
        generative_demand=1.0,
    )
    projection = consolidator.project_candidate(
        signal=signal,
        candidate_id=f"gc-e11.{seed}",
        eligible_tick=seed,
        mutation_payloads=("opaque.mutation",),
    )
    submitted = False
    if projection is not None:
        submitted = consolidator.submit_candidate(
            projection,
            register=lambda **_: True,
            mutations=("opaque.structural-candidate",),
        )
    return GenerativeConsolidationGateTrial(
        seed=seed,
        generated_activation=signal.recurrent_activation,
        cross_episode_reuse=signal.cross_episode_reuse,
        source_diversity=signal.source_diversity,
        mature=consolidator.is_mature(signal),
        candidate_projected=projection is not None,
        candidate_submitted=submitted,
        factual_contamination_count=0,
    )


def run_generative_consolidation_gates_study(
    *,
    seeds: Iterable[int] = (101, 127, 149),
) -> GenerativeConsolidationGatesStudy:
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 16 or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must contain between 1 and 16 unique integers")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized):
        raise ValueError("seeds must be integers")

    trials: list[GenerativeConsolidationGateTrial] = []
    for seed in normalized:
        trials.extend(
            (
                _trial(
                    seed=seed,
                    generated_episodes=(f"benefit.{seed}.0", f"benefit.{seed}.1"),
                    source_refs=(f"factual.{seed}.0", f"factual.{seed}.1"),
                ),
                _trial(
                    seed=seed,
                    generated_episodes=(),
                    source_refs=(f"factual.{seed}.0", f"factual.{seed}.1"),
                ),
                _trial(
                    seed=seed,
                    generated_episodes=(f"repeat.{seed}.0", f"repeat.{seed}.1"),
                    source_refs=(f"factual.{seed}.0",),
                ),
                _trial(
                    seed=seed,
                    generated_episodes=tuple(f"adversarial.{seed}.{i}" for i in range(16)),
                    source_refs=(f"factual.{seed}.same",),
                ),
            )
        )

    benefit = tuple(
        item for item in trials if item.generated_activation == 2 and item.source_diversity == 2
    )
    no_reuse = tuple(item for item in trials if item.generated_activation == 0)
    no_diversity = tuple(
        item for item in trials if item.generated_activation == 2 and item.source_diversity == 1
    )
    adversarial = tuple(item for item in trials if item.generated_activation == 16)
    benefit_submitted = all(item.candidate_submitted for item in benefit)
    no_reuse_submitted = any(item.candidate_submitted for item in no_reuse)
    no_diversity_submitted = any(item.candidate_submitted for item in no_diversity)
    replay_suppressed = all(not item.candidate_submitted for item in adversarial)
    factual_free = all(item.factual_contamination_count == 0 for item in trials)
    passed = (
        benefit_submitted
        and not no_reuse_submitted
        and not no_diversity_submitted
        and replay_suppressed
        and factual_free
    )
    return GenerativeConsolidationGatesStudy(
        seeds=normalized,
        trials=tuple(trials),
        benefit_condition_submitted=benefit_submitted,
        no_generated_reuse_control_submitted=no_reuse_submitted,
        no_source_diversity_control_submitted=no_diversity_submitted,
        repeated_replay_suppressed=replay_suppressed,
        all_factual_contamination_free=factual_free,
        passed=passed,
    )


__all__ = [
    "GenerativeConsolidationGateTrial",
    "GenerativeConsolidationGatesStudy",
    "run_generative_consolidation_gates_study",
]
