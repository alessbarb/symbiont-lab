"""Launch a persistent Symbiont World with Observatory as its only web UI."""

from __future__ import annotations

import argparse
from pathlib import Path

from observatory.config import DEFAULT_OBSERVATORY_DIR
from observatory.server import ObservatoryServer
from symbiont_lab.world.genesis_v1 import build_constitution, build_ground_truth
from symbiont_lab.world.persistence import WorldStorage
from symbiont_lab.world.runtime import WorldRuntimeState


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Launch or resume a persistent Symbiont World observed through Observatory"
    )
    parser.add_argument("world", nargs="?", default="Genesis", help="World name (default: Genesis)")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--founders", type=int, default=8)
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--tick-delay", type=float, default=0.5, help="seconds between ticks")
    parser.add_argument("--port", type=int, default=8766, help="Observatory port")
    parser.add_argument(
        "--storage-dir", type=str, default=None, help="Directory for checkpoint storage"
    )
    parser.add_argument(
        "--observatory-dir",
        type=Path,
        default=Path(DEFAULT_OBSERVATORY_DIR).expanduser(),
        help="Observatory state directory",
    )
    parser.add_argument("--checkpoint-interval", type=int, default=50)
    args = parser.parse_args(argv)

    storage = None
    population = None
    if args.storage_dir:
        storage = WorldStorage(args.storage_dir)
        storage.ensure_dirs()
        if storage.head_file.exists():
            print(f"Loading {args.world}...")
            ground_truth = build_ground_truth()
            checkpoint = storage.load_latest_checkpoint()
            constitution = build_constitution(
                ground_truth,
                dimensions=(checkpoint.topology["width"], checkpoint.topology["height"]),
            )
            population = storage.restore(ground_truth, expected_constitution=constitution)
            print(f"world_id        {checkpoint.world_id}")
            print(f"fingerprint     {checkpoint.world_fingerprint[:16]}...")
            print(f"epoch           {checkpoint.epoch}")
            print(f"tick            {checkpoint.tick}")
            print(f"population      {len(checkpoint.organisms)}")
            print("Resuming world.")
        else:
            print(f"Starting fresh world '{args.world}' with persistence at {args.storage_dir}...")
    else:
        print(f"Starting in-memory world '{args.world}'...")

    world = WorldRuntimeState(
        world_seed=args.seed,
        founders=args.founders,
        width=args.width,
        height=args.height,
        tick_delay_s=args.tick_delay,
        storage=storage,
        checkpoint_interval=args.checkpoint_interval,
        population=population,
    )
    world.start()

    server = ObservatoryServer(
        args.observatory_dir,
        port=args.port,
        world_state=world,
    )
    print(f"Observatory: http://127.0.0.1:{server.server_address[1]}/")
    print(f"World view:  http://127.0.0.1:{server.server_address[1]}/world.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        world.stop()
        server.server_close()


if __name__ == "__main__":
    main()
