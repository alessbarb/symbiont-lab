"""Canonical Physics3D execution engine, independent of command-line transport."""
from __future__ import annotations

import multiprocessing as mp
import platform
import signal
import shutil
import sys
import threading
from pathlib import Path
import time

from symbiont import __version__ as symbiont_version

from symbiont_lab.app.physics3d_monitor import (
    MonitorSnapshot,
    UnifiedViewerProcess,
    _viewer_main,
    strongest_outputs,
)
from .persistence import (
    load_body_state_file,
    load_symbiont_bundle,
    load_telemetry_records,
    save_body_state_file,
    save_symbiont_bundle,
)
from .runtime import PhysicsServerDisconnected, PyBulletEmbodimentRuntime
from .slm import Physics3DSlmManager
from .telemetry_v41 import AsyncTelemetryV41Writer


DEFAULT_STATE_DIR = Path("~/.local/state/symbiont/physics3d").expanduser()
# v2 deliberately uses a new file. The former Physics3D portable file belonged
# to the parallel Symbiont/Individual stack and cannot be losslessly reinterpreted
# as a canonical OrganismRuntime checkpoint.
DEFAULT_SYMBIONT_FILE = DEFAULT_STATE_DIR / "subject.symbiont"
LEGACY_SYMBIONT_FILE = DEFAULT_STATE_DIR / "subject.symbiont.json"
LEGACY_RUNTIME_FILE = DEFAULT_STATE_DIR / "subject.symbiont-v2.json"
LEGACY_BODY_FILE = DEFAULT_STATE_DIR / "subject.body-v4.json"
DEFAULT_BODY_FILE = DEFAULT_STATE_DIR / "subject.body-v5.json"
DEFAULT_TELEMETRY_FILE = DEFAULT_STATE_DIR / "telemetry-v4.1"


def _archive_existing_subject(
    *,
    symbiont_file: Path,
    body_file: Path,
    telemetry_file: Path,
) -> Path | None:
    candidates = [symbiont_file, body_file, telemetry_file]
    if (
        symbiont_file == DEFAULT_SYMBIONT_FILE
        and body_file == DEFAULT_BODY_FILE
        and LEGACY_BODY_FILE not in candidates
    ):
        # Preserve the final v4 pose as historical apparatus evidence when the
        # default subject is moved to the v5 constitution.
        candidates.append(LEGACY_BODY_FILE)
    existing = tuple(
        path
        for path in candidates
        if path.exists() and (path != telemetry_file or path.is_file())
    )
    if not existing:
        return None

    archive_root = symbiont_file.parent / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        destination = archive_root / f"run-{index:04d}"
        if not destination.exists():
            break
        index += 1
    destination.mkdir()

    for source in existing:
        shutil.move(str(source), str(destination / source.name))
    return destination


def _write_checkpoint_payloads(
    runtime_payload: dict,
    body_payload: dict,
    *,
    symbiont_file: Path,
    body_file: Path,
    models_dir: Path,
) -> None:
    # The portable organism is authoritative. Save it first so loss of the
    # native physics server can never erase the newest cognitive state.
    save_symbiont_bundle(runtime_payload, models_dir, symbiont_file)
    save_body_state_file(body_payload, body_file)


def _save_checkpoint(
    runtime: PyBulletEmbodimentRuntime,
    *,
    symbiont_file: Path,
    body_file: Path,
    models_dir: Path,
    async_write: bool = False,
    active_thread: threading.Thread | None = None,
    lifecycle_state: str = "active",
) -> threading.Thread | None:
    if active_thread is not None and active_thread.is_alive():
        active_thread.join()
    runtime_payload = runtime.checkpoint(lifecycle_state=lifecycle_state)
    saved_tick = int(runtime_payload.get("saved_at_tick") or 0)
    signal_payload = runtime.organism.signal_knowledge.checkpoint()
    signal_tick = signal_payload.get("last_tick")
    # A signal can arrive in the middle of organism.tick().  The signal
    # knowledge engine observes the next tick before the kernel increments its
    # public counter, so persisting at that point would create a checkpoint
    # that cannot be restored coherently.
    if signal_tick is not None and int(signal_tick) != saved_tick:
        raise RuntimeError(
            "refusing incoherent checkpoint: signal knowledge tick "
            f"{signal_tick} != runtime tick {saved_tick}"
        )

    if not async_write:
        # The portable organism is authoritative. Save it first so loss of the
        # native physics server can never erase the newest cognitive state.
        save_symbiont_bundle(runtime_payload, models_dir, symbiont_file)
        body_payload, physical_tick = runtime.physical_checkpoint()
        body_payload["symbiont_ticks"] = physical_tick
        save_body_state_file(body_payload, body_file)
        return None

    try:
        body_payload, physical_tick = runtime.physical_checkpoint()
        body_payload["symbiont_ticks"] = physical_tick
    except Exception:
        save_symbiont_bundle(runtime_payload, models_dir, symbiont_file)
        raise

    thread = threading.Thread(
        target=_write_checkpoint_payloads,
        args=(runtime_payload, body_payload),
        kwargs={
            "symbiont_file": symbiont_file,
            "body_file": body_file,
            "models_dir": models_dir,
        },
        daemon=True,
    )
    thread.start()
    return thread



