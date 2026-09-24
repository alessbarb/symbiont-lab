from __future__ import annotations

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True, slots=True)
class SettlingResult:
    converged: bool
    steps: int
    stable_samples_required: int
    stable_samples_observed: int
    max_linear_speed_m_s: float
    max_angular_speed_rad_s: float
    max_joint_speed_rad_s: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def settle_passive_body(
    pybullet_module,
    client_id: int,
    body,
    *,
    max_steps: int = 1440,
    stable_samples: int = 48,
    linear_threshold: float = 0.025,
    angular_threshold: float = 0.05,
    joint_threshold: float = 0.08,
) -> SettlingResult:
    """Measure passive mechanical convergence without inventing controller input."""
    if max_steps < 1 or stable_samples < 1:
        raise ValueError("settling bounds must be positive")
    for value, name in (
        (linear_threshold, "linear_threshold"),
        (angular_threshold, "angular_threshold"),
        (joint_threshold, "joint_threshold"),
    ):
        if not math.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError(f"{name} must be finite and non-negative")

    body.apply_effectors({})
    stable = 0
    last_linear = 0.0
    last_angular = 0.0
    last_joint = 0.0

    for step in range(1, max_steps + 1):
        body.prepare_physics_substep()
        pybullet_module.stepSimulation(physicsClientId=client_id)

        linear_velocity, angular_velocity = pybullet_module.getBaseVelocity(
            body.body_id,
            physicsClientId=client_id,
        )
        last_linear = math.sqrt(
            sum(float(value) ** 2 for value in linear_velocity)
        )
        last_angular = math.sqrt(
            sum(float(value) ** 2 for value in angular_velocity)
        )
        states = pybullet_module.getJointStates(
            body.body_id,
            body.motor_joint_indices,
            physicsClientId=client_id,
        )
        last_joint = max(
            (abs(float(state[1])) for state in states),
            default=0.0,
        )

        if (
            last_linear <= linear_threshold
            and last_angular <= angular_threshold
            and last_joint <= joint_threshold
        ):
            stable += 1
            if stable >= stable_samples:
                return SettlingResult(
                    converged=True,
                    steps=step,
                    stable_samples_required=stable_samples,
                    stable_samples_observed=stable,
                    max_linear_speed_m_s=last_linear,
                    max_angular_speed_rad_s=last_angular,
                    max_joint_speed_rad_s=last_joint,
                )
        else:
            stable = 0

    return SettlingResult(
        converged=False,
        steps=max_steps,
        stable_samples_required=stable_samples,
        stable_samples_observed=stable,
        max_linear_speed_m_s=last_linear,
        max_angular_speed_rad_s=last_angular,
        max_joint_speed_rad_s=last_joint,
    )


__all__ = ["SettlingResult", "settle_passive_body"]
