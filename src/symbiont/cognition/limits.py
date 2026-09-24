from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(slots=True, frozen=True)
class KernelLimits:
    """Hard, owner-configured resource ceilings for the cognitive graph
    (master doc §7.4). Never part of a genome and never learnable (§4.1,
    §13 invariant 1) -- a genome's soft budgets are validated against
    these but can never exceed them."""

    # Safety ceilings only. Developmental budgets start much lower in the
    # genome and may expand endogenously when sustained evidence justifies it.
    max_nodes: int = 768
    max_concepts: int = 192
    max_edges: int = 6144
    max_tentative_edges: int = 512
    max_structural_mutations_per_consolidation: int = 16
    consolidation_interval_ticks: int = 32
    max_plastic_checkpoint_bytes: int = 8 * 1024 * 1024
    max_consolidation_candidates: int = 1024
    max_salient_event_traces: int = 64
    consolidation_epoch_ticks: int = 8
    slow_support_epochs: int = 4
    fast_consolidation_threshold: float = 0.80
    fast_min_reliability: float = 0.60
    max_incoming_consolidated_weight_norm: float = 8.0
    reacclimation_ticks: int = 32

    # Resident episodic-experience memory. These are kernel ceilings, never
    # organism-learnable parameters. The memory stores only opaque tokens
    # already available to the organism, never lab/world ground truth.
    max_episodic_episodes: int = 4096
    max_episodic_episode_records: int = 32
    max_episodic_retrieval_candidates: int = 64
    max_episodic_replay_items: int = 16
    max_episodic_interpretations_per_episode: int = 128
    max_episodic_checkpoint_bytes: int = 2 * 1024 * 1024
    episodic_epoch_ticks: int = 32
    episodic_min_consolidation_epochs: int = 3

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if value <= 0:
                raise ValueError(f"{field.name} must be positive")
        if self.max_episodic_episode_records > 256:
            raise ValueError(
                "max_episodic_episode_records must be <= 256"
            )
        if (
            self.max_episodic_replay_items
            > self.max_episodic_retrieval_candidates
        ):
            raise ValueError(
                "max_episodic_replay_items must be <= "
                "max_episodic_retrieval_candidates"
            )
