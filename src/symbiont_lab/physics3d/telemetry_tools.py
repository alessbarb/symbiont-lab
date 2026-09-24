"""Operational conversion and benchmarking for Physics3D telemetry."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any, Mapping

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
                "checkpoint_interval",
                manifest.get(
                    "snapshot_interval",
                    manifest.get("anchor_interval", 1024),
                ),
            )
            or 1024
        ),
        anchor_interval=256,
        run_id=target_run_id,
    )
    ticks = 0
    try:
        for state, summary in reader.iter_records():
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
    checked = 0
    for (
        left_state,
        left_summary,
    ), (
        right_state,
        right_summary,
    ) in zip(
        source_reader.iter_records(),
        target_reader.iter_records(),
        strict=True,
    ):
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


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _v41_breakdown(root: Path) -> dict[str, int]:
    groups = {
        "ticks": root / "ticks.ndjson",
        "schemas": root / "schemas",
        "dense": _first_existing(
            root / "frames" / "dense.bin",
            root / "frames" / "dense.ndjson",
        ),
        "summary": _first_existing(
            root / "frames" / "summary.bin",
            root / "frames" / "summary.ndjson",
        ),
        "fallback": _first_existing(
            root / "frames" / "fallback.bin",
            root / "frames" / "fallback.ndjson",
        ),
        "structural": _first_existing(
            root / "structures" / "state.bin",
            root / "structures" / "state.ndjson",
        ),
        "static": _first_existing(
            root / "structures" / "static.bin",
            root / "structures" / "static.ndjson",
        ),
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
    for state, summary in reader.iter_records():
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
    integrity = (
        verify_v41_run(root)
        if version == "v4.1"
        else None
    )
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
        "integrity": integrity,
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


def evaluate_acceptance_gates(
    report: Mapping[str, Any],
    *,
    max_evidence_bytes: int = 200 * 1024 * 1024,
    max_fallback_fraction: float = 0.05,
    max_state_at_p95_ms: float = 100.0,
    expected_ticks: int | None = None,
) -> dict[str, Any]:
    version = str(report.get("version", ""))
    integrity = report.get("integrity")
    integrity_complete = (
        isinstance(integrity, Mapping)
        and bool(integrity.get("complete"))
    )
    evidence_bytes = int(
        report.get("evidence_bytes_excluding_checkpoints", 0) or 0
    )
    fallback_fraction = float(report.get("fallback_fraction", 0.0) or 0.0)
    state_at = report.get("state_at_ms", {})
    p95_raw = (
        state_at.get("p95")
        if isinstance(state_at, Mapping)
        else None
    )
    p95_ms = float(p95_raw) if p95_raw is not None else float("inf")
    ticks = int(report.get("ticks", 0) or 0)

    checks = {
        "version_is_v41": version == "v4.1",
        "integrity_complete": integrity_complete,
        "evidence_bytes": evidence_bytes <= int(max_evidence_bytes),
        "fallback_fraction": fallback_fraction <= float(max_fallback_fraction),
        "state_at_p95_ms": p95_ms <= float(max_state_at_p95_ms),
        "expected_ticks": (
            True if expected_ticks is None else ticks == int(expected_ticks)
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "observed": {
            "ticks": ticks,
            "evidence_bytes_excluding_checkpoints": evidence_bytes,
            "fallback_fraction": fallback_fraction,
            "state_at_p95_ms": p95_raw,
        },
        "limits": {
            "expected_ticks": expected_ticks,
            "max_evidence_bytes": int(max_evidence_bytes),
            "max_fallback_fraction": float(max_fallback_fraction),
            "max_state_at_p95_ms": float(max_state_at_p95_ms),
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
    "evaluate_acceptance_gates",
    "convert_run",
]
