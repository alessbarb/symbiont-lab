"""Operational conversion and benchmarking for Physics3D telemetry."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any

from .telemetry_compaction import canonical_json_bytes
from .telemetry_reader import detect_telemetry_run, open_telemetry
from .telemetry_v41 import TelemetryV41Writer, verify_v41_run


@dataclass(frozen=True, slots=True)
class ConversionReport:
    source_version: str
    source_run: str
    destination_run: str
    ticks: int
    verified: bool


def _read_manifest(root: Path) -> dict[str, Any]:
    path = root / "manifest.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def convert_run(
    source: str | Path,
    destination_root: str | Path,
    *,
    run_id: str | None = None,
) -> ConversionReport:
    version, source_root = detect_telemetry_run(source)
    if version == "legacy":
        raise ValueError("legacy summary-only telemetry cannot be converted losslessly")
    reader = open_telemetry(source_root)
    manifest = _read_manifest(source_root)
    target_run_id = run_id or f"{source_root.name}-v41"
    writer = TelemetryV41Writer(
        destination_root,
        organism_id=str(manifest.get("organism_id", "unknown")),
        start_tick=int(manifest.get("start_tick", 0) or 0),
        seed=int(manifest.get("seed", 0) or 0),
        physics_hz=int(manifest.get("physics_hz", 240) or 240),
        cognition_hz=int(manifest.get("cognition_hz", 24) or 24),
        embodiment_mode=str(manifest.get("embodiment_mode", "converted")),
        effective_configuration=manifest.get("effective_configuration", {}),
        software_identity={
            **(
                manifest.get("software_identity", {})
                if isinstance(manifest.get("software_identity"), dict)
                else {}
            ),
            "telemetry_conversion_source": version,
        },
        snapshot_interval=int(
            manifest.get(
                "anchor_interval",
                manifest.get("snapshot_interval", 1024),
            )
            or 1024
        ),
        run_id=target_run_id,
    )
    ticks = 0
    try:
        state_iter = reader.iter_states()
        summary_iter = reader.iter_summaries()
        while True:
            try:
                state = next(state_iter)
            except StopIteration:
                try:
                    next(summary_iter)
                except StopIteration:
                    break
                raise ValueError("source telemetry has more summaries than states")
            try:
                summary = next(summary_iter)
            except StopIteration as exc:
                raise ValueError(
                    "source telemetry has more states than summaries"
                ) from exc
            if int(state.get("tick", -1)) != int(summary.get("tick", -2)):
                raise ValueError("source telemetry state/summary tick mismatch")
            writer.append(summary, rich_state=state)
            ticks += 1
    finally:
        writer.close()

    destination = writer.root
    verification = verify_v41_run(destination)
    if not verification["complete"]:
        raise ValueError("converted v4.1 run failed integrity verification")

    # Prove exact logical equivalence against the immutable source.
    source_reader = open_telemetry(source_root)
    target_reader = open_telemetry(destination)
    source_states = source_reader.iter_states()
    target_states = target_reader.iter_states()
    source_summaries = source_reader.iter_summaries()
    target_summaries = target_reader.iter_summaries()
    checked = 0
    while True:
        try:
            left_state = next(source_states)
        except StopIteration:
            try:
                next(target_states)
            except StopIteration:
                break
            raise ValueError("converted telemetry contains extra states")
        try:
            right_state = next(target_states)
            left_summary = next(source_summaries)
            right_summary = next(target_summaries)
        except StopIteration as exc:
            raise ValueError("converted telemetry ended before source") from exc
        if canonical_json_bytes(left_state) != canonical_json_bytes(right_state):
            raise ValueError(
                f"converted state differs at tick {left_state.get('tick')}"
            )
        if canonical_json_bytes(left_summary) != canonical_json_bytes(right_summary):
            raise ValueError(
                f"converted summary differs at tick {left_summary.get('tick')}"
            )
        checked += 1

    if checked != ticks:
        raise ValueError("conversion verification count mismatch")
    return ConversionReport(
        source_version=version,
        source_run=str(source_root),
        destination_run=str(destination),
        ticks=ticks,
        verified=True,
    )


def _tree_bytes(root: Path) -> int:
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file()
    )


def _v41_breakdown(root: Path) -> dict[str, int]:
    groups = {
        "ticks": root / "ticks.ndjson",
        "schemas": root / "schemas",
        "dense": root / "frames" / "dense.ndjson",
        "summary": root / "frames" / "summary.ndjson",
        "fallback": root / "frames" / "fallback.ndjson",
        "structural": root / "structures" / "state.ndjson",
        "static": root / "structures" / "static.ndjson",
        "events": root / "events",
        "objects": root / "objects",
        "anchors": root / "anchors",
        "checkpoints": root / "checkpoints",
        "indexes": root / "indexes",
        "manifest": root / "manifest.json",
    }
    result: dict[str, int] = {}
    for name, path in groups.items():
        if path.is_file():
            result[name] = path.stat().st_size
        elif path.is_dir():
            result[name] = _tree_bytes(path)
        else:
            result[name] = 0
    return result


def benchmark_run(path: str | Path) -> dict[str, Any]:
    version, root = detect_telemetry_run(path)
    reader = open_telemetry(root)
    ticks: list[int] = []
    raw_bytes = 0
    for state, summary in zip(
        reader.iter_states(),
        reader.iter_summaries(),
        strict=True,
    ):
        tick = int(summary.get("tick", state.get("tick", -1)))
        ticks.append(tick)
        raw_bytes += len(canonical_json_bytes(state))
        raw_bytes += len(canonical_json_bytes(summary))

    total_bytes = _tree_bytes(root)
    breakdown = (
        _v41_breakdown(root)
        if version == "v4.1"
        else {"total": total_bytes}
    )
    if version == "v4.1":
        evidence_bytes = total_bytes - breakdown.get("checkpoints", 0)
    else:
        evidence_bytes = total_bytes

    samples: list[int] = []
    if ticks:
        indexes = sorted(
            {
                0,
                len(ticks) // 4,
                len(ticks) // 2,
                (3 * len(ticks)) // 4,
                len(ticks) - 1,
            }
        )
        samples = [ticks[index] for index in indexes]

    latencies_ms: list[float] = []
    for tick in samples:
        started = time.perf_counter()
        reader.state_at(tick)
        latencies_ms.append((time.perf_counter() - started) * 1000.0)

    sorted_latency = sorted(latencies_ms)
    p95 = (
        sorted_latency[min(len(sorted_latency) - 1, int(len(sorted_latency) * 0.95))]
        if sorted_latency
        else None
    )
    manifest = _read_manifest(root)
    fallback_bytes = int(
        (
            manifest.get("compaction", {})
            if isinstance(manifest.get("compaction"), dict)
            else {}
        ).get("fallback_bytes", 0)
        or 0
    )
    return {
        "version": version,
        "run": str(root),
        "ticks": len(ticks),
        "first_tick": ticks[0] if ticks else None,
        "last_tick": ticks[-1] if ticks else None,
        "total_bytes": total_bytes,
        "evidence_bytes_excluding_checkpoints": evidence_bytes,
        "bytes_per_tick": (
            evidence_bytes / len(ticks) if ticks else None
        ),
        "raw_canonical_bytes": raw_bytes,
        "storage_ratio_vs_raw": (
            evidence_bytes / raw_bytes if raw_bytes else None
        ),
        "fallback_bytes": fallback_bytes,
        "fallback_fraction": (
            fallback_bytes / evidence_bytes if evidence_bytes else 0.0
        ),
        "breakdown": breakdown,
        "state_at_ms": {
            "samples": latencies_ms,
            "p50": (
                sorted_latency[len(sorted_latency) // 2]
                if sorted_latency
                else None
            ),
            "p95": p95,
            "max": max(sorted_latency) if sorted_latency else None,
        },
    }


def compare_runs(left: str | Path, right: str | Path) -> dict[str, Any]:
    a = benchmark_run(left)
    b = benchmark_run(right)
    a_bytes = int(a["evidence_bytes_excluding_checkpoints"])
    b_bytes = int(b["evidence_bytes_excluding_checkpoints"])
    return {
        "left": a,
        "right": b,
        "saved_bytes": a_bytes - b_bytes,
        "saved_fraction": (
            (a_bytes - b_bytes) / a_bytes if a_bytes else None
        ),
    }


__all__ = [
    "ConversionReport",
    "benchmark_run",
    "compare_runs",
    "convert_run",
]
