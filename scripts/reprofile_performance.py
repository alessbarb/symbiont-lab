#!/usr/bin/env python3
"""P8 full-system performance reprofile after P0-P7.

Canonical local usage:
    python scripts/reprofile_performance.py
    python scripts/reprofile_performance.py --quick
    python scripts/reprofile_performance.py --output-dir .artifacts/p8

The runner deliberately separates deterministic correctness gates from timing.
It writes machine-readable JSON and a human-readable Markdown report. Timings
are evidence and are never interpreted as CI pass/fail thresholds.
"""

from __future__ import annotations

import argparse
import ast
import cProfile
import json
import platform
import pstats
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from lab.studies.learning.agency_acquisition_body import CausalBody, build_subject
from symbiont.core.orchestration.runtime import OrganismRuntime

ROOT = Path(__file__).resolve().parents[1]


def _subject(seed: int, *, observed: bool) -> tuple[OrganismRuntime, CausalBody]:
    body = CausalBody(actuator_count=4, seed=seed)
    runtime = build_subject(
        body,
        organism_id=f"p8-{seed}",
        factorized_effects=True,
    )
    for _ in range(50):
        runtime.tick(include_observability=observed)
        body.advance(runtime.last_actuations)
    return runtime, body


def _run_ticks(*, ticks: int, seed: int, observed: bool) -> dict[str, Any]:
    runtime, body = _subject(seed, observed=observed)
    started = time.perf_counter()
    for _ in range(ticks):
        runtime.tick(include_observability=observed)
        body.advance(runtime.last_actuations)
    elapsed = time.perf_counter() - started
    return {
        "observed": observed,
        "ticks": ticks,
        "elapsed_s": elapsed,
        "ms_per_tick": elapsed * 1000.0 / ticks,
        "ticks_per_s": ticks / elapsed if elapsed else None,
        "end_hash": runtime.state_hash(),
    }


def _category(filename: str, function: str) -> str:
    path = filename.replace("\\", "/").lower()
    name = function.lower()
    if "/actuation/" in path or "sensorimotor" in path or "competence" in name:
        return "sensorimotor_action"
    if "/cognition/" in path or "cognitive" in name:
        return "cognition"
    if "/sensory/" in path or "/perception/" in path or "percept" in path:
        return "perception"
    if "/physiology" in path or "living_body" in path:
        return "physiology"
    if "narrative" in path or "phenotype" in name or "/observation/" in path:
        return "observability"
    if "json" in path or "serialize" in name or "snapshot" in name:
        return "serialization"
    if "/genetics/" in path or "genome" in name:
        return "genetics"
    if "/lib/python" in path or path.startswith("~"):
        return "python_stdlib"
    return "other_runtime"


def _profile(*, ticks: int, seed: int, observed: bool, profile_path: Path) -> dict[str, Any]:
    runtime, body = _subject(seed, observed=observed)
    profiler = cProfile.Profile()
    profiler.enable()
    started = time.perf_counter()
    for _ in range(ticks):
        runtime.tick(include_observability=observed)
        body.advance(runtime.last_actuations)
    elapsed = time.perf_counter() - started
    profiler.disable()
    profiler.dump_stats(profile_path)

    stats = pstats.Stats(profiler)
    categories: dict[str, dict[str, float]] = {}
    functions: list[dict[str, Any]] = []
    total_self = 0.0

    for (filename, line, function), (_cc, nc, tt, ct, _callers) in stats.stats.items():
        total_self += float(tt)
        category = _category(filename, function)
        bucket = categories.setdefault(category, {"self_seconds": 0.0, "calls": 0.0})
        bucket["self_seconds"] += float(tt)
        bucket["calls"] += float(nc)
        functions.append(
            {
                "file": filename,
                "line": int(line),
                "function": function,
                "calls": int(nc),
                "self_seconds": float(tt),
                "cumulative_seconds": float(ct),
            }
        )

    category_rows = []
    for name, values in categories.items():
        self_seconds = values["self_seconds"]
        category_rows.append(
            {
                "category": name,
                "self_seconds": self_seconds,
                "self_percent": (self_seconds / total_self * 100.0) if total_self else 0.0,
                "calls": int(values["calls"]),
            }
        )
    category_rows.sort(key=lambda row: row["self_seconds"], reverse=True)

    top_self = sorted(functions, key=lambda row: row["self_seconds"], reverse=True)[:25]
    top_cumulative = sorted(
        functions,
        key=lambda row: row["cumulative_seconds"],
        reverse=True,
    )[:25]

    return {
        "mode": "observer_on" if observed else "observer_off",
        "ticks": ticks,
        "elapsed_s": elapsed,
        "ms_per_tick": elapsed * 1000.0 / ticks,
        "total_profile_self_seconds": total_self,
        "categories": category_rows,
        "top_self": top_self,
        "top_cumulative": top_cumulative,
        "profile_file": str(profile_path),
    }


