from __future__ import annotations

from dataclasses import dataclass

import pytest

from symbiont.cognition.generative import (
    EpistemicOrigin,
    GeneratedFeature,
    GeneratedProposal,
    GenerativeContext,
    GenerativeModelRegistry,
    GenerativeOperation,
    GenerativeState,
)


def state() -> GenerativeState:
    return GenerativeState(
        "s0", "e0", EpistemicOrigin.INFERRED, None, 0, (), (), (), (), (), (), 0.4, 0.8, 0
    )


@dataclass
class Model:
    model_id: str

    def supports(self, operation, state):
        return operation is GenerativeOperation.PREDICT

    def generate(self, *, state, operation, context):
        return (
            GeneratedProposal(
                (GeneratedFeature("next", None, 0.5, self.model_id),),
                ("outcome",),
                0.5,
                0.8,
                self.model_id,
                context.references,
            ),
        )


def test_registry_routes_only_capable_models_in_stable_order():
    registry = GenerativeModelRegistry()
    registry.register(Model("model-b"))
    registry.register(Model("model-a"))
    result = registry.query(
        operation=GenerativeOperation.PREDICT,
        state=state(),
        context=GenerativeContext(references=("s0",)),
    )
    assert [item.model_id for item in result] == ["model-a", "model-b"]


def test_registry_rejects_duplicates_and_protocol_violations():
    registry = GenerativeModelRegistry()
    registry.register(Model("model-a"))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Model("model-a"))
    with pytest.raises(TypeError):
        registry.register(object())
