from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import fmean
from typing import Iterable

from symbiont_lab.physics3d.humanoid import (
    GROUND_MATERIAL,
    HumanoidPhysics,
    apply_surface_material,
    configure_physics_solver,
)

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
    mass = float(
        p.getDynamicsInfo(
            body.body_id,
            -1,
            physicsClientId=client_id,
        )[0]
    )
    for link_index in range(
        int(p.getNumJoints(body.body_id, physicsClientId=client_id))
    ):
        mass += float(
            p.getDynamicsInfo(
                body.body_id,
                link_index,
                physicsClientId=client_id,
            )[0]
        )
    return mass


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


def _contact_metrics(p, client_id: int, body_id: int, plane_id: int) -> tuple[float, float]:
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
    return normal_force, penetration


def _settle(
    p,
    client_id: int,
    body: HumanoidPhysics,
    *,
    max_steps: int = 1440,
    stable_samples: int = 48,
    linear_threshold: float = 0.025,
    angular_threshold: float = 0.05,
    joint_threshold: float = 0.08,
) -> int:
    body.apply_effectors({})
    stable = 0
    for step in range(1, max_steps + 1):
        body.prepare_physics_substep()
        p.stepSimulation(physicsClientId=client_id)

        linear_velocity, angular_velocity = p.getBaseVelocity(
            body.body_id,
            physicsClientId=client_id,
        )
        max_linear = max(abs(float(value)) for value in linear_velocity)
        max_angular = max(abs(float(value)) for value in angular_velocity)
        states = p.getJointStates(
            body.body_id,
            body.motor_joint_indices,
            physicsClientId=client_id,
        )
        max_joint = max((abs(float(state[1])) for state in states), default=0.0)

        if (
            max_linear <= linear_threshold
            and max_angular <= angular_threshold
            and max_joint <= joint_threshold
        ):
            stable += 1
            if stable >= stable_samples:
                return step
        else:
            stable = 0
    return max_steps


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
    max_linear_speed = 0.0
    max_angular_speed = 0.0

    for _ in range(steps):
        body.prepare_physics_substep()
        p.stepSimulation(physicsClientId=client_id)
        normal, penetration = _contact_metrics(
            p,
            client_id,
            body.body_id,
            plane_id,
        )
        normal_forces.append(normal)
        penetrations.append(penetration)

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
        "max_base_linear_speed_m_s": max_linear_speed,
        "max_base_angular_speed_rad_s": max_angular_speed,
    }


def _spread_indices(total: int, count: int) -> tuple[int, ...]:
    if count >= total:
        return tuple(range(total))
    if count <= 1:
        return (0,)
    return tuple(
        sorted({
            round(i * (total - 1) / (count - 1))
            for i in range(count)
        })
    )


def _motor_dimensionality_trial(
    active_dof: int,
    *,
    amplitude: float,
    drive_steps: int,
    time_step: float,
) -> dict[str, float | int]:
    p, client_id, plane_id, body = _connect_world(time_step)
    try:
        settle_steps = _settle(p, client_id, body)
        selected = _spread_indices(len(body.motor_bindings), active_dof)
        activations = {
            body.motor_bindings[index].positive_port: amplitude
            for index in selected
        }

        start_pos, _ = p.getBasePositionAndOrientation(
            body.body_id,
            physicsClientId=client_id,
        )
        previous = tuple(float(v) for v in start_pos)
        base_path = 0.0
        work = 0.0
        max_joint_speed = 0.0
        max_penetration = 0.0
        max_ground_reaction = 0.0

        body.apply_effectors(activations)
        for _ in range(drive_steps):
            body.prepare_physics_substep()
            p.stepSimulation(physicsClientId=client_id)
            work += body.mechanical_work_step(time_step)

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

            normal, penetration = _contact_metrics(
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
            "active_dof": len(selected),
            "active_directional_channels": len(selected),
            "amplitude": amplitude,
            "drive_steps": drive_steps,
            "settle_steps": settle_steps,
            "mechanical_work_j": work,
            "base_path_m": base_path,
            "net_base_displacement_m": math.dist(
                tuple(float(v) for v in start_pos),
                tuple(float(v) for v in end_pos),
            ),
            "max_joint_speed_rad_s": max_joint_speed,
            "max_ground_reaction_n": max_ground_reaction,
            "max_ground_penetration_m": max_penetration,
        }
    finally:
        p.disconnect(physicsClientId=client_id)


def run_constitution_audit(
    *,
    time_step: float = DEFAULT_TIME_STEP,
    passive_steps: int = 480,
    motor_dimensions: Iterable[int] = (1, 2, 4, 8, 16, 31),
    motor_amplitude: float = 0.35,
    motor_drive_steps: int = 240,
) -> dict[str, object]:
    if time_step <= 0.0 or not math.isfinite(time_step):
        raise ValueError("time_step must be finite and positive")
    if passive_steps < 1:
        raise ValueError("passive_steps must be positive")
    if not 0.0 < motor_amplitude <= 1.0:
        raise ValueError("motor_amplitude must be within (0, 1]")
    if motor_drive_steps < 1:
        raise ValueError("motor_drive_steps must be positive")

    p, client_id, plane_id, body = _connect_world(time_step)
    try:
        total_mass = _total_mass(p, client_id, body)
        settle_steps = _settle(p, client_id, body)
        passive = _passive_characterization(
            p,
            client_id,
            plane_id,
            body,
            steps=passive_steps,
        )
        constitution = {
            "gravity_m_s2": GRAVITY,
            "physics_hz": 1.0 / time_step,
            "time_step_s": time_step,
            "motor_dof": len(body.motor_bindings),
            "directional_effector_channels": len(body.effector_ids),
            "total_mass_kg": total_mass,
            "expected_weight_n": total_mass * GRAVITY,
            "settle_steps": settle_steps,
            "settle_time_s": settle_steps * time_step,
        }
    finally:
        p.disconnect(physicsClientId=client_id)

    dimensions = tuple(
        sorted({
            max(1, min(31, int(value)))
            for value in motor_dimensions
        })
    )
    motor_trials = [
        _motor_dimensionality_trial(
            dimension,
            amplitude=motor_amplitude,
            drive_steps=motor_drive_steps,
            time_step=time_step,
        )
        for dimension in dimensions
    ]

    return {
        "schema_version": 1,
        "study": "physics3d.constitution-audit",
        "constitution": constitution,
        "passive": passive,
        "motor_dimensionality": motor_trials,
        "interpretation_contract": {
            "observer_only": True,
            "changes_organism": False,
            "changes_physics_parameters": False,
            "purpose": (
                "Characterize the existing Physics3D constitution before tuning "
                "mass, gravity, torque, friction, solver, or motor learning."
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
    args = parser.parse_args(argv)

    result = run_constitution_audit(
        passive_steps=args.passive_steps,
        motor_amplitude=args.motor_amplitude,
        motor_drive_steps=args.motor_drive_steps,
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
