from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile

from symbiont.modeling.authority import (
    ArchitectureId,
    ModelArtifactManifest,
    ModelObjective,
)


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    manifest: ModelArtifactManifest
    weights: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, ModelArtifactManifest):
            raise ValueError("manifest must be a ModelArtifactManifest")
        if not isinstance(self.weights, bytes) or not self.weights:
            raise ValueError("weights must be non-empty bytes")
        digest = hashlib.sha256(self.weights).hexdigest()
        if digest != self.manifest.weights_hash:
            raise ValueError("artifact weights do not match manifest hash")
        if len(self.weights) != self.manifest.artifact_bytes:
            raise ValueError("artifact byte count does not match manifest")


class FileArtifactStore:
    """Content-addressed, atomic model artifact persistence outside runtime state."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _paths(self, model_id: str) -> tuple[Path, Path]:
        if not isinstance(model_id, str) or len(model_id) != 64 or any(c not in "0123456789abcdef" for c in model_id):
            raise ValueError("model_id must be a sha256 digest")
        return self._root / f"{model_id}.json", self._root / f"{model_id}.pt"

    def put(self, artifact: ModelArtifact) -> None:
        manifest_path, weights_path = self._paths(artifact.manifest.model_id)
        manifest_payload = {
            "schema_version": artifact.manifest.schema_version,
            "model_id": artifact.manifest.model_id,
            "organism_id": artifact.manifest.organism_id,
            "parent_model_id": artifact.manifest.parent_model_id,
            "corpus_hash": artifact.manifest.corpus_hash,
            "tokenizer_hash": artifact.manifest.tokenizer_hash,
            "architecture_id": artifact.manifest.architecture_id.value,
            "objective": artifact.manifest.objective.value,
            "parameter_count": artifact.manifest.parameter_count,
            "context_window": artifact.manifest.context_window,
            "seed": artifact.manifest.seed,
            "weights_hash": artifact.manifest.weights_hash,
            "artifact_bytes": artifact.manifest.artifact_bytes,
            "created_tick_class": artifact.manifest.created_tick_class,
        }
        self._atomic_write(weights_path, artifact.weights)
        encoded = json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self._atomic_write(manifest_path, encoded)

    def get(self, model_id: str) -> ModelArtifact:
        manifest_path, weights_path = self._paths(model_id)
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = ModelArtifactManifest(
            schema_version=int(raw["schema_version"]),
            model_id=str(raw["model_id"]),
            organism_id=str(raw["organism_id"]),
            parent_model_id=(None if raw.get("parent_model_id") is None else str(raw["parent_model_id"])),
            corpus_hash=str(raw["corpus_hash"]),
            tokenizer_hash=str(raw["tokenizer_hash"]),
            architecture_id=ArchitectureId(str(raw["architecture_id"])),
            objective=ModelObjective(str(raw["objective"])),
            parameter_count=int(raw["parameter_count"]),
            context_window=int(raw["context_window"]),
            seed=int(raw["seed"]),
            weights_hash=str(raw["weights_hash"]),
            artifact_bytes=int(raw["artifact_bytes"]),
            created_tick_class=int(raw["created_tick_class"]),
        )
        if manifest.model_id != model_id:
            raise ValueError("artifact manifest identity mismatch")
        return ModelArtifact(manifest=manifest, weights=weights_path.read_bytes())

    def contains(self, model_id: str) -> bool:
        manifest_path, weights_path = self._paths(model_id)
        return manifest_path.is_file() and weights_path.is_file()

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(dir=path.parent, delete=False)
        try:
            with handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(handle.name, path)
        finally:
            try:
                if os.path.exists(handle.name):
                    os.unlink(handle.name)
            except OSError:
                pass
