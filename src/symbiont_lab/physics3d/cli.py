"""CLI for the lightweight canonical 3D embodiment experiment."""
from __future__ import annotations

import argparse
import multiprocessing as mp
from pathlib import Path
import time

from .monitor import MonitorProcess, MonitorSnapshot, strongest_outputs
from .persistence import (
    TelemetryWriter,
    load_body_state_file,
    load_runtime_state_file,
    save_body_state_file,
    save_runtime_state_file,
)
from .runtime import PyBulletEmbodimentRuntime
from .slm import Physics3DSlmManager


DEFAULT_STATE_DIR = Path("~/.local/state/symbiont/physics3d").expanduser()
# v2 deliberately uses a new file. The former Physics3D portable file belonged
# to the parallel Symbiont/Individual stack and cannot be losslessly reinterpreted
# as a canonical OrganismRuntime checkpoint.
DEFAULT_SYMBIONT_FILE = DEFAULT_STATE_DIR / "subject.symbiont-v2.json"
LEGACY_SYMBIONT_FILE = DEFAULT_STATE_DIR / "subject.symbiont.json"
DEFAULT_BODY_FILE = DEFAULT_STATE_DIR / "subject.body.json"
DEFAULT_TELEMETRY_FILE = DEFAULT_STATE_DIR / "subject.telemetry.ndjson"
DEFAULT_MODELS_DIR = DEFAULT_STATE_DIR / "models"


def _save_checkpoint(
    runtime: PyBulletEmbodimentRuntime,
    *,
    symbiont_file: Path,
    body_file: Path,
) -> None:
    body_payload = runtime.apparatus.export_physical_state()
    body_payload["symbiont_ticks"] = runtime.tick_count
    # Physical state first. A mismatched body checkpoint is ignored on restore.
    save_body_state_file(body_payload, body_file)
    save_runtime_state_file(runtime.checkpoint(), symbiont_file)


