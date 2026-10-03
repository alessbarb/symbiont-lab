from types import SimpleNamespace

from lab.physics3d.bodies import ANTHROPOMORPHIC_V6
from lab.physics3d.observer_semantics import (
    action_dimension_semantics,
    motor_semantics,
    receptor_ground_truth,
    sensory_semantics,
)
from symbiont.actuation.intervention import opaque_channel_ref


def test_physics3d_receptor_ground_truth_is_complete_and_external() -> None:
    truth = receptor_ground_truth(
        joint_specs=ANTHROPOMORPHIC_V6.observer_joint_specs,
        contact_region_names=ANTHROPOMORPHIC_V6.observer_contact_region_names,
        interoceptive_source_ordinals=(0, 1, 2, 3),
    )

    assert len(truth) == 107
    assert truth["rec.0"]["label"] == "trunk yaw angle"
    assert truth["rec.1"]["label"] == "trunk yaw angular velocity"
    assert truth["rec.62"]["label"] == "base orientation x"
    assert truth["rec.72"]["label"] == "pelvis contact"
    assert truth["rec.87"]["label"] == "resource field intensity"
    assert truth["rec.88"]["label"] == "pelvis contact load"
    assert truth["rec.103"]["label"] == "energy reserve"
    assert truth["rec.106"]["label"] == "fatigue"


def test_interoceptive_ground_truth_follows_hidden_apparatus_permutation() -> None:
    truth = receptor_ground_truth(
        joint_specs=ANTHROPOMORPHIC_V6.observer_joint_specs,
        contact_region_names=ANTHROPOMORPHIC_V6.observer_contact_region_names,
        interoceptive_source_ordinals=(3, 1, 0, 2),
    )

    assert truth["rec.103"]["label"] == "fatigue"
    assert truth["rec.104"]["label"] == "structural integrity"
    assert truth["rec.105"]["label"] == "energy reserve"
    assert truth["rec.106"]["label"] == "temperature"


def test_sensory_semantics_preserves_self_label_and_separates_observer_truth() -> None:
    sensors = (
        SimpleNamespace(cognitive_name="sense_deadbeef0001", source_ids=("rec.0",)),
        SimpleNamespace(
            cognitive_name="sense_deadbeef0002",
            source_ids=("rec.0", "rec.1"),
        ),
        SimpleNamespace(cognitive_name="sense_unknown", source_ids=("opaque.x",)),
    )

    semantics = sensory_semantics(
        sensors,
        joint_specs=ANTHROPOMORPHIC_V6.observer_joint_specs,
        contact_region_names=ANTHROPOMORPHIC_V6.observer_contact_region_names,
        interoceptive_source_ordinals=(0, 1, 2, 3),
    )

    exact = semantics["sense_deadbeef0001"]
    assert exact["self_label"] == "sense_deadbeef0001"
    assert exact["observer_summary"] == "trunk yaw angle"
    assert exact["mapping"] == "exact-source"

    composite = semantics["sense_deadbeef0002"]
    assert composite["observer_labels"] == [
        "trunk yaw angle",
        "trunk yaw angular velocity",
    ]
    assert composite["mapping"] == "composite-source"

    unresolved = semantics["sense_unknown"]
    assert unresolved["observer_summary"] is None
    assert unresolved["mapping"] == "unresolved"


def test_motor_semantics_maps_opaque_actuators_to_observer_physics() -> None:
    semantics = motor_semantics(
        {
            "actuator.a": "eff.0",
            "actuator.b": "eff.1",
            "actuator.c": "eff.44",
        },
        joint_specs=ANTHROPOMORPHIC_V6.observer_joint_specs,
    )

    assert semantics["actuator.a"]["observer_summary"] == "trunk yaw positive drive"
    assert semantics["actuator.b"]["observer_summary"] == "trunk yaw negative drive"
    assert semantics["actuator.c"]["observer_summary"] == "left knee pitch positive drive"
    assert semantics["actuator.a"]["self_label"] == "actuator.a"


def test_action_dimension_semantics_projects_multi_channel_grounding_observer_only() -> None:
    actuator_to_effector = {
        "actuator.a": "eff.0",
        "actuator.b": "eff.1",
        "actuator.c": "eff.44",
    }
    dimension = SimpleNamespace(dimension_id="action.dimension.aaaa")
    registry = SimpleNamespace(
        items=(dimension,),
        channel_refs=lambda _dimension_id: (
            opaque_channel_ref("actuator.a"),
            opaque_channel_ref("actuator.c"),
        ),
    )

    semantics = action_dimension_semantics(
        registry,
        actuator_to_effector,
        joint_specs=ANTHROPOMORPHIC_V6.observer_joint_specs,
    )

    item = semantics["action.dimension.aaaa"]
    assert item["channel_count"] == 2
    assert item["mapped_channel_count"] == 2
    assert item["mapping"] == "exact"
    assert item["effector_ids"] == ["eff.0", "eff.44"]
    assert item["observer_joints"] == ["left knee pitch", "trunk yaw"]
    assert item["actuator_ids"] == ["actuator.a", "actuator.c"]
