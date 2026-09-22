from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from symbiont.modeling.authority import ArchitectureId, ModelArtifactManifest


@dataclass(frozen=True, slots=True)
class ArchitectureSpec:
    architecture_id: ArchitectureId
    embedding_dim: int
    hidden_dim: int
    layers: int
    heads: int
    feedforward_dim: int
    dropout: float

    def __post_init__(self) -> None:
        if not isinstance(self.architecture_id, ArchitectureId):
            raise ValueError("architecture_id must be an ArchitectureId")
        for name, value, low, high in (
            ("embedding_dim", self.embedding_dim, 16, 1024),
            ("hidden_dim", self.hidden_dim, 16, 2048),
            ("layers", self.layers, 1, 16),
            ("heads", self.heads, 1, 32),
            ("feedforward_dim", self.feedforward_dim, 16, 8192),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"{name} outside supported bounds")
        if not isinstance(self.dropout, (int, float)) or isinstance(self.dropout, bool) or not 0.0 <= float(self.dropout) <= 0.5:
            raise ValueError("dropout must be within [0, 0.5]")
        if self.architecture_id is ArchitectureId.TRANSFORMER_V1 and self.embedding_dim % self.heads != 0:
            raise ValueError("transformer embedding_dim must be divisible by heads")


class ArchitectureCapacityError(ValueError):
    """No valid member of an architecture family fits the authorized budget."""


_SPECS: dict[ArchitectureId, ArchitectureSpec] = {
    ArchitectureId.GRU_V1: ArchitectureSpec(
        ArchitectureId.GRU_V1, embedding_dim=96, hidden_dim=192, layers=2, heads=1, feedforward_dim=192, dropout=0.10
    ),
    ArchitectureId.TRANSFORMER_V1: ArchitectureSpec(
        ArchitectureId.TRANSFORMER_V1, embedding_dim=128, hidden_dim=128, layers=4, heads=4, feedforward_dim=512, dropout=0.10
    ),
}


def architecture_spec(architecture_id: ArchitectureId) -> ArchitectureSpec:
    if not isinstance(architecture_id, ArchitectureId):
        raise ValueError("architecture_id must be an ArchitectureId")
    return _SPECS[architecture_id]


def _gru_parameter_count(*, vocab_size: int, embedding_dim: int, hidden_dim: int, layers: int) -> int:
    recurrent = (
        3 * hidden_dim * embedding_dim
        + (6 * layers - 3) * hidden_dim * hidden_dim
        + (6 * layers) * hidden_dim
    )
    layer_norm = 2 * hidden_dim
    vocabulary = vocab_size * embedding_dim + vocab_size * hidden_dim + vocab_size
    return recurrent + layer_norm + vocabulary


def resolve_architecture_spec(
    architecture_id: ArchitectureId, *, vocab_size: int, parameter_ceiling: int
) -> ArchitectureSpec:
    """Resolve the largest deterministic family member that fits a hard ceiling."""
    if isinstance(vocab_size, bool) or not isinstance(vocab_size, int) or not 8 <= vocab_size <= 8192:
        raise ValueError("vocab_size must be within [8, 8192]")
    if isinstance(parameter_ceiling, bool) or not isinstance(parameter_ceiling, int) or parameter_ceiling < 1_000:
        raise ValueError("parameter_ceiling must be at least 1000")
    base = architecture_spec(architecture_id)
    if architecture_id is not ArchitectureId.GRU_V1:
        return base
    candidates: list[tuple[int, int, int]] = []
    for hidden_dim in range(base.hidden_dim, 15, -16):
        for embedding_dim in range(base.embedding_dim, 15, -16):
            count = _gru_parameter_count(
                vocab_size=vocab_size, embedding_dim=embedding_dim, hidden_dim=hidden_dim, layers=base.layers
            )
            if count <= parameter_ceiling:
                candidates.append((count, hidden_dim, embedding_dim))
    if not candidates:
        minimum = _gru_parameter_count(vocab_size=vocab_size, embedding_dim=16, hidden_dim=16, layers=base.layers)
        raise ArchitectureCapacityError(
            f"gru-v1 minimum parameter count {minimum} exceeds authorized ceiling {parameter_ceiling}"
        )
    _, hidden_dim, embedding_dim = max(candidates)
    return ArchitectureSpec(
        ArchitectureId.GRU_V1,
        embedding_dim=embedding_dim,
        hidden_dim=hidden_dim,
        layers=base.layers,
        heads=base.heads,
        feedforward_dim=hidden_dim,
        dropout=base.dropout,
    )


