"""Hard, owner-configured somatic and resource limits for Symbiont.

Analogous to :class:`symbiont.cognition.limits.KernelLimits`, these boundaries
represent physical and computational capacity ceilings (memory, byte budgets,
collection cardinalities, and growth protection).

They deliberately exclude temporal dynamics, maturation rates, decay intervals,
or homeostatic thresholds, which belong to physiology or epistemic conventions.
"""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(slots=True, frozen=True)
class OrganismLimits:
    """Hard resource and security ceilings for somatic and host runtime state."""

    # Storage and checkpoint byte caps
    max_host_checkpoint_bytes: int = 2 * 1024 * 1024
    max_knowledge_checkpoint_bytes: int = 256 * 1024
    max_exchange_bytes: int = 4096

    # Body schema & somatic topology limits
    max_sensory_parts: int = 512
    max_cognitive_regions: int = 128
    max_body_dependencies: int = 1024
    max_dependency_evidence: int = 6144
    max_coactivity_candidates: int = 4096
    max_cognitive_channels_per_tick: int = 128

    # Behavior and action limits
    max_action_kinds: int = 64
    max_action_ids: int = 256
    max_selection_opportunities: int = 256

    # Degradation queue capacity (physical capacity only, not timing)
    max_degradation_items: int = 256

    # Evidence and dissent retention
    max_dissent: int = 256

    # Inheritance channels
    max_epigenetic_priors: int = 16
    max_cultural_artifacts: int = 32

    # Host sensory acclimation & discovery
    max_capabilities: int = 512
    max_candidate_senses: int = 1024
    max_relations: int = 4096
    max_rhythm_contexts: int = 1024
    max_trust_contexts: int = 1024

    # Endogenous signal knowledge
    max_knowledge_profiles: int = 64
    max_knowledge_claims: int = 192
    max_knowledge_claims_per_signal: int = 4
    max_pending_trials: int = 128

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field.name} must be a positive integer")

    @property
    def max_body_parts(self) -> int:
        """Derived ceiling for total distinct body parts."""
        return self.max_sensory_parts + self.max_cognitive_regions

    @property
    def max_cognitive_channel_candidates(self) -> int:
        return self.max_cognitive_channels_per_tick * 4


__all__ = ["OrganismLimits"]
