"""Core cognitive and biological models of the Symbiont organism."""

from .host.advisory import (
    AdvisoryConsentRequiredError,
    AdvisorySignal,
    DefensiveAdvisor,
    DefensiveAdvisory,
    append_advisories_to_log,
    load_advisory_log,
)
from .cognition.agent import Agent
from .cognition.attention import AttentionAllocation, AttentionBudget, AttentionCandidate, attend_to_host, uncertainty_from_baseline
from .social.capsule import CAPSULE_SCHEMA_VERSION, CapsuleKeyPair, KnowledgeCapsule, create_capsule, verify_capsule
from .social.collective import CollectiveMemory, InheritedPrior, OpenQuestion, PatternEvidence, SourceTrust, SourceVote
from .cognition.curiosity import CuriosityPlanner, CuriosityProbe
from .orchestration.governor import ConsentRevokedError, GovernedOrganism, RateLimitedError, TickBudgetExhaustedError
from .cognition.evidence import DissentRecord, EvidenceRevisionLedger, EvidenceRevisionResult
from .lineage.heritage import HeritagePattern, SpeciesHeritage, apply_heritage, distill_heritage
from .cognition.memory import AgentMemory, Episode, SemanticMemory
from .cognition.metacognition import MetacognitionEngine, MetacognitiveState
from .foundation.model import FEATURES, Assessment, HostModel, Observation, RunningStat, fingerprint, mean
from .foundation.narrative import NarrativeEntry, narrate_capability, narrate_host
from .cognition.reasoning import Hypothesis, ReasoningEngine
from .orchestration.resident import ResidentConfig, ResidentOrganism
from .orchestration.runtime import ActionExecutionResult, OrganismDeadError, OrganismRuntime, RuntimeTickResult
from .signals.identity import SignalIdentity, claim_id
from .signals.knowledge import (SignalKnowledgeEngine, SignalProfile, Claim, KnowledgeEvent,
                               EvidenceWindow, MAX_KNOWLEDGE_CHECKPOINT_BYTES,
                               MIN_VALIDATION_TRIALS, EPOCH_TICKS, MIN_EPOCH_TRIALS)
from .signals.knowledge_types import SignalObservation, SignalObservationBatch
from .signals.prediction import BoundedPredictor, RidgePredictor, PredictionTrial, absolute_loss, baseline_predictions, scaled_squared_loss, improvement_class
from .signals.knowledge_checkpoint import validate_checkpoint
from .social.trust import SourceTrustModel, TrustSnapshot, agreement_score, observe_capsule_trust
from .embodiment.metabolism import MetabolicLedger, MetabolicSnapshot, ResourcePressure
from .embodiment.assimilation import AssimilationAction, AssimilationDecision, InformationAssimilator
from .embodiment.degradation import DegradationQueue, RetainedItem, RetentionState
from .embodiment.homeostasis import HomeostaticAction, HomeostaticController, HomeostaticSnapshot
from .embodiment.lifecycle import LifeState, ViabilityController
from .lineage.birth_authority import BirthRecord, DeathRecord, HabitatBirthAuthority
import sys as _sys
from .lineage import birth_authority as _birth_authority
from .lineage import heredity as _heredity
from .lineage import inheritance as _inheritance
from .lineage import heritage as _heritage
from .lineage import germline as _germline
from .signals import identity as _signal_identity
from .signals import knowledge as _signal_knowledge
from .signals import knowledge_checkpoint as _signal_knowledge_checkpoint
from .signals import knowledge_types as _signal_knowledge_types
from .signals import prediction as _signal_prediction
_sys.modules[__name__ + ".birth_authority"] = _birth_authority
_sys.modules[__name__ + ".heredity"] = _heredity
_sys.modules[__name__ + ".inheritance"] = _inheritance
_sys.modules[__name__ + ".heritage"] = _heritage
_sys.modules[__name__ + ".germline"] = _germline
_sys.modules[__name__ + ".signal_identity"] = _signal_identity
_sys.modules[__name__ + ".signal_knowledge"] = _signal_knowledge
_sys.modules[__name__ + ".signal_knowledge_checkpoint"] = _signal_knowledge_checkpoint
_sys.modules[__name__ + ".signal_knowledge_types"] = _signal_knowledge_types
_sys.modules[__name__ + ".signal_prediction"] = _signal_prediction
from .lineage.heredity import HeritableGenome, recombine_loci
from .lineage.inheritance import CulturalArtifact, EpigeneticPrior, InheritanceChannels, mutate_genome
from .social.ecology import HabitatSnapshot, SharedHabitat
from .social.interactions import Allocation, EcologicalResourcePool
from .social.exchange import ExchangeEnvelope, ExchangeReplayGuard, MAX_EXCHANGE_BYTES
from .social.evidence_trust import EvidenceTrust
from .social.collective_revision import RevisionResult, revise_claim
from .social.communication import ConsentBoundChannel, SignedMessage
from .social.adversarial import AdversarialAssessment, AdversarialEcology
from .embodiment.development import DevelopmentalPhase, DevelopmentalSnapshot, DevelopmentalTracker
from .embodiment.ontogeny import OntogenyController, OntogenySnapshot, PhysicalLifeStage

