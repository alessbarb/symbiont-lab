from __future__ import annotations

from .canonical_sensorimotor_adaptation import (
    AdaptationStudy,
    AdaptationTrial,
    run_sensorimotor_adaptation_study,
    run_sensorimotor_adaptation_trial,
)
from .canonical_sensorimotor_agency import (
    SensorimotorAgencyStudy,
    SensorimotorAgencyTrial,
    run_sensorimotor_agency_study,
    run_sensorimotor_agency_trial,
)
from .canonical_sensorimotor_counterfactual import (
    CounterfactualReplayStudy,
    CounterfactualReplayTrial,
    run_counterfactual_replay_study,
    run_counterfactual_replay_trial,
)
from .cultural_foundation import (
    CulturalFoundationStudy,
    CulturalSeedResult,
    run_cultural_foundation_study,
)
from .cumulative_culture import (
    CumulativeCultureStudy,
    CumulativeSeedResult,
    run_cumulative_culture_study,
)
from .embodied_counterfactual import (
    CounterfactualSeedResult,
    EmbodiedCounterfactualStudy,
    FrozenCounterfactualResult,
    FrozenOpaqueLagPredictor,
    OpaqueLagCandidate,
    evaluate_frozen_counterfactual,
    fit_frozen_lag_predictors,
    run_embodied_counterfactual,
)
from .embodied_intervention import EmbodiedInterventionStudy, run_embodied_intervention
from .embodied_model_comparison import EmbodiedModelComparisonStudy, run_embodied_model_comparison
from .embodied_sensorimotor_shadow import (
    EmbodiedSensorimotorShadowStudy,
    run_embodied_sensorimotor_shadow,
)
from .emergent_structured_communication import (
    EmergentStructuredCommunicationStudy,
    StructuredCommunicationSeedResult,
    run_emergent_structured_communication_study,
)
from .emergent_symbol_grounding import (
    EmergentSymbolGroundingStudy,
    SymbolGroundingSeedResult,
    run_emergent_symbol_grounding_study,
)
from .independent_symbol_grounding import (
    ConditionAgreement,
    IndependentSymbolGroundingSeedResult,
    IndependentSymbolGroundingStudy,
    run_independent_symbol_grounding_study,
)
from .predictive_discovery import (
    PredictiveDiscoverySeedResult,
    PredictiveDiscoveryStudy,
    run_predictive_discovery_study,
)
from .predictive_utility import (
    PredictiveUtilityOutcome,
    PredictiveUtilityStudyResult,
    run_predictive_utility_study,
    run_predictive_utility_trial,
)
from .private_model_adaptation import (
    AdaptationSeedResult,
    PrivateModelAdaptationStudy,
    run_private_model_adaptation_study,
)

__all__ = [
    "PredictiveUtilityOutcome",
    "PredictiveUtilityStudyResult",
    "run_predictive_utility_study",
    "run_predictive_utility_trial",
    "AdaptationSeedResult",
    "PrivateModelAdaptationStudy",
    "run_private_model_adaptation_study",
    "CulturalFoundationStudy",
    "CulturalSeedResult",
    "run_cultural_foundation_study",
    "CumulativeCultureStudy",
    "CumulativeSeedResult",
    "run_cumulative_culture_study",
    "EmergentSymbolGroundingStudy",
    "SymbolGroundingSeedResult",
    "run_emergent_symbol_grounding_study",
    "ConditionAgreement",
    "IndependentSymbolGroundingSeedResult",
    "IndependentSymbolGroundingStudy",
    "run_independent_symbol_grounding_study",
    "PredictiveDiscoveryStudy",
    "PredictiveDiscoverySeedResult",
    "run_predictive_discovery_study",
    "EmergentStructuredCommunicationStudy",
    "StructuredCommunicationSeedResult",
    "run_emergent_structured_communication_study",
    "EmbodiedSensorimotorShadowStudy",
    "run_embodied_sensorimotor_shadow",
    "EmbodiedInterventionStudy",
    "run_embodied_intervention",
    "CounterfactualSeedResult",
    "EmbodiedCounterfactualStudy",
    "FrozenCounterfactualResult",
    "FrozenOpaqueLagPredictor",
    "OpaqueLagCandidate",
    "evaluate_frozen_counterfactual",
    "fit_frozen_lag_predictors",
    "run_embodied_counterfactual",
    "EmbodiedModelComparisonStudy",
    "run_embodied_model_comparison",
    "SensorimotorAgencyStudy",
    "SensorimotorAgencyTrial",
    "run_sensorimotor_agency_study",
    "run_sensorimotor_agency_trial",
    "CounterfactualReplayStudy",
    "CounterfactualReplayTrial",
    "run_counterfactual_replay_study",
    "run_counterfactual_replay_trial",
    "AdaptationStudy",
    "AdaptationTrial",
    "run_sensorimotor_adaptation_study",
    "run_sensorimotor_adaptation_trial",
]
from .signal_knowledge import SignalKnowledgeOutcome, run_signal_knowledge

