import inspect
import math

import pytest

from symbiont_lab.viewer.camera import Camera, axial_to_world, world_to_axial
from symbiont_lab.viewer.client import WorldObserverClient, validate_loopback_url
from symbiont_lab.viewer.projection import VisualCell, VisualOrganism, VisualSnapshot, project_snapshot
from symbiont_lab.viewer.scene import HabitatScene, classify_event, morphology_for


def _raw_snapshot(*, tick=1, q=0, r=0, generation=0, senses=5):
    return {
        "world_id": "w",
        "tick": tick,
        "width": 16,
        "height": 16,
        "cells": {
            "0,0": {
                "q": 0,
                "r": 0,
                "elevation": 0.7,
                "moisture": 0.4,
                "temperature": 0.3,
                "fertility": 0.8,
                "traces": 0.2,
                "disturbance": 0.1,
                "density": 0.25,
                "resources": {"opaque-a": 5.0, "opaque-b": 1.0},
                "resource_capacities": {"opaque-a": 10.0, "opaque-b": 2.0},
                "hazards": {"opaque-h": 0.25},
            }
        },
        "organisms": [
            {
                "id": "founder-0",
                "q": q,
                "r": r,
                "alive": True,
                "integrity": 0.9,
                "metabolic_reserve": 0.6,
                "senses_count": senses,
                "generation": generation,
                "age": tick,
                "recent_damage": 0.1,
            }
        ],
    }


def test_projection_uses_physical_values_without_resource_labels():
    snapshot = project_snapshot(_raw_snapshot())

    assert snapshot.world_id == "w"
    assert snapshot.tick == 1
    assert snapshot.cells == (
        VisualCell(
            q=0,
            r=0,
            elevation=0.7,
            moisture=0.4,
            temperature=0.3,
            fertility=0.8,
            traces=0.2,
            disturbance=0.1,
            density=0.25,
            resource_level=0.5,
            hazard_level=0.25,
        ),
    )
    assert snapshot.organisms == (
        VisualOrganism(
            organism_id="founder-0",
            q=0,
            r=0,
            alive=True,
            integrity=0.9,
            reserve=0.6,
            senses_count=5,
            generation=0,
            age=1,
            recent_damage=0.1,
        ),
    )


def test_projection_clamps_non_finite_and_out_of_range_values():
    raw = _raw_snapshot()
    cell = raw["cells"]["0,0"]
    cell.update(
        elevation=9,
        moisture=-3,
        temperature="nan",
        fertility=None,
        traces=2,
        disturbance=-1,
        density=4,
        hazards={"h": 4},
    )
    projected = project_snapshot(raw)
    cell = projected.cells[0]
    assert cell.elevation == 1.0
    assert cell.moisture == 0.0
    assert cell.temperature == 0.5
    assert cell.fertility == 0.5
    assert cell.traces == 1.0
    assert cell.disturbance == 0.0
    assert cell.density == 1.0
    assert cell.hazard_level == 1.0


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8766/world/state",
        "http://localhost:8766/world/state",
        "http://[::1]:8766/world/state",
    ],
)
def test_viewer_accepts_only_local_observatory_urls(url):
    validate_loopback_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8766/world/state",
        "http://example.com/world/state",
        "http://user:secret@127.0.0.1:8766/world/state",
    ],
)
def test_viewer_rejects_non_local_or_credentialed_urls(url):
    with pytest.raises(ValueError):
        validate_loopback_url(url)


def test_events_endpoint_is_derived_from_state_endpoint():
    assert (
        WorldObserverClient("http://127.0.0.1:9911/world/state").events_url
        == "http://127.0.0.1:9911/world/events"
    )
    assert (
        WorldObserverClient("http://[::1]:9911/world/state").events_url
        == "http://[::1]:9911/world/events"
    )


@pytest.mark.parametrize("q,r", [(0, 0), (1, 0), (0, 1), (7, 9), (-2, 4)])
def test_axial_world_conversion_roundtrips(q, r):
    x, y = axial_to_world(q, r, 46.0)
    qq, rr = world_to_axial(x, y, 46.0)
    assert qq == pytest.approx(q)
    assert rr == pytest.approx(r)


def test_camera_lod_and_zoom_are_bounded():
    camera = Camera()
    camera.zoom_by(100)
    assert camera.zoom == camera.max_zoom
    assert camera.lod == "near"
    camera.zoom_by(0.0001)
    assert camera.zoom == camera.min_zoom
    assert camera.lod == "far"


