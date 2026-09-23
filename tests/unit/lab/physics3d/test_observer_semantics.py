from types import SimpleNamespace

from symbiont_lab.physics3d.observer_semantics import (
    receptor_ground_truth,
    sensory_semantics,
)


def test_physics3d_receptor_ground_truth_is_complete_and_external() -> None:
    truth = receptor_ground_truth(interoceptive_source_ordinals=(0, 1, 2, 3))

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
    truth = receptor_ground_truth(interoceptive_source_ordinals=(3, 1, 0, 2))

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