def _sensorimotor_checkpoint_schema(payload: dict | None) -> int | None:
    if not isinstance(payload, dict):
        return None
    actuation = payload.get("actuation")
    if not isinstance(actuation, dict):
        return None
    sensorimotor = actuation.get("sensorimotor")
    if not isinstance(sensorimotor, dict):
        return None
    value = sensorimotor.get("schema_version")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _require_current_motor_evidence(
    payload: dict | None,
    *,
    fresh_body: bool,
    new_symbiont: bool,
) -> None:
    if payload is None or fresh_body or new_symbiont:
        return
    schema = _sensorimotor_checkpoint_schema(payload)
    if schema in (9, 10):
        return
    raise RuntimeError(
        "Physics3D checkpoint carries sensorimotor evidence from an incompatible "
        f"schema ({schema!r}); canonical motor learning requires migratable v9 "
        "or body-scoped v10 evidence. "
        "Use --fresh-body to re-embody the same Symbiont and revalidate "
        "body-specific knowledge, or --new-symbiont for a clean individual. "
        "The old motor evidence will not be silently reinterpreted."
    )


_HEADLESS_PROGRESS_TTY = sys.stdout.isatty()


def _print_headless_progress(
    record: object, *, checkpoint_age: int, realtime_ratio: float
) -> None:
    """Emit a compact progress line in headless mode.

    TTY: overwrite the same line with \\r so the terminal stays clean.
    Non-TTY (pipe / log): append a newline so every tick is grep-able.
    """
    pos = getattr(record, "base_position", (0.0, 0.0, 0.0))
    line = (
        f"tick={getattr(record, 'tick', 0):>7,}"
        f"  z={pos[2]:+.3f}"
        f"  schema={getattr(record, 'schema_confidence', 0.0):.3f}"
        f"  parts={getattr(record, 'schema_parts', 0):>3}"
        f"  deps={getattr(record, 'schema_dependencies', 0):>3}"
        f"  effort={getattr(record, 'absolute_actuator_work_joules', getattr(record, 'mechanical_work_joules', 0.0)):.3f}J"
        f"  rt={realtime_ratio:.2f}x"
        f"  ckpt={checkpoint_age:>5}"
    )
    if _HEADLESS_PROGRESS_TTY:
        sys.stdout.write(f"\r{line}  ")
        sys.stdout.flush()
    else:
        print(line)


