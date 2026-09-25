"""Lossless-derived history summaries for Observatory journals.

Summaries never replace journal segments. They contain coverage, counters and
hashes so a consumer can find and verify the exact raw records behind a rollup.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


def _lines(path: Path) -> Iterable[str]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        yield from handle


def build_history_summary(journal_dir: Path | str, *, run_id: str) -> dict[str, Any]:
    root = Path(journal_dir)
    paths = sorted([*root.glob(f"{run_id}-*.ndjson"), *root.glob(f"{run_id}-*.ndjson.gz")])
    files: list[dict[str, Any]] = []
    states: Counter[str] = Counter()
    versions: Counter[str] = Counter()
    total = 0
    ticks: list[int] = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines = 0
        for line in _lines(path):
            if not line.strip():
                continue
            entry = json.loads(line)
            snapshot = entry.get("snapshot", entry)
            total += 1
            lines += 1
            versions[str(snapshot.get("schema_version"))] += 1
            tick = snapshot.get("tick")
            if isinstance(tick, int):
                ticks.append(tick)
            state = snapshot.get("organism", {}).get("state")
            if isinstance(state, str):
                states[state] += 1
        files.append(
            {
                "name": path.name,
                "sha256": digest,
                "entries": lines,
                "compressed": path.suffix == ".gz",
            }
        )
    return {
        "summary_version": 1,
        "run_id": run_id,
        "segments": files,
        "entries": total,
        "tick_range": {"min": min(ticks) if ticks else None, "max": max(ticks) if ticks else None},
        "schema_versions": dict(sorted(versions.items())),
        "organism_states": dict(sorted(states.items())),
    }


def write_history_summary(summary: dict[str, Any], target: Path | str) -> Path:
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


__all__ = ["build_history_summary", "write_history_summary"]
