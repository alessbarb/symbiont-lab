"""Laboratory recipes and real apparatus detectability, not learned recognition."""

from types import SimpleNamespace

import pytest

from environment.physics3d.environments import (
    build_environment,
    environment_recipe,
    resolve_environment,
)
from environment.physics3d.resource import PhysicalResource
from lab.integration.physics3d.bodies import DEFAULT_BODY_REGISTRY
from lab.physics3d.world_observation import PhysicsWorldObserver


def test_recipe_resume_is_exact_and_cannot_silently_change_world():
    saved = environment_recipe("contact-garden-v1")
    assert resolve_environment(None, saved) == saved
    assert resolve_environment(None, None)["name"] == "flat-v1"
    with pytest.raises(ValueError):
        resolve_environment("flat-v1", saved)
    saved["fixtures"][0]["position"][0] = 99
    with pytest.raises(ValueError):
        resolve_environment(None, saved)
    assert environment_recipe("contact-garden-v1")["fixtures"][0]["position"][0] == 1.8


@pytest.mark.slow
@pytest.mark.parametrize("kind", tuple(DEFAULT_BODY_REGISTRY._descriptors))
def test_uncontacted_objects_are_invisible_but_contact_changes_opaque_receptors(kind):
    p = pytest.importorskip("pybullet")
    client = p.connect(p.DIRECT)
    try:
        descriptor = DEFAULT_BODY_REGISTRY.get(kind)
        apparatus = descriptor.apparatus_factory(client)
        p.resetBasePositionAndOrientation(
            apparatus.body_id, [0, 0, 3], [0, 0, 0, 1], physicsClientId=client
        )
        p.performCollisionDetection(physicsClientId=client)
        before = apparatus.sample_receptors()
        recipe = environment_recipe("contact-garden-v1")
        fixtures = build_environment(client, recipe)
        p.performCollisionDetection(physicsClientId=client)
        assert apparatus.sample_receptors() == before  # No vision or object IDs.
        p.resetBasePositionAndOrientation(
            apparatus.body_id, [1.8, 1, 0.5], [0, 0, 0, 1], physicsClientId=client
        )
        p.performCollisionDetection(physicsClientId=client)
        after = apparatus.sample_receptors()
        start = len(descriptor.observer_joint_specs) * 2 + 10
        contact_ids = [
            f"rec.{start + i}" for i in range(len(descriptor.observer_contact_region_names))
        ]
        assert any(before[r] != after[r] for r in contact_ids)
        assert set(before) == set(after)
        resource = PhysicalResource(client)
        runtime = SimpleNamespace(
            p=p,
            client_id=client,
            apparatus=apparatus,
            resource=resource,
            body_descriptor=descriptor,
            environment_recipe=recipe,
            passive_physical_state=apparatus.export_physical_state,
        )
        scene = PhysicsWorldObserver().capture(runtime)
        assert len(scene["entities"]) == len(fixtures) + 1
        assert scene["environment_recipe"] == recipe
        assert all(
            v == 0
            for v in [p.getDynamicsInfo(body, -1, physicsClientId=client)[0] for body in fixtures]
        )
    finally:
        p.disconnect(client)


@pytest.mark.slow
def test_runtime_restores_environment_without_putting_world_in_organism():
    pytest.importorskip("pybullet")
    from lab.physics3d.runtime import PyBulletEmbodimentRuntime

    runtime = PyBulletEmbodimentRuntime(
        gui=False, environment="contact-garden-v1", physics_substeps_per_tick=1, seed=42
    )
    try:
        runtime.step()
        physical, _ = runtime.physical_checkpoint()
        cognitive = runtime.checkpoint()
        assert physical["lab_world"]["name"] == "contact-garden-v1"
        assert "lab_world" not in cognitive
        assert len(runtime.passive_world_observation()["entities"]) == 6
    finally:
        runtime.close()
    restored = PyBulletEmbodimentRuntime(
        gui=False,
        physical_state=physical,
        runtime_checkpoint=cognitive,
        physics_substeps_per_tick=1,
    )
    try:
        assert restored.environment_recipe == physical["lab_world"]
        assert len(restored.environment_bodies) == 4
        restored.step()
        assert len(restored.passive_world_observation()["entities"]) == 6
    finally:
        restored.close()


def test_home_launch_keeps_environment_in_laboratory_run(tmp_path):
    from lab.app.physics3d.runs import Physics3DRunStore

    store = Physics3DRunStore(tmp_path)
    launch = store.prepare({"environment": "contact-garden-v1"})
    assert launch.runner_kwargs()["environment"] == "contact-garden-v1"
    assert launch.as_dict()["environment"] == "contact-garden-v1"
    with pytest.raises(ValueError):
        store.prepare({"environment": "invented"})
