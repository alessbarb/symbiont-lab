from __future__ import annotations

from typing import Any, Callable

from symbiont.simulation import run_simulation
from symbiont_lab.studies.attention.causal import run_causal_attention_budget
from symbiont_lab.studies.attention.replicated import run_causal_budget_study
from symbiont_lab.studies.attention.retrospective import run_attention_budget
from symbiont_lab.studies.evidence.causal_budget import run_replicated_causal_evidence_study
from symbiont_lab.studies.evidence.noise_sweep import run_evidence_noise_sweep
from symbiont_lab.studies.evidence.replicated import run_replicated_evidence_study
from symbiont_lab.studies.evidence.second_look import run_second_look_study
from symbiont_lab.studies.continuity.recurrent_restoration import run_recurrent_restoration_study
from symbiont_lab.studies.heritage.ecological_shift import run_ecological_shift_study
from symbiont_lab.studies.heritage.longitudinal import run_longitudinal_study
from symbiont_lab.studies.heritage.replicated import run_replicated_heritage_stress_study
from symbiont_lab.studies.heritage.stress import run_heritage_stress_study
from symbiont_lab.studies.learning.predictive_utility import run_predictive_utility_study
from symbiont_lab.studies.learning.continuous_temporal_challenge import run_continuous_temporal_challenge
from symbiont_lab.studies.learning.cognitive_ecology_embodiment import run_cognitive_ecology_embodiment_study
from symbiont_lab.studies.learning.structural_producer_fairness import run_structural_producer_fairness_study
from symbiont_lab.studies.learning.private_model_utility import run_private_model_utility_study
from symbiont_lab.studies.learning.private_model_controls import run_private_model_controls_study
from symbiont_lab.studies.learning.temporal_private_model_controls import run_temporal_private_model_controls_study
from symbiont_lab.studies.learning.private_model_regime_shift import run_private_model_symmetric_regime_study
from symbiont_lab.studies.learning.private_model_adaptation import run_private_model_adaptation_study
from symbiont_lab.studies.learning.cultural_foundation import run_cultural_foundation_study
from symbiont_lab.studies.learning.cumulative_culture import run_cumulative_culture_study
from symbiont_lab.studies.learning.autonomous_cultural_agency import run_autonomous_cultural_agency_study
from symbiont_lab.studies.learning.emergent_symbol_grounding import run_emergent_symbol_grounding_study
from symbiont_lab.studies.learning.independent_symbol_grounding import run_independent_symbol_grounding_study
from symbiont_lab.studies.learning.predictive_discovery import run_predictive_discovery_study
from symbiont_lab.studies.embodiment.yoked_external_causation import run_yoked_external_causation_study
from symbiont_lab.studies.embodiment.somatic_correlation_trap import run_somatic_correlation_trap_study
from symbiont_lab.studies.embodiment.causal_revision_sequence import run_causal_revision_sequence_study
from symbiont_lab.studies.embodiment.temporal_causality_challenge import run_temporal_causality_challenge_study
from symbiont_lab.studies.embodiment.tool_body_distinction import run_tool_body_distinction_study
from symbiont_lab.studies.embodiment.hidden_common_cause import run_hidden_common_cause_study
from symbiont_lab.studies.embodiment.label_invariance import run_label_invariance_study
from symbiont_lab.studies.embodiment.heredity_leakage_challenge import run_heredity_leakage_challenge_study
from symbiont_lab.studies.learning.emergent_structured_communication import run_emergent_structured_communication_study
from symbiont_lab.studies.learning.structured_communication_characterization import run_structured_communication_characterization
from symbiont_lab.studies.observability.population_communication import run_population_communication_study
from symbiont_lab.studies.longitudinal_population_ecology import run_longitudinal_population_ecology_study
from symbiont_lab.studies.world.genesis_viability import run_genesis_viability_characterization
from symbiont_lab.studies.perception.autonomous_selection import (
    run_autonomous_sensory_selection_study,
    run_sensory_regime_reversal_study,
    run_sensory_null_selection_study,
    run_experience_conditioned_phenotype_study,
)
from symbiont_lab.studies.perception.sensory_specialisation import (
    run_identity_equivalence_study,
    run_adaptive_delta_discovery_study,
    run_temporal_scale_specialisation_study,
    run_modality_specialisation_study,
    run_duplication_divergence_study,
    run_sensory_ablation_study,
    run_multisource_specialisation_study,
    run_same_world_phenotype_divergence_study,
)


