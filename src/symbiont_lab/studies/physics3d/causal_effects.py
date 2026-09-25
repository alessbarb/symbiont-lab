"""Matched-control analysis for primitive physical consequences.

This module analyzes counterfactual trials produced by Physics3D studies. It
never selects primitives, schedules organism actions, supplies reward or feeds
results back into Symbiont.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean

from symbiont_lab.physics3d.effects import PhysicalConsequence, PhysicalState

Vector3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class MatchedControlTrial:
    """Three-arm replay from one shared physical initial state.

    primitive replays the discovered coordination, passive applies no motor
    command, and motor_control uses a matched command budget while disrupting
    the primitive's temporal or coordination structure.
    """

    trial_id: str
    primitive_id: str
    initial_state: PhysicalState
    primitive: PhysicalConsequence
    passive: PhysicalConsequence
    motor_control: PhysicalConsequence


@dataclass(frozen=True, slots=True)
class MatchedControlReport:
    primitive_id: str
    trials: int
    primitive_translation_mean: Vector3
    passive_translation_mean: Vector3
    motor_control_translation_mean: Vector3
    primitive_minus_passive_translation_mean: Vector3
    primitive_minus_motor_control_translation_mean: Vector3
    primitive_minus_passive_com_mean: Vector3
    primitive_minus_motor_control_com_mean: Vector3
    passive_adjusted_directional_concentration: float
    control_adjusted_directional_concentration: float
    primitive_minus_passive_rotation_mean: float
    primitive_minus_motor_control_rotation_mean: float
    primitive_minus_passive_pose_mean: float
    primitive_minus_motor_control_pose_mean: float
    primitive_minus_passive_work_mean: float
    primitive_minus_motor_control_work_mean: float


def _sub(left: Vector3, right: Vector3) -> Vector3:
    return tuple(a - b for a, b in zip(left, right))  # type: ignore[return-value]


def _mean_vector(vectors: list[Vector3]) -> Vector3:
    if not vectors:
        return (0.0, 0.0, 0.0)
    return tuple(fmean(item[axis] for item in vectors) for axis in range(3))  # type: ignore[return-value]


def _directional_concentration(
    vectors: list[Vector3],
    *,
    noise_floor: float = 1e-4,
) -> float:
    horizontal: list[tuple[float, float]] = []
    for x, y, _z in vectors:
        magnitude = math.hypot(x, y)
        if magnitude <= noise_floor:
            continue
        horizontal.append((x / magnitude, y / magnitude))
    if not horizontal:
        return 0.0
    return min(
        1.0,
        math.hypot(
            fmean(item[0] for item in horizontal),
            fmean(item[1] for item in horizontal),
        ),
    )


def analyze_matched_controls(
    trials: tuple[MatchedControlTrial, ...] | list[MatchedControlTrial],
) -> tuple[MatchedControlReport, ...]:
    by_primitive: dict[str, list[MatchedControlTrial]] = {}
    seen_trial_ids: set[str] = set()
    for trial in trials:
        if trial.trial_id in seen_trial_ids:
            raise ValueError(f"duplicate matched-control trial_id: {trial.trial_id}")
        seen_trial_ids.add(trial.trial_id)
        by_primitive.setdefault(trial.primitive_id, []).append(trial)

    reports: list[MatchedControlReport] = []
    for primitive_id, group in sorted(by_primitive.items()):
        primitive_vectors = [item.primitive.translation_body for item in group]
        passive_vectors = [item.passive.translation_body for item in group]
        control_vectors = [item.motor_control.translation_body for item in group]
        passive_adjusted = [
            _sub(item.primitive.translation_body, item.passive.translation_body) for item in group
        ]
        control_adjusted = [
            _sub(
                item.primitive.translation_body,
                item.motor_control.translation_body,
            )
            for item in group
        ]
        passive_adjusted_com = [
            _sub(
                item.primitive.com_translation_body,
                item.passive.com_translation_body,
            )
            for item in group
        ]
        control_adjusted_com = [
            _sub(
                item.primitive.com_translation_body,
                item.motor_control.com_translation_body,
            )
            for item in group
        ]

        reports.append(
            MatchedControlReport(
                primitive_id=primitive_id,
                trials=len(group),
                primitive_translation_mean=_mean_vector(primitive_vectors),
                passive_translation_mean=_mean_vector(passive_vectors),
                motor_control_translation_mean=_mean_vector(control_vectors),
                primitive_minus_passive_translation_mean=_mean_vector(passive_adjusted),
                primitive_minus_motor_control_translation_mean=_mean_vector(control_adjusted),
                primitive_minus_passive_com_mean=_mean_vector(passive_adjusted_com),
                primitive_minus_motor_control_com_mean=_mean_vector(control_adjusted_com),
                passive_adjusted_directional_concentration=(
                    _directional_concentration(passive_adjusted)
                ),
                control_adjusted_directional_concentration=(
                    _directional_concentration(control_adjusted)
                ),
                primitive_minus_passive_rotation_mean=fmean(
                    item.primitive.rotation_angle - item.passive.rotation_angle for item in group
                ),
                primitive_minus_motor_control_rotation_mean=fmean(
                    item.primitive.rotation_angle - item.motor_control.rotation_angle
                    for item in group
                ),
                primitive_minus_passive_pose_mean=fmean(
                    item.primitive.pose_delta - item.passive.pose_delta for item in group
                ),
                primitive_minus_motor_control_pose_mean=fmean(
                    item.primitive.pose_delta - item.motor_control.pose_delta for item in group
                ),
                primitive_minus_passive_work_mean=fmean(
                    item.primitive.mechanical_work_joules - item.passive.mechanical_work_joules
                    for item in group
                ),
                primitive_minus_motor_control_work_mean=fmean(
                    item.primitive.mechanical_work_joules
                    - item.motor_control.mechanical_work_joules
                    for item in group
                ),
            )
        )
    return tuple(reports)


__all__ = [
    "MatchedControlReport",
    "MatchedControlTrial",
    "analyze_matched_controls",
]
