from __future__ import annotations
import os
from pathlib import Path
from typing import Iterable
from symbiont_lab.experiments.loader import load_experiment_file
from .models import ExperimentEntry

def _candidate_roots() -> Iterable[Path]:
    configured = os.environ.get("SYMBIONT_LAB_ROOT")
    if configured:
        yield Path(configured).expanduser()
    cwd = Path.cwd()
    yield cwd
    yield from cwd.parents
    yield Path(__file__).resolve().parents[3]

def find_experiments_root() -> Path | None:
    seen: set[Path] = set()
    for candidate in _candidate_roots():
        try:
            root = candidate.resolve()
        except OSError:
            continue
        if root in seen:
            continue
        seen.add(root)
        experiments = root / "experiments"
        if experiments.is_dir():
            return experiments
    return None

def discover_experiments(root: Path | None = None) -> list[ExperimentEntry]:
    experiments_root = root or find_experiments_root()
    if experiments_root is None:
        return []
    entries: list[ExperimentEntry] = []
    for path in sorted(experiments_root.rglob("experiment.toml")):
        try:
            spec = load_experiment_file(path)
        except (OSError, ValueError):
            continue
        relative = path.relative_to(experiments_root)
        entries.append(ExperimentEntry(
            path=path,
            category=relative.parts[0] if len(relative.parts) > 1 else "other",
            experiment_id=spec.experiment_id,
            title=spec.title,
            protocol=spec.protocol,
            protocol_version=spec.protocol_version,
            hypothesis=spec.hypothesis.strip(),
            success_criteria=spec.success_criteria.strip(),
            steps=spec.steps,
            seeds=tuple(int(seed) for seed in spec.seeds),
        ))
    return entries