def test_scene_interpolates_between_world_ticks_without_mutating_endpoints():
    scene = HabitatScene(transition_seconds=0.4)
    scene.ingest_snapshot(project_snapshot(_raw_snapshot(tick=1, q=0, r=0)), now=1.0)
    start = scene.tracks["founder-0"].position(1.0, scene.transition_seconds)

    scene.ingest_snapshot(project_snapshot(_raw_snapshot(tick=2, q=1, r=0)), now=2.0)
    at_change = scene.tracks["founder-0"].position(2.0, scene.transition_seconds)
    halfway = scene.tracks["founder-0"].position(2.2, scene.transition_seconds)
    finished = scene.tracks["founder-0"].position(2.4, scene.transition_seconds)
    target = axial_to_world(1, 0, scene.spacing)

    assert at_change == pytest.approx(start)
    assert start[0] < halfway[0] < target[0]
    assert finished == pytest.approx(target)


def test_morphology_is_deterministic_and_identity_independent():
    base = project_snapshot(_raw_snapshot(generation=0, senses=5)).organisms[0]
    same_shape = VisualOrganism("other-id", 3, 4, True, 0.4, 0.2, 5, 99, 500, 0.0)
    different_structure = project_snapshot(_raw_snapshot(generation=0, senses=9)).organisms[0]

    assert morphology_for(base) == morphology_for(same_shape)
    assert morphology_for(base) != morphology_for(different_structure)


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("PHYSIOLOGICAL_DAMAGE", "shock"),
        ("RESOURCE_ACQUIRED", "absorb"),
        ("DEATH", "collapse"),
        ("REPRODUCTION", "emerge"),
        ("REPAIR", "recover"),
        ("MOVE", "motion"),
    ],
)
def test_events_have_non_textual_physical_manifestations(kind, expected):
    assert classify_event(kind)[0] == expected


def test_scene_event_effects_are_bounded_and_expire():
    scene = HabitatScene()
    scene.ingest_snapshot(project_snapshot(_raw_snapshot()), now=1.0)
    scene.ingest_events(
        [{"kind": "PHYSIOLOGICAL_DAMAGE", "actor": "founder-0", "payload": {"damage": 0.5}}],
        now=1.1,
    )
    assert len(scene.effects) == 1
    assert scene.effects[0].kind == "shock"
    scene.update(now=5.0)
    assert scene.effects == []


def test_spatial_index_returns_only_visible_chunks():
    cells = tuple(
        VisualCell(
            q=q,
            r=r,
            elevation=0.5,
            moisture=0.5,
            temperature=0.5,
            fertility=0.5,
            traces=0.0,
            disturbance=0.0,
            density=0.0,
            resource_level=0.0,
            hazard_level=0.0,
        )
        for q in range(32)
        for r in range(32)
    )
    organism = VisualOrganism("o", 20, 20, True, 1.0, 1.0, 3, 0, 1, 0.0)
    snapshot = VisualSnapshot("w", 1, 32, 32, cells, (organism,))
    scene = HabitatScene(chunk_size=8)
    scene.ingest_snapshot(snapshot, now=1.0)

    visible = scene.visible_cells((0, 4, 0, 4))
    assert len(visible) == 25
    assert all(0 <= cell.q <= 4 and 0 <= cell.r <= 4 for cell in visible)
    assert scene.visible_track_ids((0, 4, 0, 4)) == set()
    assert scene.visible_track_ids((18, 22, 18, 22)) == {"o"}


def test_viewer_modules_have_no_world_runtime_imports():
    import symbiont_lab.viewer.camera as camera
    import symbiont_lab.viewer.client as client
    import symbiont_lab.viewer.projection as projection
    import symbiont_lab.viewer.renderer as renderer
    import symbiont_lab.viewer.scene as scene
    import symbiont_lab.viewer.world_pygame as entry

    for module in (camera, client, projection, renderer, scene, entry):
        source = inspect.getsource(module)
        assert "symbiont_lab.world" not in source
        assert "symbiont_world" not in source


def test_camera_viewport_bounds_cover_center():
    camera = Camera()
    camera.center_on(*axial_to_world(10, 10, 46.0))
    qmin, qmax, rmin, rmax = camera.axial_bounds(1280, 800, 46.0)
    assert qmin <= 10 <= qmax
    assert rmin <= 10 <= rmax
    assert math.isfinite(qmin)
