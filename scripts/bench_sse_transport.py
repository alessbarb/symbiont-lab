#!/usr/bin/env python3
"""Focused benchmark for P6 SSE framing overhead."""

from __future__ import annotations

import argparse
import json
import time

from lab.observation.bus import ObservationMessage
from lab.server.sse import _drain_observation_batch


class _Queue:
    def __init__(self, messages):
        self._messages = list(messages)

    def get_nowait(self):
        import queue

        if not self._messages:
            raise queue.Empty
        return self._messages.pop(0)


def _legacy_frame(data: bytes) -> bytes:
    payload = data.decode("utf-8")
    event_id = json.loads(payload).get("_stream_id")
    prefix = "" if event_id is None else f"id: {event_id}\n"
    return (prefix + "data: " + payload + "\n\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--messages", type=int, default=10_000)
    parser.add_argument("--payload-bytes", type=int, default=4096)
    args = parser.parse_args()

    padding = "x" * max(0, args.payload_bytes - 80)
    legacy_payloads = [
        json.dumps(
            {"type": "cognition", "tick": index, "_stream_id": index + 1, "blob": padding},
            separators=(",", ":"),
        ).encode("utf-8")
        for index in range(args.messages)
    ]
    optimized_messages = [
        ObservationMessage(
            index + 1,
            json.dumps(
                {"type": "cognition", "tick": index, "blob": padding},
                separators=(",", ":"),
            ).encode("utf-8"),
        )
        for index in range(args.messages)
    ]

    started = time.perf_counter()
    legacy_bytes = 0
    for payload in legacy_payloads:
        legacy_bytes += len(_legacy_frame(payload))
    legacy_s = time.perf_counter() - started

    started = time.perf_counter()
    optimized_bytes = 0
    batch_size = 64
    for offset in range(0, len(optimized_messages), batch_size):
        batch = optimized_messages[offset : offset + batch_size]
        optimized_bytes += len(_drain_observation_batch(_Queue(batch[1:]), batch[0]))
    optimized_s = time.perf_counter() - started

    print(
        {
            "messages": args.messages,
            "payload_bytes": args.payload_bytes,
            "legacy_seconds": round(legacy_s, 6),
            "optimized_seconds": round(optimized_s, 6),
            "speedup": round(legacy_s / optimized_s, 3) if optimized_s else None,
            "legacy_wire_bytes": legacy_bytes,
            "optimized_wire_bytes": optimized_bytes,
            "wire_reduction_percent": round(
                100.0 * (legacy_bytes - optimized_bytes) / legacy_bytes,
                3,
            )
            if legacy_bytes
            else 0.0,
        }
    )


if __name__ == "__main__":
    main()
