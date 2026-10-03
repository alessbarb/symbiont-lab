def test_physics3d_monitor_facade_reexports_private_contract():
    from lab.app.physics3d.monitor import viewer as facade
    from lab.app.physics3d.monitor import viewer as implementation

    assert facade.MonitorSnapshot is implementation.MonitorSnapshot
    assert facade.UnifiedViewerProcess is implementation.UnifiedViewerProcess
    assert facade._viewer_main is implementation._viewer_main
    assert facade._put_latest is implementation._put_latest
    assert facade._event_transition is implementation._event_transition


def test_physics3d_engine_uses_application_owned_monitor():
    from lab.app.physics3d.monitor import viewer as physics3d_monitor
    from lab.physics3d import engine

    assert engine.MonitorSnapshot is physics3d_monitor.MonitorSnapshot
    assert engine.UnifiedViewerProcess is physics3d_monitor.UnifiedViewerProcess


def test_application_owned_monitor_has_no_broken_relative_physics_imports():
    import inspect

    from lab.app.physics3d.monitor import viewer as physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "from .humanoid" not in source
    assert "from .resource" not in source
    assert "from embodiment.physics3d.humanoid import HumanoidPhysics" in source
    assert "from environment.physics3d.resource import PhysicalResource" in source


def test_physics3d_runtime_accepts_embedded_viewer_bridge():
    import inspect

    from lab.physics3d.cli import run

    assert "viewer_bridge" in inspect.signature(run).parameters


def test_embedded_viewer_api_is_exposed():
    from lab.app.physics3d.monitor import viewer as physics3d_monitor

    assert callable(physics3d_monitor.mount_embedded_viewer)
    assert physics3d_monitor.QueueViewerBridge is not None


def test_embedded_viewer_renders_to_actual_viewport_size():
    import inspect

    from lab.app.physics3d.monitor import viewer as physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "viewport_width = scene_label.winfo_width()" in source
    assert "width, height = 540, 360" not in source
    assert 'scene_panel.bind("<Configure>"' in source


def test_mission_control_uses_resizable_internal_panes():
    import inspect

    from lab.app.physics3d.monitor import viewer as physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert 'workspace = ttk.Panedwindow(root, orient="horizontal")' in source
    assert "workspace.insert(0, left_panel" in source
    assert "workspace.add(right_panel" in source
    assert "workspace.forget(left_panel)" in source
    assert "workspace.forget(right_panel)" in source


def test_embedded_monitor_does_not_repeat_mission_control_branding():
    import inspect

    from lab.app.physics3d.monitor import viewer as physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert 'text="BODY" if embedded else "SYMBIONT 3D"' in source


def test_viewer_supports_contextual_3d_selection():
    import inspect

    from lab.app.physics3d.monitor import viewer as physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "pick_targets" in source
    assert "def select_target" in source
    assert '"<ButtonRelease-1>", on_release' in source
    assert "Observed physics" in source


def test_timeline_can_inspect_historical_ticks_without_mutating_runtime():
    import inspect

    from lab.app.physics3d.monitor import viewer as physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "def inspect_timeline_tick" in source
    assert 'chart.bind("<Button-1>", inspect_timeline_tick)' in source
    assert "record_history=False" in source
    assert "physical_history" in source


def test_timeline_historical_inspection_can_return_to_live():
    import inspect

    from lab.app.physics3d.monitor import viewer as physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert "def return_to_live" in source
    assert '"pause", "paused": True' in source
    assert '"pause", "paused": False' in source
    assert "if historical_inspection:\n            return" in source


def test_cognition_deep_dive_has_human_facing_knowledge_summary():
    import inspect

    from lab.app.physics3d.monitor import viewer as physics3d_monitor

    source = inspect.getsource(physics3d_monitor._viewer_main)
    assert '"What does it know?"' in source
    assert 'knowledge_vars["perception"]' in source
    assert 'knowledge_vars["body"]' in source
    assert 'knowledge_vars["world"]' in source
    assert 'knowledge_vars["agency"]' in source
    assert "never labels injected into cognition" in source
