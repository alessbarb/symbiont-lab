from pathlib import Path

from symbiont_lab.app.discovery import discover_experiments
from symbiont_lab.app.models import RunKind, RunStatus


def test_desktop_run_model_is_explicit():
    assert RunKind.EXPERIMENT.value == "experiment"
    assert RunKind.PHYSICS3D.value == "physics3d"
    assert RunStatus.RUNNING.value == "running"


def test_discover_experiments_reads_declarative_catalog(tmp_path: Path):
    exp = tmp_path / "learning" / "demo"
    exp.mkdir(parents=True)
    (exp / "experiment.toml").write_text(
        """schema_version = 1
[experiment]
id = "demo"
title = "Demo experiment"
protocol = "simulate"
protocol_version = 1
hypothesis = "demo hypothesis"
success_criteria = "demo criteria"
[world]
hosts = 4
steps = 12
seed = 7
""",
        encoding="utf-8",
    )
    entries = discover_experiments(tmp_path)
    assert len(entries) == 1
    assert entries[0].category == "learning"
    assert entries[0].experiment_id == "demo"
    assert entries[0].steps == 12


def test_physics3d_monitor_facade_reexports_private_contract():
    from symbiont_lab.app import physics3d_monitor as implementation
    from symbiont_lab.physics3d import monitor as facade

    assert facade.MonitorSnapshot is implementation.MonitorSnapshot
    assert facade.UnifiedViewerProcess is implementation.UnifiedViewerProcess
    assert facade._viewer_main is implementation._viewer_main
    assert facade._put_latest is implementation._put_latest
    assert facade._event_transition is implementation._event_transition


def test_physics3d_cli_uses_application_owned_monitor():
    from symbiont_lab.app import physics3d_monitor
    from symbiont_lab.physics3d import cli

    assert cli.MonitorSnapshot is physics3d_monitor.MonitorSnapshot
    assert cli.UnifiedViewerProcess is physics3d_monitor.UnifiedViewerProcess


def test_application_owned_monitor_has_no_broken_relative_physics_imports():
    import inspect

    from symbiont_lab.app import physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "from .humanoid" not in source
    assert "from .resource" not in source
    assert "from symbiont_lab.physics3d.humanoid import HumanoidPhysics" in source
    assert "from symbiont_lab.physics3d.resource import PhysicalResource" in source


def test_physics3d_runtime_accepts_embedded_viewer_bridge():
    import inspect

    from symbiont_lab.physics3d.cli import run

    assert "viewer_bridge" in inspect.signature(run).parameters


def test_embedded_viewer_api_is_exposed():
    from symbiont_lab.app import physics3d_monitor

    assert callable(physics3d_monitor.mount_embedded_viewer)
    assert physics3d_monitor.QueueViewerBridge is not None


def test_workbench_has_physics_focus_mode():
    import inspect

    from symbiont_lab.app.main_window import SymbiontLabWindow

    source = inspect.getsource(SymbiontLabWindow._set_physics_focus)
    assert "forget(self.left_sidebar)" in source
    assert "forget(self.right_sidebar)" in source
    assert "physics_controls" in source


def test_embedded_viewer_renders_to_actual_viewport_size():
    import inspect

    from symbiont_lab.app import physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "viewport_width = scene_label.winfo_width()" in source
    assert "width, height = 540, 360" not in source
    assert 'scene_panel.bind("<Configure>"' in source


def test_mission_control_uses_resizable_internal_panes():
    import inspect

    from symbiont_lab.app import physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert 'workspace = ttk.Panedwindow(root, orient="horizontal")' in source
    assert "workspace.insert(0, left_panel" in source
    assert "workspace.add(right_panel" in source
    assert "workspace.forget(left_panel)" in source
    assert "workspace.forget(right_panel)" in source


def test_modern_workbench_shell_has_persistent_navigation_rail():
    import inspect

    from symbiont_lab.app.main_window import SymbiontLabWindow

    source = inspect.getsource(SymbiontLabWindow._build_body)
    assert "self.nav_rail" in source
    assert "Experiments" in source
    assert "Body" in source
    assert "Output" in source


def test_embedded_monitor_does_not_repeat_mission_control_branding():
    import inspect

    from symbiont_lab.app import physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert 'text="BODY" if embedded else "SYMBIONT 3D"' in source


def test_workspace_navigation_replaces_visible_notebook_tabs():
    import inspect

    from symbiont_lab.app.main_window import SymbiontLabWindow

    style_source = inspect.getsource(SymbiontLabWindow._configure_style)
    body_source = inspect.getsource(SymbiontLabWindow._build_body)
    assert 'style.layout("Workspace.TNotebook.Tab", [])' in style_source
    assert 'style="Workspace.TNotebook"' in body_source
    assert "_nav_buttons" in body_source


def test_viewer_supports_contextual_3d_selection():
    import inspect

    from symbiont_lab.app import physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "pick_targets" in source
    assert "def select_target" in source
    assert '"<ButtonRelease-1>", on_release' in source
    assert "Observed physics" in source


def test_timeline_can_inspect_historical_ticks_without_mutating_runtime():
    import inspect

    from symbiont_lab.app import physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "def inspect_timeline_tick" in source
    assert 'chart.bind("<Button-1>", inspect_timeline_tick)' in source
    assert "record_history=False" in source
    assert "physical_history" in source


def test_timeline_historical_inspection_can_return_to_live():
    import inspect

    from symbiont_lab.app import physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "def return_to_live" in source
    assert '"pause", "paused": True' in source
    assert '"pause", "paused": False' in source
    assert "if historical_inspection:\n            return" in source


def test_cognition_deep_dive_has_human_facing_knowledge_summary():
    import inspect

    from symbiont_lab.app import physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert '"What does it know?"' in source
    assert 'knowledge_vars["perception"]' in source
    assert 'knowledge_vars["body"]' in source
    assert 'knowledge_vars["world"]' in source
    assert 'knowledge_vars["agency"]' in source
    assert "never labels injected into cognition" in source


def test_physics3d_cli_is_only_an_adapter_over_the_engine():
    import inspect

    from symbiont_lab.app import physics3d_session, run_controller
    from symbiont_lab.physics3d import cli, engine

    assert cli.run is engine.run
    session_source = inspect.getsource(physics3d_session.Physics3DSession._run)
    worker_source = inspect.getsource(run_controller._run_physics3d_worker)
    assert "symbiont_lab.physics3d.engine" in session_source
    assert "symbiont_lab.physics3d.cli" not in session_source
    assert "symbiont_lab.physics3d.engine" in worker_source
    assert "symbiont_lab.physics3d.cli" not in worker_source
