import math

import pytest

from symbiont_lab.physics3d.humanoid import (
    HumanoidPhysics,
    JOINT_LIMIT_SOLVER_TOLERANCE,
    JOINT_SPECS,
)


def test_humanoid_v3_hard_limits_hold_under_deterministic_actuation():
    pybullet = pytest.importorskip("pybullet")
    client_id = pybullet.connect(pybullet.DIRECT)
    try:
        pybullet.setGravity(0.0, 0.0, -9.81, physicsClientId=client_id)
        pybullet.setTimeStep(1.0 / 240.0, physicsClientId=client_id)
        plane_shape = pybullet.createCollisionShape(
            pybullet.GEOM_PLANE,
            planeNormal=(0.0, 0.0, 1.0),
            physicsClientId=client_id,
        )
        pybullet.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=plane_shape,
            physicsClientId=client_id,
        )

        body = HumanoidPhysics(pybullet, client_id)
        start_position, _ = pybullet.getBasePositionAndOrientation(
            body.body_id, physicsClientId=client_id
        )

        max_speed_seen = 0.0
        max_total_speed_seen = 0.0
        max_limit_violation = 0.0

        # Broad, deterministic excitation of the complete opaque motor surface.
        for step in range(360):
            activations = {}
            for index, effector_id in enumerate(body.effector_ids):
                phase = (step + index * 7) % 80
                activations[effector_id] = 0.65 if phase < 20 else 0.0
            body.apply_effectors(activations)

            for _ in range(2):
                body.prepare_physics_substep()
                pybullet.stepSimulation(physicsClientId=client_id)

                states = pybullet.getJointStates(
                    body.body_id,
                    body.motor_joint_indices,
                    physicsClientId=client_id,
                )
                speeds = [abs(float(state[1])) for state in states]
                max_speed_seen = max(max_speed_seen, max(speeds, default=0.0))
                max_total_speed_seen = max(
                    max_total_speed_seen, sum(speeds)
                )

                for ordinal, state in enumerate(states):
                    position = float(state[0])
                    spec = JOINT_SPECS[ordinal]
                    violation = max(
                        spec.lower - position,
                        position - spec.upper,
                        0.0,
                    )
                    max_limit_violation = max(max_limit_violation, violation)

        assert math.isfinite(max_speed_seen)
        assert math.isfinite(max_total_speed_seen)
        assert max_speed_seen <= max(spec.max_velocity for spec in JOINT_SPECS) + 1e-6
        assert max_total_speed_seen < 150.0
        # Bullet/URDF owns the anatomical stop. No controller spring may be
        # needed to keep a joint inside its declared constitution.
        assert max_limit_violation < JOINT_LIMIT_SOLVER_TOLERANCE

        end_position, _ = pybullet.getBasePositionAndOrientation(
            body.body_id, physicsClientId=client_id
        )
        displacement = math.dist(
            tuple(float(value) for value in start_position),
            tuple(float(value) for value in end_position),
        )
        assert math.isfinite(displacement)
        assert displacement < 8.0
    finally:
        pybullet.disconnect(physicsClientId=client_id)
