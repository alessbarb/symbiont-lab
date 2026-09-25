from __future__ import annotations

import io
from typing import Any

from symbiont.modeling.gateway import ModelInferenceResult, TokenPrediction

from .architectures import architecture_spec_from_manifest, build_model
from .artifacts import FileArtifactStore, ModelArtifact


def _torch() -> Any:
    try:
        import torch
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "private-model inference requires the optional 'modeling' dependency (torch)"
        ) from exc
    return torch


def load_artifact_model(
    artifact: ModelArtifact, *, vocab_size: int, pad_id: int = 0, device: str = "cpu"
):
    torch = _torch()
    model = build_model(
        artifact.manifest.architecture_id,
        vocab_size=vocab_size,
        context_window=artifact.manifest.context_window,
        pad_id=pad_id,
        spec=architecture_spec_from_manifest(artifact.manifest),
    )
    buffer = io.BytesIO(artifact.weights)
    try:
        state = torch.load(buffer, map_location="cpu", weights_only=True)
    except TypeError:  # pragma: no cover
        buffer.seek(0)
        state = torch.load(buffer, map_location="cpu")
    model.load_state_dict(state, strict=True)
    model.to(torch.device(device))
    model.eval()
    return model


class ArtifactInferenceGateway:
    """Read-only inference over verified content-addressed model artifacts."""

    def __init__(
        self,
        store: FileArtifactStore,
        *,
        vocab_size: int,
        pad_id: int = 0,
        device: str = "cpu",
    ) -> None:
        if (
            isinstance(vocab_size, bool)
            or not isinstance(vocab_size, int)
            or not 8 <= vocab_size <= 8192
        ):
            raise ValueError("vocab_size must be within [8, 8192]")
        self._store = store
        self._vocab_size = vocab_size
        self._pad_id = pad_id
        self._device = device
        self._artifact_cache: dict[str, ModelArtifact] = {}
        self._cache: dict[str, object] = {}

    def _artifact(self, model_id: str) -> ModelArtifact:
        artifact = self._artifact_cache.get(model_id)
        if artifact is None:
            artifact = self._store.get(model_id)
            self._artifact_cache[model_id] = artifact
        return artifact

    def _model(self, model_id: str):
        if model_id not in self._cache:
            artifact = self._artifact(model_id)
            self._cache[model_id] = load_artifact_model(
                artifact,
                vocab_size=self._vocab_size,
                pad_id=self._pad_id,
                device=self._device,
            )
        return self._cache[model_id]

    def warm(self, model_id: str) -> None:
        """Load and verify one model once before latency-sensitive inference."""
        self._model(model_id)

    def infer(
        self,
        *,
        model_id: str,
        token_ids: tuple[int, ...],
        top_k: int = 4,
    ) -> ModelInferenceResult:
        if not isinstance(token_ids, tuple) or not token_ids:
            raise ValueError("token_ids must be a non-empty tuple")
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value < self._vocab_size
            for value in token_ids
        ):
            raise ValueError("token_ids contain values outside vocabulary")
        if (
            isinstance(top_k, bool)
            or not isinstance(top_k, int)
            or not 1 <= top_k <= min(16, self._vocab_size)
        ):
            raise ValueError("top_k outside supported bounds")
        artifact = self._artifact(model_id)
        context = token_ids[-artifact.manifest.context_window :]
        torch = _torch()
        model = self._model(model_id)
        device = next(model.parameters()).device
        input_ids = torch.tensor([context], dtype=torch.long, device=device)
        attention = torch.ones_like(input_ids, dtype=torch.bool)
        with torch.no_grad():
            logits = model(input_ids, attention_mask=attention)[0, -1]
            probabilities = torch.softmax(logits, dim=-1)
            values, indices = torch.topk(probabilities, k=top_k)
        predictions = tuple(
            TokenPrediction(int(index), float(value))
            for value, index in zip(values.detach().cpu().tolist(), indices.detach().cpu().tolist())
        )
        return ModelInferenceResult(model_id=model_id, predictions=predictions)
