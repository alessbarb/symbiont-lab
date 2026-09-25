from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import Enum


class ArchitectureId(str, Enum):
    GRU_V1 = "gru-v1"
    TRANSFORMER_V1 = "transformer-v1"


class ModelObjective(str, Enum):
    NEXT_TOKEN = "next-token"


@dataclass(frozen=True, slots=True)
class TrainingBudget:
    """Externally governed ceiling for one private-model training request."""

    max_parameters: int = 20_000_000
    max_context: int = 1024
    max_examples: int = 32_768
    max_epochs: int = 128
    max_steps: int = 200_000
    max_artifact_bytes: int = 512 * 1024 * 1024

    def __post_init__(self) -> None:
        bounds = (
            (self.max_parameters, 1_000, 128_000_000, "max_parameters"),
            (self.max_context, 8, 2048, "max_context"),
            (self.max_examples, 3, 262_144, "max_examples"),
            (self.max_epochs, 1, 4096, "max_epochs"),
            (self.max_steps, 1, 10_000_000, "max_steps"),
            (self.max_artifact_bytes, 1024, 4 * 1024 * 1024 * 1024, "max_artifact_bytes"),
        )
        for value, low, high, name in bounds:
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"{name} must be an integer within [{low}, {high}]")


@dataclass(frozen=True, slots=True)
class TrainingRequest:
    organism_id: str
    corpus_hash: str
    tokenizer_hash: str
    architecture_id: ArchitectureId
    objective: ModelObjective
    seed: int
    context_window: int
    requested_parameters: int
    requested_epochs: int
    requested_steps: int
    created_tick_class: int
    parent_model_id: str | None = None
    adaptation_reason: str | None = None
    autonomous_stopping: bool = False
    requested_patience: int = 4
    requested_min_validation_gain: float = 1e-9

    def __post_init__(self) -> None:
        for name, value, maximum in (
            ("organism_id", self.organism_id, 128),
            ("corpus_hash", self.corpus_hash, 128),
            ("tokenizer_hash", self.tokenizer_hash, 128),
        ):
            if not isinstance(value, str) or not value or len(value) > maximum:
                raise ValueError(f"{name} must be a non-empty bounded string")
        for name, value in (
            ("corpus_hash", self.corpus_hash),
            ("tokenizer_hash", self.tokenizer_hash),
        ):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValueError(f"{name} must be a lowercase sha256 digest")
        if not isinstance(self.architecture_id, ArchitectureId):
            raise ValueError("architecture_id must be an ArchitectureId")
        if not isinstance(self.objective, ModelObjective):
            raise ValueError("objective must be a ModelObjective")
        if (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, int)
            or not 0 <= self.seed <= 2**63 - 1
        ):
            raise ValueError("seed must be a non-negative 63-bit integer")
        for name, value in (
            ("context_window", self.context_window),
            ("requested_parameters", self.requested_parameters),
            ("requested_epochs", self.requested_epochs),
            ("requested_steps", self.requested_steps),
            ("created_tick_class", self.created_tick_class),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if not 8 <= self.context_window <= 2048:
            raise ValueError("context_window must be within [8, 2048]")
        if self.requested_parameters < 1_000:
            raise ValueError("requested_parameters must be at least 1000")
        if self.requested_epochs < 1 or self.requested_steps < 1:
            raise ValueError("training epochs and steps must be positive")
        if self.parent_model_id is not None and (
            not isinstance(self.parent_model_id, str)
            or not self.parent_model_id
            or len(self.parent_model_id) > 128
        ):
            raise ValueError("parent_model_id must be a bounded non-empty string when present")
        if self.adaptation_reason is not None and (
            not isinstance(self.adaptation_reason, str)
            or not self.adaptation_reason
            or len(self.adaptation_reason) > 256
        ):
            raise ValueError("adaptation_reason must be bounded when present")
        if self.parent_model_id is None and self.adaptation_reason is not None:
            raise ValueError("adaptation_reason requires a parent model")
        if not isinstance(self.autonomous_stopping, bool):
            raise ValueError("autonomous_stopping must be boolean")
        if (
            isinstance(self.requested_patience, bool)
            or not isinstance(self.requested_patience, int)
            or not 1 <= self.requested_patience <= 64
        ):
            raise ValueError("requested_patience must be within [1, 64]")
        if (
            isinstance(self.requested_min_validation_gain, bool)
            or not isinstance(self.requested_min_validation_gain, (int, float))
            or not math.isfinite(float(self.requested_min_validation_gain))
            or not 0.0 <= float(self.requested_min_validation_gain) <= 1.0
        ):
            raise ValueError("requested_min_validation_gain must be within [0, 1]")

    @property
    def request_id(self) -> str:
        payload = {
            "organism_id": self.organism_id,
            "corpus_hash": self.corpus_hash,
            "tokenizer_hash": self.tokenizer_hash,
            "architecture_id": self.architecture_id.value,
            "objective": self.objective.value,
            "seed": self.seed,
            "context_window": self.context_window,
            "requested_parameters": self.requested_parameters,
            "requested_epochs": self.requested_epochs,
            "requested_steps": self.requested_steps,
            "created_tick_class": self.created_tick_class,
            "parent_model_id": self.parent_model_id,
            "adaptation_reason": self.adaptation_reason,
        }
        if self.autonomous_stopping:
            payload["autonomous_stopping"] = True
            payload["requested_patience"] = self.requested_patience
            payload["requested_min_validation_gain"] = self.requested_min_validation_gain
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class TrainingAuthorization:
    request_id: str
    organism_id: str
    architecture_id: ArchitectureId
    objective: ModelObjective
    context_window: int
    parameter_ceiling: int
    epoch_ceiling: int
    step_ceiling: int
    artifact_byte_ceiling: int


@dataclass(frozen=True, slots=True)
class ModelArtifactManifest:
    schema_version: int
    model_id: str
    organism_id: str
    parent_model_id: str | None
    corpus_hash: str
    tokenizer_hash: str
    architecture_id: ArchitectureId
    objective: ModelObjective
    parameter_count: int
    context_window: int
    seed: int
    weights_hash: str
    artifact_bytes: int
    created_tick_class: int
    ancestor_model_id: str | None = None
    generation: int = 0
    adaptation_reason: str | None = None
    authorized_parameter_ceiling: int | None = None
    authorized_epoch_ceiling: int | None = None
    authorized_step_ceiling: int | None = None
    authorized_artifact_byte_ceiling: int | None = None
    adaptation_cost_epochs: int = 0
    adaptation_cost_steps: int = 0
    autonomous_stopping: bool = False
    requested_patience: int = 4
    requested_min_validation_gain: float = 1e-9
    resolved_embedding_dim: int | None = None
    resolved_hidden_dim: int | None = None
    resolved_layers: int | None = None
    resolved_heads: int | None = None
    resolved_feedforward_dim: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or self.schema_version != 1:
            raise ValueError("unsupported model artifact schema")
        if (
            not isinstance(self.model_id, str)
            or len(self.model_id) != 64
            or any(c not in "0123456789abcdef" for c in self.model_id)
        ):
            raise ValueError("model_id must be a lowercase sha256 digest")
        if (
            not isinstance(self.organism_id, str)
            or not self.organism_id
            or len(self.organism_id) > 128
        ):
            raise ValueError("organism_id must be a bounded non-empty string")
        if self.parent_model_id is not None and (
            not isinstance(self.parent_model_id, str)
            or not self.parent_model_id
            or len(self.parent_model_id) > 128
        ):
            raise ValueError("parent_model_id must be bounded when present")
        for name, digest in (
            ("corpus_hash", self.corpus_hash),
            ("tokenizer_hash", self.tokenizer_hash),
            ("weights_hash", self.weights_hash),
        ):
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
            ):
                raise ValueError(f"{name} must be a lowercase sha256 digest")
        if not isinstance(self.architecture_id, ArchitectureId) or not isinstance(
            self.objective, ModelObjective
        ):
            raise ValueError("invalid artifact architecture or objective")
        if (
            isinstance(self.parameter_count, bool)
            or not isinstance(self.parameter_count, int)
            or not 1 <= self.parameter_count <= 128_000_000
        ):
            raise ValueError("parameter_count outside supported bounds")
        if (
            isinstance(self.context_window, bool)
            or not isinstance(self.context_window, int)
            or not 8 <= self.context_window <= 2048
        ):
            raise ValueError("context_window outside supported bounds")
        if (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, int)
            or not 0 <= self.seed <= 2**63 - 1
        ):
            raise ValueError("seed must be a non-negative 63-bit integer")
        if (
            isinstance(self.artifact_bytes, bool)
            or not isinstance(self.artifact_bytes, int)
            or not 1 <= self.artifact_bytes <= 4 * 1024 * 1024 * 1024
        ):
            raise ValueError("artifact_bytes outside supported bounds")
        if (
            isinstance(self.created_tick_class, bool)
            or not isinstance(self.created_tick_class, int)
            or self.created_tick_class < 0
        ):
            raise ValueError("created_tick_class must be non-negative")
        if self.ancestor_model_id is not None and (
            not isinstance(self.ancestor_model_id, str)
            or len(self.ancestor_model_id) != 64
            or any(c not in "0123456789abcdef" for c in self.ancestor_model_id)
        ):
            raise ValueError("ancestor_model_id must be a sha256 digest or null")
        if (
            isinstance(self.generation, bool)
            or not isinstance(self.generation, int)
            or not 0 <= self.generation <= 2_147_483_647
        ):
            raise ValueError("generation outside serialization safety bounds")
        if self.adaptation_reason is not None and (
            not isinstance(self.adaptation_reason, str)
            or not self.adaptation_reason
            or len(self.adaptation_reason) > 256
        ):
            raise ValueError("adaptation_reason must be bounded when present")
        ceilings = (
            (self.authorized_parameter_ceiling, 1_000, 128_000_000, "authorized_parameter_ceiling"),
            (self.authorized_epoch_ceiling, 1, 4096, "authorized_epoch_ceiling"),
            (self.authorized_step_ceiling, 1, 10_000_000, "authorized_step_ceiling"),
            (
                self.authorized_artifact_byte_ceiling,
                1_024,
                4 * 1024 * 1024 * 1024,
                "authorized_artifact_byte_ceiling",
            ),
        )
        for value, low, high, name in ceilings:
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high
            ):
                raise ValueError(f"{name} outside supported bounds")
        for name, value in (
            ("adaptation_cost_epochs", self.adaptation_cost_epochs),
            ("adaptation_cost_steps", self.adaptation_cost_steps),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be non-negative")
        if not isinstance(self.autonomous_stopping, bool):
            raise ValueError("artifact autonomous_stopping must be boolean")
        if (
            isinstance(self.requested_patience, bool)
            or not isinstance(self.requested_patience, int)
            or not 1 <= self.requested_patience <= 64
        ):
            raise ValueError("artifact requested_patience must be within [1, 64]")
        if (
            isinstance(self.requested_min_validation_gain, bool)
            or not isinstance(self.requested_min_validation_gain, (int, float))
            or not math.isfinite(float(self.requested_min_validation_gain))
            or not 0.0 <= float(self.requested_min_validation_gain) <= 1.0
        ):
            raise ValueError("artifact requested_min_validation_gain must be within [0, 1]")
        resolved_shape = (
            self.resolved_embedding_dim,
            self.resolved_hidden_dim,
            self.resolved_layers,
            self.resolved_heads,
            self.resolved_feedforward_dim,
        )
        if any(value is not None for value in resolved_shape):
            if any(
                isinstance(value, bool) or not isinstance(value, int) or value < 1
                for value in resolved_shape
            ):
                raise ValueError("resolved architecture shape must contain positive integers")

    @classmethod
    def build(
        cls,
        *,
        request: TrainingRequest,
        parameter_count: int,
        weights_hash: str,
        artifact_bytes: int,
        parent: "ModelArtifactManifest | None" = None,
        authorization: "TrainingAuthorization | None" = None,
        adaptation_cost_epochs: int = 0,
        adaptation_cost_steps: int = 0,
        resolved_embedding_dim: int | None = None,
        resolved_hidden_dim: int | None = None,
        resolved_layers: int | None = None,
        resolved_heads: int | None = None,
        resolved_feedforward_dim: int | None = None,
    ) -> "ModelArtifactManifest":
        material = f"{request.request_id}:{weights_hash}:{parameter_count}".encode("utf-8")
        return cls(
            schema_version=1,
            model_id=hashlib.sha256(material).hexdigest(),
            organism_id=request.organism_id,
            parent_model_id=request.parent_model_id,
            corpus_hash=request.corpus_hash,
            tokenizer_hash=request.tokenizer_hash,
            architecture_id=request.architecture_id,
            objective=request.objective,
            parameter_count=parameter_count,
            context_window=request.context_window,
            seed=request.seed,
            weights_hash=weights_hash,
            artifact_bytes=artifact_bytes,
            created_tick_class=request.created_tick_class,
            ancestor_model_id=(parent.ancestor_model_id or parent.model_id)
            if parent is not None
            else None,
            generation=(parent.generation + 1) if parent is not None else 0,
            adaptation_reason=request.adaptation_reason,
            authorized_parameter_ceiling=authorization.parameter_ceiling
            if authorization is not None
            else None,
            authorized_epoch_ceiling=authorization.epoch_ceiling
            if authorization is not None
            else None,
            authorized_step_ceiling=authorization.step_ceiling
            if authorization is not None
            else None,
            authorized_artifact_byte_ceiling=authorization.artifact_byte_ceiling
            if authorization is not None
            else None,
            adaptation_cost_epochs=adaptation_cost_epochs,
            adaptation_cost_steps=adaptation_cost_steps,
            autonomous_stopping=request.autonomous_stopping,
            requested_patience=request.requested_patience,
            requested_min_validation_gain=request.requested_min_validation_gain,
            resolved_embedding_dim=resolved_embedding_dim,
            resolved_hidden_dim=resolved_hidden_dim,
            resolved_layers=resolved_layers,
            resolved_heads=resolved_heads,
            resolved_feedforward_dim=resolved_feedforward_dim,
        )


class ModelTrainingAuthority:
    """Pure validation boundary; it never executes trainer-supplied code."""

    def __init__(self, budget: TrainingBudget | None = None) -> None:
        self._budget = budget or TrainingBudget()

    @property
    def budget(self) -> TrainingBudget:
        return self._budget

    def authorize(self, request: TrainingRequest, *, corpus_records: int) -> TrainingAuthorization:
        if not isinstance(request, TrainingRequest):
            raise ValueError("request must be a TrainingRequest")
        if (
            isinstance(corpus_records, bool)
            or not isinstance(corpus_records, int)
            or corpus_records < 3
        ):
            raise ValueError("corpus_records must be at least 3")
        if corpus_records > self._budget.max_examples:
            raise ValueError("training corpus exceeds authority example ceiling")
        if request.context_window > self._budget.max_context:
            raise ValueError("requested context exceeds authority ceiling")
        if request.requested_parameters > self._budget.max_parameters:
            raise ValueError("requested parameter count exceeds authority ceiling")
        if request.requested_epochs > self._budget.max_epochs:
            raise ValueError("requested epochs exceed authority ceiling")
        if request.requested_steps > self._budget.max_steps:
            raise ValueError("requested steps exceed authority ceiling")
        return TrainingAuthorization(
            request_id=request.request_id,
            organism_id=request.organism_id,
            architecture_id=request.architecture_id,
            objective=request.objective,
            context_window=request.context_window,
            parameter_ceiling=min(request.requested_parameters, self._budget.max_parameters),
            epoch_ceiling=min(request.requested_epochs, self._budget.max_epochs),
            step_ceiling=min(request.requested_steps, self._budget.max_steps),
            artifact_byte_ceiling=self._budget.max_artifact_bytes,
        )
