"""CLI for the lightweight 3D embodiment experiment."""
from __future__ import annotations

import argparse
import time

from .runtime import PyBulletEmbodimentRuntime


def run(
    *,
    headless: bool = False,
    ticks: int = 0,
    seed: int = 42,
    hz: int = 240,
) -> int:
    if hz < 30:
        raise ValueError("hz must be >= 30")
    time_step = 1.0 / float(hz)

    with PyBulletEmbodimentRuntime(
        gui=not headless,
        seed=seed,
        time_step=time_step,
    ) as runtime:
        remaining = None if ticks <= 0 else ticks
        try:
            while remaining is None or remaining > 0:
                record = runtime.step()
                if remaining is not None:
                    remaining -= 1
                if not headless:
                    time.sleep(time_step)
                if not record.alive:
                    break
        except KeyboardInterrupt:
            pass

        if headless:
            pos = record.base_position if runtime.tick_count else (0.0, 0.0, 0.0)
            print(
                f"ticks={runtime.tick_count} "
                f"base=({pos[0]:+.3f},{pos[1]:+.3f},{pos[2]:+.3f})"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a Symbiont in a lightweight PyBullet anthropomorphic body"
    )
    parser.add_argument("--headless", action="store_true", help="run PyBullet DIRECT without a window")
    parser.add_argument("--ticks", type=int, default=0, help="ticks to run; 0 means until interrupted")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hz", type=int, default=240)
    args = parser.parse_args(argv)
    return run(
        headless=args.headless,
        ticks=args.ticks,
        seed=args.seed,
        hz=args.hz,
    )


if __name__ == "__main__":
    raise SystemExit(main())
