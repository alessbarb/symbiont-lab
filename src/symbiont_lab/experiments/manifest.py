from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from symbiont_lab import __version__ as lab_version


def get_git_info(repo_dir: Path | str | None = None) -> tuple[str, bool]:
    """Return provenance for this source tree, never for the caller's cwd."""
    cwd = Path(repo_dir) if repo_dir is not None else Path(__file__).resolve().parents[3]
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(cwd), "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
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
    config_digest: str = ""

    def as_dict(self) -> dict[str, Any]:
        if not self.config_digest:
            self.config_digest = hashlib.sha256(
                json.dumps(self.config, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
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
            config_digest=data.get("config_digest", ""),
        )
