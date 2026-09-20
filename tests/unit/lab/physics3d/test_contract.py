import inspect

import pytest

from symbiont_lab.physics3d.humanoid import (
    BODY_MATERIAL,
    GROUND_MATERIAL,
    JOINT_LIMITS,
    HumanoidPhysics,
    JointLimit,
    SurfaceMaterial,
    apply_surface_material,
    effector_contract_ids,
    receptor_contract_ids,
)
from symbiont_lab.physics3d.apparatus import (
    physics3d_cognition,
    physics3d_sensory_system,
)


def test_physics3d_contract_uses_only_opaque_port_ids():
    receptors = receptor_contract_ids()
    effectors = effector_contract_ids()

    assert len(receptors) == 33
    assert len(effectors) == 16
    assert receptors == tuple(f"rec.{i}" for i in range(33))
    assert effectors == tuple(f"eff.{i}" for i in range(16))


def test_effector_contract_rejects_non_positive_motor_count():
    with pytest.raises(ValueError):
        effector_contract_ids(0)


def test_physics3d_optional_dependency_is_lazy():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime)
    assert "import pybullet as p" in source
    assert "PyBullet is optional" in source


def test_anatomical_labels_do_not_live_in_core_symbiont_surface():
    import symbiont.core.symbiont as symbiont

    source = inspect.getsource(symbiont).lower()
    for anatomical_term in ("knee", "elbow", "shoulder", "hip", "thigh", "shin"):
        assert anatomical_term not in source



def test_physics3d_uses_canonical_runtime_motor_constitution():
    genome, _graph, _limits = physics3d_cognition(motor_slots=16)

    assert genome.motor.slot_count == 16
    assert genome.genome_id == "genome_symbiont_physics3d_v1"


def test_physics3d_runtime_does_not_call_parallel_symbiont_step():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime)
    assert "PrivateModelOrganismRuntime" in source
    assert "Symbiont(" not in source
    assert ".symbiont.step(" not in source



def test_physics3d_grants_body_sized_bounded_sensory_checkpoint_budget():
    sensory = physics3d_sensory_system()

    assert sensory.plasticity_enabled is True
    assert sensory.limits.max_active_sensors == 64
    assert sensory.limits.max_sensor_checkpoint_bytes == 512 * 1024



def test_physics3d_opts_into_autonomous_validated_predictor_promotion():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime)
    assert source.count("auto_promote_predictors=True") >= 2



def test_humanoid_self_collision_excludes_only_direct_joint_neighbours():
    excluded = HumanoidPhysics._directly_connected_link_pairs()

    assert len(excluded) == 10
    assert (-1, 0) in excluded
    assert (0, 2) in excluded
    assert (2, 3) in excluded
    assert (-1, 6) in excluded
    assert (6, 7) in excluded

    # Non-adjacent pairs that must remain physically collidable.
    assert (0, 3) not in excluded      # torso <-> lower arm
    assert (2, 4) not in excluded      # left/right upper arms
    assert (6, 8) not in excluded      # left/right thighs
    assert (-1, 7) not in excluded     # pelvis <-> left shin


def test_humanoid_configures_all_self_collision_pairs_explicitly():
    class FakeBullet:
        def __init__(self):
            self.calls = []

        def setCollisionFilterPair(
            self,
            body_a,
            body_b,
            link_a,
            link_b,
            *,
            enableCollision,
            physicsClientId,
        ):
            self.calls.append(
                (body_a, body_b, link_a, link_b, enableCollision, physicsClientId)
            )

    fake = FakeBullet()
    humanoid = HumanoidPhysics.__new__(HumanoidPhysics)
    humanoid.p = fake
    humanoid.client_id = 7
    humanoid.body_id = 99

    humanoid._configure_self_collisions()

    assert len(fake.calls) == 55  # C(11, 2)
    disabled = [call for call in fake.calls if call[4] == 0]
    enabled = [call for call in fake.calls if call[4] == 1]
    assert len(disabled) == 10
    assert len(enabled) == 45
    assert any(call[2:5] == (0, 3, 1) for call in fake.calls)
    assert any(call[2:5] == (-1, 7, 1) for call in fake.calls)



def test_new_physics3d_subjects_do_not_reuse_one_fixed_organism_identity():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime)
    assert 'organism_id="symbiont:3d-subject"' not in source
    assert "secrets.token_hex(8)" in source



def test_unified_viewer_mode_keeps_pybullet_native_gui_disabled():
    import symbiont_lab.physics3d.cli as cli

    source = inspect.getsource(cli.run)
    assert "gui=(not headless and not show_monitor)" in source
    assert "UnifiedViewerProcess" in source


def test_passive_camera_render_does_not_enter_organism_contract():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.render_camera_frame)
    assert "getCameraImage" in source
    assert "organism.tick" not in source
    assert "signal_knowledge" not in source
    assert "experience_ledger" not in source