def architecture_spec_from_manifest(manifest: ModelArtifactManifest) -> ArchitectureSpec:
    base = architecture_spec(manifest.architecture_id)
    values = (manifest.resolved_embedding_dim, manifest.resolved_hidden_dim, manifest.resolved_layers, manifest.resolved_heads, manifest.resolved_feedforward_dim)
    if all(value is None for value in values):
        return base
    if any(value is None for value in values):
        raise ValueError("artifact contains incomplete resolved architecture shape")
    return ArchitectureSpec(
        manifest.architecture_id,
        embedding_dim=int(manifest.resolved_embedding_dim),
        hidden_dim=int(manifest.resolved_hidden_dim),
        layers=int(manifest.resolved_layers),
        heads=int(manifest.resolved_heads),
        feedforward_dim=int(manifest.resolved_feedforward_dim),
        dropout=base.dropout,
    )


def _torch() -> Any:
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise RuntimeError("private-model training requires the optional modeling dependency (torch)") from exc
    return torch, nn


def build_model(architecture_id: ArchitectureId, *, vocab_size: int, context_window: int, pad_id: int = 0, spec: ArchitectureSpec | None = None):
    if isinstance(vocab_size, bool) or not isinstance(vocab_size, int) or not 8 <= vocab_size <= 8192:
        raise ValueError("vocab_size must be within [8, 8192]")
    if isinstance(context_window, bool) or not isinstance(context_window, int) or not 8 <= context_window <= 512:
        raise ValueError("context_window must be within [8, 512]")
    if isinstance(pad_id, bool) or not isinstance(pad_id, int) or not 0 <= pad_id < vocab_size:
        raise ValueError("pad_id outside vocabulary")
    torch, nn = _torch()
    resolved = spec or architecture_spec(architecture_id)
    if resolved.architecture_id is not architecture_id:
        raise ValueError("architecture spec does not match architecture id")
    if architecture_id is ArchitectureId.GRU_V1:
        class CausalGRU(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.embedding = nn.Embedding(vocab_size, resolved.embedding_dim, padding_idx=pad_id)
                self.gru = nn.GRU(resolved.embedding_dim, resolved.hidden_dim, num_layers=resolved.layers, batch_first=True, dropout=resolved.dropout if resolved.layers > 1 else 0.0)
                self.norm = nn.LayerNorm(resolved.hidden_dim)
                self.output = nn.Linear(resolved.hidden_dim, vocab_size)
            def forward(self, token_ids, attention_mask=None):
                embedded = self.embedding(token_ids)
                hidden, _ = self.gru(embedded)
                return self.output(self.norm(hidden))
        return CausalGRU()
    if architecture_id is ArchitectureId.TRANSFORMER_V1:
        class CausalTransformer(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.embedding = nn.Embedding(vocab_size, resolved.embedding_dim, padding_idx=pad_id)
                self.position = nn.Embedding(context_window, resolved.embedding_dim)
                layer = nn.TransformerEncoderLayer(d_model=resolved.embedding_dim, nhead=resolved.heads, dim_feedforward=resolved.feedforward_dim, dropout=resolved.dropout, activation="gelu", batch_first=True, norm_first=True)
                self.encoder = nn.TransformerEncoder(layer, num_layers=resolved.layers)
                self.norm = nn.LayerNorm(resolved.embedding_dim)
                self.output = nn.Linear(resolved.embedding_dim, vocab_size)
            def forward(self, token_ids, attention_mask=None):
                batch, seq = token_ids.shape
                positions = torch.arange(seq, device=token_ids.device).unsqueeze(0).expand(batch, seq)
                hidden = self.embedding(token_ids) + self.position(positions)
                causal_mask = torch.triu(torch.ones(seq, seq, dtype=torch.bool, device=token_ids.device), diagonal=1)
                padding_mask = None if attention_mask is None else ~attention_mask.bool()
                hidden = self.encoder(hidden, mask=causal_mask, src_key_padding_mask=padding_mask)
                return self.output(self.norm(hidden))
        return CausalTransformer()
    raise ValueError(f"unsupported architecture {architecture_id}")


def count_parameters(model: Any) -> int:
    return sum(int(parameter.numel()) for parameter in model.parameters())
