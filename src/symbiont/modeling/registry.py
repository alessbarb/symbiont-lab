from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Mapping

from .authority import ArchitectureId, ModelArtifactManifest, ModelObjective


class ModelState(str, Enum):
    CANDIDATE = "candidate"
    SHADOW = "shadow"
    ACTIVE = "active"
    DEGRADED = "degraded"
    RETIRED = "retired"


_ALLOWED_TRANSITIONS: dict[ModelState, frozenset[ModelState]] = {
    ModelState.CANDIDATE: frozenset({ModelState.SHADOW, ModelState.RETIRED}),
    ModelState.SHADOW: frozenset({ModelState.ACTIVE, ModelState.RETIRED}),
    ModelState.ACTIVE: frozenset({ModelState.DEGRADED, ModelState.RETIRED}),
    ModelState.DEGRADED: frozenset({ModelState.SHADOW, ModelState.RETIRED}),
    ModelState.RETIRED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class ModelRecord:
    model_id: str
    organism_id: str
    parent_model_id: str | None
    corpus_hash: str
    tokenizer_hash: str
    architecture_id: ArchitectureId
    parameter_count: int
    objective: ModelObjective
    state: ModelState
    created_tick_class: int
    artifact_hash: str
    evaluation_summary: tuple[int, ...] = ()
    generation: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.model_id, str) or not self.model_id or len(self.model_id) > 128:
            raise ValueError("model_id must be a bounded non-empty string")
        if not isinstance(self.organism_id, str) or not self.organism_id or len(self.organism_id) > 128:
            raise ValueError("organism_id must be a bounded non-empty string")
        if self.parent_model_id is not None and (
            not isinstance(self.parent_model_id, str) or not self.parent_model_id or len(self.parent_model_id) > 128
        ):
            raise ValueError("parent_model_id must be bounded when present")
        for name, digest in (
            ("corpus_hash", self.corpus_hash),
            ("tokenizer_hash", self.tokenizer_hash),
            ("artifact_hash", self.artifact_hash),
        ):
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(f"{name} must be a lowercase sha256 digest")
        if not isinstance(self.architecture_id, ArchitectureId):
            raise ValueError("invalid architecture_id")
        if not isinstance(self.objective, ModelObjective):
            raise ValueError("invalid objective")
        if not isinstance(self.state, ModelState):
            raise ValueError("invalid model state")
        if isinstance(self.parameter_count, bool) or not isinstance(self.parameter_count, int) or self.parameter_count < 1:
            raise ValueError("parameter_count must be positive")
        if isinstance(self.created_tick_class, bool) or not isinstance(self.created_tick_class, int) or self.created_tick_class < 0:
            raise ValueError("created_tick_class must be non-negative")
        if not isinstance(self.evaluation_summary, tuple) or len(self.evaluation_summary) > 16:
            raise ValueError("evaluation_summary must be a bounded tuple")
        if any(isinstance(value, bool) or not isinstance(value, int) or not -32768 <= value <= 32767
               for value in self.evaluation_summary):
            raise ValueError("evaluation summary entries must be bounded integers")
        if isinstance(self.generation, bool) or not isinstance(self.generation, int) or not 0 <= self.generation <= 256:
            raise ValueError("generation outside supported bounds")

    @classmethod
    def from_artifact(cls, artifact: ModelArtifactManifest) -> "ModelRecord":
        return cls(
            model_id=artifact.model_id,
            organism_id=artifact.organism_id,
            parent_model_id=artifact.parent_model_id,
            corpus_hash=artifact.corpus_hash,
            tokenizer_hash=artifact.tokenizer_hash,
            architecture_id=artifact.architecture_id,
            parameter_count=artifact.parameter_count,
            objective=artifact.objective,
            state=ModelState.CANDIDATE,
            created_tick_class=artifact.created_tick_class,
            artifact_hash=artifact.weights_hash,
            generation=artifact.generation,
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "organism_id": self.organism_id,
            "parent_model_id": self.parent_model_id,
            "corpus_hash": self.corpus_hash,
            "tokenizer_hash": self.tokenizer_hash,
            "architecture_id": self.architecture_id.value,
            "parameter_count": self.parameter_count,
            "objective": self.objective.value,
            "state": self.state.value,
            "created_tick_class": self.created_tick_class,
            "artifact_hash": self.artifact_hash,
            "evaluation_summary": list(self.evaluation_summary),
            "generation": self.generation,
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "ModelRecord":
        if not isinstance(payload, Mapping):
            raise ValueError("model record checkpoint must be an object")
        try:
            required_strings = (
                "model_id", "organism_id", "corpus_hash", "tokenizer_hash",
                "architecture_id", "objective", "state", "artifact_hash",
            )
            for key in required_strings:
                if not isinstance(payload.get(key), str):
                    raise ValueError(f"{key} must be a string")
            parent = payload.get("parent_model_id")
            if parent is not None and not isinstance(parent, str):
                raise ValueError("parent_model_id must be a string or null")
            parameter_count = payload.get("parameter_count")
            created_tick_class = payload.get("created_tick_class")
            if isinstance(parameter_count, bool) or not isinstance(parameter_count, int):
                raise ValueError("parameter_count must be an integer")
            if isinstance(created_tick_class, bool) or not isinstance(created_tick_class, int):
                raise ValueError("created_tick_class must be an integer")
            raw_summary = payload.get("evaluation_summary", [])
            if not isinstance(raw_summary, list) or any(
                isinstance(value, bool) or not isinstance(value, int) for value in raw_summary
            ):
                raise ValueError("evaluation_summary must be a list of integers")
            generation = payload.get("generation", 0)
            if isinstance(generation, bool) or not isinstance(generation, int):
                raise ValueError("generation must be an integer")
            return cls(
                model_id=payload["model_id"],
                organism_id=payload["organism_id"],
                parent_model_id=parent,
                corpus_hash=payload["corpus_hash"],
                tokenizer_hash=payload["tokenizer_hash"],
                architecture_id=ArchitectureId(payload["architecture_id"]),
                parameter_count=parameter_count,
                objective=ModelObjective(payload["objective"]),
                state=ModelState(payload["state"]),
                created_tick_class=created_tick_class,
                artifact_hash=payload["artifact_hash"],
                evaluation_summary=tuple(raw_summary),
                generation=generation,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid model record checkpoint") from exc


class ModelRegistry:
    """Bounded organism-local registry for acquired private-model phenotype."""

    SCHEMA_VERSION = 1

    def __init__(self, organism_id: str, *, max_models: int = 16) -> None:
        if not isinstance(organism_id, str) or not organism_id or len(organism_id) > 128:
            raise ValueError("organism_id must be a bounded non-empty string")
        if isinstance(max_models, bool) or not isinstance(max_models, int) or not 1 <= max_models <= 128:
            raise ValueError("max_models must be within [1, 128]")
        self._organism_id = organism_id
        self._max_models = max_models
        self._records: dict[str, ModelRecord] = {}

    @property
    def organism_id(self) -> str:
        return self._organism_id

    @property
    def records(self) -> tuple[ModelRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda record: (record.created_tick_class, record.model_id)))

    @property
    def active(self) -> ModelRecord | None:
        active = [record for record in self._records.values() if record.state is ModelState.ACTIVE]
        if len(active) > 1:
            raise RuntimeError("private model registry invariant violated: multiple active models")
        return active[0] if active else None

    def get(self, model_id: str) -> ModelRecord | None:
        return self._records.get(model_id)

    def register(self, artifact: ModelArtifactManifest) -> ModelRecord:
        if not isinstance(artifact, ModelArtifactManifest):
            raise ValueError("artifact must be a ModelArtifactManifest")
        if artifact.organism_id != self._organism_id:
            raise ValueError("private model artifact belongs to a different organism")
        if artifact.model_id in self._records:
            existing = self._records[artifact.model_id]
            if existing.artifact_hash != artifact.weights_hash:
                raise ValueError("model id collision with different artifact")
            return existing
        if len(self._records) >= self._max_models:
            removable = [record for record in self.records if record.state is ModelState.RETIRED]
            if not removable:
                raise ValueError("private model registry capacity exhausted")
            del self._records[removable[0].model_id]
        record = ModelRecord.from_artifact(artifact)
        self._records[record.model_id] = record
        return record

    def transition(
        self,
        model_id: str,
        state: ModelState,
        *,
        evaluation_summary: tuple[int, ...] | None = None,
        promotion_authorized: bool = False,
    ) -> ModelRecord:
        if model_id not in self._records:
            raise ValueError("unknown model_id")
        if not isinstance(state, ModelState):
            raise ValueError("state must be a ModelState")
        current = self._records[model_id]
        if state is current.state:
            return current
        if state not in _ALLOWED_TRANSITIONS[current.state]:
            raise ValueError(f"invalid model transition {current.state.value}->{state.value}")
        if state is ModelState.ACTIVE:
            if not promotion_authorized:
                raise ValueError("activation requires independent promotion authorization")
            for other_id, other in tuple(self._records.items()):
                if other_id != model_id and other.state is ModelState.ACTIVE:
                    self._records[other_id] = replace(other, state=ModelState.DEGRADED)
        summary = current.evaluation_summary if evaluation_summary is None else evaluation_summary
        updated = replace(current, state=state, evaluation_summary=summary)
        self._records[model_id] = updated
        return updated

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "organism_id": self._organism_id,
            "max_models": self._max_models,
            "records": [record.checkpoint() for record in self.records],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None, *, organism_id: str) -> "ModelRegistry":
        if payload is None:
            return cls(organism_id)
        if not isinstance(payload, Mapping) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid private model registry checkpoint")
        if payload.get("organism_id") != organism_id:
            raise ValueError("model registry checkpoint organism mismatch")
        max_models = payload.get("max_models", 16)
        if isinstance(max_models, bool) or not isinstance(max_models, int):
            raise ValueError("invalid model registry capacity")
        registry = cls(organism_id, max_models=max_models)
        raw_records = payload.get("records", [])
        if not isinstance(raw_records, list) or len(raw_records) > registry._max_models:
            raise ValueError("invalid model registry record list")
        for item in raw_records:
            record = ModelRecord.restore(item)
            if record.organism_id != organism_id or record.model_id in registry._records:
                raise ValueError("invalid or duplicate model registry record")
            registry._records[record.model_id] = record
        _ = registry.active
        return registry
