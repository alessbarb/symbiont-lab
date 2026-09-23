"""Offline assay of physical consequences associated with motor primitives.

The assay reads immutable Physics3D telemetry. It never schedules actions,
changes primitive competence, supplies reward, or feeds any result back into
the organism.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from statistics import fmean, median, pstdev
from typing import Mapping

from symbiont_lab.physics3d.effects import (
    PhysicalConsequence,
    PhysicalState,
    StateDistance,
    physical_consequence,
    physical_state_from_payload,
    state_distance,
)
from symbiont_lab.physics3d.persistence import (
    load_telemetry_records,
    load_telemetry_transitions,
)


@dataclass(frozen=True, slots=True)
class StateComparability:
    """Transparent observer-side tolerances for matched initial states.

    Every dimension is checked independently. The values are study apparatus
    parameters; they are never exposed to or used by the organism.
    """

    orientation_angle_max: float = math.radians(15.0)
    linear_velocity_delta_max: float = 0.25
    angular_velocity_delta_max: float = 0.75
    joint_rms_delta_max: float = 0.25
    contact_jaccard_distance_max: float = 0.25
    com_height_delta_max: float = 0.05


DEFAULT_STATE_COMPARABILITY = StateComparability()


@dataclass(frozen=True, slots=True)
class PrimitiveEffectSample:
    primitive_id: str
    sample_index: int
    source: str
    materialized: bool
    competence: bool
    evidence_blocks: tuple[int, ...]
    start_tick: int
    end_tick: int
    initial_state: PhysicalState
    consequence: PhysicalConsequence


@dataclass(frozen=True, slots=True)
class PrimitiveEffectReport:
    primitive_id: str
    episodes: int
    materialized: bool
    competence: bool
    independent_evidence_blocks: int
    replication_target_met: bool
    body_translation_mean: tuple[float, float, float]
    com_translation_mean: tuple[float, float, float]
    translation_magnitude_mean: float
    translation_magnitude_median: float
    translation_magnitude_std: float
    translation_magnitude_cv: float | None
    directional_concentration: float
    rotation_mean: float
    rotation_std: float
    path_efficiency_mean: float
    base_com_agreement_mean: float
    mechanical_work_mean: float
    metabolic_cost_mean: float
    contact_persistence_mean: float
    initial_orientation_spread: float
    initial_linear_velocity_spread: float
    initial_angular_velocity_spread: float
    initial_joint_spread: float
    initial_contact_spread: float
    initial_com_height_spread: float
    comparable_state_pairs: int
    noncomparable_state_pairs: int
    within_state_translation_delta_mean: float | None
    between_state_translation_delta_mean: float | None
    within_state_direction_delta_mean: float | None
    between_state_direction_delta_mean: float | None
    within_state_com_translation_delta_mean: float | None
    between_state_com_translation_delta_mean: float | None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mean_vector(
    vectors: list[tuple[float, float, float]],
) -> tuple[float, float, float]:
    if not vectors:
        return (0.0, 0.0, 0.0)
    return tuple(fmean(vector[axis] for vector in vectors) for axis in range(3))


def _vector_delta(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def _direction_delta(
    left: PhysicalConsequence,
    right: PhysicalConsequence,
    *,
    noise_floor: float = 1e-4,
) -> float | None:
    lx, ly, _ = left.translation_body
    rx, ry, _ = right.translation_body
    left_magnitude = math.hypot(lx, ly)
    right_magnitude = math.hypot(rx, ry)
    if left_magnitude <= noise_floor or right_magnitude <= noise_floor:
        return None
    cosine = (lx * rx + ly * ry) / (left_magnitude * right_magnitude)
    return math.acos(max(-1.0, min(1.0, cosine)))


def _states_comparable(
    distance: StateDistance,
    criteria: StateComparability,
) -> bool:
    return (
        distance.orientation_angle <= criteria.orientation_angle_max
        and distance.linear_velocity_delta <= criteria.linear_velocity_delta_max
        and distance.angular_velocity_delta <= criteria.angular_velocity_delta_max
        and distance.joint_rms_delta <= criteria.joint_rms_delta_max
        and distance.contact_jaccard_distance
        <= criteria.contact_jaccard_distance_max
        and distance.com_height_delta <= criteria.com_height_delta_max
    )


def _mean_or_none(values: list[float]) -> float | None:
    return fmean(values) if values else None


def _directional_concentration(
    effects: list[PhysicalConsequence],
    *,
    noise_floor: float = 1e-4,
) -> float:
    unit_vectors: list[tuple[float, float]] = []
    for effect in effects:
        x, y, _z = effect.translation_body
        magnitude = math.hypot(x, y)
        if magnitude <= noise_floor:
            continue
        unit_vectors.append((x / magnitude, y / magnitude))
    if not unit_vectors:
        return 0.0
    mean_x = fmean(item[0] for item in unit_vectors)
    mean_y = fmean(item[1] for item in unit_vectors)
    return min(1.0, math.hypot(mean_x, mean_y))


def _episode_samples(
    transitions: list[dict[str, object]],
    summaries: list[dict[str, object]],
) -> tuple[PrimitiveEffectSample, ...]:
    transition_by_tick = {
        int(item["tick"]): item
        for item in transitions
        if isinstance(item.get("tick"), int)
    }
    summary_by_tick = {
        int(item["tick"]): item
        for item in summaries
        if isinstance(item.get("tick"), int)
    }
    samples: list[PrimitiveEffectSample] = []

    for transition in transitions:
        sensorimotor = _mapping(transition.get("sensorimotor"))
        raw_episodes = sensorimotor.get("episodes", ())
        if not isinstance(raw_episodes, (list, tuple)):
            continue
        for raw_episode in raw_episodes:
            if not isinstance(raw_episode, Mapping):
                continue
            primitive_id = raw_episode.get("primitive_id")
            start_tick = raw_episode.get("start_tick")
            end_tick = raw_episode.get("end_tick")
            if (
                not isinstance(primitive_id, str)
                or isinstance(start_tick, bool)
                or not isinstance(start_tick, int)
                or isinstance(end_tick, bool)
                or not isinstance(end_tick, int)
            ):
                continue
            start_transition = transition_by_tick.get(start_tick)
            end_transition = transition_by_tick.get(end_tick)
            if start_transition is None or end_transition is None:
                continue
            before_payload = _mapping(
                _mapping(start_transition.get("pre")).get("physical")
            )
            after_payload = _mapping(
                _mapping(end_transition.get("pre")).get("physical")
            )
            if not before_payload or not after_payload:
                continue

            path_length = 0.0
            mechanical_work = 0.0
            metabolic_cost = 0.0
            for tick in range(start_tick, end_tick):
                step = transition_by_tick.get(tick)
                if step is not None:
                    physics = _mapping(step.get("physics"))
                    path_length += max(
                        0.0,
                        float(physics.get("base_path_length", 0.0) or 0.0),
                    )
                    mechanical_work += max(
                        0.0,
                        float(physics.get("mechanical_work_joules", 0.0) or 0.0),
                    )
                summary = summary_by_tick.get(tick)
                if summary is not None:
                    metabolic_cost += max(
                        0.0,
                        float(summary.get("metabolic_work_cost", 0.0) or 0.0),
                    )

            before = physical_state_from_payload(start_tick, before_payload)
            after = physical_state_from_payload(end_tick, after_payload)
            consequence = physical_consequence(
                before,
                after,
                path_length=path_length,
                mechanical_work_joules=mechanical_work,
                metabolic_cost=metabolic_cost,
            )
            raw_blocks = raw_episode.get("evidence_blocks", ())
            blocks = tuple(
                int(item)
                for item in raw_blocks
                if isinstance(item, int) and not isinstance(item, bool)
            ) if isinstance(raw_blocks, (list, tuple)) else ()
            samples.append(
                PrimitiveEffectSample(
                    primitive_id=primitive_id,
                    sample_index=int(raw_episode.get("sample_index", 0) or 0),
                    source=str(raw_episode.get("source", "unknown")),
                    materialized=bool(raw_episode.get("materialized", False)),
                    competence=bool(raw_episode.get("competence", False)),
                    evidence_blocks=blocks,
                    start_tick=start_tick,
                    end_tick=end_tick,
                    initial_state=before,
                    consequence=consequence,
                )
            )
    return tuple(samples)


def analyze_primitive_effects(
    telemetry_run: str | Path,
    *,
    comparability: StateComparability = DEFAULT_STATE_COMPARABILITY,
    replication_target: int = 8,
) -> tuple[PrimitiveEffectReport, ...]:
    if replication_target < 1:
        raise ValueError("replication_target must be >= 1")

    transitions = load_telemetry_transitions(telemetry_run)
    summaries = load_telemetry_records(telemetry_run)
    samples = _episode_samples(transitions, summaries)

    by_primitive: dict[str, list[PrimitiveEffectSample]] = {}
    for sample in samples:
        by_primitive.setdefault(sample.primitive_id, []).append(sample)

    reports: list[PrimitiveEffectReport] = []
    for primitive_id, primitive_samples in sorted(by_primitive.items()):
        effects = [item.consequence for item in primitive_samples]
        initial = [item.initial_state for item in primitive_samples]
        magnitudes = [item.translation_magnitude for item in effects]
        rotations = [item.rotation_angle for item in effects]

        pair_distances: list[StateDistance] = []
        comparable_translation: list[float] = []
        noncomparable_translation: list[float] = []
        comparable_direction: list[float] = []
        noncomparable_direction: list[float] = []
        comparable_com: list[float] = []
        noncomparable_com: list[float] = []
        comparable_pairs = 0
        noncomparable_pairs = 0

        for left in range(len(initial)):
            for right in range(left + 1, len(initial)):
                distance = state_distance(initial[left], initial[right])
                pair_distances.append(distance)
                comparable = _states_comparable(distance, comparability)
                translation_delta = _vector_delta(
                    effects[left].translation_body,
                    effects[right].translation_body,
                )
                com_delta = _vector_delta(
                    effects[left].com_translation_body,
                    effects[right].com_translation_body,
                )
                direction_delta = _direction_delta(effects[left], effects[right])
                if comparable:
                    comparable_pairs += 1
                    comparable_translation.append(translation_delta)
                    comparable_com.append(com_delta)
                    if direction_delta is not None:
                        comparable_direction.append(direction_delta)
                else:
                    noncomparable_pairs += 1
                    noncomparable_translation.append(translation_delta)
                    noncomparable_com.append(com_delta)
                    if direction_delta is not None:
                        noncomparable_direction.append(direction_delta)

        magnitude_mean = fmean(magnitudes)
        magnitude_std = pstdev(magnitudes) if len(magnitudes) > 1 else 0.0
        evidence_blocks = {
            block
            for sample in primitive_samples
            for block in sample.evidence_blocks
        }

        reports.append(
            PrimitiveEffectReport(
                primitive_id=primitive_id,
                episodes=len(effects),
                materialized=any(item.materialized for item in primitive_samples),
                competence=any(item.competence for item in primitive_samples),
                independent_evidence_blocks=len(evidence_blocks),
                replication_target_met=len(effects) >= replication_target,
                body_translation_mean=_mean_vector(
                    [effect.translation_body for effect in effects]
                ),
                com_translation_mean=_mean_vector(
                    [effect.com_translation_body for effect in effects]
                ),
                translation_magnitude_mean=magnitude_mean,
                translation_magnitude_median=median(magnitudes),
                translation_magnitude_std=magnitude_std,
                translation_magnitude_cv=(
                    magnitude_std / magnitude_mean
                    if magnitude_mean > 1e-12
                    else None
                ),
                directional_concentration=_directional_concentration(effects),
                rotation_mean=fmean(rotations),
                rotation_std=(
                    pstdev(rotations) if len(rotations) > 1 else 0.0
                ),
                path_efficiency_mean=fmean(
                    effect.translation_efficiency for effect in effects
                ),
                base_com_agreement_mean=fmean(
                    effect.base_com_agreement for effect in effects
                ),
                mechanical_work_mean=fmean(
                    effect.mechanical_work_joules for effect in effects
                ),
                metabolic_cost_mean=fmean(
                    effect.metabolic_cost for effect in effects
                ),
                contact_persistence_mean=fmean(
                    effect.contact_persistence for effect in effects
                ),
                initial_orientation_spread=(
                    fmean(item.orientation_angle for item in pair_distances)
                    if pair_distances else 0.0
                ),
                initial_linear_velocity_spread=(
                    fmean(item.linear_velocity_delta for item in pair_distances)
                    if pair_distances else 0.0
                ),
                initial_angular_velocity_spread=(
                    fmean(item.angular_velocity_delta for item in pair_distances)
                    if pair_distances else 0.0
                ),
                initial_joint_spread=(
                    fmean(item.joint_rms_delta for item in pair_distances)
                    if pair_distances else 0.0
                ),
                initial_contact_spread=(
                    fmean(item.contact_jaccard_distance for item in pair_distances)
                    if pair_distances else 0.0
                ),
                initial_com_height_spread=(
                    fmean(item.com_height_delta for item in pair_distances)
                    if pair_distances else 0.0
                ),
                comparable_state_pairs=comparable_pairs,
                noncomparable_state_pairs=noncomparable_pairs,
                within_state_translation_delta_mean=_mean_or_none(
                    comparable_translation
                ),
                between_state_translation_delta_mean=_mean_or_none(
                    noncomparable_translation
                ),
                within_state_direction_delta_mean=_mean_or_none(
                    comparable_direction
                ),
                between_state_direction_delta_mean=_mean_or_none(
                    noncomparable_direction
                ),
                within_state_com_translation_delta_mean=_mean_or_none(
                    comparable_com
                ),
                between_state_com_translation_delta_mean=_mean_or_none(
                    noncomparable_com
                ),
            )
        )
    return tuple(reports)


__all__ = [
    "DEFAULT_STATE_COMPARABILITY",
    "PrimitiveEffectReport",
    "PrimitiveEffectSample",
    "StateComparability",
    "analyze_primitive_effects",
]
