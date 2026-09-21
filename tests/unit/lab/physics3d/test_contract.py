import inspect

import pytest

from symbiont_lab.physics3d.humanoid import (
    BODY_KIND,
    BODY_MATERIAL,
    BODY_STATE_SCHEMA_VERSION,
    GROUND_MATERIAL,
    JOINT_AXES,
    JOINT_LIMITS,
    JOINT_SPECS,
    MECHANICAL_LIMIT_GUARD,
    MOTOR_DOF,
    PHYSICAL_RECEPTOR_COUNT,
    TOTAL_RECEPTOR_COUNT,
    HumanoidPhysics,
    SurfaceMaterial,
    apply_surface_material,
    build_anthropomorphic_urdf,
    effector_contract_ids,
    mechanical_joint_limits,
    interoceptive_receptor_contract_ids,
    physical_receptor_contract_ids,
    receptor_contract_ids,
)
from symbiont_lab.physics3d.apparatus import (
    OpaqueBodyInteroception,
    physics3d_cognition,
    physics3d_sensory_system,
)
from symbiont.core.physiology import LivingBodyState


def test_physics3d_contract_uses_only_opaque_port_ids():
    receptors = receptor_contract_ids()
    effectors = effector_contract_ids()

    assert len(receptors) == TOTAL_RECEPTOR_COUNT == 107
    assert len(effectors) == MOTOR_DOF * 2 == 62
    assert receptors == tuple(f"rec.{i}" for i in range(TOTAL_RECEPTOR_COUNT))
    assert effectors == tuple(f"eff.{i}" for i in range(MOTOR_DOF * 2))
    assert interoceptive_receptor_contract_ids() == tuple(
        f"rec.{i}" for i in range(PHYSICAL_RECEPTOR_COUNT, TOTAL_RECEPTOR_COUNT)
    )


def test_v3_body_is_generated_as_hard_limited_urdf():
    import xml.etree.ElementTree as ET

    root = ET.fromstring(build_anthropomorphic_urdf())
    joints = root.findall("joint")

    assert root.attrib["name"] == "symbiont_anthropomorphic_v3"
    assert len(joints) == MOTOR_DOF
    assert [joint.attrib["name"] for joint in joints] == [
        spec.name for spec in JOINT_SPECS
    ]

    for joint, spec in zip(joints, JOINT_SPECS):
        limit = joint.find("limit")
        dynamics = joint.find("dynamics")
        assert limit is not None
        assert dynamics is not None
        mechanical_lower, mechanical_upper = mechanical_joint_limits(spec)
        assert float(limit.attrib["lower"]) == pytest.approx(mechanical_lower)
        assert float(limit.attrib["upper"]) == pytest.approx(mechanical_upper)
        assert mechanical_lower > spec.lower
        assert mechanical_upper < spec.upper
        assert mechanical_lower - spec.lower <= MECHANICAL_LIMIT_GUARD + 1e-12
        assert spec.upper - mechanical_upper <= MECHANICAL_LIMIT_GUARD + 1e-12
        assert float(limit.attrib["effort"]) == pytest.approx(spec.max_motor_torque)
        assert float(limit.attrib["velocity"]) == pytest.approx(spec.max_velocity)
        assert float(dynamics.attrib["damping"]) == pytest.approx(spec.passive_damping)


def test_mechanical_guard_band_never_expands_anatomical_range():
    for spec in JOINT_SPECS:
        lower, upper = mechanical_joint_limits(spec)
        assert spec.lower < lower < upper < spec.upper


def test_v3_body_loader_does_not_use_soft_limit_multibody_path():
    source = inspect.getsource(HumanoidPhysics._create_body)
    assert "loadURDF" in source
    assert "createMultiBody" not in source


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
    genome, _graph, _limits = physics3d_cognition()

    assert genome.motor.slot_count == 62
    assert genome.genome_id == "genome_symbiont_physics3d_v8"
    assert genome.development.soft_node_budget == 192
    assert genome.development.soft_edge_budget == 1536
    assert genome.development.sense_node_budget == 128


