"""Offline assay of physical consequences associated with motor primitives.

The assay reads immutable Physics3D telemetry. It never schedules actions,
changes primitive competence, supplies reward, or feeds any result back into
the organism.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from statistics import fmean, pstdev
from typing import Mapping

from symbiont_lab.physics3d.effects import (
    PhysicalConsequence,
    PhysicalState,
    physical_consequence,
    physical_state_from_payload,
    state_distance,
)
from symbiont_lab.physics3d.telemetry import (
    load_v3_tick_records,
    load_v3_transitions,
)


@dataclass(frozen=True, slots=True)
class PrimitiveEffectSample:
    primitive_id: str
    sample_index: int
    source: str
    materialized: bool
    competence: bool
    evidence_blocks: tuple[int, ...]
    initial_state: PhysicalState
    consequence: PhysicalConsequence


@dataclass(frozen=True, slots=True)
class PrimitiveEffectReport:
    primitive_id: str
    episodes: int
    body_translation_mean: tuple[float, float, float]
    com_translation_mean: tuple[float, float, float]
    translation_magnitude_mean: float
    translation_magnitude_std: float
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


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mean_vector(
    vectors: list[tuple[float, float, float]],
) -> tuple[float, float, float]:
    if not vectors:
        return (0.0, 0.0, 0.0)
    return tuple(fmean(vector[axis] for vector in vectors) for axis in range(3))


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
                    initial_state=before,
                    consequence=consequence,
                )
            )
    return tuple(samples)


def analyze_primitive_effects(
    telemetry_run: str | Path,
) -> tuple[PrimitiveEffectReport, ...]:
    transitions = load_v3_transitions(telemetry_run, verify=True)
    summaries = load_v3_tick_records(telemetry_run, verify=True)
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

        pair_distances = [
            state_distance(initial[left], initial[right])
            for left in range(len(initial))
            for right in range(left + 1, len(initial))
        ]

        reports.append(
            PrimitiveEffectReport(
                primitive_id=primitive_id,
                episodes=len(effects),
                body_translation_mean=_mean_vector(
                    [effect.translation_body for effect in effects]
                ),
                com_translation_mean=_mean_vector(
                    [effect.com_translation_body for effect in effects]
                ),
                translation_magnitude_mean=fmean(magnitudes),
                translation_magnitude_std=(
                    pstdev(magnitudes) if len(magnitudes) > 1 else 0.0
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
            )
        )
    return tuple(reports)


__all__ = [
    "PrimitiveEffectReport",
    "PrimitiveEffectSample",
    "analyze_primitive_effects",
]
