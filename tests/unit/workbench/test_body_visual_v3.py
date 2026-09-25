from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB = REPO_ROOT / "src" / "symbiont_lab" / "workbench" / "web"
VIEWER = WEB / "views" / "body" / "viewer.js"
ANATOMY = WEB / "views" / "body" / "anatomical-visual.js"
OBSERVATION = REPO_ROOT / "src" / "symbiont_lab" / "observation" / "physics3d.py"
HUMANOID = REPO_ROOT / "src" / "symbiont_lab" / "physics3d" / "humanoid.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_body_visual_v3_uses_passive_anatomical_projection() -> None:
    viewer = _read(VIEWER)
    anatomy = _read(ANATOMY)

    assert "createAnatomicalSegment" in viewer
    assert "createTechnicalJointMarker" in viewer
    assert "new THREE.BoxGeometry(w, h, d)" not in viewer
    assert "CylinderGeometry" in anatomy
    assert "SphereGeometry" in anatomy
    assert "visualRole = 'surface'" in anatomy
    assert "AnimationClip" not in anatomy
    assert "AnimationMixer" not in anatomy


def test_body_visual_v3_exposes_real_com_and_contacts_only_as_observation() -> None:
    observation = _read(OBSERVATION)
    humanoid = _read(HUMANOID)
    viewer = _read(VIEWER)

    assert '"center_of_mass"' in humanoid
    assert '"contacts": contact_details' in humanoid
    assert 'event["center_of_mass"]' in observation
    assert 'event["contacts"]' in observation
    assert "updateObserverSpatialOverlays(data)" in viewer
    assert "observer_center_of_mass" in viewer
    assert "observer_contact_point" in viewer
    assert '"feeds_back": False' in observation


def test_visual_interpolation_remains_observer_only() -> None:
    viewer = _read(VIEWER)

    assert "interpolatePresentationPose" in viewer
    assert "requestAnimationFrame" in viewer
    assert "Presentation frames are observer-only" in viewer
    assert "Physics/Symbiont remain untouched" in viewer
