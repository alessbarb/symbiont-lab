"""Revision Coherence §8.4 gate 2: append-only inherited vocabulary.

Every parent token keeps its id and inherited embedding/output rows in the
child; no parent token is lost; appended rows follow the child's seeded
initialisation; every other tensor is inherited exactly.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from lab.modeling.architectures import architecture_spec, build_model
from lab.modeling.trainer import _extend_vocabulary_state
from symbiont.modeling import ArchitectureId

PARENT_VOCAB, CHILD_VOCAB = 11, 15


def _model(vocab: int, seed: int):
    torch.manual_seed(seed)
    return build_model(
        ArchitectureId.GRU_V1,
        vocab_size=vocab,
        context_window=8,
        pad_id=0,
        spec=architecture_spec(ArchitectureId.GRU_V1),
    )


def test_child_inherits_every_parent_token_at_the_same_id():
    parent = _model(PARENT_VOCAB, seed=1)
    child = _model(CHILD_VOCAB, seed=2)
    seeded_child = {key: value.clone() for key, value in child.state_dict().items()}
    merged = _extend_vocabulary_state(parent.state_dict(), child.state_dict(), PARENT_VOCAB, torch)
    child.load_state_dict(merged, strict=True)
    after = child.state_dict()
    for key, value in parent.state_dict().items():
        if value.shape[0] == PARENT_VOCAB and after[key].shape[0] == CHILD_VOCAB:
            assert torch.equal(after[key][:PARENT_VOCAB], value)  # same ids, same rows
            assert torch.equal(after[key][PARENT_VOCAB:], seeded_child[key][PARENT_VOCAB:])
        else:
            assert torch.equal(after[key], value)
    assert after["embedding.weight"].shape[0] == CHILD_VOCAB
    assert after["output.weight"].shape[0] == CHILD_VOCAB  # untied projection expanded too


def test_appended_rows_are_deterministic_from_the_seed():
    parent = _model(PARENT_VOCAB, seed=1)
    first = _extend_vocabulary_state(
        parent.state_dict(), _model(CHILD_VOCAB, seed=9).state_dict(), PARENT_VOCAB, torch
    )
    second = _extend_vocabulary_state(
        parent.state_dict(), _model(CHILD_VOCAB, seed=9).state_dict(), PARENT_VOCAB, torch
    )
    assert all(torch.equal(first[key], second[key]) for key in first)


def test_a_child_can_never_lose_parent_tokens():
    parent = _model(PARENT_VOCAB, seed=1)
    smaller = _model(PARENT_VOCAB - 2, seed=2)
    with pytest.raises(ValueError):
        _extend_vocabulary_state(parent.state_dict(), smaller.state_dict(), PARENT_VOCAB, torch)
