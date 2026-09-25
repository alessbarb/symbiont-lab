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
from symbiont.cognition.limits import KernelLimits
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

    assert root.attrib["name"] == "symbiont_anthropomorphic_v5"
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


def test_physics3d_cognition_accepts_experiment_local_limits():
    experimental = KernelLimits(max_nodes=256)
    _, _, returned = physics3d_cognition(kernel_limits=experimental)

    assert returned is experimental
    assert returned.max_nodes == 256
    assert KernelLimits().max_nodes == 768


def test_anatomical_labels_do_not_live_in_core_symbiont_surface():
    import symbiont.core.symbiont as symbiont

    source = inspect.getsource(symbiont).lower()
    for anatomical_term in ("knee", "elbow", "shoulder", "hip", "thigh", "shin"):
        assert anatomical_term not in source



def test_physics3d_uses_canonical_body_independent_genome():
    genome, _graph, limits = physics3d_cognition()

    assert genome.genome_id == "genome_symbiont_base_v2"
    assert not hasattr(genome, "motor")
    assert genome.development.soft_node_budget == 192
    assert genome.development.soft_edge_budget == 1536
    assert genome.development.sense_node_budget == 128
    assert limits.max_nodes == 768
    assert limits.max_edges == 6144
    assert limits.max_nodes >= genome.development.soft_node_budget
    assert limits.max_edges >= genome.development.soft_edge_budget


def test_physics3d_runtime_does_not_call_parallel_symbiont_step():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime)
    assert "PrivateModelOrganismRuntime" in source
    assert "Symbiont(" not in source
    assert ".symbiont.step(" not in source



def test_physics3d_grants_body_sized_bounded_sensory_checkpoint_budget():
    sensory = physics3d_sensory_system()

    assert sensory.plasticity_enabled is True
    assert sensory.limits.max_active_sensors == 256
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




def test_physics3d_resume_projects_solver_penetration_but_direct_restore_stays_strict():
    import inspect
    import symbiont_lab.physics3d.runtime as runtime
    from symbiont_lab.physics3d.humanoid import HumanoidPhysics

    source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.__init__)
    assert "strict_anatomical_limits=False" in source

    signature = inspect.signature(HumanoidPhysics.restore_physical_state)
    assert signature.parameters["strict_anatomical_limits"].default is True

def test_physics3d_newborns_use_mode_free_sensorimotor_constitution():
    import symbiont_lab.physics3d.apparatus as apparatus
    import symbiont_lab.physics3d.runtime as runtime

    runtime_source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.__init__)
    exclusion_source = inspect.getsource(apparatus.actuator_exclusion_groups)

    assert "motor_exploration_mode" not in runtime_source
    assert '"genome_symbiont_physics3d_v9"' not in runtime_source
    assert "missing canonical genome identity" in runtime_source
    assert "exclusive_actuator_groups=canonical_exclusive_groups" in runtime_source
    assert "physics3d_actuator_surface(" in runtime_source
    assert 'physical_contract=f"count:{len(self.apparatus.effector_ids)}"' in runtime_source
    assert 'f"{contract.body_kind}' not in runtime_source

    # The physical directional-pair mapping belongs to the apparatus adapter,
    # not to the runtime constructor or the genome.
    assert "binding.positive_port" in exclusion_source
    assert "binding.negative_port" in exclusion_source



def test_humanoid_anatomical_axes_match_reference_planes():
    by_name = {spec.name: spec.axis for spec in JOINT_SPECS}

    # Z: axial/yaw rotations.
    for name in (
        "trunk_yaw",
        "left_hip_yaw",
        "right_hip_yaw",
        "left_shoulder_yaw",
        "right_shoulder_yaw",
    ):
        assert by_name[name] == (0.0, 0.0, 1.0)

    # X: sagittal flexion/extension.
    for name in (
        "trunk_pitch",
        "neck_pitch",
        "left_elbow_pitch",
        "right_elbow_pitch",
        "left_hip_pitch",
        "right_hip_pitch",
        "left_knee_pitch",
        "right_knee_pitch",
        "left_ankle_pitch",
        "right_ankle_pitch",
    ):
        assert by_name[name] == (1.0, 0.0, 0.0)

    # Y: frontal-plane roll / ab-adduction.
    for name in (
        "trunk_roll",
        "left_hip_roll",
        "right_hip_roll",
        "left_ankle_roll",
        "right_ankle_roll",
    ):
        assert by_name[name] == (0.0, 1.0, 0.0)


