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


def make_server(
    host: str = "127.0.0.1",
    port: int = 8766,
    state: WorldDashboardState | None = None,
) -> ThreadingHTTPServer:
    world_state = state or WorldDashboardState()
    server = ThreadingHTTPServer((host, port), make_handler(world_state))
    server.world_state = world_state  # for tests / programmatic shutdown
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch a persistent Symbiont World and watch it live")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--founders", type=int, default=8)
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--tick-delay", type=float, default=0.5, help="seconds between ticks")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()

    state = WorldDashboardState(
        world_seed=args.seed,
        founders=args.founders,
        width=args.width,
        height=args.height,
        tick_delay_s=args.tick_delay,
    )
    state.start()

    server = make_server(port=args.port, state=state)
    print(f"Symbiont World: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        state.stop()
        server.server_close()


if __name__ == "__main__":
    main()
