from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import fmean
from typing import Iterable, Mapping, Sequence

from symbiont_lab.physics3d.humanoid import (
    GROUND_MATERIAL,
    JOINT_SPECS,
    HumanoidPhysics,
    apply_surface_material,
    configure_physics_solver,
)
from symbiont_lab.physics3d.settling import SettlingResult, settle_passive_body

GRAVITY = 9.81
DEFAULT_TIME_STEP = 1.0 / 240.0


def _connect_world(time_step: float = DEFAULT_TIME_STEP):
    try:
        import pybullet as p
    except ImportError as exc:
        raise RuntimeError(
            "PyBullet is required. Install with: pip install 'symbiont-lab[physics3d]'"
        ) from exc

    client_id = p.connect(p.DIRECT)
    if client_id < 0:
        raise RuntimeError("failed to connect to PyBullet")
    p.setGravity(0.0, 0.0, -GRAVITY, physicsClientId=client_id)
    p.setTimeStep(time_step, physicsClientId=client_id)
    configure_physics_solver(p, client_id, time_step)

    plane_shape = p.createCollisionShape(
        p.GEOM_PLANE,
        planeNormal=(0.0, 0.0, 1.0),
        physicsClientId=client_id,
    )
    plane_id = p.createMultiBody(
        baseMass=0.0,
        baseCollisionShapeIndex=plane_shape,
        physicsClientId=client_id,
    )
    apply_surface_material(
        p,
        plane_id,
        -1,
        GROUND_MATERIAL,
        client_id=client_id,
    )
    body = HumanoidPhysics(p, client_id)
    return p, client_id, plane_id, body


def _total_mass(p, client_id: int, body: HumanoidPhysics) -> float:
    total = float(
        p.getDynamicsInfo(body.body_id, -1, physicsClientId=client_id)[0]
    )
    for link_index in range(
        int(p.getNumJoints(body.body_id, physicsClientId=client_id))
    ):
        total += float(
            p.getDynamicsInfo(
                body.body_id,
                link_index,
                physicsClientId=client_id,
            )[0]
        )
    return total


def _center_of_mass_height(p, client_id: int, body: HumanoidPhysics) -> float:
    weighted_z = 0.0
    total = 0.0

    base_mass = float(
        p.getDynamicsInfo(body.body_id, -1, physicsClientId=client_id)[0]
    )
    base_pos, _ = p.getBasePositionAndOrientation(
        body.body_id,
        physicsClientId=client_id,
    )
    weighted_z += base_mass * float(base_pos[2])
    total += base_mass

    for link_index in range(
        int(p.getNumJoints(body.body_id, physicsClientId=client_id))
    ):
        mass = float(
            p.getDynamicsInfo(
                body.body_id,
                link_index,
                physicsClientId=client_id,
            )[0]
        )
        if mass <= 0.0:
            continue
        state = p.getLinkState(
            body.body_id,
            link_index,
            computeForwardKinematics=True,
            physicsClientId=client_id,
        )
        weighted_z += mass * float(state[0][2])
        total += mass

    return weighted_z / max(total, 1e-12)


def _contact_metrics(
    p,
    client_id: int,
    body_id: int,
    plane_id: int,
) -> tuple[float, float, int]:
    contacts = p.getContactPoints(
        bodyA=body_id,
        bodyB=plane_id,
        physicsClientId=client_id,
    )
    normal_force = sum(max(0.0, float(item[9])) for item in contacts)

    closest = p.getClosestPoints(
        bodyA=body_id,
        bodyB=plane_id,
        distance=0.05,
        physicsClientId=client_id,
    )
    min_distance = min((float(item[8]) for item in closest), default=0.0)
    penetration = max(0.0, -min_distance)
    return normal_force, penetration, len(contacts)


def _settle(
    p,
    client_id: int,
    body: HumanoidPhysics,
    **kwargs,
) -> SettlingResult:
    return settle_passive_body(p, client_id, body, **kwargs)


