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
    max_tentative_edges: int = BASELINE_KERNEL.max_tentative_edges
    max_structural_mutations_per_consolidation: int = BASELINE_KERNEL.max_structural_mutations_per_consolidation
    consolidation_interval_ticks: int = BASELINE_KERNEL.consolidation_interval_ticks
    consolidation_epoch_ticks: int = BASELINE_KERNEL.consolidation_epoch_ticks
    slow_support_epochs: int = BASELINE_KERNEL.slow_support_epochs
    fast_consolidation_threshold: float = BASELINE_KERNEL.fast_consolidation_threshold
    fast_min_reliability: float = BASELINE_KERNEL.fast_min_reliability
    max_consolidation_candidates: int = BASELINE_KERNEL.max_consolidation_candidates
    max_salient_event_traces: int = BASELINE_KERNEL.max_salient_event_traces
    max_incoming_consolidated_weight_norm: float = BASELINE_KERNEL.max_incoming_consolidated_weight_norm
    reacclimation_ticks: int = BASELINE_KERNEL.reacclimation_ticks

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if value <= 0:
                raise ValueError(f"{field.name} must be positive")
            if field.name in {"fast_consolidation_threshold", "fast_min_reliability"} and value > 1:
                raise ValueError(f"{field.name} must be within (0, 1]")

    def limits(self) -> KernelLimits:
        return replace(
            BASELINE_KERNEL,
            max_nodes=self.max_nodes,
            max_edges=self.max_edges,
            max_concepts=self.max_concepts,
            max_tentative_edges=self.max_tentative_edges,
            max_structural_mutations_per_consolidation=self.max_structural_mutations_per_consolidation,
            consolidation_interval_ticks=self.consolidation_interval_ticks,
            consolidation_epoch_ticks=self.consolidation_epoch_ticks,
            slow_support_epochs=self.slow_support_epochs,
            fast_consolidation_threshold=self.fast_consolidation_threshold,
            fast_min_reliability=self.fast_min_reliability,
            max_consolidation_candidates=self.max_consolidation_candidates,
            max_salient_event_traces=self.max_salient_event_traces,
            max_incoming_consolidated_weight_norm=self.max_incoming_consolidated_weight_norm,
            reacclimation_ticks=self.reacclimation_ticks,
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "max_nodes": self.max_nodes,
            "max_edges": self.max_edges,
            "max_concepts": self.max_concepts,
            "max_tentative_edges": self.max_tentative_edges,
            "max_structural_mutations_per_consolidation": self.max_structural_mutations_per_consolidation,
            "consolidation_interval_ticks": self.consolidation_interval_ticks,
            "consolidation_epoch_ticks": self.consolidation_epoch_ticks,
            "slow_support_epochs": self.slow_support_epochs,
            "fast_consolidation_threshold": self.fast_consolidation_threshold,
            "fast_min_reliability": self.fast_min_reliability,
            "max_consolidation_candidates": self.max_consolidation_candidates,
            "max_salient_event_traces": self.max_salient_event_traces,
            "max_incoming_consolidated_weight_norm": self.max_incoming_consolidated_weight_norm,
            "reacclimation_ticks": self.reacclimation_ticks,
        }


def complete_kernel(limits: KernelLimits) -> dict[str, int | float]:
    """Serialize every kernel field for a reproducible run manifest."""
    return {field.name: getattr(limits, field.name) for field in fields(limits)}
