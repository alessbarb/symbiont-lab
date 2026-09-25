"""Internal state equivalence for bounded branch pruning."""

from __future__ import annotations

from .types import GenerativeState


def state_equivalence_key(state: GenerativeState) -> tuple[object, ...]:
    """Build an identity-free key from organism-owned generated structure."""

    features = tuple((item.token, item.value_class) for item in state.features)
    return (
        features,
        state.active_concept_ids,
        state.relation_refs,
    )


def equivalent_states(left: GenerativeState, right: GenerativeState) -> bool:
    return state_equivalence_key(left) == state_equivalence_key(right)


__all__ = ["equivalent_states", "state_equivalence_key"]
