from pathlib import Path


def test_physics_engine_samples_rich_observation_independently_of_cognition() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont_lab" / "physics3d" / "engine.py").read_text(encoding="utf-8")
    loop = source[source.index("            next_tick = runtime.tick_count + 1") :]

    assert "observation_due = rates.observation_due(" in loop
    assert "runtime.step(include_observability=observation_due)" in loop
    assert "if observation_due:" in loop
    assert "telemetry.append(" in loop
    assert "rich_render_due = viewer is not None and observation_due" in loop

    # The old implicit coupling/hard-coded ratios must not return.
    assert "record.tick % max(1, cognition_hz // 5)" not in loop
    assert "_presentation_substep % 4" not in source


def test_physics_runtime_keeps_rich_projection_behind_observer_boundary() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont_lab" / "physics3d" / "runtime.py").read_text(
        encoding="utf-8"
    )
    step = source[source.index("    def step(", source.index("class PyBulletEmbodimentRuntime")) :]

    assert "physical_actuation_override" in step.split("): Tick3D:", 1)[0]
    assert "include_observability=include_observability" in step
    assert "if include_observability:" in step
    assert "self._last_telemetry_state = {" in step
    assert "self._presentation_phase += self.presentation_hz" in step
    assert "self._presentation_phase >= self.physics_hz" in step
