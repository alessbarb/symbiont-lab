from __future__ import annotations

from collections import deque
from threading import Lock, Thread
import time
from typing import Any

from symbiont.simulation import SimulationSnapshot, run_simulation
from symbiont_lab.archive.runs import ExperimentArchive, ExperimentRecord
from symbiont_lab.archive.studies import StudyArchive, StudyRecord
from symbiont_lab.experiments.spec import ExperimentSpec, spec_from_payload
from symbiont_lab.studies.campaigns.campaign import analyze_campaign
from symbiont_lab.studies.campaigns.comparative import StudyResult, run_comparative_study
from symbiont_lab.studies.campaigns.interpretation import StudyInterpretation, interpret_study


class DashboardState:
    def __init__(self, max_points: int = 600, archive: ExperimentArchive | None = None) -> None:
        self._lock = Lock()
        self._history: deque[dict[str, Any]] = deque(maxlen=max_points)
        self.running = False
        self.finished = False
        self.error: str | None = None
        self.archive_error: str | None = None
        self.experiment_number = 0
        self.spec = ExperimentSpec()
        self.archive = archive
        self.records: list[ExperimentRecord] = archive.recent(20) if archive else []

    def start(self, spec: ExperimentSpec | dict[str, Any]) -> bool:
        normalized = spec if isinstance(spec, ExperimentSpec) else spec_from_payload(spec, self.spec)
        with self._lock:
            if self.running:
                return False
            self._history.clear()
            self.running = True
            self.finished = False
            self.error = None
            self.archive_error = None
            self.spec = normalized
            self.experiment_number += 1
            return True

    def add(self, snapshot: SimulationSnapshot) -> None:
        with self._lock:
            self._history.append(snapshot.as_dict())

    def finish(self, record: ExperimentRecord | None = None) -> None:
        with self._lock:
            self.running = False
            self.finished = True
            if record is not None:
                self.records.insert(0, record)
                del self.records[20:]

    def fail(self, exc: Exception) -> None:
        with self._lock:
            self.running = False
            self.finished = True
            self.error = f"{type(exc).__name__}: {exc}"

    def archive_failed(self, exc: Exception) -> None:
        with self._lock:
            self.archive_error = f"{type(exc).__name__}: {exc}"

    def payload(self) -> dict[str, Any]:
        with self._lock:
            history = list(self._history)
            return {
                "running": self.running,
                "finished": self.finished,
                "error": self.error,
                "archive_error": self.archive_error,
                "experiment_number": self.experiment_number,
                "spec": self.spec.as_dict(),
                "current": history[-1] if history else None,
                "history": history,
                "records": [record.as_dict() for record in self.records],
            }


class StudyDashboardState:
    def __init__(self, archive: StudyArchive | None = None) -> None:
        self._lock = Lock()
        self.running = False
        self.error: str | None = None
        self.archive_error: str | None = None
        self.completed = 0
        self.total = 0
        self.phase = "idle"
        self.seed: int | None = None
        self.config: dict[str, Any] = {}
        self.result: dict[str, object] | None = None
        self.interpretation: dict[str, object] | None = None
        self.archive = archive
        self.record_id: str | None = None
        self.records: list[StudyRecord] = archive.recent(20) if archive else []
        self.campaigns: dict[str, dict[str, object]] = {}
        if archive is not None:
            for record in self.records:
                lineage = archive.lineage(record.record_id)
                if lineage:
                    self.campaigns[record.record_id] = analyze_campaign(lineage).as_dict()

    def start(self, config: dict[str, Any], total: int) -> bool:
        with self._lock:
            if self.running:
                return False
            self.running = True
            self.error = None
            self.archive_error = None
            self.completed = 0
            self.total = total
            self.phase = "queued"
            self.seed = None
            self.config = config
            self.result = None
            self.interpretation = None
            self.record_id = None
            return True

    def progress(self, completed: int, total: int, phase: str, seed: int) -> None:
        with self._lock:
            self.completed = completed
            self.total = total
            self.phase = phase
            self.seed = seed

    def finish(
        self,
        result: StudyResult,
        interpretation: StudyInterpretation | None = None,
        record: StudyRecord | None = None,
    ) -> None:
        if interpretation is None:
            interpretation = interpret_study(result)
        with self._lock:
            self.running = False
            self.phase = "finished"
            self.result = result.as_dict()
            self.interpretation = interpretation.as_dict()
            if record is not None:
                self.record_id = record.record_id
                self.records.insert(0, record)
                del self.records[20:]
                if self.archive is not None:
                    lineage = self.archive.lineage(record.record_id)
                    if lineage:
                        self.campaigns[record.record_id] = analyze_campaign(lineage).as_dict()

    def fail(self, exc: Exception) -> None:
        with self._lock:
            self.running = False
            self.phase = "error"
            self.error = f"{type(exc).__name__}: {exc}"

    def archive_failed(self, exc: Exception) -> None:
        with self._lock:
            self.archive_error = f"{type(exc).__name__}: {exc}"

    def payload(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "error": self.error,
                "archive_error": self.archive_error,
                "completed": self.completed,
                "total": self.total,
                "phase": self.phase,
                "seed": self.seed,
                "config": dict(self.config),
                "result": self.result,
                "interpretation": self.interpretation,
                "record_id": self.record_id,
                "records": [record.as_dict() for record in self.records],
                "campaigns": dict(self.campaigns),
            }


