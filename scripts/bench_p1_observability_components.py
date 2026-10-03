#!/usr/bin/env python3
"""Exploratory component profile for the Physics3D observer pipeline.

Run under a display server (for example ``xvfb-run -a uv run python
scripts/bench_p1_observability_components.py``) to include the real passive
viewer process. Results are measurements, not thresholds or CI assertions.
"""

from __future__ import annotations

import copy
import json
import multiprocessing as mp
import os
import platform
import queue
import statistics
import tempfile
import time
from pathlib import Path

import pybullet

from lab.app.physics3d.monitor.viewer import UnifiedViewerProcess
from lab.physics3d.runtime import PyBulletEmbodimentRuntime
from lab.physics3d.telemetry.v41 import (
    AsyncTelemetryV41Writer,
    TelemetryV41Writer,
)


def _median_ms(samples: list[float]) -> float:
    return statistics.median(samples) * 1000.0


def _ipc_worker(incoming, outgoing, count: int) -> None:
    for _ in range(count):
        outgoing.put(incoming.get())


def _telemetry_writer(
    root: Path, asynchronous: bool, payload: dict, count: int
) -> tuple[float, float]:
    if asynchronous:
        writer = AsyncTelemetryV41Writer(
            root,
            organism_id="p1-profile",
            start_tick=0,
            seed=127,
            physics_hz=240,
            cognition_hz=24,
            observation_hz=24,
            render_hz=24,
            embodiment_mode="profile",
            snapshot_interval=count + 1,
            flush_every=count + 1,
        )
    else:
        writer = TelemetryV41Writer(
            root,
            organism_id="p1-profile",
            start_tick=0,
            seed=127,
            physics_hz=240,
            cognition_hz=24,
            observation_hz=24,
            render_hz=24,
            embodiment_mode="profile",
            snapshot_interval=count + 1,
            flush_every=count + 1,
        )
    samples: list[float] = []
    started = time.perf_counter()
    for tick in range(1, count + 1):
        state = {"tick": tick, "post": {"physical": payload}}
        summary = {"tick": tick, "contact_count": 0}
        before = time.perf_counter()
        writer.append(summary, rich_state=state)
        samples.append(time.perf_counter() - before)
    writer.close()
    elapsed = time.perf_counter() - started
    return _median_ms(samples), elapsed


def _viewer_wall_seconds(root: Path, *, with_viewer: bool, ticks: int) -> float:
    from lab.physics3d.engine import run

    viewer = UnifiedViewerProcess(mp.get_context("spawn")) if with_viewer else None
    if viewer is not None:
        viewer.start()
    try:
        started = time.perf_counter()
        run(
            headless=True,
            ticks=ticks,
            seed=127,
            symbiont_file=root / "organism.symbiont",
            body_file=root / "body.json",
            telemetry_file=root / "telemetry",
            show_monitor=False,
            viewer_bridge=viewer,
            enable_slm=False,
            new_symbiont=True,
            fresh_body=True,
        )
        return time.perf_counter() - started
    finally:
        if viewer is not None:
            viewer.close()


def main() -> None:
    parser_repeats = 3
    sample_count = 100
    with PyBulletEmbodimentRuntime(
        gui=False,
        seed=127,
        organism_id="p1-component-profile",
        physics_substeps_per_tick=1,
    ) as runtime:
        runtime.step(include_observability=True)
        checkpoint = runtime.checkpoint(advance_lineage=False)
        physical, _ = runtime.physical_checkpoint()
    payload = {"organism": checkpoint, "physical": physical}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    copy_samples: list[float] = []
    serialization_samples: list[float] = []
    queue_samples: list[float] = []
    local_queue: queue.Queue[object] = queue.Queue(maxsize=1)
    for _ in range(sample_count):
        started = time.perf_counter()
        copy.deepcopy(payload)
        copy_samples.append(time.perf_counter() - started)
        started = time.perf_counter()
        json.dumps(payload, sort_keys=True, separators=(",", ":"))
        serialization_samples.append(time.perf_counter() - started)
        started = time.perf_counter()
        local_queue.put(payload)
        local_queue.get()
        queue_samples.append(time.perf_counter() - started)

    ipc_in = mp.get_context("spawn").Queue(maxsize=2)
    ipc_out = mp.get_context("spawn").Queue(maxsize=2)
    ipc_count = 30
    process = mp.get_context("spawn").Process(target=_ipc_worker, args=(ipc_in, ipc_out, ipc_count))
    process.start()
    ipc_samples: list[float] = []
    for _ in range(ipc_count):
        started = time.perf_counter()
        ipc_in.put(payload)
        ipc_out.get()
        ipc_samples.append(time.perf_counter() - started)
    process.join(timeout=30)
    if process.exitcode != 0:
        raise RuntimeError(f"IPC profile child exit code: {process.exitcode}")

    physical_payload = {"post": {"physical": physical}}
    with tempfile.TemporaryDirectory(prefix="p1-observability-profile-") as temp:
        root = Path(temp)
        disk_samples: list[float] = []
        disk_path = root / "fsync.bin"
        fd = os.open(disk_path, os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            for _ in range(20):
                started = time.perf_counter()
                os.write(fd, encoded.encode())
                os.fsync(fd)
                disk_samples.append(time.perf_counter() - started)
        finally:
            os.close(fd)
        sync_ms, sync_total = _telemetry_writer(
            root / "sync", False, physical_payload, sample_count
        )
        async_ms, async_total = _telemetry_writer(
            root / "async", True, physical_payload, sample_count
        )
        ui_off = [
            _viewer_wall_seconds(root / f"ui-off-{n}", with_viewer=False, ticks=30)
            for n in range(parser_repeats)
        ]
        ui_on = [
            _viewer_wall_seconds(root / f"ui-on-{n}", with_viewer=True, ticks=30)
            for n in range(parser_repeats)
        ]

    report = {
        "classification": "exploratory-component-profile",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pybullet_module_build": pybullet.getAPIVersion(),
        "seed": 127,
        "payload_bytes_json": len(encoded.encode()),
        "sample_count": sample_count,
        "component_median_ms": {
            "deepcopy_checkpoint_and_physics": _median_ms(copy_samples),
            "json_serialize_checkpoint_and_physics": _median_ms(serialization_samples),
            "in_process_queue_put_get": _median_ms(queue_samples),
            "multiprocessing_queue_put_get": _median_ms(ipc_samples),
            "local_file_write_and_fsync": _median_ms(disk_samples),
            "sync_v41_append_producer": sync_ms,
            "async_v41_append_producer_queue": async_ms,
        },
        "writer_elapsed_s": {
            "sync_including_close": sync_total,
            "async_including_close": async_total,
        },
        "viewer_pipeline_30_ticks_total_s": {
            "off_samples": ui_off,
            "on_samples": ui_on,
            "off_median": statistics.median(ui_off),
            "on_median": statistics.median(ui_on),
            "difference_median": statistics.median(ui_on) - statistics.median(ui_off),
        },
        "limitations": [
            "The viewer comparison is an end-to-end delta, not a pure render-time attribution.",
            "Async append timing includes bounded-queue backpressure; close time includes writer drain and I/O.",
            "Only one seed, one body, one state payload, and 30-tick viewer runs are sampled.",
            "Timing is host-load-sensitive and is not a deterministic test or performance threshold.",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
