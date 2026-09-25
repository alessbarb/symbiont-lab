from __future__ import annotations

import math
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class SettlingResult:
    converged: bool
    steps: int
    stable_samples_required: int
    stable_samples_observed: int
    residual_linear_speed_m_s: float
    residual_angular_speed_rad_s: float
    residual_joint_speed_rad_s: float
    residual_joint_reported_speed_rad_s: float = 0.0
    peak_joint_index: int | None = None
    peak_joint_name: str | None = None
    peak_joint_position_rad: float | None = None
    peak_joint_reported_velocity_rad_s: float | None = None
    peak_joint_applied_torque_nm: float | None = None
    peak_joint_contact_count: int = 0
    peak_joint_contacts: tuple[str, ...] = ()

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
    last_reported_joint = 0.0
    peak_joint_index: int | None = None
    peak_joint_name: str | None = None
    peak_joint_position_rad: float | None = None
    peak_joint_reported_velocity_rad_s: float | None = None
    peak_joint_applied_torque_nm: float | None = None
    peak_joint_contact_count = 0
    peak_joint_contacts: tuple[str, ...] = ()

    if hasattr(pybullet_module, "getPhysicsEngineParameters"):
        parameters = pybullet_module.getPhysicsEngineParameters(
            physicsClientId=client_id,
        )
    else:
        parameters = {}
    time_step = float(parameters.get("fixedTimeStep", 1.0 / 240.0))
    if not math.isfinite(time_step) or time_step <= 0.0:
        raise RuntimeError("Physics3D settling requires a finite positive time step")

    initial_states = pybullet_module.getJointStates(
        body.body_id,
        body.motor_joint_indices,
        physicsClientId=client_id,
    )
    previous_positions = tuple(float(state[0]) for state in initial_states)

    for step in range(1, max_steps + 1):
        body.prepare_physics_substep()
        pybullet_module.stepSimulation(physicsClientId=client_id)

        linear_velocity, angular_velocity = pybullet_module.getBaseVelocity(
            body.body_id,
            physicsClientId=client_id,
        )
        last_linear = math.sqrt(sum(float(value) ** 2 for value in linear_velocity))
        last_angular = math.sqrt(sum(float(value) ** 2 for value in angular_velocity))
        states = pybullet_module.getJointStates(
            body.body_id,
            body.motor_joint_indices,
            physicsClientId=client_id,
        )
        positions = tuple(float(state[0]) for state in states)
        reported_speeds = tuple(abs(float(state[1])) for state in states)
        observed_speeds = tuple(
            abs(position - previous) / time_step
            for position, previous in zip(positions, previous_positions)
        )
        previous_positions = positions

        last_joint = max(observed_speeds, default=0.0)
        last_reported_joint = max(reported_speeds, default=0.0)
        if reported_speeds:
            peak_ordinal = max(
                range(len(reported_speeds)),
                key=reported_speeds.__getitem__,
            )
            peak_joint_index = int(body.motor_joint_indices[peak_ordinal])
            peak_joint_position_rad = positions[peak_ordinal]
            peak_joint_reported_velocity_rad_s = float(states[peak_ordinal][1])
            try:
                info = pybullet_module.getJointInfo(
                    body.body_id,
                    peak_joint_index,
                    physicsClientId=client_id,
                )
                raw_name = info[1]
                peak_joint_name = (
                    raw_name.decode("utf-8") if isinstance(raw_name, bytes) else str(raw_name)
                )
            except Exception:
                peak_joint_name = None

            try:
                joint_state = states[peak_ordinal]
                joint_state[2] if len(joint_state) > 2 else None
                peak_joint_applied_torque_nm = (
                    float(joint_state[3])
                    if len(joint_state) > 3 and isinstance(joint_state[3], (int, float))
                    else None
                )
            except Exception:
                peak_joint_applied_torque_nm = None

            peak_joint_contact_count = 0
            peak_joint_contacts = ()
            if hasattr(pybullet_module, "getContactPoints"):
                try:
                    contacts = pybullet_module.getContactPoints(
                        bodyA=body.body_id,
                        physicsClientId=client_id,
                    )
                    contact_descriptions: list[str] = []
                    for item in contacts:
                        if len(item) <= 4:
                            continue
                        link_a = int(item[3])
                        link_b = int(item[4])
                        if link_a != peak_joint_index and link_b != peak_joint_index:
                            continue
                        body_a = int(item[1])
                        body_b = int(item[2])
                        other_body = body_b if body_a == body.body_id else body_a
                        other_link = link_b if link_a == peak_joint_index else link_a
                        other_name = str(other_link)
                        if other_body == body.body_id and other_link >= 0:
                            try:
                                raw_other = pybullet_module.getJointInfo(
                                    body.body_id,
                                    other_link,
                                    physicsClientId=client_id,
                                )[12]
                                other_name = (
                                    raw_other.decode("utf-8")
                                    if isinstance(raw_other, bytes)
                                    else str(raw_other)
                                )
                            except Exception:
                                pass
                        contact_descriptions.append(f"body={other_body},link={other_name}")
                    peak_joint_contact_count = len(contact_descriptions)
                    peak_joint_contacts = tuple(sorted(contact_descriptions))
                except Exception:
                    peak_joint_contact_count = 0
                    peak_joint_contacts = ()

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
                    residual_linear_speed_m_s=last_linear,
                    residual_angular_speed_rad_s=last_angular,
                    residual_joint_speed_rad_s=last_joint,
                    residual_joint_reported_speed_rad_s=last_reported_joint,
                    peak_joint_index=peak_joint_index,
                    peak_joint_name=peak_joint_name,
                    peak_joint_position_rad=peak_joint_position_rad,
                    peak_joint_reported_velocity_rad_s=peak_joint_reported_velocity_rad_s,
                    peak_joint_applied_torque_nm=peak_joint_applied_torque_nm,
                    peak_joint_contact_count=peak_joint_contact_count,
                    peak_joint_contacts=peak_joint_contacts,
                )
        else:
            stable = 0

    return SettlingResult(
        converged=False,
        steps=max_steps,
        stable_samples_required=stable_samples,
        stable_samples_observed=stable,
        residual_linear_speed_m_s=last_linear,
        residual_angular_speed_rad_s=last_angular,
        residual_joint_speed_rad_s=last_joint,
        residual_joint_reported_speed_rad_s=last_reported_joint,
        peak_joint_index=peak_joint_index,
        peak_joint_name=peak_joint_name,
        peak_joint_position_rad=peak_joint_position_rad,
        peak_joint_reported_velocity_rad_s=peak_joint_reported_velocity_rad_s,
        peak_joint_applied_torque_nm=peak_joint_applied_torque_nm,
        peak_joint_contact_count=peak_joint_contact_count,
        peak_joint_contacts=peak_joint_contacts,
    )


__all__ = ["SettlingResult", "settle_passive_body"]
