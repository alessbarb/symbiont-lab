from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

from symbiont_lab import __version__ as lab_version


def get_git_info() -> tuple[str, bool]:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        dirty = bool(status)
        return sha, dirty
    except Exception:
        return "unknown", False


@dataclass(slots=True)
class SoftwareEnvironment:
    version: str = lab_version
    git_sha: str = field(default_factory=lambda: get_git_info()[0])
    dirty: bool = field(default_factory=lambda: get_git_info()[1])
    python: str = platform.python_version()


@dataclass(slots=True)
class RunManifest:
    run_id: str
    experiment_id: str
    protocol: str
    protocol_version: int
    started_at: str
    finished_at: str
    seed: int
    world_digest: str
    schema_version: int = 1
    software: SoftwareEnvironment = field(default_factory=SoftwareEnvironment)
    selection_digests: dict[str, str] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, run_dir: Path | str) -> Path:
        out_dir = Path(run_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = out_dir / "manifest.json"
        manifest_file.write_text(
            json.dumps(self.as_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return manifest_file

    @classmethod
    def load(cls, manifest_path: Path | str) -> RunManifest:
        path = Path(manifest_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        sw = data.get("software", {})
        software = SoftwareEnvironment(
            version=sw.get("version", "unknown"),
            git_sha=sw.get("git_sha", "unknown"),
            dirty=sw.get("dirty", False),
            python=sw.get("python", sys.version),
        )
        return cls(
            run_id=data["run_id"],
            experiment_id=data.get("experiment_id", "custom"),
            protocol=data.get("protocol", "unknown"),
            protocol_version=data.get("protocol_version", 1),
            started_at=data.get("started_at", ""),
            finished_at=data.get("finished_at", ""),
            seed=data.get("seed", 0),
            world_digest=data.get("world_digest", ""),
            schema_version=data.get("schema_version", 1),
            software=software,
            selection_digests=data.get("selection_digests", {}),
            config=data.get("config", {}),
            metrics=data.get("metrics", {}),
        )