def _command(name: str, command: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    return {
        "name": name,
        "command": command,
        "returncode": proc.returncode,
        "elapsed_s": elapsed,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _structured_command(name: str, command: list[str]) -> dict[str, Any]:
    result = _command(name, command)
    if result["returncode"] != 0:
        return result

    stdout = result["stdout"].strip()
    if not stdout:
        return result
    try:
        result["parsed"] = json.loads(stdout)
        return result
    except json.JSONDecodeError:
        pass

    parsed_lines = []
    try:
        for line in stdout.splitlines():
            if line.strip():
                parsed_lines.append(ast.literal_eval(line))
    except (SyntaxError, ValueError):
        result["parse_error"] = "stdout was neither JSON nor Python literals"
        return result
    result["parsed"] = parsed_lines[0] if len(parsed_lines) == 1 else parsed_lines
    return result


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P8 Performance Reprofile",
        "",
        f"- Python: `{report['environment']['python']}`",
        f"- Platform: `{report['environment']['platform']}`",
        f"- Mode: `{report['configuration']['mode']}`",
        f"- Seed: `{report['configuration']['seed']}`",
        "",
        "## Validity",
        "",
        f"- Overall: **{'VALID' if report['validity']['valid'] else 'INVALID'}**",
        f"- Observer ON/OFF end hash: `{report['validity']['matched_observer_end_hash']}`",
        f"- Causal equivalence gate: `{report['validity']['causal_equivalence_gate']}`",
        f"- Sensorimotor equivalence: `{report['validity']['sensorimotor_equivalence']}`",
        "",
        "## Organism throughput",
        "",
        "| mode | median ms/tick | ticks/s |",
        "|---|---:|---:|",
    ]
    for mode in ("observer_off", "observer_on"):
        row = report["organism"][mode]
        lines.append(
            f"| {mode} | {row['median_ms_per_tick']:.4f} | {row['median_ticks_per_s']:.1f} |"
        )

    tax = report["organism"]["observability_tax"]
    lines.extend(
        [
            "",
            f"Observed-minus-headless tax: **{tax['ms_per_tick']:.4f} ms/tick "
            f"({tax['percent']:.2f}%)**.",
            "",
            "## Headless self-time distribution",
            "",
            "| category | self seconds | self % |",
            "|---|---:|---:|",
        ]
    )
    for row in report["profile"]["observer_off"]["categories"]:
        lines.append(
            f"| {row['category']} | {row['self_seconds']:.4f} | {row['self_percent']:.2f}% |"
        )

    lines.extend(["", "## Top cumulative functions", ""])
    for row in report["profile"]["observer_off"]["top_cumulative"][:12]:
        lines.append(
            f"- `{Path(row['file']).name}:{row['line']}:{row['function']}` — "
            f"{row['cumulative_seconds']:.4f}s cumulative / {row['self_seconds']:.4f}s self"
        )

    lines.extend(["", "## Focused subsystem benchmarks", ""])
    for result in report["focused"]:
        state = "OK" if result["returncode"] == 0 else f"FAILED ({result['returncode']})"
        lines.append(f"- **{result['name']}**: {state} in {result['elapsed_s']:.3f}s")
        parsed = result.get("parsed")
        if parsed is not None:
            compact = json.dumps(parsed, sort_keys=True)
            if len(compact) > 600:
                compact = compact[:597] + "..."
            lines.append(f"  - `{compact}`")
        elif result["returncode"] != 0 and result.get("stderr"):
            detail = str(result["stderr"]).strip().replace("\n", " ")
            if len(detail) > 600:
                detail = detail[:597] + "..."
            lines.append(f"  - error: `{detail}`")

    lines.extend(
        [
            "",
            "## Interpretation rule",
            "",
            "P8 does not carry forward the old percentage breakdown. The next optimization "
            "target must be chosen from this report's current headless self-time and focused "
            "benchmarks. Cumulative profiler percentages must not be summed because nested "
            "calls double-count time.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="short smoke-sized local/CI run")
    parser.add_argument("--seed", type=int, default=127)
    parser.add_argument("--output-dir", type=Path, default=Path(".artifacts/p8"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    mode = "quick" if args.quick else "full"
    ticks = 180 if args.quick else 800
    profile_ticks = 140 if args.quick else 600
    repeats = 2 if args.quick else 5

    samples: dict[str, list[dict[str, Any]]] = {"observer_off": [], "observer_on": []}
    for observed, key in ((False, "observer_off"), (True, "observer_on")):
        for _ in range(repeats):
            samples[key].append(_run_ticks(ticks=ticks, seed=args.seed, observed=observed))

    organism: dict[str, Any] = {}
    for key, rows in samples.items():
        ms = [float(row["ms_per_tick"]) for row in rows]
        tps = [float(row["ticks_per_s"]) for row in rows]
        organism[key] = {
            "median_ms_per_tick": statistics.median(ms),
            "median_ticks_per_s": statistics.median(tps),
            "samples": rows,
        }

    off = organism["observer_off"]["median_ms_per_tick"]
    on = organism["observer_on"]["median_ms_per_tick"]
    tax_ms = on - off
    organism["observability_tax"] = {
        "ms_per_tick": tax_ms,
        "percent": (tax_ms / off * 100.0) if off else 0.0,
    }
    organism["matched_end_hash"] = (
        organism["observer_off"]["samples"][0]["end_hash"]
        == organism["observer_on"]["samples"][0]["end_hash"]
    )

    profiles = {}
    for observed, key in ((False, "observer_off"), (True, "observer_on")):
        profiles[key] = _profile(
            ticks=profile_ticks,
            seed=args.seed,
            observed=observed,
            profile_path=args.output_dir / f"{key}.prof",
        )

    python = sys.executable
    focused = [
        _command(
            "causal_equivalence_gate",
            [
                python,
                "-m",
                "pytest",
                "-o",
                "addopts=",
                "tests/experimental_integrity/test_performance_optimization_gate.py",
                "-q",
            ],
        ),
        _structured_command(
            "organism_scaling",
            [
                python,
                "scripts/bench_organism_tick.py",
                "--organisms",
                "1",
                "10",
                "--ticks",
                "120" if args.quick else "500",
            ],
        ),
        _structured_command(
            "sensorimotor_matching",
            [
                python,
                "scripts/bench_sensorimotor_matching.py",
                "--queries",
                "30" if args.quick else "150",
                "--candidates",
                "128" if args.quick else "512",
            ],
        ),
        _structured_command(
            "ridge_predictor",
            [
                python,
                "scripts/bench_ridge_predictor.py",
                "--queries",
                "1000" if args.quick else "10000",
            ],
        ),
        _command(
            "world_journal_age_scaling",
            [
                python,
                "scripts/bench_world_journal_index.py",
                "--ages",
                "1000",
                "5000" if args.quick else "100000",
                "--repeats",
                "40" if args.quick else "200",
            ],
        ),
        _structured_command(
            "sse_transport",
            [
                python,
                "scripts/bench_sse_transport.py",
                "--messages",
                "1000" if args.quick else "10000",
                "--payload-bytes",
                "4096",
            ],
        ),
    ]

    if shutil.which("node") is None:
        focused.append(
            {
                "name": "browser_layout",
                "command": ["node", "scripts/bench_browser_layout.mjs"],
                "returncode": 0,
                "elapsed_s": 0.0,
                "stdout": "",
                "stderr": "",
                "skipped": True,
                "reason": "node executable not available",
            }
        )
    else:
        focused.append(
            _structured_command(
                "browser_layout",
                ["node", "scripts/bench_browser_layout.mjs", "500" if args.quick else "2000"],
            )
        )

    focused_by_name = {item["name"]: item for item in focused}
    validity = {
        "matched_observer_end_hash": bool(organism["matched_end_hash"]),
        "causal_equivalence_gate": (
            focused_by_name.get("causal_equivalence_gate", {}).get("returncode") == 0
        ),
        "sensorimotor_equivalence": (
            focused_by_name.get("sensorimotor_matching", {}).get("returncode") == 0
        ),
    }
    validity["valid"] = all(validity.values())

    report = {
        "schema": "symbiont-performance-reprofile-v1",
        "generated_at_unix": time.time(),
        "environment": {
            "python": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "configuration": {
            "mode": mode,
            "seed": args.seed,
            "ticks": ticks,
            "profile_ticks": profile_ticks,
            "repeats": repeats,
        },
        "validity": validity,
        "organism": organism,
        "profile": profiles,
        "focused": focused,
    }

    json_path = args.output_dir / "report.json"
    md_path = args.output_dir / "report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")

    print(json.dumps({"report_json": str(json_path), "report_md": str(md_path)}, indent=2))


if __name__ == "__main__":
    main()
