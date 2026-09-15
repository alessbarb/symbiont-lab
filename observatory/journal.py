"""Segmented ndjson journal: a transport aid for the Observatory server to
tail/replay-on-connect, never a second source of truth (the runtime
checkpoint remains the only durable organism state). Segments are rotated
by deleting whole closed files, never truncated in place, because
truncating a file a tailer holds open shifts offsets under it."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Journal:
    def __init__(
        self,
        observatory_dir: Path,
        *,
        run_id: str,
        max_lines_per_segment: int = 500,
        max_segments: int = 20,
    ) -> None:
        self._dir = Path(observatory_dir) / "journal"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._run_id = run_id
        self._max_lines = max_lines_per_segment
        self._max_segments = max_segments
        self._sequence = 0
        self._segment_index = len(self.segments())
        self._lines_in_current_segment = self._max_lines  # forces rotation on first append

    @property
    def sequence(self) -> int:
        return self._sequence

    def segments(self) -> list[Path]:
        return sorted(self._dir.glob(f"{self._run_id}-*.ndjson"))

    def _current_path(self) -> Path:
        return self._dir / f"{self._run_id}-{self._segment_index:06d}.ndjson"

    def append(self, envelope: dict[str, Any]) -> int:
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
        self._prune_old_segments()
        return sequence

    def _prune_old_segments(self) -> None:
        segments = self.segments()
        excess = len(segments) - self._max_segments
        for path in segments[: max(0, excess)]:
            path.unlink(missing_ok=True)