def run_comparative_study(*args: Any, **kwargs: Any) -> Any:
    """Lazy import avoids the experiments/studies package cycle at collection."""
    if not args and "base_spec" not in kwargs:
        raise ValueError("campaign.comparative requires base_spec")
    from symbiont_lab.studies.campaigns.comparative import run_comparative_study as implementation
    return implementation(*args, **kwargs)


PROTOCOLS: dict[str, Callable[..., Any]] = {
    "simulate": run_simulation,
    "attention.retrospective": run_attention_budget,
    "attention.causal": run_causal_attention_budget,
    "attention.replicated": run_causal_budget_study,
    "evidence.second-look": run_second_look_study,
    "evidence.replicated": run_replicated_evidence_study,
    "evidence.noise-sweep": run_evidence_noise_sweep,
    "evidence.causal-budget": run_replicated_causal_evidence_study,
    "heritage.longitudinal": run_longitudinal_study,
    "heritage.stress": run_heritage_stress_study,
    "heritage.replicated": run_replicated_heritage_stress_study,
    "heritage.ecological-shift": run_ecological_shift_study,
    "campaign.comparative": run_comparative_study,
    "learning.predictive-utility": run_predictive_utility_study,
    "learning.continuous-temporal-challenge": run_continuous_temporal_challenge,
    "learning.cognitive-ecology-embodiment": run_cognitive_ecology_embodiment_study,
    "learning.structural-producer-fairness": run_structural_producer_fairness_study,
    "learning.private-model-utility": run_private_model_utility_study,
    "learning.private-model-controls": run_private_model_controls_study,
    "learning.temporal-private-model-controls": run_temporal_private_model_controls_study,
    "learning.private-model-regime-symmetric": run_private_model_symmetric_regime_study,
    "learning.private-model-adaptation": run_private_model_adaptation_study,
    "learning.cultural-foundation": run_cultural_foundation_study,
    "learning.cumulative-culture": run_cumulative_culture_study,
    "learning.autonomous-cultural-agency": run_autonomous_cultural_agency_study,
    "learning.emergent-symbol-grounding": run_emergent_symbol_grounding_study,
    "learning.independent-symbol-grounding": run_independent_symbol_grounding_study,
    "learning.predictive-discovery": run_predictive_discovery_study,
    "embodiment.yoked-external-causation": run_yoked_external_causation_study,
    "embodiment.somatic-correlation-trap": run_somatic_correlation_trap_study,
    "embodiment.causal-revision-sequence": run_causal_revision_sequence_study,
    "embodiment.temporal-causality-challenge": run_temporal_causality_challenge_study,
    "embodiment.tool-body-distinction": run_tool_body_distinction_study,
    "embodiment.hidden-common-cause": run_hidden_common_cause_study,
    "embodiment.label-invariance": run_label_invariance_study,
    "embodiment.heredity-leakage-challenge": run_heredity_leakage_challenge_study,
    "learning.emergent-structured-communication": run_emergent_structured_communication_study,
    "learning.structured-communication-characterization": run_structured_communication_characterization,
    "observability.population-communication": run_population_communication_study,
    "learning.longitudinal-population-ecology": run_longitudinal_population_ecology_study,
    "world.genesis-viability-characterization": run_genesis_viability_characterization,
    "continuity.recurrent-restoration": run_recurrent_restoration_study,
    "perception.identity-equivalence": run_identity_equivalence_study,
    "perception.adaptive-delta-discovery": run_adaptive_delta_discovery_study,
    "perception.temporal-scale-specialisation": run_temporal_scale_specialisation_study,
    "perception.modality-specialisation": run_modality_specialisation_study,
    "perception.sensory-duplication-divergence": run_duplication_divergence_study,
    "perception.sensory-ablation": run_sensory_ablation_study,
    "perception.multisource-specialisation": run_multisource_specialisation_study,
    "perception.same-world-phenotype-divergence": run_same_world_phenotype_divergence_study,
    "perception.autonomous-sensory-selection": run_autonomous_sensory_selection_study,
    "perception.sensory-regime-reversal": run_sensory_regime_reversal_study,
    "perception.sensory-null-selection": run_sensory_null_selection_study,
    "perception.experience-conditioned-phenotype": run_experience_conditioned_phenotype_study,
}


def get_protocol(name: str) -> Callable[..., Any]:
    if name not in PROTOCOLS:
        valid = ", ".join(sorted(PROTOCOLS.keys()))
        raise ValueError(f"Unknown protocol: '{name}'. Available protocols: {valid}")
    return PROTOCOLS[name]
