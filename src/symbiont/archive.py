from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from .experiment import ExperimentSpec
from .simulation import SimulationResult


@dataclass(slots=True, frozen=True)
class ExperimentRecord:
    record_id: str
    created_at: str
    source: str
    spec: dict[str, object]
    metrics: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class ExperimentArchive:
    """Append-only local research memory for completed synthetic experiments.

    The archive is an observer-side facility. It is never exposed to agents,
    collective trust, reasoning, curiosity or metacognition.
    """

    def __init__(self, path: str | Path = ".symbiont/experiments.jsonl") -> None:
        self.path = Path(path)
        self._lock = Lock()

    def append(
        self,
        spec: ExperimentSpec,
        result: SimulationResult,
        *,
        source: str,
    ) -> ExperimentRecord:
        record = ExperimentRecord(
            record_id=uuid4().hex[:12],
            created_at=datetime.now(timezone.utc).isoformat(),
            source=source,
            spec=spec.as_dict(),
            metrics=self._metrics(result),
        )
        line = json.dumps(record.as_dict(), sort_keys=True, separators=(",", ":"))
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return record

    def recent(self, limit: int = 12) -> list[ExperimentRecord]:
        if limit <= 0 or not self.path.exists():
            return []
        with self._lock:
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return []
        records: list[ExperimentRecord] = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                raw: dict[str, Any] = json.loads(line)
                records.append(
                    ExperimentRecord(
                        record_id=str(raw["record_id"]),
                        created_at=str(raw["created_at"]),
                        source=str(raw.get("source", "unknown")),
                        spec=dict(raw.get("spec", {})),
                        metrics=dict(raw.get("metrics", {})),
                    )
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            if len(records) >= limit:
                break
        return records

    @staticmethod
    def _metrics(result: SimulationResult) -> dict[str, object]:
        return {
            "detection_rate": result.detection_rate,
            "precision": result.precision,
            "false_positive_rate": result.false_positive_rate,
            "calibration_error": result.calibration_error,
            "brier_score": result.brier_score,
            "overconfidence_rate": result.overconfidence_rate,
            "blind_spot_rate": result.blind_spot_rate,
            "self_confidence": result.self_confidence,
            "epistemic_pressure": result.epistemic_pressure,
            "metacognitive_status": result.metacognitive_status,
            "open_questions": result.open_questions,
            "reasoning_hypotheses": result.reasoning_hypotheses,
            "curiosity_probes": result.curiosity_probes,
            "top_probe_utility": result.top_probe_utility,
            "drift_adaptations": result.drift_adaptations,
            "recent_drift_false_positive_rate": result.recent_drift_false_positive_rate,
        }
