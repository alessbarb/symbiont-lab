"""Command-line adapter for the canonical Physics3D execution engine."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from symbiont_lab.app.physics3d_monitor import _viewer_main
from .engine import (
    DEFAULT_BODY_FILE,
    DEFAULT_STATE_DIR,
    DEFAULT_SYMBIONT_FILE,
    DEFAULT_TELEMETRY_FILE,
    LEGACY_RUNTIME_FILE,
    LEGACY_SYMBIONT_FILE,
    MonitorSnapshot,
    UnifiedViewerProcess,
    _archive_existing_subject,
    _save_checkpoint,
    run,
)
from .persistence import load_telemetry_records

def run_replay(telemetry_file: Path) -> int:
    path = telemetry_file.expanduser()
    if not path.exists():
        print(f"Error: Telemetry file not found at {path}", file=sys.stderr)
        return 1
    print(f"Loading telemetry records from {path}...")
    records = load_telemetry_records(path, ignore_errors=True)
    if not records:
        print(f"Error: No valid telemetry records found in {path}", file=sys.stderr)
        return 1
    print(f"Loaded {len(records):,} records. Launching Mission Control Replay...")
    _viewer_main(
        frame_queue=None,
        command_queue=None,
        replay_records=records,
        replay_file=path,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a canonical Symbiont runtime in a PyBullet body or replay historical telemetry"
    )
    parser.add_argument(
        "--replay",
        nargs="?",
        const=str(DEFAULT_TELEMETRY_FILE),
        default=None,
        help="launch Mission Control replay from a telemetry run/root (v3, v4.0, v4.1 or archived NDJSON)",
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
    parser.add_argument("--hz", type=int, default=240, help="PyBullet physics frequency")
    parser.add_argument(
        "--cognition-hz",
        type=int,
        default=24,
        help="canonical Symbiont decision/perception frequency",
    )
    parser.add_argument(
        "--work-cost-per-joule",
        type=float,
        default=0.001,
        help="bounded metabolic maintenance units charged per measured joule",
    )
    parser.add_argument(
        "--symbiont-file",
        type=Path,
        default=DEFAULT_SYMBIONT_FILE,
        help="portable canonical Symbiont bundle (runtime + private SLM artifacts)",
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
        help="telemetry root directory; current canonical writer is v4.0; each execution creates an immutable run",
    )
    parser.add_argument(
        "--telemetry-physics-trace",
        action="store_true",
        help="persist every physics substep (high-volume 240 Hz diagnostic trace)",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=256,
        help="ticks between durable portable saves",
    )
    parser.add_argument(
        "--fresh-body",
        action="store_true",
        help="load the Symbiont runtime but ignore its previous PyBullet pose",
    )
    parser.add_argument(
        "--new-symbiont",
        action="store_true",
        help="ignore existing organism/body files and create a new subject",
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="disable the unified 3D evaluator window (uses native PyBullet GUI)",
    )
    parser.add_argument(
        "--no-slm",
        action="store_true",
        help="disable Private SLM capture/training integration",
    )
    parser.add_argument(
        "--slm-train-interval",
        type=int,
        default=1,
        help="minimum substrate service cooldown between organism-authored Private SLM requests",
    )
    parser.add_argument(
        "--slm-device",
        default="cpu",
        help="Private SLM training device (cpu or cuda)",
    )
    args = parser.parse_args(argv)
    if args.replay is not None:
        return run_replay(Path(args.replay))
    return run(
        headless=args.headless,
        ticks=args.ticks,
        seed=args.seed,
        hz=args.hz,
        cognition_hz=args.cognition_hz,
        mechanical_work_cost_per_joule=args.work_cost_per_joule,
        telemetry_physics_trace=args.telemetry_physics_trace,
        symbiont_file=args.symbiont_file.expanduser(),
        body_file=args.body_state_file.expanduser(),
        telemetry_file=args.telemetry_file.expanduser(),
        checkpoint_interval=args.checkpoint_interval,
        fresh_body=args.fresh_body,
        new_symbiont=args.new_symbiont,
        show_monitor=not args.no_monitor,
        enable_slm=not args.no_slm,
        slm_train_interval=args.slm_train_interval,
        slm_device=args.slm_device,
    )


if __name__ == "__main__":
    raise SystemExit(main())
