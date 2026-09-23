import math

import pytest

from symbiont_lab.studies.physics3d.constitution_audit import (
    GRAVITY,
    _connect_world,
    _contact_metrics,
    _settle,
    _total_mass,
    run_constitution_audit,
)


def test_passive_body_is_supported_by_ground_without_material_penetration():
    pybullet = pytest.importorskip("pybullet")
    p, client_id, plane_id, body = _connect_world()
    try:
        _settle(p, client_id, body)
        mass = _total_mass(p, client_id, body)
        expected_weight = mass * GRAVITY

        forces = []
        penetrations = []
        body.apply_effectors({})
        for _ in range(240):
            body.prepare_physics_substep()
            p.stepSimulation(physicsClientId=client_id)
            normal, penetration = _contact_metrics(
                p, client_id, body.body_id, plane_id
            )
            forces.append(normal)
            penetrations.append(penetration)

        mean_force = sum(forces) / len(forces)
        assert mass > 0.0
        assert expected_weight > 0.0
        # A passively settled dynamic body must be supported by the actual
        # PyBullet ground, not by a viewer-side visual floor.
        assert mean_force == pytest.approx(expected_weight, rel=0.20)
        # Millimetric solver penetration is acceptable; centimetric sinking is not.
        assert max(penetrations) < 0.01
    finally:
        p.disconnect(physicsClientId=client_id)


def test_constitution_audit_reports_mass_weight_ground_and_motor_scaling():
    pytest.importorskip("pybullet")
    result = run_constitution_audit(
        passive_steps=24,
        motor_dimensions=(1, 4),
        motor_amplitude=0.20,
        motor_drive_steps=12,
    )

    constitution = result["constitution"]
    passive = result["passive"]
    trials = result["motor_dimensionality"]

    assert constitution["gravity_m_s2"] == pytest.approx(9.81)
    assert constitution["physics_hz"] == pytest.approx(240.0)
    assert constitution["motor_dof"] == 31
    assert constitution["directional_effector_channels"] == 62
    assert constitution["total_mass_kg"] > 30.0
    assert constitution["expected_weight_n"] == pytest.approx(
        constitution["total_mass_kg"] * 9.81
    )

    assert math.isfinite(passive["reaction_to_weight_ratio"])
    assert passive["max_ground_penetration_m"] < 0.01

    assert [trial["active_dof"] for trial in trials] == [1, 4]
    assert all(math.isfinite(trial["mechanical_work_j"]) for trial in trials)
    assert result["interpretation_contract"]["changes_physics_parameters"] is False
