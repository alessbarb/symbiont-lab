#!/usr/bin/env python3
"""Measure P3 World journal access cost as accumulated history grows."""

from __future__ import annotations

import argparse
import time

from environment.events import EventJournal, WorldEvent


def _event(index: int, events_per_tick: int) -> WorldEvent:
    tick = index // events_per_tick
    return WorldEvent(
        event_id=f"evt-{index:09d}",
        world_id="bench",
        tick=tick,
        kind="WORLD_FIELD_CHANGED",
        actor=None,
        position=None,
        payload={"value": index % 17},
    )


def _measure(journal: EventJournal, events_per_tick: int, repeats: int) -> dict[str, float]:
    latest_tick = (len(journal) - 1) // events_per_tick
    cursor = journal.event_at(max(0, len(journal) - 129)).event_id

    started = time.perf_counter()
    for _ in range(repeats):
        journal.events_for_tick(latest_tick)
    tick_s = time.perf_counter() - started

    started = time.perf_counter()
    for _ in range(repeats):
        journal.tail(60)
    tail_s = time.perf_counter() - started

    started = time.perf_counter()
    for _ in range(repeats):
        journal.page_after(cursor, limit=128)
    page_s = time.perf_counter() - started

    started = time.perf_counter()
    for _ in range(repeats):
        tuple(event for event in journal.replay() if event.tick == latest_tick)
    replay_tick_s = time.perf_counter() - started

    return {
        "indexed_tick_us": tick_s * 1_000_000 / repeats,
        "tail_us": tail_s * 1_000_000 / repeats,
        "indexed_page_us": page_s * 1_000_000 / repeats,
        "reference_replay_tick_us": replay_tick_s * 1_000_000 / repeats,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ages", type=int, nargs="+", default=[1_000, 10_000, 100_000])
    parser.add_argument("--events-per-tick", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=200)
    args = parser.parse_args()

    journal = EventJournal()
    previous = 0
    for age in sorted(args.ages):
        for index in range(previous, age):
            journal.append(_event(index, args.events_per_tick))
        previous = age
        print({"events": age, **_measure(journal, args.events_per_tick, args.repeats)})


if __name__ == "__main__":
    main()
