"""Segmented ndjson journal used by the Observatory for tail/replay-on-connect.
The runtime checkpoint remains the organism source of truth. Segments are never
deleted automatically; closed segments can be losslessly gzipped explicitly."""

from __future__ import annotations

import json
import gzip
from pathlib import Path
from typing import Any

try:
    from .history_summary import build_history_summary, write_history_summary
except ImportError:  # pragma: no cover - supports direct script-style imports
    from history_summary import build_history_summary, write_history_summary


class Journal:
    def __init__(
        self,
        observatory_dir: Path,
        *,
        run_id: str,
        max_lines_per_segment: int = 500,
        max_segments: int = 20,
        max_total_bytes: int = 512 * 1024 * 1024,
    ) -> None:
        self._dir = Path(observatory_dir) / "journal"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._run_id = run_id
        self._max_lines = max_lines_per_segment
        self._max_segments = max_segments
        self._max_total_bytes = max_total_bytes  # compaction target, never a deletion quota
        self._sequence = 0
        indices = []
        for path in (*self._dir.glob(f"{self._run_id}-*.ndjson"), *self._dir.glob(f"{self._run_id}-*.ndjson.gz")):
            stem = path.name.removesuffix(".gz").removesuffix(".ndjson")
            suffix = stem.rsplit("-", 1)[-1]
            if suffix.isdigit():
                indices.append(int(suffix))
        self._segment_index = max(indices, default=0)
        self._lines_in_current_segment = self._max_lines  # forces rotation on first append

    @property
    def sequence(self) -> int:
        return self._sequence

    def segments(self) -> list[Path]:
        return sorted(self._dir.glob(f"{self._run_id}-*.ndjson"))

    def _current_path(self) -> Path:
        return self._dir / f"{self._run_id}-{self._segment_index:06d}.ndjson"

    def append(self, envelope: dict[str, Any]) -> int:
        rotated = self._lines_in_current_segment >= self._max_lines
        if self._lines_in_current_segment >= self._max_lines:
            self._segment_index += 1
            self._lines_in_current_segment = 0
        sequence = self._sequence
        self._sequence += 1
        entry = {"run_id": self._run_id, "sequence": sequence, "snapshot": envelope.get("snapshot", envelope)}
        with self._current_path().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
        self._lines_in_current_segment += 1
        if rotated:
            self.write_summary()
        return sequence

    def write_summary(self) -> None:
        """Write the current derived summary without changing raw history."""
        summary = build_history_summary(self._dir, run_id=self._run_id)
        write_history_summary(summary, self._dir.parent / "summaries" / f"{self._run_id}.summary.json")

    def compact(self) -> int:
        """Losslessly gzip closed segments; never deletes journal records.

        Compacted files keep their original bytes and name with a ``.gz`` suffix.
        The active segment is never touched. Readers that need historical replay
        should expand these archives before serving them.
        """
        candidates = sorted(path for path in self.segments() if path != self._current_path())
        compacted = 0
        for path in candidates:
            target = path.with_suffix(path.suffix + ".gz")
            if target.exists():
                continue
            with path.open("rb") as source, gzip.open(target, "wb", compresslevel=6) as compressed:
                compressed.write(source.read())
            path.unlink()
            compacted += 1
        return compacted