def _passive_characterization(
    p,
    client_id: int,
    plane_id: int,
    body: HumanoidPhysics,
    *,
    steps: int = 480,
) -> dict[str, float | int]:
    body.apply_effectors({})
    start_pos, _ = p.getBasePositionAndOrientation(
        body.body_id,
        physicsClientId=client_id,
    )
    start_com = _center_of_mass_height(p, client_id, body)

    normal_forces: list[float] = []
    penetrations: list[float] = []
    ground_contacts: list[int] = []
    max_linear_speed = 0.0
    max_angular_speed = 0.0
    max_joint_speed = 0.0

    for _ in range(steps):
        body.prepare_physics_substep()
        p.stepSimulation(physicsClientId=client_id)
        normal, penetration, contacts = _contact_metrics(
            p,
            client_id,
            body.body_id,
            plane_id,
        )
        normal_forces.append(normal)
        penetrations.append(penetration)
        ground_contacts.append(contacts)

        linear, angular = p.getBaseVelocity(
            body.body_id,
            physicsClientId=client_id,
        )
        max_linear_speed = max(
            max_linear_speed,
            math.sqrt(sum(float(value) ** 2 for value in linear)),
        )
        max_angular_speed = max(
            max_angular_speed,
            math.sqrt(sum(float(value) ** 2 for value in angular)),
        )
        states = p.getJointStates(
            body.body_id,
            body.motor_joint_indices,
            physicsClientId=client_id,
        )
        max_joint_speed = max(
            max_joint_speed,
            max((abs(float(state[1])) for state in states), default=0.0),
        )

    end_pos, _ = p.getBasePositionAndOrientation(
        body.body_id,
        physicsClientId=client_id,
    )
    end_com = _center_of_mass_height(p, client_id, body)
    total_mass = _total_mass(p, client_id, body)
    expected_weight = total_mass * GRAVITY
    mean_reaction = fmean(normal_forces) if normal_forces else 0.0

    return {
        "steps": steps,
        "base_drift_m": math.dist(
            tuple(float(v) for v in start_pos),
            tuple(float(v) for v in end_pos),
        ),
        "com_height_start_m": start_com,
        "com_height_end_m": end_com,
        "com_drift_m": abs(end_com - start_com),
        "mean_ground_reaction_n": mean_reaction,
        "max_ground_reaction_n": max(normal_forces, default=0.0),
        "expected_weight_n": expected_weight,
        "reaction_to_weight_ratio": (
            mean_reaction / expected_weight if expected_weight > 0.0 else 0.0
        ),
        "max_ground_penetration_m": max(penetrations, default=0.0),
        "mean_ground_penetration_m": (
            fmean(penetrations) if penetrations else 0.0
        ),
        "mean_ground_contact_points": (
            fmean(ground_contacts) if ground_contacts else 0.0
        ),
        "max_ground_contact_points": max(ground_contacts, default=0),
        "max_base_linear_speed_m_s": max_linear_speed,
        "max_base_angular_speed_rad_s": max_angular_speed,
        "max_joint_speed_rad_s": max_joint_speed,
    }


def _spread_indices(total: int, count: int, *, offset: int = 0) -> tuple[int, ...]:
    if count >= total:
        return tuple(range(total))
    if count <= 1:
        return (offset % total,)
    base = {
        round(i * (total - 1) / (count - 1))
        for i in range(count)
    }
    return tuple(sorted({(index + offset) % total for index in base}))