def test_unified_viewer_rendering_is_not_in_canonical_runtime_loop():
    import symbiont_lab.physics3d.cli as cli

    source = inspect.getsource(cli.run)
    assert "render_camera_frame(" not in source
    assert "physical_state=runtime.passive_physical_state()" in source



def test_every_motor_joint_has_one_bounded_mechanical_limit():
    assert set(JOINT_LIMITS) == set(range(2, 10))
    for limit in JOINT_LIMITS.values():
        assert limit.lower < limit.upper
        assert 0.0 < limit.stop_margin < (limit.upper - limit.lower) / 2.0
        assert limit.stiffness > 0.0
        assert limit.damping >= 0.0
        assert limit.max_stop_torque > 0.0


def test_joint_stop_torque_is_passive_directional_and_bounded():
    limit = JointLimit(
        lower=-1.0,
        upper=1.0,
        stop_margin=0.1,
        stiffness=100.0,
        damping=5.0,
        max_stop_torque=25.0,
    )

    assert HumanoidPhysics._joint_stop_torque(
        limit,
        position=0.0,
        velocity=0.0,
    ) == 0.0

    lower_push = HumanoidPhysics._joint_stop_torque(
        limit,
        position=-1.2,
        velocity=-1.0,
    )
    upper_push = HumanoidPhysics._joint_stop_torque(
        limit,
        position=1.2,
        velocity=1.0,
    )
    assert 0.0 < lower_push <= 25.0
    assert -25.0 <= upper_push < 0.0


def test_surface_material_propagates_contact_physics_explicitly():
    class FakeBullet:
        def __init__(self):
            self.kwargs = None

        def changeDynamics(self, body_id, link_index, **kwargs):
            self.kwargs = (body_id, link_index, kwargs)

    fake = FakeBullet()
    material = SurfaceMaterial(
        lateral_friction=0.7,
        spinning_friction=0.04,
        rolling_friction=0.003,
        restitution=0.1,
        linear_damping=0.02,
        angular_damping=0.06,
    )

    apply_surface_material(
        fake,
        11,
        3,
        material,
        client_id=9,
    )

    body_id, link_index, kwargs = fake.kwargs
    assert (body_id, link_index) == (11, 3)
    assert kwargs == {
        "lateralFriction": 0.7,
        "spinningFriction": 0.04,
        "rollingFriction": 0.003,
        "restitution": 0.1,
        "linearDamping": 0.02,
        "angularDamping": 0.06,
        "physicsClientId": 9,
    }


def test_body_and_ground_have_nonzero_friction_without_semantic_specialization():
    assert BODY_MATERIAL.lateral_friction > 0.0
    assert GROUND_MATERIAL.lateral_friction > 0.0
    assert BODY_MATERIAL.spinning_friction >= 0.0
    assert GROUND_MATERIAL.spinning_friction >= 0.0
    assert BODY_MATERIAL.restitution < 0.1
    assert GROUND_MATERIAL.restitution < 0.1


def test_runtime_reapplies_passive_joint_stops_each_physics_substep():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.step)
    assert "self.apparatus.prepare_physics_substep()" in source
    assert source.index("prepare_physics_substep()") < source.index("stepSimulation(")



def test_physics3d_locomotion_constitution_uses_explicit_metabolism():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.__init__)
    assert "explicit_metabolism=True" in source
    assert "replenishment={kind: 0.0 for kind in metabolic_capacity}" in source
    assert "interoception_mode=\"absent\"" in source


def test_ecological_receptors_remain_opaque_ordinals():
    receptors = receptor_contract_ids()
    assert receptors[-2:] == ("rec.31", "rec.32")
    assert all("resource" not in receptor for receptor in receptors)
    assert all("energy" not in receptor for receptor in receptors)
    assert all("hunger" not in receptor for receptor in receptors)


def test_resource_ground_truth_is_evaluator_only():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.step)
    assert "resource_distance" in source
    assert "set_opaque_environment_state" in source
    assert "resource_distance=" not in inspect.getsource(
        runtime.PyBulletEmbodimentRuntime.checkpoint
    )



def test_physics3d_applies_all_concurrent_actuations_in_one_tick():
    from types import SimpleNamespace
    from symbiont.actuation.types import Actuation
    from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

    applied = {}

    class Apparatus:
        def apply_effectors(self, physical):
            applied.update(physical)

    runtime = PyBulletEmbodimentRuntime.__new__(PyBulletEmbodimentRuntime)
    runtime.apparatus = Apparatus()
    runtime._actuator_to_effector = {
        "a": "motor.0",
        "b": "motor.3",
        "c": "motor.7",
    }
    runtime.organism = SimpleNamespace(
        last_actuations=(
            Actuation("a", 0.9, 0.8, 0.1, 1.0),
            Actuation("b", 0.7, 0.6, 0.1, 1.0),
            Actuation("c", 0.5, 0.4, 0.1, 1.0),
        )
    )

    active = runtime._apply_runtime_actuation()

    assert active == 3
    assert applied == {
        "motor.0": 0.8,
        "motor.3": 0.6,
        "motor.7": 0.4,
    }