def test_left_and_right_knees_are_mirrored_hinges_not_lateral_rotators():
    by_name = {spec.name: spec for spec in JOINT_SPECS}
    left = by_name["left_knee_pitch"]
    right = by_name["right_knee_pitch"]

    assert left.axis == right.axis == (1.0, 0.0, 0.0)
    assert left.lower == pytest.approx(right.lower)
    assert left.upper == pytest.approx(right.upper)
    assert left.lower == pytest.approx(0.0)


def test_v5_hard_limited_body_exposes_multiple_rotational_axes():
    assert set(JOINT_AXES) == set(JOINT_LIMITS)
    axes = set(JOINT_AXES.values())

    assert (1.0, 0.0, 0.0) in axes
    assert (0.0, 1.0, 0.0) in axes
    assert (0.0, 0.0, 1.0) in axes
    assert JOINT_AXES[0] == (0.0, 0.0, 1.0)
    assert JOINT_AXES[1] == (0.0, 1.0, 0.0)


def test_physics3d_l4_uses_one_physical_energy_pool_for_all_metabolism() -> None:
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.__init__)
    assert "physical_energy_capacity = sum(metabolic_capacity.values())" in source
    assert "living_body_state=living_body_state" in source
    source = inspect.getsource(runtime.PyBulletEmbodimentRuntime.__init__)
    assert "genome_symbiont_physics3d_v9" not in source


def _body_state_with_joint_position(joint_ordinal: int, position: float) -> dict:
    return {
        "schema_version": BODY_STATE_SCHEMA_VERSION,
        "body_kind": BODY_KIND,
        "base_position": [0.0, 0.0, 1.0],
        "base_orientation": [0.0, 0.0, 0.0, 1.0],
        "linear_velocity": [0.0, 0.0, 0.0],
        "angular_velocity": [0.0, 0.0, 0.0],
        "joints": [
            {
                "joint_index": ordinal,
                "position": (
                    float(position)
                    if ordinal == joint_ordinal
                    else float(
                        sum(mechanical_joint_limits(JOINT_SPECS[ordinal])) / 2.0
                    )
                ),
                "velocity": 0.0,
            }
            for ordinal in range(MOTOR_DOF)
        ],
    }


def test_canonical_body_restore_still_rejects_large_anatomical_excursion():
    humanoid = HumanoidPhysics.__new__(HumanoidPhysics)
    humanoid.p = object()
    humanoid.body_id = 11
    humanoid.client_id = 3
    humanoid.motor_joint_indices = tuple(range(MOTOR_DOF))
    humanoid._joint_ordinal_by_index = {
        index: index for index in range(MOTOR_DOF)
    }

    shoulder = next(
        index
        for index, spec in enumerate(JOINT_SPECS)
        if spec.name == "right_shoulder_pitch"
    )
    payload = _body_state_with_joint_position(
        shoulder,
        JOINT_SPECS[shoulder].upper + 0.25,
    )

    with pytest.raises(
        ValueError,
        match="joint state outside hard anatomical limit: right_shoulder_pitch",
    ):
        humanoid.restore_physical_state(payload)


def test_visual_body_restore_projects_large_solver_excursion_without_mutating_source():
    class FakeBullet:
        def __init__(self):
            self.joints = {}

        def resetBasePositionAndOrientation(self, *args, **kwargs):
            pass

        def resetBaseVelocity(self, *args, **kwargs):
            pass

        def resetJointState(
            self,
            body_id,
            joint_index,
            *,
            targetValue,
            targetVelocity,
            physicsClientId,
        ):
            self.joints[int(joint_index)] = (
                float(targetValue),
                float(targetVelocity),
            )

    humanoid = HumanoidPhysics.__new__(HumanoidPhysics)
    fake = FakeBullet()
    humanoid.p = fake
    humanoid.body_id = 11
    humanoid.client_id = 3
    humanoid.motor_joint_indices = tuple(range(MOTOR_DOF))
    humanoid._joint_ordinal_by_index = {
        index: index for index in range(MOTOR_DOF)
    }

    shoulder = next(
        index
        for index, spec in enumerate(JOINT_SPECS)
        if spec.name == "right_shoulder_pitch"
    )
    raw_position = JOINT_SPECS[shoulder].upper + 0.25
    payload = _body_state_with_joint_position(shoulder, raw_position)

    humanoid.restore_physical_state(
        payload,
        strict_anatomical_limits=False,
    )

    _lower, mechanical_upper = mechanical_joint_limits(JOINT_SPECS[shoulder])
    assert fake.joints[shoulder][0] == pytest.approx(mechanical_upper)
    assert payload["joints"][shoulder]["position"] == pytest.approx(raw_position)


