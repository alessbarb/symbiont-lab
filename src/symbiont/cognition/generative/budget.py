"""Explicit engineering limits for one generative workspace."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GenerativeBudget:
    max_states: int = 64
    max_transitions: int = 64
    max_depth: int = 8
    max_branches: int = 8
    max_model_queries: int = 128

    def __post_init__(self) -> None:
        for name in (
            "max_states",
            "max_transitions",
            "max_depth",
            "max_branches",
            "max_model_queries",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


__all__ = ["GenerativeBudget"]