def run_experiment(state: DashboardState, spec: ExperimentSpec) -> None:
    def publish(snapshot: SimulationSnapshot) -> None:
        state.add(snapshot)
        if spec.delay > 0:
            time.sleep(spec.delay)

    try:
        result, _ = run_simulation(
            spec.hosts,
            spec.steps,
            spec.seed,
            spec.threat_rate,
            spec.poison_fraction,
            spec.heterogeneity,
            spec.drift_step,
            spec.drift_fraction,
            spec.drift_magnitude,
            on_snapshot=publish,
        )
        record = None
        if state.archive is not None:
            try:
                record = state.archive.append(spec, result, source="dashboard")
            except OSError as exc:
                state.archive_failed(exc)
        state.finish(record)
    except Exception as exc:
        state.fail(exc)


def start_experiment(
    state: DashboardState,
    study_state: StudyDashboardState,
    spec: ExperimentSpec,
) -> bool:
    if study_state.running or not state.start(spec):
        return False
    Thread(target=run_experiment, args=(state, spec), daemon=True).start()
    return True


def _parse_seeds(raw: object) -> tuple[int, ...]:
    parts = raw if isinstance(raw, list) else str(raw or "").split(",")
    seeds = tuple(int(str(part).strip()) for part in parts if str(part).strip())
    if not seeds:
        raise ValueError("study requires at least one seed")
    if len(seeds) > 50:
        raise ValueError("dashboard studies are limited to 50 seeds")
    return seeds


def run_study_dashboard(
    state: StudyDashboardState,
    base_spec: ExperimentSpec,
    *,
    title: str,
    parameter: str,
    baseline: float,
    variant: float,
    seeds: tuple[int, ...],
    parent_record_id: str | None = None,
) -> None:
    try:
        result = run_comparative_study(
            base_spec,
            parameter=parameter,
            baseline_value=baseline,
            variant_value=variant,
            seeds=seeds,
            title=title,
            on_progress=state.progress,
        )
        interpretation = interpret_study(result)
        record = None
        if state.archive is not None:
            try:
                record = state.archive.append(
                    base_spec,
                    result,
                    interpretation,
                    source="dashboard",
                    parent_record_id=parent_record_id,
                )
            except OSError as exc:
                state.archive_failed(exc)
        state.finish(result, interpretation, record)
    except Exception as exc:
        state.fail(exc)


def start_study(
    experiment_state: DashboardState,
    state: StudyDashboardState,
    base_spec: ExperimentSpec,
    *,
    title: str,
    parameter: str,
    baseline: float,
    variant: float,
    seeds: tuple[int, ...],
    parent_record_id: str | None = None,
) -> bool:
    if experiment_state.running:
        return False
    config = {
        "title": title,
        "parameter": parameter,
        "baseline": baseline,
        "variant": variant,
        "seeds": seeds,
        "base_spec": base_spec.as_dict(),
        "parent_record_id": parent_record_id,
    }
    if not state.start(config, len(seeds) * 2):
        return False
    Thread(
        target=run_study_dashboard,
        args=(state, base_spec),
        kwargs={
            "title": title,
            "parameter": parameter,
            "baseline": baseline,
            "variant": variant,
            "seeds": seeds,
            "parent_record_id": parent_record_id,
        },
        daemon=True,
    ).start()
    return True
