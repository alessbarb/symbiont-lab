import inspect

import pytest

from symbiont_lab.physics3d.humanoid import (
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

    assert len(receptors) == 31
    assert len(effectors) == 16
    assert receptors == tuple(f"rec.{i}" for i in range(31))
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
