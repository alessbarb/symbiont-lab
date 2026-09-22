from __future__ import annotations

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
    PredictiveDiscoveryStudy,
    PredictiveDiscoverySeedResult,
    run_predictive_discovery_study,
)
from .emergent_structured_communication import (
    EmergentStructuredCommunicationStudy,
    StructuredCommunicationSeedResult,
    run_emergent_structured_communication_study,
)
from .embodied_sensorimotor_shadow import (
    EmbodiedSensorimotorShadowStudy,
    run_embodied_sensorimotor_shadow,
)
from .embodied_intervention import EmbodiedInterventionStudy, run_embodied_intervention
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
from .embodied_model_comparison import EmbodiedModelComparisonStudy, run_embodied_model_comparison
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
from .canonical_sensorimotor_adaptation import (
    AdaptationStudy,
    AdaptationTrial,
    run_sensorimotor_adaptation_study,
    run_sensorimotor_adaptation_trial,
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
    ProspectiveEmbodiedTrial,
    ProspectiveEmbodiedStudy,
    run_prospective_embodied_trial,
    run_prospective_embodied_study,
)

__all__ += [
    "ProspectiveEmbodiedCondition",
    "ProspectiveEmbodiedTrial",
    "ProspectiveEmbodiedStudy",
    "run_prospective_embodied_trial",
    "run_prospective_embodied_study",
]