def _matched_index_sets(
    total: int,
    count: int,
    repeats: int,
) -> tuple[tuple[int, ...], ...]:
    if count >= total:
        return (tuple(range(total)),)
    sets: list[tuple[int, ...]] = []
    for trial in range(max(1, repeats * 2)):
        offset = (trial * max(1, total // max(1, repeats))) % total
        selected = _spread_indices(total, count, offset=offset)
        if len(selected) != count or selected in sets:
            continue
        sets.append(selected)
        if len(sets) >= repeats:
            break
    return tuple(sets) or (_spread_indices(total, count),)


def _run_motor_trial(
    selected: Sequence[int],
    *,
    amplitudes: Mapping[int, float],
    drive_steps: int,
    time_step: float,
    mode: str,
) -> dict[str, object]:
    p, client_id, plane_id, body = _connect_world(time_step)
    try:
        settle = _settle(p, client_id, body)
        if not settle.converged:
            return {
                "mode": mode,
                "selected_joint_indices": [int(value) for value in selected],
                "settling": settle.as_dict(),
                "valid": False,
                "reason": "passive_settling_failed",
            }

        activations = {
            body.motor_bindings[index].positive_port: float(amplitudes[index])
            for index in selected
        }
        commanded_torque_capacity = sum(
            JOINT_SPECS[index].max_motor_torque * float(amplitudes[index])
            for index in selected
        )

        start_pos, _ = p.getBasePositionAndOrientation(
            body.body_id,
            physicsClientId=client_id,
        )
        previous = tuple(float(v) for v in start_pos)
        base_path = 0.0
        positive_work = 0.0
        negative_work = 0.0
        absolute_work = 0.0
        net_work = 0.0
        max_joint_speed = 0.0
        max_penetration = 0.0
        max_ground_reaction = 0.0
        saturated_joint_substeps = 0
        observed_joint_substeps = 0

        body.apply_effectors(activations)
        for _ in range(drive_steps):
            body.prepare_physics_substep()
            p.stepSimulation(physicsClientId=client_id)
            work = body.actuator_work_step(time_step)
            positive_work += work.positive_j
            negative_work += work.negative_j
            absolute_work += work.absolute_j
            net_work += work.net_j

            current, _ = p.getBasePositionAndOrientation(
                body.body_id,
                physicsClientId=client_id,
            )
            current_t = tuple(float(v) for v in current)
            base_path += math.dist(previous, current_t)
            previous = current_t

            states = p.getJointStates(
                body.body_id,
                body.motor_joint_indices,
                physicsClientId=client_id,
            )
            max_joint_speed = max(
                max_joint_speed,
                max((abs(float(state[1])) for state in states), default=0.0),
            )
            for index in selected:
                speed = abs(float(states[index][1]))
                limit = max(1e-12, float(JOINT_SPECS[index].max_velocity))
                observed_joint_substeps += 1
                saturated_joint_substeps += int(speed >= 0.98 * limit)

            normal, penetration, _ = _contact_metrics(
                p,
                client_id,
                body.body_id,
                plane_id,
            )
            max_ground_reaction = max(max_ground_reaction, normal)
            max_penetration = max(max_penetration, penetration)

        end_pos, _ = p.getBasePositionAndOrientation(
            body.body_id,
            physicsClientId=client_id,
        )
        return {
            "mode": mode,
            "valid": True,
            "active_dof": len(selected),
            "active_directional_channels": len(selected),
            "selected_joint_indices": [int(value) for value in selected],
            "amplitudes": {
                str(index): float(amplitudes[index])
                for index in selected
            },
            "commanded_torque_capacity_nm": commanded_torque_capacity,
            "drive_steps": drive_steps,
            "settling": settle.as_dict(),
            "positive_actuator_work_j": positive_work,
            "negative_actuator_work_j": negative_work,
            "absolute_actuator_work_j": absolute_work,
            "net_actuator_work_j": net_work,
            "base_path_m": base_path,
            "net_base_displacement_m": math.dist(
                tuple(float(v) for v in start_pos),
                tuple(float(v) for v in end_pos),
            ),
            "max_joint_speed_rad_s": max_joint_speed,
            "velocity_saturation_ratio": (
                saturated_joint_substeps / observed_joint_substeps
                if observed_joint_substeps
                else 0.0
            ),
            "max_ground_reaction_n": max_ground_reaction,
            "max_ground_penetration_m": max_penetration,
        }
    finally:
        p.disconnect(physicsClientId=client_id)


def _dimensionality_trials(
    dimensions: Sequence[int],
    *,
    amplitude: float,
    drive_steps: int,
    time_step: float,
    repeats: int,
) -> list[dict[str, object]]:
    trials: list[dict[str, object]] = []
    for dimension in dimensions:
        for selected in _matched_index_sets(len(JOINT_SPECS), dimension, repeats):
            amplitudes = {index: amplitude for index in selected}
            trials.append(
                _run_motor_trial(
                    selected,
                    amplitudes=amplitudes,
                    drive_steps=drive_steps,
                    time_step=time_step,
                    mode="fixed_amplitude",
                )
            )
    return trials


def _fixed_total_torque_trials(
    dimensions: Sequence[int],
    *,
    reference_amplitude: float,
    drive_steps: int,
    time_step: float,
    repeats: int,
) -> tuple[float, list[dict[str, object]]]:
    # Reference budget is one trunk-yaw channel at the requested amplitude.
    torque_budget = JOINT_SPECS[0].max_motor_torque * reference_amplitude
    trials: list[dict[str, object]] = []
    for dimension in dimensions:
        for selected in _matched_index_sets(len(JOINT_SPECS), dimension, repeats):
            capacity = sum(JOINT_SPECS[index].max_motor_torque for index in selected)
            scale = min(1.0, torque_budget / max(capacity, 1e-12))
            amplitudes = {index: scale for index in selected}
            trials.append(
                _run_motor_trial(
                    selected,
                    amplitudes=amplitudes,
                    drive_steps=drive_steps,
                    time_step=time_step,
                    mode="fixed_total_torque",
                )
            )
    return torque_budget, trials


def _single_joint_trials(
    *,
    amplitude: float,
    drive_steps: int,
    time_step: float,
    joint_indices: Sequence[int] | None = None,
) -> list[dict[str, object]]:
    trials: list[dict[str, object]] = []
    selected_indices = (
        tuple(range(len(JOINT_SPECS)))
        if joint_indices is None
        else tuple(int(value) for value in joint_indices)
    )
    if any(not 0 <= index < len(JOINT_SPECS) for index in selected_indices):
        raise ValueError("single_joint_indices contains an invalid joint index")
    for index in selected_indices:
        spec = JOINT_SPECS[index]
        trial = _run_motor_trial(
            (index,),
            amplitudes={index: amplitude},
            drive_steps=drive_steps,
            time_step=time_step,
            mode="single_joint",
        )
        trial["joint_index"] = index
        trial["joint_name"] = spec.name
        trial["max_motor_torque_nm"] = spec.max_motor_torque
        trial["velocity_limit_rad_s"] = spec.max_velocity
        trials.append(trial)
    return trials


def run_constitution_audit(
    *,
    time_step: float = DEFAULT_TIME_STEP,
    passive_steps: int = 480,
    motor_dimensions: Iterable[int] = (1, 2, 4, 8, 16, 31),
    motor_amplitude: float = 0.35,
    motor_drive_steps: int = 240,
    dimensionality_repeats: int = 4,
    single_joint_indices: Iterable[int] | None = None,
) -> dict[str, object]:
    if time_step <= 0.0 or not math.isfinite(time_step):
        raise ValueError("time_step must be finite and positive")
    if passive_steps < 1:
        raise ValueError("passive_steps must be positive")
    if not 0.0 < motor_amplitude <= 1.0:
        raise ValueError("motor_amplitude must be within (0, 1]")
    if motor_drive_steps < 1:
        raise ValueError("motor_drive_steps must be positive")
    if dimensionality_repeats < 1:
        raise ValueError("dimensionality_repeats must be positive")

    p, client_id, plane_id, body = _connect_world(time_step)
    try:
        total_mass = _total_mass(p, client_id, body)
        settle = _settle(p, client_id, body)
        passive = (
            _passive_characterization(
                p,
                client_id,
                plane_id,
                body,
                steps=passive_steps,
            )
            if settle.converged
            else None
        )
        constitution = {
            "gravity_m_s2": GRAVITY,
            "physics_hz": 1.0 / time_step,
            "time_step_s": time_step,
            "motor_dof": len(body.motor_bindings),
            "directional_effector_channels": len(body.effector_ids),
            "mutually_exclusive_effector_groups": len(body.motor_bindings),
            "total_mass_kg": total_mass,
            "expected_weight_n": total_mass * GRAVITY,
            "settling": settle.as_dict(),
            "passive_postural_tone": True,
        }
    finally:
        p.disconnect(physicsClientId=client_id)

    dimensions = tuple(
        sorted({
            max(1, min(len(JOINT_SPECS), int(value)))
            for value in motor_dimensions
        })
    )
    fixed_amplitude = _dimensionality_trials(
        dimensions,
        amplitude=motor_amplitude,
        drive_steps=motor_drive_steps,
        time_step=time_step,
        repeats=dimensionality_repeats,
    )
    torque_budget, fixed_total_torque = _fixed_total_torque_trials(
        dimensions,
        reference_amplitude=motor_amplitude,
        drive_steps=motor_drive_steps,
        time_step=time_step,
        repeats=dimensionality_repeats,
    )
    single_joint = _single_joint_trials(
        amplitude=motor_amplitude,
        drive_steps=motor_drive_steps,
        time_step=time_step,
        joint_indices=(
            None
            if single_joint_indices is None
            else tuple(single_joint_indices)
        ),
    )

    return {
        "schema_version": 2,
        "study": "physics3d.constitution-audit",
        "constitution": constitution,
        "passive": passive,
        "fixed_amplitude_dimensionality": fixed_amplitude,
        "fixed_total_torque": {
            "budget_nm": torque_budget,
            "trials": fixed_total_torque,
        },
        "single_joint_characterization": single_joint,
        "interpretation_contract": {
            "observer_only": True,
            "changes_organism": False,
            "changes_physics_parameters": False,
            "purpose": (
                "Characterize passive stability, ground support, actuator work, "
                "velocity saturation and dimensionality independently before "
                "changing physical or learning parameters."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reproducible Physics3D constitution characterization"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("physics3d-constitution-audit.json"),
    )
    parser.add_argument("--passive-steps", type=int, default=480)
    parser.add_argument("--motor-amplitude", type=float, default=0.35)
    parser.add_argument("--motor-drive-steps", type=int, default=240)
    parser.add_argument("--dimensionality-repeats", type=int, default=4)
    args = parser.parse_args(argv)

    result = run_constitution_audit(
        passive_steps=args.passive_steps,
        motor_amplitude=args.motor_amplitude,
        motor_drive_steps=args.motor_drive_steps,
        dimensionality_repeats=args.dimensionality_repeats,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["run_constitution_audit"]
