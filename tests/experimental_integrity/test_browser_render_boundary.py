from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_cognition_layout_uses_spatial_bucketing_not_all_pairs() -> None:
    root = _root()
    controller = (
        root / "src" / "symbiont_lab" / "workbench" / "web" / "views" / "mind"
        / "cognition-controller.js"
    ).read_text(encoding="utf-8")
    three_d = (
        root / "src" / "symbiont_lab" / "workbench" / "web" / "views" / "mind"
        / "cognition-3d.js"
    ).read_text(encoding="utf-8")

    assert "forEachNearbyPair2D(" in controller
    assert "forEachNearbyPair3D(" in three_d
    assert "for (let j = i + 1; j < n; j++)" not in controller
    assert "for (let j = i + 1; j < nodes.length; j++)" not in three_d


def test_3d_layout_does_not_rescan_all_edges_for_each_node() -> None:
    root = _root()
    source = (
        root / "src" / "symbiont_lab" / "workbench" / "web" / "views" / "mind"
        / "cognition-3d.js"
    ).read_text(encoding="utf-8")
    relax = source[source.index("export function relaxCognition3D(") :]

    assert "plasticityByNode" in relax
    assert "edges.filter(edge =>" not in relax


def test_cognition_summary_is_not_rebuilt_on_every_animation_frame() -> None:
    root = _root()
    source = (
        root / "src" / "symbiont_lab" / "workbench" / "web" / "views" / "mind"
        / "cognition-controller.js"
    ).read_text(encoding="utf-8")

    assert "function maybeUpdateCognitionSummary" in source
    assert "now - lastSummaryAt < 250" in source
    assert "maybeUpdateCognitionSummary();" in source


def test_canvas_shadows_are_reserved_for_focused_nodes() -> None:
    root = _root()
    source = (
        root / "src" / "symbiont_lab" / "workbench" / "web" / "views" / "mind"
        / "cognition-controller.js"
    ).read_text(encoding="utf-8")

    assert "ctx.shadowBlur = isSelected ? 14 : pathNode ? 8 : 0;" in source
    assert "fmriEnabled && node.activationLevel > 0 ? 3 + node.activationLevel * 8 : 2" not in source


def test_body_workspace_ignores_unchanged_metric_updates() -> None:
    root = _root()
    source = (
        root / "src" / "symbiont_lab" / "workbench" / "web" / "views" / "body"
        / "workspace.js"
    ).read_text(encoding="utf-8")

    update = source[source.index("  updateMetric(id, text, color = null)") :]
    assert "if (!textChanged && !colorChanged) return;" in update
