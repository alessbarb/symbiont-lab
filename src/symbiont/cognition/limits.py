from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(slots=True, frozen=True)
class KernelLimits:
    """Hard, owner-configured resource ceilings for the cognitive graph
    (master doc §7.4). Never part of a genome and never learnable (§4.1,
    §13 invariant 1) -- a genome's soft budgets are validated against
    these but can never exceed them."""

    max_nodes: int = 128
    max_concepts: int = 32
    max_edges: int = 1024
    max_tentative_edges: int = 128
    max_structural_mutations_per_consolidation: int = 8
    consolidation_interval_ticks: int = 32
    max_plastic_checkpoint_bytes: int = 2 * 1024 * 1024

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if value <= 0:
                raise ValueError(f"{field.name} must be positive")