def test_physics3d_runtime_does_not_call_parallel_symbiont_step():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime)
    assert "PrivateModelOrganismRuntime" in source
    assert "Symbiont(" not in source
    assert ".symbiont.step(" not in source



def test_physics3d_grants_body_sized_bounded_sensory_checkpoint_budget():
    sensory = physics3d_sensory_system()

    assert sensory.plasticity_enabled is True
    assert sensory.limits.max_active_sensors == 128
    assert sensory.limits.max_sensor_checkpoint_bytes == 1024 * 1024



def test_physics3d_opts_into_autonomous_validated_predictor_promotion():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime)
    assert source.count("auto_promote_predictors=True") >= 2



def test_humanoid_self_collision_excludes_direct_and_structural_neighbours():
    humanoid = HumanoidPhysics.__new__(HumanoidPhysics)
    humanoid._direct_pairs = {(-1, 0), (0, 1), (1, 2), (2, 3)}
    humanoid._structural_collision_exclusions = {(-1, 2), (2, 4)}

    assert humanoid._directly_connected_link_pairs() == {
        (-1, 0), (0, 1), (1, 2), (2, 3)
    }
    excluded = humanoid._self_collision_exclusions()
    assert (-1, 2) in excluded
    assert (2, 4) in excluded
    assert (0, 2) not in excluded
    assert (-1, 4) not in excluded


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
    humanoid._direct_pairs = {(-1, 0), (0, 1), (1, 2)}
    humanoid._structural_collision_exclusions = {(-1, 2), (2, 4)}

    humanoid._configure_self_collisions()

    assert len(fake.calls) == 496  # C(32, 2)
    disabled = [call for call in fake.calls if call[4] == 0]
    enabled = [call for call in fake.calls if call[4] == 1]
    assert len(disabled) == 5
    assert len(enabled) == 491
    assert any(call[2:5] == (-1, 2, 0) for call in fake.calls)
    assert any(call[2:5] == (2, 4, 0) for call in fake.calls)
    assert any(call[2:5] == (0, 2, 1) for call in fake.calls)



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
    assert set(JOINT_LIMITS) == set(range(MOTOR_DOF))
    for limit in JOINT_LIMITS.values():
        assert limit.lower < limit.upper


def test_humanoid_configures_joint_velocity_ceilings_in_bullet():
    class FakeBullet:
        def __init__(self):
            self.calls = []

        def changeDynamics(self, body_id, link_index, **kwargs):
            self.calls.append((body_id, link_index, kwargs))

    fake = FakeBullet()
    humanoid = HumanoidPhysics.__new__(HumanoidPhysics)
    humanoid.p = fake
    humanoid.body_id = 77
    humanoid.client_id = 9
    humanoid.motor_joint_indices = tuple(range(MOTOR_DOF))

    humanoid._configure_joint_dynamics()

    assert len(fake.calls) == MOTOR_DOF
    assert {call[1] for call in fake.calls} == set(range(MOTOR_DOF))
    for _body_id, link_index, kwargs in fake.calls:
        assert kwargs["maxJointVelocity"] > 0.0
        assert kwargs["physicsClientId"] == 9
        assert kwargs["maxJointVelocity"] == pytest.approx(
            __import__(
                "symbiont_lab.physics3d.humanoid",
                fromlist=["JOINT_SPECS"],
            ).JOINT_SPECS[link_index].max_velocity
        )


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


def test_humanoid_restore_rejects_untyped_vectors_before_pybullet_calls():
    humanoid = HumanoidPhysics.__new__(HumanoidPhysics)
    humanoid.p = object()
    humanoid.body_id = 11
    humanoid.client_id = 3

    with pytest.raises(ValueError, match="base_position must be a list or tuple"):
        humanoid.restore_physical_state(
            {
                "schema_version": BODY_STATE_SCHEMA_VERSION,
                "body_kind": BODY_KIND,
                "base_position": object(),
            }
        )


