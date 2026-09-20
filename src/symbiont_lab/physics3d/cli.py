"""CLI for the lightweight 3D embodiment experiment."""
from __future__ import annotations

import argparse
from pathlib import Path
import time
import multiprocessing as mp

from symbiont.core.portable import load_symbiont_file, save_symbiont_file

from .persistence import (
    TelemetryWriter,
    load_body_state_file,
    save_body_state_file,
)
from .runtime import PyBulletEmbodimentRuntime
from .monitor import MonitorProcess, MonitorSnapshot, strongest_outputs


DEFAULT_STATE_DIR = Path("~/.local/state/symbiont/physics3d").expanduser()
DEFAULT_SYMBIONT_FILE = DEFAULT_STATE_DIR / "subject.symbiont.json"
DEFAULT_BODY_FILE = DEFAULT_STATE_DIR / "subject.body.json"
DEFAULT_TELEMETRY_FILE = DEFAULT_STATE_DIR / "subject.telemetry.ndjson"


def _save_checkpoint(
    runtime: PyBulletEmbodimentRuntime,
    *,
    symbiont_file: Path,
    body_file: Path,
) -> None:
    """Persist cognitive identity and current embodiment as separate artifacts."""
    body_payload = runtime.apparatus.export_physical_state()
    body_payload["symbiont_ticks"] = runtime.individual.symbiont.total_ticks
    # Save physical state first. If interrupted before the cognitive file lands,
    # the next load rejects mismatched ticks rather than mixing two moments.
    save_body_state_file(body_payload, body_file)
    save_symbiont_file(runtime.individual.symbiont, symbiont_file)


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
) -> int:
    if hz < 30:
        raise ValueError("hz must be >= 30")
    if checkpoint_interval < 1:
        raise ValueError("checkpoint_interval must be >= 1")

    symbiont = None
    if symbiont_file.exists() and not new_symbiont:
        symbiont = load_symbiont_file(symbiont_file)
        print(
            f"Loaded Symbiont {symbiont.symbiont_id} "
            f"at cognitive tick {symbiont.total_ticks} from {symbiont_file}"
        )

    physical_state = None
    if body_file.exists() and not fresh_body and not new_symbiont:
        candidate = load_body_state_file(body_file)
        expected_tick = symbiont.total_ticks if symbiont is not None else 0
        saved_tick = int(candidate.get("symbiont_ticks", -1))
        if symbiont is not None and saved_tick == expected_tick:
            physical_state = candidate
            print(f"Restoring physical embodiment from {body_file}")
        elif symbiont is not None:
            print(
                "Ignoring physical body checkpoint because it does not match "
                f"the Symbiont tick ({saved_tick} != {expected_tick})."
            )

    if fresh_body and symbiont is not None:
        print("Implanting persisted Symbiont into a fresh anthropomorphic body.")

    if new_symbiont or symbiont is None:
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
        symbiont=symbiont,
        physical_state=physical_state,
    )
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
            if monitor is not None and record.tick % max(1, hz // 5) == 0:
                monitor.publish(
                    MonitorSnapshot(
                        tick=record.tick,
                        symbiont_id=runtime.individual.symbiont.symbiont_id,
                        embodiment_mode=embodiment_mode,
                        schema_confidence=record.schema_confidence,
                        prediction_error=record.prediction_error,
                        active_effectors=record.active_effectors,
                        joint_motion=record.joint_motion,
                        contact_count=record.contact_count,
                        height=record.base_position[2],
                        checkpoint_age=max(0, record.tick - last_checkpoint_tick),
                        symbiont_file=str(symbiont_file),
                        strongest_outputs=strongest_outputs(
                            runtime.individual.symbiont.last_activations
                        ),
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
                f"prediction_error={record.prediction_error:.4f}"
            )
        print(f"Symbiont file: {symbiont_file}")
        print(f"Body state:    {body_file}")
        print(f"Telemetry:     {telemetry_file}")
        if monitor is not None:
            monitor.close()
        runtime.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run or transplant a persistent Symbiont in a PyBullet body"
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
        help="portable body-independent cognitive identity file",
    )
    parser.add_argument(
        "--body-state-file",
        type=Path,
        default=DEFAULT_BODY_FILE,
        help="optional physical pose for resuming the current embodiment",
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
        help="load the Symbiont but ignore its previous physical body state",
    )
    parser.add_argument(
        "--new-symbiont",
        action="store_true",
        help="ignore any existing Symbiont and body files and create a new subject",
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="disable the separate passive monitor window",
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
    )


if __name__ == "__main__":
    raise SystemExit(main())