__all__ = [
    "FEATURES", "AdvisoryConsentRequiredError", "AdvisorySignal", "Agent", "AgentMemory",
    "Assessment", "AttentionAllocation", "AttentionBudget", "AttentionCandidate",
    "CAPSULE_SCHEMA_VERSION", "CapsuleKeyPair", "CollectiveMemory", "ConsentRevokedError",
    "CuriosityPlanner", "CuriosityProbe", "DefensiveAdvisor", "DefensiveAdvisory",
    "DissentRecord", "Episode", "EvidenceRevisionLedger", "EvidenceRevisionResult",
    "GovernedOrganism", "HeritagePattern", "HostModel", "Hypothesis", "InheritedPrior",
    "KnowledgeCapsule", "MetacognitionEngine", "MetacognitiveState", "NarrativeEntry",
    "Observation", "OpenQuestion", "OrganismRuntime", "PatternEvidence", "RateLimitedError",
    "ReasoningEngine", "ResidentConfig", "ResidentOrganism", "RunningStat", "RuntimeTickResult", "OrganismDeadError",
    "SemanticMemory", "SourceTrust", "SourceTrustModel", "SourceVote", "SpeciesHeritage",
    "TickBudgetExhaustedError", "TrustSnapshot", "agreement_score", "append_advisories_to_log",
    "MetabolicLedger", "MetabolicSnapshot", "ResourcePressure",
    "AssimilationAction", "AssimilationDecision", "InformationAssimilator",
    "DegradationQueue", "RetainedItem", "RetentionState",
    "HomeostaticAction", "HomeostaticController", "HomeostaticSnapshot",
    "LifeState", "ViabilityController",
    "BirthRecord", "DeathRecord", "HabitatBirthAuthority",
    "HeritableGenome", "recombine_loci",
    "CulturalArtifact", "EpigeneticPrior", "InheritanceChannels", "mutate_genome",
    "HabitatSnapshot", "SharedHabitat",
    "Allocation", "EcologicalResourcePool",
    "ExchangeEnvelope", "ExchangeReplayGuard", "MAX_EXCHANGE_BYTES",
    "EvidenceTrust",
    "RevisionResult", "revise_claim",
    "ConsentBoundChannel", "SignedMessage",
    "AdversarialAssessment", "AdversarialEcology",
    "ActionExecutionResult",
    "DevelopmentalPhase", "DevelopmentalSnapshot", "DevelopmentalTracker",
    "OntogenyController", "OntogenySnapshot", "PhysicalLifeStage",
    "apply_heritage", "attend_to_host", "create_capsule", "distill_heritage", "fingerprint",
    "load_advisory_log", "mean", "narrate_capability", "narrate_host", "observe_capsule_trust",
    "uncertainty_from_baseline", "verify_capsule",
    "SignalIdentity", "SignalKnowledgeEngine", "SignalProfile", "Claim", "KnowledgeEvent",
    "EvidenceWindow", "MIN_VALIDATION_TRIALS", "EPOCH_TICKS", "MIN_EPOCH_TRIALS",
    "SignalObservation", "SignalObservationBatch", "claim_id",
    "MAX_KNOWLEDGE_CHECKPOINT_BYTES",
    "validate_checkpoint",
    "LivingBodyState", "PhysiologyController", "PhysiologySnapshot", "VitalState",
    "InteractionOutcome", "RelationLedger", "RelationValence", "SocialHabitat", "SocialInteractionEngine", "SocialRelation", "SocialPresence", "SocialCompetitionRequest",
    "BoundedPredictor", "PredictionTrial", "absolute_loss",
    "baseline_predictions",
    "RidgePredictor",
    "scaled_squared_loss", "improvement_class",
]
from .embodiment.body import (
    ActivationConsequence,
    Body,
    BodyPhysiology,
    EffectorPort,
    ReceptorPort,
    create_standard_body,
)
from .embodiment.session import EmbodimentSession, PortBinding, implant
from .embodiment.body_schema import BodySchemaEngine
from .embodiment.dynamics import SensorimotorDynamicsModel
from ..actuation.model import AgencyModel, CompetenceEffectModel, ControllabilityModel
from .orchestration.symbiont import Symbiont
from .orchestration.individual import Individual, IndividualTickRecord, create_individual