def test_humanoid_restore_rejects_invalid_joint_records():
    class FakeBullet:
        def __init__(self):
            self.calls = []

        def resetBasePositionAndOrientation(self, *args, **kwargs):
            self.calls.append("resetBasePositionAndOrientation")

        def resetBaseVelocity(self, *args, **kwargs):
            self.calls.append("resetBaseVelocity")

    humanoid = HumanoidPhysics.__new__(HumanoidPhysics)
    fake = FakeBullet()
    humanoid.p = fake
    humanoid.body_id = 11
    humanoid.client_id = 3
    humanoid.motor_joint_indices = tuple(sorted(JOINT_LIMITS))

    with pytest.raises(ValueError, match="each joint state must be a mapping"):
        humanoid.restore_physical_state(
            {
                "schema_version": BODY_STATE_SCHEMA_VERSION,
                "body_kind": BODY_KIND,
                "base_position": [0.0, 0.0, 1.0],
                "base_orientation": [0.0, 0.0, 0.0, 1.0],
                "linear_velocity": [0.0, 0.0, 0.0],
                "angular_velocity": [0.0, 0.0, 0.0],
                "joints": [None],
            }
        )
    assert fake.calls == []


def test_body_and_ground_have_nonzero_friction_without_semantic_specialization():
    assert BODY_MATERIAL.lateral_friction > 0.0
    assert GROUND_MATERIAL.lateral_friction > 0.0
    assert BODY_MATERIAL.spinning_friction >= 0.0
    assert GROUND_MATERIAL.spinning_friction >= 0.0
    assert BODY_MATERIAL.restitution < 0.1
    assert GROUND_MATERIAL.restitution < 0.1


def test_runtime_module_source_compiles():
    import pathlib
    import symbiont_lab.physics3d.runtime as runtime

    source = pathlib.Path(runtime.__file__).read_text(encoding="utf-8")
    compile(source, runtime.__file__, "exec")


def test_runtime_imports_canonical_solver_configuration():
    import symbiont_lab.physics3d.runtime as runtime

    assert runtime.configure_physics_solver is not None


def test_runtime_reapplies_motor_command_each_physics_substep():
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


def test_l3_receptors_remain_opaque_ordinals():
    receptors = receptor_contract_ids()
    assert receptors == tuple(f"rec.{i}" for i in range(TOTAL_RECEPTOR_COUNT))
    for forbidden in (
        "resource", "energy", "hunger", "integrity", "temperature",
        "fatigue", "stress", "damage", "repair", "pressure",
    ):
        assert all(forbidden not in receptor for receptor in receptors)


def test_l3_interoceptive_channels_are_independent():
    surface = OpaqueBodyInteroception()
    baseline = LivingBodyState(
        energy_reserve=1.0,
        max_energy=2.0,
        structural_integrity=0.8,
        temperature=0.4,
        fatigue=0.2,
    )
    values = surface.sample(baseline)

    mutations = (
        ("energy_reserve", 0.4),
        ("structural_integrity", 0.3),
        ("temperature", 0.9),
        ("fatigue", 0.7),
    )
    for expected_slot, (field_name, value) in enumerate(mutations):
        changed = LivingBodyState(
            energy_reserve=baseline.energy_reserve,
            max_energy=baseline.max_energy,
            structural_integrity=baseline.structural_integrity,
            temperature=baseline.temperature,
            fatigue=baseline.fatigue,
        )
        setattr(changed, field_name, value)
        sample = surface.sample(changed)
        changed_ids = {
            receptor_id
            for receptor_id in surface.receptor_ids
            if sample[receptor_id] != values[receptor_id]
        }
        assert changed_ids == {surface.receptor_ids[expected_slot]}