def run(
    *,
    headless: bool = False,
    ticks: int = 0,
    seed: int = 42,
    hz: int = 240,
    cognition_hz: int = 24,
    mechanical_work_cost_per_joule: float = 0.001,
    telemetry_physics_trace: bool = False,
    body_kind: str = "anthropomorphic-v5",
    symbiont_file: Path = DEFAULT_SYMBIONT_FILE,
    body_file: Path = DEFAULT_BODY_FILE,
    telemetry_file: Path = DEFAULT_TELEMETRY_FILE,
    checkpoint_interval: int = 256,
    fresh_body: bool = False,
    new_symbiont: bool = False,
    show_monitor: bool = True,
    viewer_bridge=None,
    enable_slm: bool = True,
    slm_train_interval: int = 1,
    slm_device: str = "cpu",
    ready_callback=None,
    startup_callback=None,
) -> int:
    if hz < 30:
        raise ValueError("hz must be >= 30")
    if cognition_hz < 1 or cognition_hz > hz:
        raise ValueError("cognition_hz must be within [1, hz]")
    if hz % cognition_hz != 0:
        raise ValueError("hz must be an integer multiple of cognition_hz")
    if checkpoint_interval < 1:
        raise ValueError("checkpoint_interval must be >= 1")

    if new_symbiont:
        archived = _archive_existing_subject(
            symbiont_file=symbiont_file,
            body_file=body_file,
            telemetry_file=telemetry_file,
        )
        if archived is not None:
            print(f"Archived previous Physics3D subject at {archived}")

    def _startup(stage: str) -> None:
        if startup_callback is not None:
            startup_callback(stage)

    models_dir = symbiont_file.parent / "models"
    runtime_checkpoint = None
    _startup("loading_checkpoint")
    if symbiont_file.exists() and not new_symbiont:
        runtime_checkpoint = load_symbiont_bundle(symbiont_file, models_dir)
        print(
            f"Loaded canonical Symbiont {runtime_checkpoint.get('organism_id', 'unknown')} "
            f"at tick {int(runtime_checkpoint.get('saved_at_tick') or 0):,} "
            f"from {symbiont_file}"
        )
        _require_current_motor_evidence(
            runtime_checkpoint,
            fresh_body=fresh_body,
            new_symbiont=new_symbiont,
        )
    elif symbiont_file == DEFAULT_SYMBIONT_FILE and not new_symbiont:
        legacy = next(
            (
                path
                for path in (LEGACY_SYMBIONT_FILE, LEGACY_RUNTIME_FILE)
                if path.exists()
            ),
            None,
        )
        if legacy is not None:
            print(
                f"Legacy Physics3D subject preserved at {legacy}. "
                "Starting a new canonical-runtime subject; no incompatible cognitive "
                "state is being fabricated or silently migrated."
            )

    physical_state = None
    if body_file.exists() and not fresh_body and not new_symbiont:
        candidate = load_body_state_file(body_file)
        expected_tick = (
            int(runtime_checkpoint.get("saved_at_tick") or 0)
            if runtime_checkpoint is not None
            else 0
        )
        saved_tick = int(candidate.get("symbiont_ticks", -1))
        if runtime_checkpoint is not None and saved_tick == expected_tick:
            physical_state = candidate
            print(f"Restoring physical embodiment from {body_file}")
        elif runtime_checkpoint is not None:
            print(
                "Ignoring physical body checkpoint because it does not match "
                f"the organism tick ({saved_tick} != {expected_tick})."
            )

    if fresh_body and runtime_checkpoint is not None:
        print("Implanting persisted canonical Symbiont into a fresh physical body.")

    if new_symbiont or runtime_checkpoint is None:
        embodiment_mode = "new"
    elif physical_state is not None:
        embodiment_mode = "resume"
    else:
        embodiment_mode = "reembodiment"

    time_step = 1.0 / float(hz)
    cognition_period = 1.0 / float(cognition_hz)
    physics_substeps_per_tick = hz // cognition_hz
    # Normal interactive mode renders PyBullet in DIRECT and embeds the camera
    # image into the unified evaluator window. The native PyBullet GUI remains
    # available only when the evaluator is explicitly disabled.
    _startup("restoring_runtime")
    runtime = PyBulletEmbodimentRuntime(
        gui=(not headless and not show_monitor),
        seed=seed,
        time_step=time_step,
        physics_substeps_per_tick=physics_substeps_per_tick,
        mechanical_work_cost_per_joule=mechanical_work_cost_per_joule,
        capture_physics_trace=telemetry_physics_trace,
        body_kind=body_kind,
        runtime_checkpoint=runtime_checkpoint,
        physical_state=physical_state,
    )
    runtime_config = runtime.checkpoint().get("effective_config", {})
    telemetry_configuration = (
        dict(runtime_config) if isinstance(runtime_config, dict) else {}
    )
    telemetry_configuration["telemetry_physics_trace"] = bool(
        telemetry_physics_trace
    )
    telemetry_configuration["body_kind"] = body_kind
    runtime_checkpoint_for_identity = runtime.checkpoint()
    raw_genome = runtime_checkpoint_for_identity.get("genome", {})
    software_identity = {
        "symbiont_version": str(symbiont_version),
        "python": platform.python_version(),
        "genome_id": (
            raw_genome.get("genome_id")
            if isinstance(raw_genome, dict)
            else None
        ),
    }
    if runtime_checkpoint is not None:
        expected_tick = int(runtime_checkpoint.get("saved_at_tick") or 0)
        expected_id = str(runtime_checkpoint.get("organism_id") or "")
        ledger_payload = runtime_checkpoint.get("experience_ledger", {})
        registry_payload = runtime_checkpoint.get("private_model_registry", {})
        expected_records = (
            len(ledger_payload.get("records", []))
            if isinstance(ledger_payload, dict)
            and isinstance(ledger_payload.get("records", []), list)
            else 0
        )
        expected_models = (
            len(registry_payload.get("records", []))
            if isinstance(registry_payload, dict)
            and isinstance(registry_payload.get("records", []), list)
            else 0
        )
        restored_records = len(runtime.organism.experience_ledger.records)
        restored_models = len(runtime.organism.model_registry.records)
        if runtime.tick_count != expected_tick:
            raise RuntimeError(
                "continuity verification failed: restored tick "
                f"{runtime.tick_count} != checkpoint tick {expected_tick}"
            )
        if expected_id and runtime.organism_id != expected_id:
            raise RuntimeError(
                "continuity verification failed: restored organism identity changed"
            )
        if restored_records != expected_records:
            raise RuntimeError(
                "continuity verification failed: restored experience ledger "
                f"{restored_records} != checkpoint {expected_records}"
            )
        if restored_models != expected_models:
            raise RuntimeError(
                "continuity verification failed: restored model registry "
                f"{restored_models} != checkpoint {expected_models}"
            )
        print(
            "Continuity verified: "
            f"tick={runtime.tick_count:,}, "
            f"experiences={restored_records:,}, "
            f"models={restored_models}"
        )

    previous_signal_handlers: dict[int, object] = {}
    stop_requested = False

    def _graceful_stop(signum, _frame) -> None:
        nonlocal stop_requested
        # WARN: Defer shutdown until the current organism tick has returned. Raising
        # here can interrupt runtime.tick() after signal knowledge has advanced
        # but before the kernel tick counter is incremented.
        stop_requested = True

    owns_signal_handlers = threading.current_thread() is threading.main_thread()
    if owns_signal_handlers:
        for signal_name in ("SIGINT", "SIGTERM", "SIGHUP"):
            signum = getattr(signal, signal_name, None)
            if signum is not None:
                previous_signal_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, _graceful_stop)

    slm = None
    if enable_slm:
        _startup("attaching_model")
        slm = Physics3DSlmManager(
            models_dir=models_dir,
            train_interval=slm_train_interval,
            device=slm_device,
        )
        slm.attach_existing(
            runtime.organism,
            candidate_model_ids=runtime.historical_private_model_candidates,
        )

    remaining = None if ticks <= 0 else ticks
    record = None
    last_checkpoint_tick = runtime.tick_count
    viewer = viewer_bridge
    if viewer is None and show_monitor and not headless:
        viewer = UnifiedViewerProcess(mp.get_context("spawn"))
        viewer.start()
    if viewer is not None and viewer.poll_stop():
        stop_requested = True

    telemetry = AsyncTelemetryV41Writer(
        telemetry_file,
        organism_id=runtime.organism_id,
        start_tick=runtime.tick_count,
        seed=seed,
        physics_hz=hz,
        cognition_hz=cognition_hz,
        embodiment_mode=embodiment_mode,
        effective_configuration=telemetry_configuration,
        software_identity=software_identity,
    )

    _startup("ready")
    if ready_callback is not None:
        ready_callback()

    is_paused = False
    step_once = False
    speed_multiplier = 1.0
    active_checkpoint_thread: threading.Thread | None = None

    try:
        while not stop_requested and (remaining is None or remaining > 0):
            if viewer is not None:
                for cmd in viewer.poll_commands():
                    cmd_type = cmd.get("type")
                    if cmd_type == "stop":
                        stop_requested = True
                    elif cmd_type == "pause":
                        is_paused = bool(cmd.get("paused", True))
                    elif cmd_type == "step":
                        step_once = True
                    elif cmd_type == "speed":
                        speed_multiplier = max(0.1, min(10.0, float(cmd.get("speed", 1.0))))

            if stop_requested:
                break

            if is_paused and not step_once:
                time.sleep(0.04)
                continue

            was_manual_step = step_once
            step_once = False

            cycle_started = time.perf_counter()
            record = runtime.step()
            runtime_elapsed = time.perf_counter() - cycle_started

            # Drain presentation-only pose samples captured inside the 240 Hz
            # physics integration loop. The bridge emits them as a lightweight
            # 60 Hz observer stream; they never enter organism state.
            pose_frames = runtime.drain_presentation_pose_frames()
            if viewer is not None:
                publish_pose_frame = getattr(viewer, "publish_pose_frame", None)
                if callable(publish_pose_frame):
                    for pose_frame in pose_frames:
                        physical_state = pose_frame.get("physical_state")
                        if not isinstance(physical_state, dict):
                            continue
                        publish_pose_frame(
                            physical_state=physical_state,
                            tick=int(pose_frame["tick"]),
                            substep_index=int(pose_frame["substep_index"]),
                            physics_step=int(pose_frame["physics_step"]),
                            simulation_time_s=float(
                                pose_frame["simulation_time_s"]
                            ),
                            tick_simulation_span_s=float(
                                pose_frame["tick_simulation_span_s"]
                            ),
                        )

            rich_state = runtime.passive_telemetry_state()
            episodic_snapshot = getattr(runtime.organism, "episodic_memory_snapshot", None)
            if callable(episodic_snapshot):
                rich_state["episodic_memory"] = episodic_snapshot()
            if slm is not None:
                rich_state["slm"] = {
                    "training": bool(slm.training),
                    "last_error": slm.last_error,
                    "last_gate_reason": slm.last_gate_reason,
                    "last_gate_gain": slm.last_gate_gain,
                    "last_best_baseline": slm.last_best_baseline,
                    "last_candidate_loss": slm.last_candidate_loss,
                    "last_best_baseline_loss": slm.last_best_baseline_loss,
                    "last_plan_reason": slm.last_plan_reason,
                    "last_plan_replay_pressure": slm.last_plan_replay_pressure,
                    "last_plan_epochs": slm.last_plan_epochs,
                    "last_plan_steps": slm.last_plan_steps,
                    "last_internal_validation_loss": slm.last_internal_validation_loss,
                    "last_internal_validation_accuracy": slm.last_internal_validation_accuracy,
                    "last_epochs_completed": slm.last_epochs_completed,
                    "last_steps_completed": slm.last_steps_completed,
                    "last_parameter_count": slm.last_parameter_count,
                    "last_resolved_embedding_dim": slm.last_resolved_embedding_dim,
                    "last_resolved_hidden_dim": slm.last_resolved_hidden_dim,
                    "last_vocab_size": slm.last_vocab_size,
                }
            full_snapshot = None
            if telemetry.needs_snapshot(record.tick):
                full_snapshot = {
                    "organism": runtime.checkpoint(),
                    "physical": runtime.passive_physical_state(),
                }
            telemetry.append(
                record,
                rich_state=rich_state,
                full_snapshot=full_snapshot,
            )

            if slm is not None:
                slm.maybe_schedule(runtime.organism, current_tick=record.tick)

            # The dense 60 Hz body_pose stream above owns motion rendering.
            # Keep body/cognition/vitals and rich snapshots at the original
            # sparse observer cadence so presentation traffic cannot crowd out
            # diagnostics on the SSE transport.
            rich_render_due = (
                viewer is not None
                and (was_manual_step or record.tick % max(1, cognition_hz // 5) == 0)
            )
            body_render_due = rich_render_due

            cycle_elapsed = time.perf_counter() - cycle_started
            realtime_ratio = min(
                1.0,
                cognition_period / max(cycle_elapsed, 1e-9),
            )

            if headless and record.tick % cognition_hz == 0:
                _print_headless_progress(
                    record,
                    checkpoint_age=max(0, record.tick - last_checkpoint_tick),
                    realtime_ratio=realtime_ratio,
                )

            if body_render_due and viewer is not None:
                episodic_state = rich_state.get("episodic_memory", {})
                if not isinstance(episodic_state, dict):
                    episodic_state = {}
                viewer.publish(
                    MonitorSnapshot(
                        tick=record.tick,
                        symbiont_id=runtime.organism_id,
                        embodiment_mode=embodiment_mode,
                        alive=record.alive,
                        schema_confidence=record.schema_confidence,
                        schema_parts=record.schema_parts,
                        schema_sensory_parts=record.schema_sensory_parts,
                        schema_cognitive_regions=record.schema_cognitive_regions,
                        schema_dependency_evidence=record.schema_dependency_evidence,
                        schema_dependencies=record.schema_dependencies,
                        predictor_count=record.predictor_count,
                        shadow_prediction_count=record.shadow_prediction_count,
                        promotable_shadow_count=record.promotable_shadow_count,
                        prediction_error=record.prediction_error,
                        active_effectors=record.active_effectors,
                        joint_motion=record.joint_motion,
                        contact_count=record.contact_count,
                        ground_contact_count=record.ground_contact_count,
                        self_contact_count=record.self_contact_count,
                        resource_contact_count=record.resource_contact_count,
                        mechanical_work_joules=record.mechanical_work_joules,
                        positive_actuator_work_joules=record.positive_actuator_work_joules,
                        negative_actuator_work_joules=record.negative_actuator_work_joules,
                        absolute_actuator_work_joules=record.absolute_actuator_work_joules,
                        net_actuator_work_joules=record.net_actuator_work_joules,
                        metabolic_work_cost=record.metabolic_work_cost,
                        height=record.base_position[2],
                        checkpoint_age=max(0, record.tick - last_checkpoint_tick),
                        symbiont_file=str(symbiont_file),
                        strongest_outputs=strongest_outputs(runtime.motor_activity()),
                        slm_records=record.slm_records,
                        slm_transition_records=record.slm_transition_records,
                        slm_models=record.slm_models,
                        slm_active=record.slm_active,
                        slm_training=bool(slm.training) if slm is not None else False,
                        slm_error=slm.last_error if slm is not None else None,
                        slm_gate_reason=(
                            slm.last_gate_reason if slm is not None else None
                        ),
                        slm_gate_gain=(
                            slm.last_gate_gain if slm is not None else None
                        ),
                        slm_best_baseline=(
                            slm.last_best_baseline if slm is not None else None
                        ),
                        slm_candidate_loss=(
                            slm.last_candidate_loss if slm is not None else None
                        ),
                        slm_best_baseline_loss=(
                            slm.last_best_baseline_loss if slm is not None else None
                        ),
                        cycle_ms=runtime_elapsed * 1000.0,
                        realtime_ratio=realtime_ratio,
                        organism_ms=record.organism_ms,
                        physics_ms=record.physics_ms,
                        diagnostics_ms=record.diagnostics_ms,
                        resource_distance=record.resource_distance,
                        resource_field=record.resource_field,
                        resource_remaining=record.resource_remaining,
                        absorbed_energy=record.absorbed_energy,
                        metabolic_reserve_ratio=record.metabolic_reserve_ratio,
                        displacement_from_origin=record.displacement_from_origin,
                        action_source=record.action_source,
                        initial_resource_distance=record.initial_resource_distance,
                        minimum_resource_distance=record.minimum_resource_distance,
                        resource_progress=record.resource_progress,
                        action_source_competence=record.action_source_competence,
                        action_source_exploration=record.action_source_exploration,
                        action_source_protection=record.action_source_protection,
                        action_source_prospection=record.action_source_prospection,
                        action_source_regulation=record.action_source_regulation,
                        action_source_none=record.action_source_none,
                                                motor_repertoire_size=record.motor_repertoire_size,
                        sensorimotor_coverage=record.sensorimotor_coverage,
                        sensorimotor_patterns=record.sensorimotor_patterns,
                        motor_competence_candidates=record.motor_competence_candidates,
                        motor_competences=record.motor_competences,
                        best_motor_controllability=record.best_motor_controllability,
                        best_motor_directional_consistency=record.best_motor_directional_consistency,
                        competence_replay_active=record.competence_replay_active,
                        sensorimotor_h1_samples=record.sensorimotor_h1_samples,
                        sensorimotor_h4_samples=record.sensorimotor_h4_samples,
                        sensorimotor_h16_samples=record.sensorimotor_h16_samples,
                        sensorimotor_h64_samples=record.sensorimotor_h64_samples,
                        passive_baseline_samples=record.passive_baseline_samples,
                        episodic_episodes=int(episodic_state.get("episode_count", 0)),
                        episodic_pending_records=int(episodic_state.get("pending_records", 0)),
                        episodic_compressed_episodes=int(
                            episodic_state.get("compressed_episode_count", 0)
                        ),
                        episodic_total_occurrences=int(
                            episodic_state.get("total_occurrences", 0)
                        ),
                        episodic_mean_recurrence=float(
                            episodic_state.get("mean_recurrence", 0.0)
                        ),
                        episodic_exceptions=int(
                            episodic_state.get("exception_count", 0)
                        ),
                        episodic_checkpoint_bytes=int(
                            episodic_state.get("checkpoint_bytes", 0)
                        ),
                        episodic_interpretations=int(
                            episodic_state.get("interpretation_count", 0)
                        ),
                        episodic_contingencies=int(
                            episodic_state.get("consolidated_contingencies", 0)
                        ),
                        episodic_retrievals=int(
                            episodic_state.get("retrieval_count", 0)
                        ),
                        episodic_replays=int(
                            episodic_state.get("replay_count", 0)
                        ),
                        episodic_compactions=int(
                            episodic_state.get("compaction_count", 0)
                        ),
                        episodic_evictions=int(
                            episodic_state.get("eviction_count", 0)
                        ),
                        episodic_oldest_age=int(
                            episodic_state.get("oldest_episode_age", 0)
                        ),
                        episodic_mean_age=float(
                            episodic_state.get("mean_episode_age", 0.0)
                        ),
                                                                        prospective_reason=record.prospective_reason,
                        prospective_candidates=record.prospective_candidates,
                        prospective_selected=record.prospective_selected,
                        prospective_action_id=record.prospective_action_id,
                        prospective_predicted_outcome=record.prospective_predicted_outcome,
                        prospective_expected_value=record.prospective_expected_value,
                        prospective_model_confidence=record.prospective_model_confidence,
                        prospective_value_confidence=record.prospective_value_confidence,
                        prospective_value_samples=record.prospective_value_samples,
                        prospective_decision_margin=record.prospective_decision_margin,
                        prospective_cost=record.prospective_cost,
                        recurrent_competence_candidates=record.recurrent_competence_candidates,
                        max_competence_samples=record.max_competence_samples,
                        full_competence_gate_candidates=record.full_competence_gate_candidates,
                        motor_readout_nodes=record.motor_readout_nodes,
                        competence_readout_nodes=record.competence_readout_nodes,
                        cognitive_motor_output_edges=record.cognitive_motor_output_edges,
                        cognitive_concepts=record.cognitive_concepts,
                        cognitive_readouts=record.cognitive_readouts,
                    ),
                    physical_state=runtime.passive_physical_state(),
                )
                if rich_render_due:
                    publish_rich = getattr(viewer, "publish_rich_state", None)
                    if callable(publish_rich):
                        publish_rich(rich_state)

            if remaining is not None:
                remaining -= 1

            if runtime.tick_count % checkpoint_interval == 0:
                telemetry.flush()
                active_checkpoint_thread = _save_checkpoint(
                    runtime,
                    symbiont_file=symbiont_file,
                    body_file=body_file,
                    models_dir=models_dir,
                    async_write=True,
                    active_thread=active_checkpoint_thread,
                )
                last_checkpoint_tick = runtime.tick_count

            if not headless:
                target_period = cognition_period / max(0.1, speed_multiplier)
                remaining_time = target_period - cycle_elapsed
                if remaining_time > 0.0:
                    time.sleep(remaining_time)
            if not record.alive:
                break
    except PhysicsServerDisconnected:
        print("PyBullet window closed; ending embodiment cleanly.")
    except KeyboardInterrupt:
        pass
    finally:
        telemetry.flush()
        if active_checkpoint_thread is not None and active_checkpoint_thread.is_alive():
            active_checkpoint_thread.join()
        try:
            _save_checkpoint(
                runtime,
                symbiont_file=symbiont_file,
                body_file=body_file,
                models_dir=models_dir,
                lifecycle_state="dormant",
            )
        except Exception as exc:
            print(
                f"Final checkpoint failed: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
        if headless and _HEADLESS_PROGRESS_TTY:
            # Terminate the last \r-overwritten progress line before the summary.
            print()
        if headless and record is not None:
            pos = record.base_position
            print(
                f"ticks={runtime.tick_count} "
                f"base=({pos[0]:+.3f},{pos[1]:+.3f},{pos[2]:+.3f}) "
                f"schema={record.schema_confidence:.4f} "
                f"parts={record.schema_parts} "
                f"deps={record.schema_dependencies} "
                f"slm_records={record.slm_records}"
            )
        print(f"Symbiont state: {symbiont_file}")
        print(f"Body state:     {body_file}")
        print(f"Telemetry run:  {telemetry.root}")
        if viewer is not None:
            viewer.close()
        if slm is not None:
            slm.close()
        telemetry.close()
        runtime.close()
        if owns_signal_handlers:
            for signum, previous_handler in previous_signal_handlers.items():
                signal.signal(signum, previous_handler)
    return 0
