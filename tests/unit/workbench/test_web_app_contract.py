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
    assert 'class="statusbar-state" role="status" aria-live="polite"' in html
    assert '<footer class="statusbar" role="status"' not in html


def test_router_is_declarative_and_polling_is_not_interval_based():
    app = _read("app.js")
    assert "const ROUTES = {" in app
    assert "RuntimeStatePoller" in app
    assert "setInterval(" not in app
    assert "removeAttribute('aria-current')" in app
    assert "history.replaceState" in app


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