from .lineage.germline import (
    EpigeneticMark,
    GermlineState,
    InheritancePackage,
    LocusSpec,
    LocusType,
    STANDARD_COGNITIVE_LOCI,
    SymbiontGenome,
    create_offspring_package,
    create_standard_genome,
)

__all__.extend([
    "ActivationConsequence",
    "Body",
    "BodyPhysiology",
    "EffectorPort",
    "ReceptorPort",
    "create_standard_body",
    "EmbodimentSession",
    "PortBinding",
    "implant",
    "AgencyModel",
    "BodySchemaEngine",
    "CompetenceEffectModel",
    "ControllabilityModel",
    "SensorimotorDynamicsModel",
    "Symbiont",
    "Individual",
    "IndividualTickRecord",
    "create_individual",
    "EpigeneticMark",
    "GermlineState",
    "InheritancePackage",
    "LocusSpec",
    "LocusType",
    "STANDARD_COGNITIVE_LOCI",
    "SymbiontGenome",
    "create_offspring_package",
    "create_standard_genome",
])

# Keep historical module paths importable while callers migrate to the domain
# packages above. These aliases preserve object identity and checkpoint code.
from importlib import import_module as _import_module

_legacy_module_paths = {
    "advisory": "host.advisory",
    "agent": "cognition.agent",
    "beliefs": "cognition.beliefs",
    "attention": "cognition.attention",
    "capsule": "social.capsule",
    "collective": "social.collective",
    "curiosity": "cognition.curiosity",
    "governor": "orchestration.governor",
    "evidence": "cognition.evidence",
    "consolidation": "cognition.consolidation",
    "memory": "cognition.memory",
    "metacognition": "cognition.metacognition",
    "model": "foundation.model",
    "narrative": "foundation.narrative",
    "reasoning": "cognition.reasoning",
    "resident": "orchestration.resident",
    "runtime": "orchestration.runtime",
    "trust": "social.trust",
    "local_habitat": "host.local_habitat",
    "metabolism": "embodiment.metabolism",
    "physiology": "embodiment.physiology",
    "physiology_config": "embodiment.physiology_config",
    "assimilation": "embodiment.assimilation",
    "degradation": "embodiment.degradation",
    "homeostasis": "embodiment.homeostasis",
    "lifecycle": "embodiment.lifecycle",
    "ecology": "social.ecology",
    "interactions": "social.interactions",
    "exchange": "social.exchange",
    "evidence_trust": "social.evidence_trust",
    "collective_revision": "social.collective_revision",
    "communication": "social.communication",
    "adversarial": "social.adversarial",
    "development": "embodiment.development",
    "ontogeny": "embodiment.ontogeny",
    "body": "embodiment.body",
    "body_schema": "embodiment.body_schema",
    "agency": "embodiment.agency",
    "symbiont": "orchestration.symbiont",
    "individual": "orchestration.individual",
    "epistemic": "foundation.epistemic",
    "limits": "foundation.limits",
    "regulation": "foundation.regulation",
    "fingerprint": "foundation.fingerprint",
    "weight_stability": "foundation.weight_stability",
    "cognition_bridge": "cognition.bridge",
    "cognitive_self": "cognition.self_model",
    "selfmodel": "cognition.host_self_model",
    "embodiment_session": "embodiment.session",
}
for _legacy_name, _current_name in _legacy_module_paths.items():
    _sys.modules[f"{__name__}.{_legacy_name}"] = _import_module(
        f"{__name__}.{_current_name}"
    )
