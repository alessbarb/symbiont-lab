import math

import pytest

from symbiont_lab.physics3d.settling import settle_passive_body
from symbiont_lab.studies.physics3d.constitution_audit import (
    GRAVITY,
    _connect_world,
    _contact_metrics,
    _total_mass,
    run_constitution_audit,
)


def test_passive_body_converges_and_is_supported_by_ground():
    pytest.importorskip("pybullet")
    p, client_id, plane_id, body = _connect_world()
    try:
        settling = settle_passive_body(p, client_id, body)
        assert settling.converged is True
        assert settling.steps < 1440

        mass = _total_mass(p, client_id, body)
        expected_weight = mass * GRAVITY

        forces = []
        penetrations = []
        body.apply_effectors({})
        for _ in range(240):
            body.prepare_physics_substep()
            p.stepSimulation(physicsClientId=client_id)
            normal, penetration, _contacts = _contact_metrics(
                p, client_id, body.body_id, plane_id
            )
            forces.append(normal)
            penetrations.append(penetration)

        mean_force = sum(forces) / len(forces)
        assert mass > 0.0
        assert expected_weight > 0.0
        assert mean_force == pytest.approx(expected_weight, rel=0.20)
        assert max(penetrations) < 0.01
    finally:
        p.disconnect(physicsClientId=client_id)


def test_constitution_audit_separates_dimensionality_from_total_torque():
    pytest.importorskip("pybullet")
    result = run_constitution_audit(
        passive_steps=24,
        motor_dimensions=(1, 4),
        motor_amplitude=0.20,
        motor_drive_steps=12,
        dimensionality_repeats=1,
        single_joint_indices=(0, 1),
    )

    assert result["schema_version"] == 2
    constitution = result["constitution"]
    settling = constitution["settling"]
    passive = result["passive"]
    fixed_amplitude = result["fixed_amplitude_dimensionality"]
    fixed_torque = result["fixed_total_torque"]
    single_joint = result["single_joint_characterization"]

    assert constitution["gravity_m_s2"] == pytest.approx(9.81)
    assert constitution["physics_hz"] == pytest.approx(240.0)
    assert constitution["motor_dof"] == 31
    assert constitution["directional_effector_channels"] == 62
    assert constitution["mutually_exclusive_effector_groups"] == 31
    assert constitution["total_mass_kg"] > 30.0
    assert constitution["expected_weight_n"] == pytest.approx(
        constitution["total_mass_kg"] * 9.81
    )
    assert constitution["passive_postural_tone"] is True
    assert settling["converged"] is True

    assert passive is not None
    assert math.isfinite(passive["reaction_to_weight_ratio"])
    assert passive["max_ground_penetration_m"] < 0.01
    assert passive["mean_ground_contact_points"] >= 1.0

    assert [trial["active_dof"] for trial in fixed_amplitude] == [1, 4]
    assert all(trial["mode"] == "fixed_amplitude" for trial in fixed_amplitude)
    assert all(math.isfinite(trial["absolute_actuator_work_j"]) for trial in fixed_amplitude)

    torque_trials = fixed_torque["trials"]
    assert [trial["active_dof"] for trial in torque_trials] == [1, 4]
    assert all(trial["mode"] == "fixed_total_torque" for trial in torque_trials)
    for trial in torque_trials:
        assert trial["commanded_torque_capacity_nm"] == pytest.approx(
            fixed_torque["budget_nm"],
            rel=1e-6,
        )

    assert [trial["joint_index"] for trial in single_joint] == [0, 1]
    assert all(0.0 <= trial["velocity_saturation_ratio"] <= 1.0 for trial in single_joint)
    assert result["interpretation_contract"]["changes_physics_parameters"] is False


def test_audit_work_decomposition_is_consistent():
    pytest.importorskip("pybullet")
    result = run_constitution_audit(
        passive_steps=8,
        motor_dimensions=(1,),
        motor_amplitude=0.15,
        motor_drive_steps=8,
        dimensionality_repeats=1,
        single_joint_indices=(0,),
    )
    trial = result["fixed_amplitude_dimensionality"][0]
    assert trial["valid"] is True
    assert trial["absolute_actuator_work_j"] == pytest.approx(
        trial["positive_actuator_work_j"] + trial["negative_actuator_work_j"]
    )
    assert trial["net_actuator_work_j"] == pytest.approx(
        trial["positive_actuator_work_j"] - trial["negative_actuator_work_j"]
    )