def test_monitor_uses_visual_only_non_strict_body_projection():
    import symbiont_lab.physics3d.monitor as monitor

    source = inspect.getsource(monitor._viewer_main)
    assert "strict_anatomical_limits=False" in source



def test_passive_postural_tone_is_body_owned_and_bounded():
    from symbiont_lab.physics3d.humanoid import (
        PASSIVE_TONE_TORQUE_CAP_FRACTION,
        _neutral_rest_position,
        _passive_postural_tone,
    )

    for spec in JOINT_SPECS:
        rest = _neutral_rest_position(spec)
        assert spec.lower <= rest <= spec.upper
        at_rest = _passive_postural_tone(
            spec,
            position=rest,
            velocity=0.0,
        )
        assert at_rest == pytest.approx(0.0)

        displaced = _passive_postural_tone(
            spec,
            position=rest + 0.1,
            velocity=0.0,
        )
        assert displaced <= 0.0
        assert abs(displaced) <= (
            spec.max_motor_torque * PASSIVE_TONE_TORQUE_CAP_FRACTION + 1e-12
        )


def test_actuator_work_decomposition_keeps_absolute_effort_distinct_from_net():
    from symbiont_lab.physics3d.humanoid import ActuatorWork

    work = ActuatorWork(
        positive_j=4.0,
        negative_j=1.5,
        absolute_j=5.5,
        net_j=2.5,
    )
    assert work.absolute_j == work.positive_j + work.negative_j
    assert work.net_j == work.positive_j - work.negative_j


def test_runtime_physics_trace_initializes_joint_payload_before_append():
    import symbiont_lab.physics3d.runtime as runtime

    source = inspect.getsource(
        runtime.PyBulletEmbodimentRuntime._physics_trace_sample
    )
    assert "joints: list[dict[str, object]] = []" in source
    assert source.index("joints: list") < source.index("joints.append")


def test_runtime_settling_fails_closed_instead_of_treating_timeout_as_success():
    from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

    class NeverSettlesBullet:
        def stepSimulation(self, **_kwargs):
            return None

        def getBaseVelocity(self, *_args, **_kwargs):
            return ((1.0, 0.0, 0.0), (0.0, 0.5, 0.0))

        def getJointStates(self, *_args, **_kwargs):
            return ((0.0, 0.25, 0.0, 0.0),)

    class Body:
        body_id = 1
        motor_joint_indices = (0,)

        def apply_effectors(self, _values):
            return None

        def prepare_physics_substep(self):
            return None

    runtime = PyBulletEmbodimentRuntime.__new__(PyBulletEmbodimentRuntime)
    runtime.p = NeverSettlesBullet()
    runtime.client_id = 7
    runtime.apparatus = Body()

    with pytest.raises(RuntimeError, match="failed passive settling"):
        runtime._settle_new_body(
            max_steps=3,
            stable_samples=2,
            linear_threshold=0.01,
            angular_threshold=0.01,
            joint_threshold=0.01,
        )

    assert runtime._settling_result.converged is False
    assert runtime._settling_result.steps == 3



def test_engine_rejects_pre_v9_motor_evidence_without_explicit_reembodiment():
    from symbiont_lab.physics3d.engine import _require_current_motor_evidence

    legacy = {
        "actuation": {
            "sensorimotor": {
                "schema_version": 8,
            },
        },
    }
    with pytest.raises(RuntimeError, match="requires migratable v9"):
        _require_current_motor_evidence(
            legacy,
            fresh_body=False,
            new_symbiont=False,
        )

    # Explicit re-embodiment is the honest path: the old learned motor state
    # is not restored as current-body evidence.
    _require_current_motor_evidence(
        legacy,
        fresh_body=True,
        new_symbiont=False,
    )

    for schema in (9, 10):
        current = {
            "actuation": {
                "sensorimotor": {
                    "schema_version": schema,
                },
            },
        }
        _require_current_motor_evidence(
            current,
            fresh_body=False,
            new_symbiont=False,
        )


