from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from .proposals import ModelPredictionProposal, confidence_class
from .registry import ModelRegistry, ModelState
from .tokenizer import NativeTokenizer


@dataclass(frozen=True, slots=True)
class TokenPrediction:
    token_id: int
    probability: float

    def __post_init__(self) -> None:
        if isinstance(self.token_id, bool) or not isinstance(self.token_id, int) or self.token_id < 0:
            raise ValueError("token_id must be a non-negative integer")
        if isinstance(self.probability, bool) or not isinstance(self.probability, (int, float)):
            raise ValueError("probability must be numeric")
        if not math.isfinite(float(self.probability)) or not 0.0 <= float(self.probability) <= 1.0:
            raise ValueError("probability must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class ModelInferenceResult:
    model_id: str
    predictions: tuple[TokenPrediction, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.model_id, str) or not self.model_id or len(self.model_id) > 128:
            raise ValueError("model_id must be a bounded non-empty string")
        if not isinstance(self.predictions, tuple) or not 1 <= len(self.predictions) <= 16:
            raise ValueError("predictions must contain between 1 and 16 entries")
        if any(not isinstance(item, TokenPrediction) for item in self.predictions):
            raise ValueError("invalid prediction entry")
        if len({item.token_id for item in self.predictions}) != len(self.predictions):
            raise ValueError("prediction token ids must be unique")
        total = sum(float(item.probability) for item in self.predictions)
        if total > 1.000001:
            raise ValueError("reported top-k probabilities cannot sum above 1")


class PrivateModelGateway(Protocol):
    """Inference-only boundary implemented outside the organism package."""

    def infer(
        self,
        *,
        model_id: str,
        token_ids: tuple[int, ...],
        top_k: int = 4,
    ) -> ModelInferenceResult: ...


class PrivateModelBridge:
    """Converts a permitted model inference into a typed organism prediction.

    The bridge accepts SHADOW models for evaluator-only observation and ACTIVE
    models for organism-facing proposals. It never mutates evidence or memory.
    """

    def __init__(
        self,
        *,
        registry: ModelRegistry,
        tokenizer: NativeTokenizer,
        gateway: PrivateModelGateway,
    ) -> None:
        self._registry = registry
        self._tokenizer = tokenizer
        self._gateway = gateway

    def predict(
        self,
        context_tokens: tuple[str, ...],
        *,
        model_id: str,
        target_token: str = "<NEXT>",
        allow_shadow: bool = False,
    ) -> ModelPredictionProposal:
        record = self._registry.get(model_id)
        if record is None:
            raise ValueError("unknown model_id")
        allowed = {ModelState.ACTIVE}
        if allow_shadow:
            allowed.add(ModelState.SHADOW)
        if record.state not in allowed:
            raise ValueError("model is not eligible for this inference path")
        if record.tokenizer_hash != self._tokenizer.tokenizer_hash:
            raise ValueError("model tokenizer does not match bridge tokenizer")
        encoded = self._tokenizer.encode_tokens(context_tokens, max_sequence=512)
        if not encoded:
            raise ValueError("private model context must not be empty")
        result = self._gateway.infer(model_id=model_id, token_ids=encoded, top_k=4)
        if result.model_id != model_id:
            raise ValueError("gateway returned a different model identity")
        best = max(result.predictions, key=lambda item: (item.probability, -item.token_id))
        if best.token_id >= len(self._tokenizer.vocabulary):
            raise ValueError("gateway prediction exceeds tokenizer vocabulary")
        return ModelPredictionProposal(
            target_token=target_token,
            horizon_class=1,
            predicted_token=self._tokenizer.vocabulary[best.token_id],
            confidence_class=confidence_class(best.probability),
            model_id=model_id,
        )
