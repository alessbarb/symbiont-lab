from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math


class ArchitectureId(str, Enum):
    GRU_V1 = "gru-v1"
    TRANSFORMER_V1 = "transformer-v1"


class ModelObjective(str, Enum):
    NEXT_TOKEN = "next-token"


@dataclass(frozen=True, slots=True)
class TrainingBudget:
    """Externally governed ceiling for one private-model training request."""

    max_parameters: int = 5_000_000
    max_context: int = 256
    max_examples: int = 8192
    max_epochs: int = 32
    max_steps: int = 20_000
    max_artifact_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        bounds = (
            (self.max_parameters, 1_000, 20_000_000, "max_parameters"),
            (self.max_context, 8, 512, "max_context"),
            (self.max_examples, 3, 65_536, "max_examples"),
            (self.max_epochs, 1, 256, "max_epochs"),
            (self.max_steps, 1, 1_000_000, "max_steps"),
            (self.max_artifact_bytes, 1024, 512 * 1024 * 1024, "max_artifact_bytes"),
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

    def __post_init__(self) -> None:
        for name, value, maximum in (
            ("organism_id", self.organism_id, 128),
            ("corpus_hash", self.corpus_hash, 128),
            ("tokenizer_hash", self.tokenizer_hash, 128),
        ):
            if not isinstance(value, str) or not value or len(value) > maximum:
                raise ValueError(f"{name} must be a non-empty bounded string")
        for name, value in (("corpus_hash", self.corpus_hash), ("tokenizer_hash", self.tokenizer_hash)):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValueError(f"{name} must be a lowercase sha256 digest")
        if not isinstance(self.architecture_id, ArchitectureId):
            raise ValueError("architecture_id must be an ArchitectureId")
        if not isinstance(self.objective, ModelObjective):
            raise ValueError("objective must be a ModelObjective")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or not 0 <= self.seed <= 2**63 - 1:
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
        if self.context_window < 8:
            raise ValueError("context_window must be at least 8")
        if self.requested_parameters < 1_000:
            raise ValueError("requested_parameters must be at least 1000")
        if self.requested_epochs < 1 or self.requested_steps < 1:
            raise ValueError("training epochs and steps must be positive")
        if self.parent_model_id is not None and (
            not isinstance(self.parent_model_id, str) or not self.parent_model_id or len(self.parent_model_id) > 128
        ):
            raise ValueError("parent_model_id must be a bounded non-empty string when present")

    @property
    def request_id(self) -> str:
        encoded = json.dumps(
            {
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
            },
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

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported model artifact schema")
        if not isinstance(self.model_id, str) or not self.model_id or len(self.model_id) > 128:
            raise ValueError("model_id must be a bounded non-empty string")
        if not isinstance(self.organism_id, str) or not self.organism_id or len(self.organism_id) > 128:
            raise ValueError("organism_id must be a bounded non-empty string")
        for name, digest in (
            ("corpus_hash", self.corpus_hash),
            ("tokenizer_hash", self.tokenizer_hash),
            ("weights_hash", self.weights_hash),
        ):
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(f"{name} must be a lowercase sha256 digest")
        if not isinstance(self.architecture_id, ArchitectureId) or not isinstance(self.objective, ModelObjective):
            raise ValueError("invalid artifact architecture or objective")
        if isinstance(self.parameter_count, bool) or not isinstance(self.parameter_count, int) or self.parameter_count < 1:
            raise ValueError("parameter_count must be positive")
        if isinstance(self.context_window, bool) or not isinstance(self.context_window, int) or self.context_window < 1:
            raise ValueError("context_window must be positive")
        if isinstance(self.artifact_bytes, bool) or not isinstance(self.artifact_bytes, int) or self.artifact_bytes < 1:
            raise ValueError("artifact_bytes must be positive")
        if isinstance(self.created_tick_class, bool) or not isinstance(self.created_tick_class, int) or self.created_tick_class < 0:
            raise ValueError("created_tick_class must be non-negative")

    @classmethod
    def build(
        cls,
        *,
        request: TrainingRequest,
        parameter_count: int,
        weights_hash: str,
        artifact_bytes: int,
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
        if isinstance(corpus_records, bool) or not isinstance(corpus_records, int) or corpus_records < 3:
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
