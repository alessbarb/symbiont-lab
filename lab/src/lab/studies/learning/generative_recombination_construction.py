"""Observer-only construction gate for Generative Cognition recombination.

This assay checks the resident boundary, compatibility rejection and
multi-episode provenance.  It deliberately does not claim that a recombined
state is externally correct or useful: no environment outcome is supplied.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.cognition.generative import (
    GeneratedFeature,
    RecombinationFragment,
    ResidentGenerativeCognition,
)


@dataclass(frozen=True, slots=True)
class GenerativeRecombinationConstructionSeedResult:
    seed: int
    treatment_constructed: bool
    treatment_origin_imagined: bool
    treatment_episode_provenance_preserved: bool
    treatment_state_provenance_preserved: bool
    treatment_features_combined: bool
    treatment_factual_contamination: int
    control_constructed: bool
    incompatible_pair_rejected: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GenerativeRecombinationConstructionStudy:
    seeds: tuple[int, ...]
    results: tuple[GenerativeRecombinationConstructionSeedResult, ...]
    treatment_construction_rate: float
    provenance_preservation_rate: float
    incompatible_rejection_rate: float
    all_factual_contamination_free: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "results": [result.as_dict() for result in self.results],
        }


def _fragment(
    *, episode: str, state: str, feature: str, keys: tuple[str, ...]
) -> RecombinationFragment:
    return RecombinationFragment(
        source_episode_id=episode,
        source_state_id=state,
        features=(GeneratedFeature(feature, None, 0.8),),
        compatibility_keys=keys,
        uncertainty=0.2,
        coherence=0.9,
    )


def run_generative_recombination_construction_study(
    *, seeds: Iterable[int] = (101, 127, 149)
) -> GenerativeRecombinationConstructionStudy:
    """Run a deterministic construction/provenance gate across seeds.

    ``seed`` is used only to keep each resident identity distinct.  The
    construction inputs are fixed intentionally; this is a boundary assay,
    not a stochastic utility campaign.
    """
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 16 or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must contain between 1 and 16 unique integers")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized):
        raise ValueError("seeds must be integers")

    results: list[GenerativeRecombinationConstructionSeedResult] = []
    for seed in normalized:
        treatment = ResidentGenerativeCognition(organism_id=f"gc-e4-{seed}-treatment")
        left = _fragment(
            episode="episode.left",
            state="state.left",
            feature="feature.left",
            keys=("relation.shared", "relation.left"),
        )
        right = _fragment(
            episode="episode.right",
            state="state.right",
            feature="feature.right",
            keys=("relation.shared", "relation.right"),
        )
        snapshot = treatment.materialize_recombination(tick=seed, left=left, right=right)
        state = treatment.last_workspace.states[0] if treatment.last_workspace else None
        treatment_constructed = state is not None and snapshot.state_count == 1
        treatment_origin_imagined = treatment_constructed and state.origin.value == "imagined"
        treatment_episode_provenance_preserved = treatment_constructed and (
            state.source_episode_ids == ("episode.left", "episode.right")
            and treatment.last_workspace.episode.source_episode_ids
            == ("episode.left", "episode.right")
        )
        treatment_state_provenance_preserved = treatment_constructed and state.source_state_ids == (
            "state.left",
            "state.right",
        )
        treatment_features_combined = treatment_constructed and tuple(
            feature.token for feature in state.features
        ) == ("feature.left", "feature.right")

        control = ResidentGenerativeCognition(organism_id=f"gc-e4-{seed}-control")
        control_constructed = control.last_workspace is not None

        incompatible = ResidentGenerativeCognition(organism_id=f"gc-e4-{seed}-negative")
        rejected = False
        try:
            incompatible.materialize_recombination(
                tick=seed,
                left=_fragment(
                    episode="episode.left",
                    state="state.left",
                    feature="feature.left",
                    keys=("relation.left",),
                ),
                right=_fragment(
                    episode="episode.right",
                    state="state.right",
                    feature="feature.right",
                    keys=("relation.right",),
                ),
            )
        except ValueError as error:
            rejected = "no organism-owned compatibility relation" in str(error)

        results.append(
            GenerativeRecombinationConstructionSeedResult(
                seed=seed,
                treatment_constructed=treatment_constructed,
                treatment_origin_imagined=treatment_origin_imagined,
                treatment_episode_provenance_preserved=treatment_episode_provenance_preserved,
                treatment_state_provenance_preserved=treatment_state_provenance_preserved,
                treatment_features_combined=treatment_features_combined,
                treatment_factual_contamination=treatment.factual_contamination_count,
                control_constructed=control_constructed,
                incompatible_pair_rejected=rejected and incompatible.last_workspace is None,
            )
        )

    count = len(results)
    construction_rate = sum(item.treatment_constructed for item in results) / count
    provenance_rate = (
        sum(
            item.treatment_episode_provenance_preserved
            and item.treatment_state_provenance_preserved
            and item.treatment_features_combined
            for item in results
        )
        / count
    )
    rejection_rate = sum(item.incompatible_pair_rejected for item in results) / count
    contamination_free = all(item.treatment_factual_contamination == 0 for item in results)
    passed = (
        construction_rate == 1.0
        and provenance_rate == 1.0
        and rejection_rate == 1.0
        and not any(item.control_constructed for item in results)
        and contamination_free
    )
    return GenerativeRecombinationConstructionStudy(
        seeds=normalized,
        results=tuple(results),
        treatment_construction_rate=construction_rate,
        provenance_preservation_rate=provenance_rate,
        incompatible_rejection_rate=rejection_rate,
        all_factual_contamination_free=contamination_free,
        passed=passed,
    )


__all__ = [
    "GenerativeRecombinationConstructionSeedResult",
    "GenerativeRecombinationConstructionStudy",
    "run_generative_recombination_construction_study",
]
