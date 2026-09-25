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


def test_body_visual_v3_reports_flexion_separately_from_activity() -> None:
    viewer = _read(VIEWER)
    workspace = _read(WEB / "views" / "body" / "workspace.js")

    assert "displayedJointAngles" in viewer
    assert "jointFlexionSummary" in viewer
    assert "jointAngleDegrees" in viewer
    assert "Flexed joints ≥10°" in workspace
    assert "Largest joint angle" in workspace


def test_articulation_diagnostic_is_visual_only() -> None:
    viewer = _read(VIEWER)
    workspace = _read(WEB / "views" / "body" / "workspace.js")

    assert "articulationDiagnosticPose" in viewer
    assert "applyArticulationDiagnosticPose" in viewer
    assert "Visual-only pose check" in viewer
    assert "Physics and Symbiont continue untouched" in workspace


def test_compound_anatomy_does_not_assume_one_material_per_segment() -> None:
    viewer = _read(VIEWER)
    anatomy = _read(ANATOMY)

    assert "forEachSegmentMaterial" in viewer
    assert "setSegmentInspectorHighlight" in viewer
    assert "const group = new THREE.Group()" in anatomy
    assert "mesh.material.emissive.setHex(activity" not in viewer