__all__ = ["SignalKnowledgeOutcome", "run_signal_knowledge"]
from .autonomous_cultural_agency import (
    AutonomousAgencySeedResult,
    AutonomousCulturalAgencyStudy,
    run_autonomous_cultural_agency_study,
)

__all__ = [
    "AutonomousAgencySeedResult",
    "AutonomousCulturalAgencyStudy",
    "run_autonomous_cultural_agency_study",
]

from .prospective_agency_controls import (
    ProspectiveAgencyControlSeedResult,
    ProspectiveAgencyControlsStudy,
    run_prospective_agency_controls_study,
)

__all__ += [
    "ProspectiveAgencyControlSeedResult",
    "ProspectiveAgencyControlsStudy",
    "run_prospective_agency_controls_study",
]

from .prospective_agency_embodied import (
    ProspectiveEmbodiedCondition,
    ProspectiveEmbodiedStudy,
    ProspectiveEmbodiedTrial,
    run_prospective_embodied_study,
    run_prospective_embodied_trial,
)

__all__ += [
    "ProspectiveEmbodiedCondition",
    "ProspectiveEmbodiedTrial",
    "ProspectiveEmbodiedStudy",
    "run_prospective_embodied_trial",
    "run_prospective_embodied_study",
]


from .episodic_memory_utility import (
    EpisodicUtilityReport,
    EpisodicUtilitySeedResult,
    EpisodicUtilityStudy,
    evaluate_episodic_predictive_utility,
    run_episodic_memory_utility_study,
)
from .generative_consolidation_gates import (
    GenerativeConsolidationGatesStudy,
    GenerativeConsolidationGateTrial,
    run_generative_consolidation_gates_study,
)
from .generative_planning_utility import (
    GenerativePlanningUtilityStudy,
    GenerativePlanningUtilityTrial,
    run_generative_planning_utility_study,
)
from .generative_replay_utility import (
    GenerativeReplayUtilityStudy,
    GenerativeReplayUtilityTrial,
    run_generative_replay_utility_study,
)

__all__ += [
    "GenerativeReplayUtilityStudy",
    "GenerativeReplayUtilityTrial",
    "run_generative_replay_utility_study",
    "GenerativeConsolidationGateTrial",
    "GenerativeConsolidationGatesStudy",
    "run_generative_consolidation_gates_study",
    "GenerativePlanningUtilityStudy",
    "GenerativePlanningUtilityTrial",
    "run_generative_planning_utility_study",
]
from .generative_counterfactual_utility import (
    GenerativeCounterfactualUtilitySeedResult,
    GenerativeCounterfactualUtilityStudy,
    run_generative_counterfactual_utility_study,
)
from .generative_depth_calibration import (
    GenerativeDepthCalibrationStudy,
    GenerativeDepthCalibrationTrial,
    run_generative_depth_calibration_study,
)
from .generative_model_correction import (
    GenerativeModelCorrectionStudy,
    GenerativeModelCorrectionTrial,
    run_generative_model_correction_study,
)
from .generative_predictive_utility import (
    GenerativePredictiveUtilityStudy,
    GenerativePredictiveUtilityTrial,
    run_generative_predictive_utility_study,
)
from .generative_recombination_construction import (
    GenerativeRecombinationConstructionSeedResult,
    GenerativeRecombinationConstructionStudy,
    run_generative_recombination_construction_study,
)

__all__ += [
    "EpisodicUtilityReport",
    "EpisodicUtilitySeedResult",
    "EpisodicUtilityStudy",
    "evaluate_episodic_predictive_utility",
    "run_episodic_memory_utility_study",
    "GenerativeCounterfactualUtilitySeedResult",
    "GenerativeCounterfactualUtilityStudy",
    "run_generative_counterfactual_utility_study",
    "GenerativeRecombinationConstructionSeedResult",
    "GenerativeRecombinationConstructionStudy",
    "run_generative_recombination_construction_study",
    "GenerativePredictiveUtilityStudy",
    "GenerativePredictiveUtilityTrial",
    "run_generative_predictive_utility_study",
    "GenerativeModelCorrectionStudy",
    "GenerativeModelCorrectionTrial",
    "run_generative_model_correction_study",
    "GenerativeDepthCalibrationStudy",
    "GenerativeDepthCalibrationTrial",
    "run_generative_depth_calibration_study",
]
