from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from symbiont.modeling.authority import ArchitectureId, ModelArtifactManifest, ModelObjective


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
        if (
            not isinstance(model_id, str)
            or len(model_id) != 64
            or any(c not in "0123456789abcdef" for c in model_id)
        ):
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
            "ancestor_model_id": artifact.manifest.ancestor_model_id,
            "generation": artifact.manifest.generation,
            "adaptation_reason": artifact.manifest.adaptation_reason,
            "authorized_parameter_ceiling": artifact.manifest.authorized_parameter_ceiling,
            "authorized_epoch_ceiling": artifact.manifest.authorized_epoch_ceiling,
            "authorized_step_ceiling": artifact.manifest.authorized_step_ceiling,
            "authorized_artifact_byte_ceiling": artifact.manifest.authorized_artifact_byte_ceiling,
            "adaptation_cost_epochs": artifact.manifest.adaptation_cost_epochs,
            "adaptation_cost_steps": artifact.manifest.adaptation_cost_steps,
            "autonomous_stopping": artifact.manifest.autonomous_stopping,
            "requested_patience": artifact.manifest.requested_patience,
            "requested_min_validation_gain": artifact.manifest.requested_min_validation_gain,
            "resolved_embedding_dim": artifact.manifest.resolved_embedding_dim,
            "resolved_hidden_dim": artifact.manifest.resolved_hidden_dim,
            "resolved_layers": artifact.manifest.resolved_layers,
            "resolved_heads": artifact.manifest.resolved_heads,
            "resolved_feedforward_dim": artifact.manifest.resolved_feedforward_dim,
        }
        self._atomic_write(weights_path, artifact.weights)
        self._atomic_write(
            manifest_path,
            json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )

    def get(self, model_id: str) -> ModelArtifact:
        manifest_path, weights_path = self._paths(model_id)
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("artifact manifest must be an object")
        string_keys = (
            "model_id",
            "organism_id",
            "corpus_hash",
            "tokenizer_hash",
            "architecture_id",
            "objective",
            "weights_hash",
        )
        if any(not isinstance(raw.get(key), str) for key in string_keys):
            raise ValueError("artifact manifest contains invalid string fields")
        parent = raw.get("parent_model_id")
        if parent is not None and not isinstance(parent, str):
            raise ValueError("artifact parent_model_id must be a string or null")
        int_keys = (
            "schema_version",
            "parameter_count",
            "context_window",
            "seed",
            "artifact_bytes",
            "created_tick_class",
        )
        if any(
            isinstance(raw.get(key), bool) or not isinstance(raw.get(key), int) for key in int_keys
        ):
            raise ValueError("artifact manifest contains invalid integer fields")
        manifest = ModelArtifactManifest(
            schema_version=raw["schema_version"],
            model_id=raw["model_id"],
            organism_id=raw["organism_id"],
            parent_model_id=parent,
            corpus_hash=raw["corpus_hash"],
            tokenizer_hash=raw["tokenizer_hash"],
            architecture_id=ArchitectureId(raw["architecture_id"]),
            objective=ModelObjective(raw["objective"]),
            parameter_count=raw["parameter_count"],
            context_window=raw["context_window"],
            seed=raw["seed"],
            weights_hash=raw["weights_hash"],
            artifact_bytes=raw["artifact_bytes"],
            created_tick_class=raw["created_tick_class"],
            ancestor_model_id=raw.get("ancestor_model_id"),
            generation=raw.get("generation", 0),
            adaptation_reason=raw.get("adaptation_reason"),
            authorized_parameter_ceiling=raw.get("authorized_parameter_ceiling"),
            authorized_epoch_ceiling=raw.get("authorized_epoch_ceiling"),
            authorized_step_ceiling=raw.get("authorized_step_ceiling"),
            authorized_artifact_byte_ceiling=raw.get("authorized_artifact_byte_ceiling"),
            adaptation_cost_epochs=raw.get("adaptation_cost_epochs", 0),
            adaptation_cost_steps=raw.get("adaptation_cost_steps", 0),
            autonomous_stopping=raw.get("autonomous_stopping", False),
            requested_patience=raw.get("requested_patience", 4),
            requested_min_validation_gain=raw.get("requested_min_validation_gain", 1e-9),
            resolved_embedding_dim=raw.get("resolved_embedding_dim"),
            resolved_hidden_dim=raw.get("resolved_hidden_dim"),
            resolved_layers=raw.get("resolved_layers"),
            resolved_heads=raw.get("resolved_heads"),
            resolved_feedforward_dim=raw.get("resolved_feedforward_dim"),
        )
        if manifest.model_id != model_id:
            raise ValueError("artifact manifest identity mismatch")
        weights = weights_path.read_bytes()
        if len(weights) > 512 * 1024 * 1024:
            raise ValueError("artifact exceeds absolute store safety limit")
        return ModelArtifact(manifest=manifest, weights=weights)

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
