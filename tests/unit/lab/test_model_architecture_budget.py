from __future__ import annotations

from symbiont.modeling import ArchitectureId
from symbiont_lab.modeling.architectures import (
    _gru_parameter_count,
    architecture_spec,
    resolve_architecture_spec,
)


def test_gru_family_shrinks_to_fit_vocab_under_fixed_budget():
    vocab_size = 3000
    ceiling = 1_000_000
    base = architecture_spec(ArchitectureId.GRU_V1)
    base_count = _gru_parameter_count(
        vocab_size=vocab_size,
        embedding_dim=base.embedding_dim,
        hidden_dim=base.hidden_dim,
        layers=base.layers,
    )
    assert base_count > ceiling

    resolved = resolve_architecture_spec(
        ArchitectureId.GRU_V1,
        vocab_size=vocab_size,
        parameter_ceiling=ceiling,
    )
    resolved_count = _gru_parameter_count(
        vocab_size=vocab_size,
        embedding_dim=resolved.embedding_dim,
        hidden_dim=resolved.hidden_dim,
        layers=resolved.layers,
    )

    assert resolved_count <= ceiling
    assert resolved.hidden_dim <= base.hidden_dim
    assert resolved.embedding_dim <= base.embedding_dim
    assert resolved.layers == base.layers


def test_gru_family_preserves_default_shape_when_it_already_fits():
    base = architecture_spec(ArchitectureId.GRU_V1)
    resolved = resolve_architecture_spec(
        ArchitectureId.GRU_V1,
        vocab_size=64,
        parameter_ceiling=1_000_000,
    )
    assert resolved == base