def run(
    *,
    headless: bool = False,
    ticks: int = 0,
    seed: int = 42,
    hz: int = 240,
    symbiont_file: Path = DEFAULT_SYMBIONT_FILE,
    body_file: Path = DEFAULT_BODY_FILE,
    telemetry_file: Path = DEFAULT_TELEMETRY_FILE,
    checkpoint_interval: int = 1000,
    fresh_body: bool = False,
    new_symbiont: bool = False,
    show_monitor: bool = True,
    enable_slm: bool = True,
    slm_train_interval: int = 4096,
    slm_min_records: int = 64,
    slm_device: str = "cpu",
) -> int:
    if hz < 30:
        raise ValueError("hz must be >= 30")
    if checkpoint_interval < 1:
        raise ValueError("checkpoint_interval must be >= 1")

    runtime_checkpoint = None
    if symbiont_file.exists() and not new_symbiont:
        runtime_checkpoint = load_runtime_state_file(symbiont_file)
        if runtime_checkpoint.get("artifact_type") == "portable-symbiont":
            raise ValueError(
                "legacy Physics3D Symbiont file cannot be loaded as a canonical "
                "runtime; keep it as historical evidence and use the v2 default path"
            )
        print(
            f"Loaded canonical Symbiont {runtime_checkpoint.get('organism_id', 'unknown')} "
            f"at tick {int(runtime_checkpoint.get('saved_at_tick') or 0):,} "
            f"from {symbiont_file}"
        )
    elif (
        symbiont_file == DEFAULT_SYMBIONT_FILE
        and LEGACY_SYMBIONT_FILE.exists()
        and not new_symbiont
    ):
        print(
            f"Legacy Physics3D subject preserved at {LEGACY_SYMBIONT_FILE}. "
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
        embodiment_mode = "transplant"

    time_step = 1.0 / float(hz)
    telemetry = TelemetryWriter(telemetry_file)
    runtime = PyBulletEmbodimentRuntime(
        gui=not headless,
        seed=seed,
        time_step=time_step,
        runtime_checkpoint=runtime_checkpoint,
        physical_state=physical_state,
    )

    slm = None
    if enable_slm:
        slm = Physics3DSlmManager(
            models_dir=DEFAULT_MODELS_DIR,
            train_interval=slm_train_interval,
            min_records=slm_min_records,
            device=slm_device,
        )
        slm.attach_existing(runtime.organism)

    remaining = None if ticks <= 0 else ticks
    record = None
    last_checkpoint_tick = runtime.tick_count
    monitor = None
    if show_monitor and not headless:
        monitor = MonitorProcess(mp.get_context("spawn"))
        monitor.start()

    try:
        while remaining is None or remaining > 0:
            record = runtime.step()
            telemetry.append(record)

            if slm is not None and record.tick % 64 == 0:
                slm.maybe_schedule(runtime.organism, current_tick=record.tick)

            if monitor is not None and record.tick % max(1, hz // 5) == 0:
                monitor.publish(
                    MonitorSnapshot(
                        tick=record.tick,
                        symbiont_id=runtime.organism_id,
                        embodiment_mode=embodiment_mode,
                        schema_confidence=record.schema_confidence,
                        schema_parts=record.schema_parts,
                        schema_dependencies=record.schema_dependencies,
                        prediction_error=record.prediction_error,
                        active_effectors=record.active_effectors,
                        joint_motion=record.joint_motion,
                        contact_count=record.contact_count,
                        height=record.base_position[2],
                        checkpoint_age=max(0, record.tick - last_checkpoint_tick),
                        symbiont_file=str(symbiont_file),
                        strongest_outputs=strongest_outputs(runtime.motor_activity()),
                        slm_records=record.slm_records,
                        slm_models=record.slm_models,
                        slm_active=record.slm_active,
                        slm_training=bool(slm.training) if slm is not None else False,
                        slm_error=slm.last_error if slm is not None else None,
                    )
                )

            if remaining is not None:
                remaining -= 1

            if runtime.tick_count % checkpoint_interval == 0:
                _save_checkpoint(
                    runtime,
                    symbiont_file=symbiont_file,
                    body_file=body_file,
                )
                last_checkpoint_tick = runtime.tick_count

            if not headless:
                time.sleep(time_step)
            if not record.alive:
                break
    except KeyboardInterrupt:
        pass
    finally:
        _save_checkpoint(
            runtime,
            symbiont_file=symbiont_file,
            body_file=body_file,
        )
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
        print(f"Telemetry:      {telemetry_file}")
        if monitor is not None:
            monitor.close()
        if slm is not None:
            slm.close()
        runtime.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a canonical Symbiont runtime in a PyBullet body"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="run PyBullet DIRECT without a window",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=0,
        help="ticks to run; 0 means until interrupted",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hz", type=int, default=240)
    parser.add_argument(
        "--symbiont-file",
        type=Path,
        default=DEFAULT_SYMBIONT_FILE,
        help="body-independent canonical organism checkpoint",
    )
    parser.add_argument(
        "--body-state-file",
        type=Path,
        default=DEFAULT_BODY_FILE,
        help="optional PyBullet pose for resuming this embodiment",
    )
    parser.add_argument(
        "--telemetry-file",
        type=Path,
        default=DEFAULT_TELEMETRY_FILE,
        help="append-only passive 3D telemetry",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=1000,
        help="ticks between durable saves",
    )
    parser.add_argument(
        "--fresh-body",
        action="store_true",
        help="load the Symbiont runtime but ignore its previous PyBullet pose",
    )
    parser.add_argument(
        "--new-symbiont",
        action="store_true",
        help="ignore existing v2 organism/body files and create a new subject",
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="disable the separate passive monitor window",
    )
    parser.add_argument(
        "--no-slm",
        action="store_true",
        help="disable Private SLM capture/training integration",
    )
    parser.add_argument(
        "--slm-train-interval",
        type=int,
        default=4096,
        help="ticks between background Private SLM training requests",
    )
    parser.add_argument(
        "--slm-min-records",
        type=int,
        default=64,
        help="minimum private experience records before training",
    )
    parser.add_argument(
        "--slm-device",
        default="cpu",
        help="Private SLM training device (cpu or cuda)",
    )
    args = parser.parse_args(argv)
    return run(
        headless=args.headless,
        ticks=args.ticks,
        seed=args.seed,
        hz=args.hz,
        symbiont_file=args.symbiont_file.expanduser(),
        body_file=args.body_state_file.expanduser(),
        telemetry_file=args.telemetry_file.expanduser(),
        checkpoint_interval=args.checkpoint_interval,
        fresh_body=args.fresh_body,
        new_symbiont=args.new_symbiont,
        show_monitor=not args.no_monitor,
        enable_slm=not args.no_slm,
        slm_train_interval=args.slm_train_interval,
        slm_min_records=args.slm_min_records,
        slm_device=args.slm_device,
    )


if __name__ == "__main__":
    raise SystemExit(main())
