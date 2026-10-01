from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from symbiont_lab import __version__ as lab_version


def get_git_info(repo_dir: Path | str | None = None) -> tuple[str, bool]:
    """Return provenance for this source tree, never for the caller's cwd."""
    env_sha = os.environ.get("GIT_COMMIT") or os.environ.get("GITHUB_SHA")
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
        if env_sha:
            return env_sha.strip(), False
        return "unknown", False


@dataclass(slots=True, frozen=True)
class ExecutionFingerprint:
    """Rigorous execution provenance for one declared scientific execution."""

    repo_root: str
    git_commit: str
    is_dirty: bool
    python_executable: str
    python_prefix: str
    python_base_prefix: str
    python_version: str
    symbiont_file: str
    symbiont_lab_file: str
    dependency_lock_hash: str
    effective_config_hash: str
    experiment_id: str
    seed: int | None

    @classmethod
    def capture(
        cls,
        repo_root: Path | str | None = None,
        *,
        effective_config: Mapping[str, Any] | None = None,
        experiment_id: str = "",
        seed: int | None = None,
    ) -> "ExecutionFingerprint":
        import symbiont
        import symbiont_lab

        root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[3]
        git_sha, dirty = get_git_info(root)
        lock_path = root / "uv.lock"
        dependency_lock_hash = (
            hashlib.sha256(lock_path.read_bytes()).hexdigest() if lock_path.is_file() else "missing"
        )
        config_payload = json.dumps(
            dict(effective_config or {}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return cls(
            repo_root=str(root.resolve()),
            git_commit=git_sha,
            is_dirty=dirty,
            python_executable=str(Path(sys.executable).resolve()),
            python_prefix=str(Path(sys.prefix).resolve()),
            python_base_prefix=str(Path(sys.base_prefix).resolve()),
            python_version=platform.python_version(),
            symbiont_file=str(Path(symbiont.__file__ or "").resolve()),
            symbiont_lab_file=str(Path(symbiont_lab.__file__ or "").resolve()),
            dependency_lock_hash=dependency_lock_hash,
            effective_config_hash=hashlib.sha256(config_payload).hexdigest(),
            experiment_id=str(experiment_id),
            seed=seed,
        )

    def is_hermetic_to(self, expected_root: Path | str) -> bool:
        """Verify that resolved modules originate strictly within the expected repository tree."""
        root = Path(expected_root).resolve()
        return Path(self.symbiont_file).resolve().is_relative_to(root) and Path(
            self.symbiont_lab_file
        ).resolve().is_relative_to(root)

    def mismatches(self, declared: "ExecutionFingerprint") -> tuple[str, ...]:
        """Return execution-identity fields that differ from a declared parent identity."""
        fields = (
            "repo_root",
            "git_commit",
            "is_dirty",
            "python_executable",
            "python_prefix",
            "python_base_prefix",
            "python_version",
            "symbiont_file",
            "symbiont_lab_file",
            "dependency_lock_hash",
            "effective_config_hash",
            "experiment_id",
            "seed",
        )
        return tuple(name for name in fields if getattr(self, name) != getattr(declared, name))

    def assert_matches_declared(self, declared: "ExecutionFingerprint") -> None:
        """Refuse execution when the child runtime is not the declared environment."""
        mismatches = self.mismatches(declared)
        if mismatches:
            raise RuntimeError("scientific execution identity mismatch: " + ", ".join(mismatches))


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
    execution_fingerprint: ExecutionFingerprint | None = None
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
        fingerprint_data = data.get("execution_fingerprint")
        execution_fingerprint = (
            ExecutionFingerprint(**fingerprint_data) if fingerprint_data is not None else None
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
            execution_fingerprint=execution_fingerprint,
            selection_digests=data.get("selection_digests", {}),
            config=data.get("config", {}),
            metrics=data.get("metrics", {}),
            config_digest=data.get("config_digest", ""),
        )
