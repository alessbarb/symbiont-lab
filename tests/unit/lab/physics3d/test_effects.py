from __future__ import annotations

import math

import pytest

from symbiont_lab.physics3d.effects import (
    physical_consequence,
    physical_state_from_payload,
    rotate_world_to_body,
    state_distance,
)


def _payload(
    *,
    position=(0.0, 0.0, 1.0),
    orientation=(0.0, 0.0, 0.0, 1.0),
    center_of_mass=None,
    contacts=(),
    joints=(0.0, 0.0),
):
    return {
        "base_position": list(position),
        "base_orientation": list(orientation),
        "linear_velocity": [0.0, 0.0, 0.0],
        "angular_velocity": [0.0, 0.0, 0.0],
        "center_of_mass": list(center_of_mass or position),
        "contact_links": list(contacts),
        "joints": [
            {"joint_index": index, "position": value, "velocity": 0.0}
            for index, value in enumerate(joints)
        ],
    }


def test_world_translation_is_expressed_in_initial_body_frame():
    half = math.sqrt(0.5)
    orientation = (0.0, 0.0, half, half)
    body = rotate_world_to_body((0.0, 1.0, 0.0), orientation)
    assert body == pytest.approx((1.0, 0.0, 0.0), abs=1e-9)


def test_quaternion_sign_does_not_create_rotation():
    before = physical_state_from_payload(
        1,
        _payload(orientation=(0.0, 0.0, 0.0, 1.0)),
    )
    after = physical_state_from_payload(
        2,
        _payload(orientation=(0.0, 0.0, 0.0, -1.0)),
    )
    effect = physical_consequence(before, after)
    assert effect.rotation_angle == pytest.approx(0.0)


def test_translation_and_rotation_are_separate_observations():
    before = physical_state_from_payload(1, _payload())
    half = math.sqrt(0.5)
    after = physical_state_from_payload(
        2,
        _payload(
            position=(1.0, 0.0, 1.0),
            orientation=(0.0, 0.0, half, half),
        ),
    )
    effect = physical_consequence(before, after, path_length=1.2)
    assert effect.horizontal_translation == pytest.approx(1.0)
    assert effect.rotation_angle == pytest.approx(math.pi / 2.0)
    assert effect.translation_efficiency == pytest.approx(1.0 / 1.2)


def test_base_com_disagreement_exposes_deformation():
    before = physical_state_from_payload(1, _payload())
    after = physical_state_from_payload(
        2,
        _payload(
            position=(1.0, 0.0, 1.0),
            center_of_mass=(0.05, 0.0, 1.0),
        ),
    )
    effect = physical_consequence(before, after)
    assert effect.translation_magnitude == pytest.approx(1.0)
    assert effect.com_translation_magnitude == pytest.approx(0.05)
    assert effect.base_com_agreement < 0.1


def test_state_distance_keeps_dimensions_separate():
    left = physical_state_from_payload(
        1,
        _payload(contacts=(1, 2), joints=(0.0, 0.0)),
    )
    right = physical_state_from_payload(
        2,
        _payload(
            contacts=(2, 3),
            joints=(0.2, -0.2),
            center_of_mass=(0.0, 0.0, 0.9),
        ),
    )
    distance = state_distance(left, right)
    assert distance.joint_rms_delta == pytest.approx(0.2)
    assert distance.contact_jaccard_distance == pytest.approx(2.0 / 3.0)
    assert distance.com_height_delta == pytest.approx(0.1)
