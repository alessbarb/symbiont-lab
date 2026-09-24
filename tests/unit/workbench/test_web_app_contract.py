from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "src" / "symbiont_lab" / "workbench" / "web"


def _read(relative: str) -> str:
    return (WEB_ROOT / relative).read_text(encoding="utf-8")


def test_shell_uses_native_landmarks_and_focusable_view_root():
    html = _read("app.html")
    assert '<nav class="rail" aria-label="Main navigation">' in html
    assert 'role="navigation"' not in html
    assert 'role="main"' not in html
    assert '<main id="view-root" tabindex="-1"></main>' in html
    assert 'class="skip-link"' in html
    assert 'github.com/alessbarb/symbiont-lab' in html


def test_live_region_is_scoped_to_runtime_state_not_entire_footer():
    html = _read("app.html")
    assert '<footer class="statusbar">' in html
    assert 'class="statusbar-state"' in html
    assert 'id="sb-status" class="sb-item" role="status" aria-live="polite"' in html
    assert '<footer class="statusbar" role="status"' not in html


def test_router_is_declarative_and_polling_is_not_interval_based():
    app = _read("app.js")
    assert "const ROUTES = {" in app
    assert "RuntimeStatePoller" in app
    assert "setInterval(" not in app
    assert "removeAttribute('aria-current')" in app
    assert "history.pushState" in app\n    assert "popstate" in app


def test_runtime_poller_prevents_overlap_and_handles_visibility():
    runtime = _read("runtime-state.js")
    assert "if (!this.running || this.controller) return;" in runtime
    assert "new AbortController()" in runtime
    assert "visibilitychange" in runtime
    assert "document.hidden" in runtime
    assert "maxBackoffMs" in runtime


def test_all_top_level_views_have_uniform_lifecycle_contract():
    for relative in (
        "views/home.js",
        "views/lab.js",
        "views/archive.js",
        "views/mind.js",
        "views/body.js",
    ):
        source = _read(relative)
        assert "export function mount" in source, relative
        assert "export function update" in source, relative
        assert "export function unmount" in source, relative


def test_body_camera_controls_are_outside_three_renderer():
    viewer = _read("views/body/viewer.js")
    controls = _read("views/body/camera-controls.js")
    assert "mountBodyCameraControls" in viewer
    assert "body-camera-button" in controls
    assert "this.followButton.style.cssText" not in viewer


def test_package_data_contains_nested_workbench_modules():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for pattern in (
        '"web/views/body/*.js"',
        '"web/views/lab/*.js"',
        '"web/views/archive/*.js"',
        '"web/views/shared/*.js"',
        '"web/views/mind/*.js"',
    ):
        assert pattern in pyproject


def test_server_sets_browser_security_headers():
    api = (REPO_ROOT / "src" / "symbiont_lab" / "server" / "api.py").read_text(
        encoding="utf-8"
    )
    assert '"Content-Security-Policy"' in api
    assert '"X-Frame-Options", "DENY"' in api
    assert '"frame-ancestors \'none\'"' in api


def test_mind_uses_real_tab_semantics():
    layout = _read("views/mind/layout.js")
    tabs = _read("views/mind/tab-controller.js")
    assert "setAttribute('role', 'tablist')" in layout
    assert "setAttribute('role', 'tab')" in layout
    assert "setAttribute('aria-selected'" in layout
    assert "setAttribute('role', 'tabpanel')" in layout
    assert "aria-pressed" not in tabs


def test_body_unmount_releases_browser_and_gpu_resources():
    viewer = _read("views/body/viewer.js")
    for required in (
        "cancelAnimationFrame(this.rafId)",
        "this.sse.close()",
        "this.resizeObs.disconnect()",
        "this.controls.dispose()",
        "this.renderer.dispose()",
        "this.workspace?.dispose()",
    ):
        assert required in viewer


def test_mind_unmount_releases_streams_animation_and_observer():
    mind = _read("views/mind.js")
    for required in (
        "cognition.stop()",
        "_streams.close()",
        "_resizeObs.disconnect()",
        "resetPresentation()",
    ):
        assert required in mind


def test_cognition_inspector_does_not_render_snapshot_data_with_inner_html():
    cognition = _read("views/mind/cognition-controller.js")
    assert "innerHTML" not in cognition


def test_mind_layout_is_structural_not_inline_styled():
    layout = _read("views/mind/layout.js")
    assert ".style.cssText" not in layout
    assert "innerHTML" not in layout


def test_identity_sensory_only_keeps_data_driven_inline_styles():
    identity = _read("views/mind/identity-sensory.js")
    assert "innerHTML" not in identity
    # Dynamic visual encodings remain legitimate: confidence/health dots and
    # percentage bars depend on the current snapshot.
    assert identity.count("style.cssText") <= 1


def test_view_specific_css_is_split_from_app_shell():
    html = _read("app.html")
    app_css = _read("app.css")
    assert 'href="/assets/body.css"' in html
    assert 'href="/assets/mind.css"' in html
    assert (WEB_ROOT / "body.css").is_file()
    assert (WEB_ROOT / "mind.css").is_file()
    assert len(app_css) < 20000


def test_cognition_inspector_is_extracted_from_controller():
    controller = _read("views/mind/cognition-controller.js")
    inspector = _read("views/mind/cognition-inspector.js")
    assert "createCognitionInspector" in controller
    assert "function renderCognitionInspector" not in controller
    assert "function renderCognitionInspector" in inspector


def test_cognition_renderer_keeps_shared_graph_helpers():
    controller = _read("views/mind/cognition-controller.js")
    assert "function focusedSectorContext()" in controller
    assert "function currentRenderedTopology()" in controller
    assert "graphSubgraphIds" in controller
