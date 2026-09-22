from __future__ import annotations

from dataclasses import dataclass, fields, replace

from symbiont.cognition.limits import KernelLimits


BASELINE_KERNEL = KernelLimits()


@dataclass(frozen=True, slots=True)
class KernelVariant:
    """An experiment-local kernel variant.

    Only the capacity under study is varied in K1. All other limits are copied
    from the current canonical kernel so a result cannot silently mix several
    interventions.
    """

    max_nodes: int
    max_edges: int = BASELINE_KERNEL.max_edges
    max_concepts: int = BASELINE_KERNEL.max_concepts

    def __post_init__(self) -> None:
        for field in fields(self):
            if getattr(self, field.name) <= 0:
                raise ValueError(f"{field.name} must be positive")

    def limits(self) -> KernelLimits:
        return replace(
            BASELINE_KERNEL,
            max_nodes=self.max_nodes,
            max_edges=self.max_edges,
            max_concepts=self.max_concepts,
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "max_nodes": self.max_nodes,
            "max_edges": self.max_edges,
            "max_concepts": self.max_concepts,
        }


def complete_kernel(limits: KernelLimits) -> dict[str, int | float]:
    """Serialize every kernel field for a reproducible run manifest."""
    return {field.name: getattr(limits, field.name) for field in fields(limits)}