def test_l3_interoception_mapping_is_label_invariant_under_permutation():
    state = LivingBodyState(
        energy_reserve=0.6,
        max_energy=2.0,
        structural_integrity=0.7,
        temperature=0.3,
        fatigue=0.9,
    )
    canonical = OpaqueBodyInteroception(
        source_ordinals_by_slot=(0, 1, 2, 3)
    )
    permuted = OpaqueBodyInteroception(
        source_ordinals_by_slot=(2, 0, 3, 1)
    )

    canonical_values = tuple(canonical.sample(state).values())
    permuted_values = tuple(permuted.sample(state).values())

    assert permuted_values == (
        canonical_values[2],
        canonical_values[0],
        canonical_values[3],
        canonical_values[1],
    )
    assert state == LivingBodyState(
        energy_reserve=0.6,
        max_energy=2.0,
        structural_integrity=0.7,
        temperature=0.3,
        fatigue=0.9,
    )


def test_l3_local_contact_loads_are_independent_physical_channels():
    class FakeBullet:
        def getJointState(self, *_args, **_kwargs):
            return (0.0, 0.0, 0.0, 0.0)

        def getBasePositionAndOrientation(self, *_args, **_kwargs):
            return ((0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0))

        def getBaseVelocity(self, *_args, **_kwargs):
            return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

        def getContactPoints(self, *_args, **_kwargs):
            quiet = [0.0] * 10
            left = [0.0] * 10
            right = [0.0] * 10
            quiet[3], quiet[9] = -1, 0.0
            left[3], left[9] = 5, 24.0
            right[3], right[9] = 11, 72.0
            return (tuple(quiet), tuple(left), tuple(right))

    body = HumanoidPhysics.__new__(HumanoidPhysics)
    body.p = FakeBullet()
    body.client_id = 1
    body.body_id = 2
    body.motor_joint_indices = tuple(sorted(JOINT_LIMITS))
    body.receptor_ids = physical_receptor_contract_ids()
    body._contact_links = (-1, 5, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23)
    body._external_field_signal = 0.0
    body._sensor_values = {}

    values = body.sample_receptors()

    # 62 proprioception + 10 global kinematics + 15 contact-presence + 1 field.
    assert values["rec.88"] == pytest.approx(0.0)
    assert values["rec.89"] > 0.0
    assert values["rec.90"] > values["rec.89"]


def test_l3_checkpoint_preserves_only_opaque_ordinal_mapping():
    surface = OpaqueBodyInteroception(
        source_ordinals_by_slot=(3, 1, 0, 2)
    )
    checkpoint = surface.checkpoint()

    assert checkpoint == {
        "schema_version": 1,
        "source_ordinals_by_slot": [3, 1, 0, 2],
    }
    serialized = repr(checkpoint).lower()
    for forbidden in (
        "reserve", "integrity", "temperature", "fatigue", "hunger",
        "damage", "repair", "stress",
    ):
        assert forbidden not in serialized

    restored = OpaqueBodyInteroception.from_checkpoint(checkpoint)
    assert restored.source_ordinals_by_slot == (3, 1, 0, 2)


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



def test_physics3d_newborns_use_sensorimotor_babbling_constitution():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.__init__)
    assert 'motor_exploration_mode="babbling"' in source
    assert 'effective.get("motor_exploration_mode") != "babbling"' in source
    assert '"genome_symbiont_physics3d_v8"' in source



def test_v3_hard_limited_body_exposes_multiple_rotational_axes():
    assert set(JOINT_AXES) == set(JOINT_LIMITS)
    axes = set(JOINT_AXES.values())

    assert (1.0, 0.0, 0.0) in axes
    assert (0.0, 1.0, 0.0) in axes
    assert (0.0, 0.0, 1.0) in axes
    assert JOINT_AXES[0] == (0.0, 0.0, 1.0)
    assert JOINT_AXES[1] == (1.0, 0.0, 0.0)


def test_physics3d_l4_uses_one_physical_energy_pool_for_all_metabolism() -> None:
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.__init__)
    assert "physical_energy_capacity = sum(metabolic_capacity.values())" in source
    assert "living_body_state=living_body_state" in source
    assert 'genome_symbiont_physics3d_v8' in inspect.getsource(
        runtime.PyBulletEmbodimentRuntime.__init__
    )
