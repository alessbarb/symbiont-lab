from __future__ import annotations

import pytest

from symbiont_lab.physics3d.humanoid import HumanoidPhysics
from symbiont_lab.physics3d.resource import PhysicalResource


class FakeBullet:
    GEOM_SPHERE = 2

    def __init__(self):
        self.next_id = 1
        self.contacts = []

    def createCollisionShape(self, *args, **kwargs):
        value = self.next_id
        self.next_id += 1
        return value

    def createVisualShape(self, *args, **kwargs):
        value = self.next_id
        self.next_id += 1
        return value

    def createMultiBody(self, *args, **kwargs):
        value = self.next_id
        self.next_id += 1
        return value

    def changeDynamics(self, *args, **kwargs):
        return None

    def getContactPoints(self, **kwargs):
        return tuple(self.contacts)


def test_resource_field_is_local_scalar_and_extinguishes_when_depleted():
    resource = PhysicalResource(
        FakeBullet(),
        7,
        position=(2.0, 0.0, 0.0),
        radius=0.2,
        field_radius=4.0,
        remaining=10.0,
        transfer_per_tick=2.0,
    )

    near = resource.field_at((1.0, 0.0, 0.0))
    far = resource.field_at((0.0, 0.0, 0.0))

    assert 0.0 < far < near < 1.0
    resource.remaining = 0.0
    assert resource.field_at((2.0, 0.0, 0.0)) == 0.0


def test_resource_debits_only_absorbed_material():
    resource = PhysicalResource(
        FakeBullet(),
        7,
        remaining=10.0,
        transfer_per_tick=2.0,
    )

    assert resource.offered_material() == 2.0
    assert resource.consume_absorbed(0.4) == pytest.approx(0.4)
    assert resource.remaining == pytest.approx(9.6)


def test_resource_contact_is_physical_not_semantic():
    bullet = FakeBullet()
    resource = PhysicalResource(bullet, 7)

    assert resource.touching(99) is False
    bullet.contacts.append(("opaque-contact",))
    assert resource.touching(99) is True


def test_opaque_environment_state_accepts_only_bounded_scalars():
    body = HumanoidPhysics.__new__(HumanoidPhysics)
    body._external_field_signal = 0.0
    body._internal_state_signal = 1.0

    body.set_opaque_environment_state(
        external_field=0.3,
        internal_state=0.7,
    )
    assert body._external_field_signal == pytest.approx(0.3)
    assert body._internal_state_signal == pytest.approx(0.7)

    with pytest.raises(ValueError):
        body.set_opaque_environment_state(
            external_field=1.1,
            internal_state=0.7,
        )
