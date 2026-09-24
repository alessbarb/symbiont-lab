"""Auditable Genome v2 locus-to-runtime binding registry."""
from __future__ import annotations

from dataclasses import dataclass

from .schema import DEFAULT_GENOME_SCHEMA


@dataclass(frozen=True, slots=True)
class GeneBinding:
    locus: str
    consumer_id: str
    observable_projection: str
    mutation_test_id: str


# Rules are intentionally non-overlapping. Every canonical locus must match
# exactly one rule or Genome v2 fails its constitutional self-check.
_BINDING_RULES: tuple[tuple[str, str, str, str], ...] = (
    ("development.soft_node_budget", "cognition.capacity.node_ceiling", "cognition.node_capacity", "test_developmental_capacity_ceilings"),
    ("development.soft_edge_budget", "cognition.capacity.edge_ceiling", "cognition.edge_capacity", "test_developmental_capacity_ceilings"),
    ("development.sense_node_budget", "cognition.capacity.sense_ceiling", "cognition.sense_capacity", "test_developmental_capacity_ceilings"),
    ("development.capacity_growth_sensitivity", "cognition.capacity.growth_rate", "cognition.capacity_growth", "test_capacity_growth_sensitivity_changes_trajectory"),
    ("development.consolidation_interval_ticks", "cognition.consolidation.interval", "cognition.consolidation_interval", "test_consolidation_interval_is_consumed"),
    ("plasticity.learning_rate.", "expression.learning_rate", "expression.effective_learning_rate", "test_learning_rate_expression_is_causal"),
    ("plasticity.forgetting_rate.", "expression.forgetting_rate", "expression.effective_forgetting_rate", "test_forgetting_expression_is_causal"),
    ("plasticity.eligibility_decay", "cognition.learning.eligibility", "cognition.eligibility_decay", "test_eligibility_decay_is_consumed"),
    ("plasticity.structural_plasticity.", "expression.structural_plasticity", "expression.effective_structural_plasticity", "test_structural_plasticity_expression_is_causal"),
    ("plasticity.consolidation_sensitivity.", "expression.consolidation_sensitivity", "expression.effective_consolidation_sensitivity", "test_consolidation_expression_is_causal"),
    ("regulation.", "expression.regulator", "expression.regulatory_activation", "test_regulation_is_next_tick_causal"),
    ("sensorimotor.spontaneous_activity_baseline", "motor.exploration", "expression.exploration_drive", "test_spontaneous_activity_changes_motor_sampling"),
    ("sensorimotor.uncertainty_exploration_gain", "expression.exploration", "expression.exploration_drive", "test_uncertainty_changes_exploration"),
    ("sensorimotor.prediction_error_exploration_gain", "expression.exploration", "expression.exploration_drive", "test_prediction_error_changes_exploration"),
    ("sensorimotor.exploration_habituation", "expression.exploration", "expression.exploration_drive", "test_exploration_habituation_is_causal"),
    ("sensorimotor.contingency_sensitivity", "sensorimotor.contingency", "expression.contingency_sensitivity", "test_contingency_sensitivity_is_causal"),
    ("sensorimotor.contingency_window_ticks", "sensorimotor.contingency_window", "sensorimotor.contingency_window", "test_contingency_window_is_consumed"),
    ("sensorimotor.controllability_sensitivity", "sensorimotor.controllability", "sensorimotor.controllability_sensitivity", "test_controllability_sensitivity_is_consumed"),
    ("sensorimotor.body_schema_adaptation_rate", "body_schema.adaptation", "expression.body_schema_adaptation", "test_body_schema_adaptation_is_causal"),
    ("sensorimotor.reacclimation_sensitivity", "expression.reacclimation", "expression.exploration_drive", "test_reacclimation_sensitivity_is_causal"),
    ("structure.growth_threshold.", "expression.growth_threshold", "expression.effective_growth_threshold", "test_growth_threshold_is_causal"),
    ("structure.pruning_threshold.", "expression.pruning_threshold", "expression.effective_pruning_threshold", "test_pruning_threshold_is_causal"),
    ("structure.minimum_support", "cognition.structure.support_gate", "cognition.minimum_support", "test_minimum_support_is_consumed"),
    ("structure.tentative_lifetime_ticks", "cognition.structure.lifetime", "cognition.tentative_lifetime", "test_tentative_lifetime_is_consumed"),
    ("structure.complexity_pressure.", "expression.complexity_pressure", "expression.regulatory_activation", "test_complexity_pressure_is_causal"),
    ("evolvability.development_mutation_scale", "genetics.mutation.development_multiplier", "lineage.mutation_delta", "test_family_mutation_multiplier"),
    ("evolvability.plasticity_mutation_scale", "genetics.mutation.plasticity_multiplier", "lineage.mutation_delta", "test_family_mutation_multiplier"),
    ("evolvability.regulation_mutation_scale", "genetics.mutation.regulation_multiplier", "lineage.mutation_delta", "test_family_mutation_multiplier"),
    ("evolvability.sensorimotor_mutation_scale", "genetics.mutation.sensorimotor_multiplier", "lineage.mutation_delta", "test_family_mutation_multiplier"),
    ("evolvability.structure_mutation_scale", "genetics.mutation.structure_multiplier", "lineage.mutation_delta", "test_family_mutation_multiplier"),
    ("evolvability.recombination_linkage", "genetics.recombination.linkage_probability", "lineage.recombination_breaks", "test_linkage_controls_block_breakage"),
)


def _matches(locus: str, rule: str) -> bool:
    return locus == rule or (rule.endswith(".") and locus.startswith(rule))


def canonical_gene_bindings() -> tuple[GeneBinding, ...]:
    bindings: list[GeneBinding] = []
    for locus in sorted(DEFAULT_GENOME_SCHEMA.specs):
        matches = [rule for rule in _BINDING_RULES if _matches(locus, rule[0])]
        if len(matches) != 1:
            raise RuntimeError(
                f"Genome v2 locus {locus!r} must have exactly one runtime binding; got {len(matches)}"
            )
        _, consumer, projection, test_id = matches[0]
        bindings.append(GeneBinding(locus, consumer, projection, test_id))
    return tuple(bindings)


__all__ = ["GeneBinding", "canonical_gene_bindings"]
