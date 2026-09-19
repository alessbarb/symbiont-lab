"""Launch a persistent Symbiont World server: the world ticks continuously
in a background thread from the moment this starts, independent of
whether anyone is viewing it. Connect with a browser (or `curl
http://127.0.0.1:8766/api/state`) to watch it live.
"""
from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer

from .dashboard_api import make_handler
from .dashboard_state import WorldDashboardState


class WorldDashboardHTTPServer(ThreadingHTTPServer):
    world_state: WorldDashboardState


def make_server(
    host: str = "127.0.0.1",
    port: int = 8766,
    state: WorldDashboardState | None = None,
) -> WorldDashboardHTTPServer:
    world_state = state or WorldDashboardState()
    server = WorldDashboardHTTPServer((host, port), make_handler(world_state))
    server.world_state = world_state  # for tests / programmatic shutdown
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Launch a persistent Symbiont World and watch it live")
    parser.add_argument("world", nargs="?", default="Genesis", help="World name (default: Genesis)")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--founders", type=int, default=8)
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--tick-delay", type=float, default=0.5, help="seconds between ticks")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--storage-dir", type=str, default=None, help="Directory for checkpoint storage")
    parser.add_argument("--checkpoint-interval", type=int, default=50, help="Ticks between automatic checkpoints")
    args = parser.parse_args(argv)

    storage = None
    population = None
    if args.storage_dir:
        from .genesis_v1 import build_constitution, build_ground_truth
        from .persistence import WorldStorage

        storage = WorldStorage(args.storage_dir)
        storage.ensure_dirs()
        if storage.head_file.exists():
            print(f"Loading {args.world}...")
            gt = build_ground_truth()
            # The durable checkpoint is authoritative for topology. CLI
            # defaults must never change the identity of an existing world.
            chk = storage.load_latest_checkpoint()
            const = build_constitution(
                gt,
                dimensions=(chk.topology["width"], chk.topology["height"]),
            )
            population = storage.restore(gt, expected_constitution=const)
            print(f"\nworld_id        {chk.world_id}")
            print(f"fingerprint     {chk.world_fingerprint[:16]}...")
            print(f"epoch           {chk.epoch}")
            print(f"tick            {chk.tick}")
            print(f"population      {len(chk.organisms)}")
            print(f"last checkpoint {chk.tick:012d}.chk")
            print(f"journal         valid\n")
            print("Resuming world.")
        else:
            print(f"Starting fresh world '{args.world}' with persistence at {args.storage_dir}...")
    else:
        print(f"Starting in-memory world '{args.world}'...")

    state = WorldDashboardState(
        world_seed=args.seed,
        founders=args.founders,
        width=args.width,
        height=args.height,
        tick_delay_s=args.tick_delay,
        storage=storage,
        checkpoint_interval=args.checkpoint_interval,
        population=population,
    )
    state.start()

    server = make_server(port=args.port, state=state)
    print(f"Observatory:\nhttp://127.0.0.1:{args.port}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        state.stop()
        server.server_close()


if __name__ == "__main__":
    main()
