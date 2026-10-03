"""Canonical organism profile: the one place where evidence-conditioned options live.

Every option a closed scientific result can condition is a field here. A profile
version is immutable once an experiment has run under it; a new result that moves
a value creates a new version instead of editing an old one (ADR-0062). The human
register, with the result backing each value, is
``docs/design/core/canonical-organism-profile-v1.md``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields, replace
from typing import Any

from symbiont.core.domains.intention import IntentionPolicy

# How an organism's symbol policy seed is chosen.
SYMBOL_SEED_SHARED = "shared"  # every organism uses the same seed (historical)
SYMBOL_SEED_PER_ORGANISM = "per_organism"  # derived from the organism's own identity


@dataclass(frozen=True)
class OrganismProfile:
    """Evidence-conditioned configuration of one organism, valid in every scope."""

    version: str
    discover_senses: bool
    bootstrap_semantic_senses: bool
    sensory_plasticity: bool
    auto_promote_predictors: bool
    interoception_mode: str
    factorized_effects: bool
    reconcile_observed_effects: bool
    executive_outcome_learning: bool
    footprint_satisfaction_rule: str
    symbol_seed_policy: str
    ancestry_training: bool
    competence_min_support: int
    competence_min_consistency: float
    retention_price_baseline: float
    retention_price_node: float
    dormancy_retention_factor: float

    def runtime_kwargs(self) -> dict[str, Any]:
        """Keyword arguments for ``OrganismRuntime`` that realise this profile."""
        return {
            "discover_senses": self.discover_senses,
            "bootstrap_semantic_senses": self.bootstrap_semantic_senses,
            "sensory_plasticity": self.sensory_plasticity,
            "auto_promote_predictors": self.auto_promote_predictors,
            "interoception_mode": self.interoception_mode,
            "factorized_effects": self.factorized_effects,
            "intention_policy": self.intention_policy(),
            "competence_min_support": self.competence_min_support,
            "competence_min_consistency": self.competence_min_consistency,
            "retention_price_baseline": self.retention_price_baseline,
            "retention_price_node": self.retention_price_node,
            "dormancy_retention_factor": self.dormancy_retention_factor,
        }

    def intention_policy(self) -> IntentionPolicy:
        return IntentionPolicy(
            reconcile_observed_effects=self.reconcile_observed_effects,
            executive_outcome_learning=self.executive_outcome_learning,
            footprint_satisfaction_rule=self.footprint_satisfaction_rule,
        )


# Options of ``OrganismRuntime`` / ``ModeledOrganismRuntime`` / ``IntentionPolicy``
# governed by the profile. A launcher that passes one of these explicitly deviates.
GOVERNED_OPTIONS: frozenset[str] = frozenset(
    {field.name for field in fields(OrganismProfile)} - {"version", "symbol_seed_policy"}
    | {"interoception_enabled", "symbol_policy_seed"}
)

# The configuration the bare constructors produced before any convergence. Closed
# experiments that relied on constructor defaults ran under this version.
HISTORICAL_V0 = OrganismProfile(
    version="v0-historical",
    discover_senses=False,
    bootstrap_semantic_senses=True,
    sensory_plasticity=False,
    auto_promote_predictors=False,
    interoception_mode="enabled",
    factorized_effects=False,
    reconcile_observed_effects=True,
    executive_outcome_learning=True,
    footprint_satisfaction_rule="recall",
    symbol_seed_policy=SYMBOL_SEED_SHARED,
    ancestry_training=False,
    competence_min_support=2,
    competence_min_consistency=0.60,
    retention_price_baseline=0.001,
    retention_price_node=0.0005,
    dormancy_retention_factor=1.0,
)

# Convergence of the results closed up to 2026-10-02 (register §3, ADR-0062).
V1 = replace(
    HISTORICAL_V0,
    version="v1",
    discover_senses=True,
    bootstrap_semantic_senses=False,
    sensory_plasticity=True,
    auto_promote_predictors=True,
    interoception_mode="absent",
    symbol_seed_policy=SYMBOL_SEED_PER_ORGANISM,
)

PROFILES: dict[str, OrganismProfile] = {profile.version: profile for profile in (HISTORICAL_V0, V1)}

# The profile every new organism is born with.
CANONICAL = V1


def symbol_seed_for(profile: OrganismProfile, organism_id: str) -> int:
    """Symbol policy seed of one organism under ``profile``."""
    if profile.symbol_seed_policy == SYMBOL_SEED_SHARED:
        return 0
    digest = hashlib.sha256(f"symbol-policy-seed:{organism_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") & (2**31 - 1)


__all__ = [
    "CANONICAL",
    "GOVERNED_OPTIONS",
    "HISTORICAL_V0",
    "PROFILES",
    "SYMBOL_SEED_PER_ORGANISM",
    "SYMBOL_SEED_SHARED",
    "V1",
    "OrganismProfile",
    "symbol_seed_for",
]
