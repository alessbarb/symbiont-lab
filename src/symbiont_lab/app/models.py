from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class RunKind(str, Enum):
    EXPERIMENT = "experiment"
    PHYSICS3D = "physics3d"

class RunStatus(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

@dataclass(frozen=True, slots=True)
class ExperimentEntry:
    path: Path
    category: str
    experiment_id: str
    title: str
    protocol: str
    protocol_version: int
    hypothesis: str
    success_criteria: str
    steps: int
    seeds: tuple[int, ...]

@dataclass(slots=True)
class RunDescriptor:
    kind: RunKind
    label: str
    status: RunStatus = RunStatus.IDLE
    detail: str = ""
    artifact_path: str | None = None
