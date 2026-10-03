"""Deterministic model registration and capability routing."""

from __future__ import annotations

from .model import GeneratedProposal, GenerativeContext, GenerativeModel
from .types import GenerativeOperation, GenerativeState, bounded_identifier


class GenerativeModelRegistry:
    """Routes queries to existing model owners without copying their state."""

    def __init__(self) -> None:
        self._models: dict[str, GenerativeModel] = {}

    @property
    def model_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._models))

    def register(self, model: GenerativeModel) -> None:
        if not isinstance(model, GenerativeModel):
            raise TypeError("model must implement the GenerativeModel protocol")
        model_id = bounded_identifier(model.model_id, name="model_id")
        if model_id in self._models:
            raise ValueError(f"model already registered: {model_id}")
        self._models[model_id] = model

    def unregister(self, model_id: str) -> None:
        bounded_identifier(model_id, name="model_id")
        self._models.pop(model_id, None)

    def available(
        self, *, operation: GenerativeOperation, state: GenerativeState
    ) -> tuple[str, ...]:
        return tuple(
            model_id
            for model_id in self.model_ids
            if self._models[model_id].supports(operation, state)
        )

    def query(
        self, *, operation: GenerativeOperation, state: GenerativeState, context: GenerativeContext
    ) -> tuple[GeneratedProposal, ...]:
        proposals: list[GeneratedProposal] = []
        for model_id in self.available(operation=operation, state=state):
            proposals.extend(
                self._models[model_id].generate(state=state, operation=operation, context=context)
            )
        return tuple(proposals)


__all__ = ["GenerativeModelRegistry"]