def test_motor_step_applies_exclusion_before_execution_and_credit():
    from symbiont.core.orchestration.runtime import OrganismRuntime

    source = inspect.getsource(OrganismRuntime._motor_step)
    constrain_at = source.index("constrain_intents")
    execute_at = source.index("self._actuator_system.execute")
    credit_at = source.index("executed_ids")

    assert constrain_at < execute_at
    assert execute_at < credit_at
    assert "if intent.actuator_id not in executed_ids" in source



def test_apparatus_projects_directional_pairs_to_opaque_actuator_groups():
    from types import SimpleNamespace
    from symbiont_lab.physics3d.apparatus import actuator_exclusion_groups

    constitution = SimpleNamespace(
        actuator_ids=("a0", "a1", "a2", "a3"),
    )
    apparatus = SimpleNamespace(
        effector_ids=("e0", "e1", "e2", "e3"),
        motor_bindings=(
            SimpleNamespace(positive_port="e2", negative_port="e0"),
            SimpleNamespace(positive_port="e3", negative_port="e1"),
        ),
    )

    assert actuator_exclusion_groups(constitution, apparatus) == (
        ("a2", "a0"),
        ("a3", "a1"),
    )


def test_apparatus_motor_unit_contract_requires_complete_disjoint_coverage():
    from types import SimpleNamespace
    from symbiont_lab.physics3d.apparatus import actuator_exclusion_groups

    constitution = SimpleNamespace(
        actuator_ids=("a0", "a1", "a2", "a3"),
    )
    incomplete = SimpleNamespace(
        effector_ids=("e0", "e1", "e2", "e3"),
        motor_bindings=(
            SimpleNamespace(positive_port="e0", negative_port="e1"),
        ),
    )
    with pytest.raises(ValueError, match="complete actuator constitution"):
        actuator_exclusion_groups(constitution, incomplete)

    overlapping = SimpleNamespace(
        effector_ids=("e0", "e1", "e2", "e3"),
        motor_bindings=(
            SimpleNamespace(positive_port="e0", negative_port="e1"),
            SimpleNamespace(positive_port="e1", negative_port="e2"),
        ),
    )
    with pytest.raises(ValueError, match="disjoint directional pairs"):
        actuator_exclusion_groups(constitution, overlapping)



def test_actuator_work_metabolic_conversion_is_proportional_without_cap():
    from symbiont_lab.physics3d.runtime import metabolic_cost_from_actuator_work

    assert metabolic_cost_from_actuator_work(100.0, 0.1) == pytest.approx(10.0)
    assert metabolic_cost_from_actuator_work(1000.0, 0.001) == pytest.approx(1.0)

    for work, rate in (
        (-1.0, 0.1),
        (1.0, -0.1),
        (float("inf"), 0.1),
        (1.0, float("nan")),
    ):
        with pytest.raises(ValueError):
            metabolic_cost_from_actuator_work(work, rate)



def test_articulated_body_reports_signed_and_absolute_actuator_work():
    from symbiont_lab.physics3d.articulated import ArticulatedPhysics

    class Bullet:
        def getJointStates(self, _body_id, indices, **_kwargs):
            velocities = {0: 2.0, 1: -3.0}
            return tuple(
                (0.0, velocities[index], 0.0, 0.0)
                for index in indices
            )

    body = ArticulatedPhysics.__new__(ArticulatedPhysics)
    body.p = Bullet()
    body.client_id = 1
    body.body_id = 2
    body._applied_torque_by_joint = {0: 4.0, 1: 5.0}

    work = body.actuator_work_step(0.5)

    assert work.positive_j == pytest.approx(4.0)
    assert work.negative_j == pytest.approx(7.5)
    assert work.absolute_j == pytest.approx(11.5)
    assert work.net_j == pytest.approx(-3.5)
    assert body.mechanical_work_step(0.5) == pytest.approx(11.5)
