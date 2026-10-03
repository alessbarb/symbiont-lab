"""Operational conversion and benchmarking for Physics3D telemetry."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

from lab.physics3d.telemetry.compaction import canonical_json_bytes
from lab.physics3d.telemetry.reader import detect_telemetry_run, open_telemetry
from lab.physics3d.telemetry.v41 import verify_v41_run


def _read_manifest(root: Path) -> dict[str, Any]:
    path = root / "manifest.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _tree_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


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
    breakdown = _v41_breakdown(root) if version == "v4.1" else {"total": total_bytes}
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
    integrity = verify_v41_run(root) if version == "v4.1" else None
    fallback_bytes = int(
        (
            manifest.get("compaction", {}) if isinstance(manifest.get("compaction"), dict) else {}
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
        "bytes_per_tick": (evidence_bytes / len(ticks) if ticks else None),
        "raw_canonical_bytes": raw_bytes,
        "storage_ratio_vs_raw": (evidence_bytes / raw_bytes if raw_bytes else None),
        "fallback_bytes": fallback_bytes,
        "fallback_fraction": (fallback_bytes / evidence_bytes if evidence_bytes else 0.0),
        "integrity": integrity,
        "breakdown": breakdown,
        "state_at_ms": {
            "samples": latencies_ms,
            "p50": (sorted_latency[len(sorted_latency) // 2] if sorted_latency else None),
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
    integrity_complete = isinstance(integrity, Mapping) and bool(integrity.get("complete"))
    evidence_bytes = int(report.get("evidence_bytes_excluding_checkpoints", 0) or 0)
    fallback_fraction = float(report.get("fallback_fraction", 0.0) or 0.0)
    state_at = report.get("state_at_ms", {})
    p95_raw = state_at.get("p95") if isinstance(state_at, Mapping) else None
    p95_ms = float(p95_raw) if p95_raw is not None else float("inf")
    ticks = int(report.get("ticks", 0) or 0)

    checks = {
        "version_is_v41": version == "v4.1",
        "integrity_complete": integrity_complete,
        "evidence_bytes": evidence_bytes <= int(max_evidence_bytes),
        "fallback_fraction": fallback_fraction <= float(max_fallback_fraction),
        "state_at_p95_ms": p95_ms <= float(max_state_at_p95_ms),
        "expected_ticks": (True if expected_ticks is None else ticks == int(expected_ticks)),
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
        "saved_fraction": ((a_bytes - b_bytes) / a_bytes if a_bytes else None),
    }


__all__ = [
    "benchmark_run",
    "compare_runs",
    "evaluate_acceptance_gates",
]
