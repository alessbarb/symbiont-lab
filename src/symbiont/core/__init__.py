"""Core cognitive and biological models of the Symbiont organism."""

from .advisory import (
    AdvisoryConsentRequiredError,
    AdvisorySignal,
    DefensiveAdvisor,
    DefensiveAdvisory,
    append_advisories_to_log,
    load_advisory_log,
)
from .agent import Agent
from .attention import AttentionAllocation, AttentionBudget, AttentionCandidate, attend_to_host, uncertainty_from_baseline
from .capsule import CAPSULE_SCHEMA_VERSION, CapsuleKeyPair, KnowledgeCapsule, create_capsule, verify_capsule
from .collective import CollectiveMemory, InheritedPrior, OpenQuestion, PatternEvidence, SourceTrust, SourceVote
from .curiosity import CuriosityPlanner, CuriosityProbe
from .governor import ConsentRevokedError, GovernedOrganism, RateLimitedError, TickBudgetExhaustedError
from .evidence import DissentRecord, EvidenceRevisionLedger, EvidenceRevisionResult
from .heritage import HeritagePattern, SpeciesHeritage, apply_heritage, distill_heritage
from .memory import AgentMemory, Episode, SemanticMemory
from .metacognition import MetacognitionEngine, MetacognitiveState
from .model import FEATURES, Assessment, HostModel, Observation, RunningStat, fingerprint, mean
from .narrative import NarrativeEntry, narrate_capability, narrate_host
from .reasoning import Hypothesis, ReasoningEngine
from .resident import ResidentConfig, ResidentOrganism
from .runtime import ActionExecutionResult, OrganismDeadError, OrganismRuntime, RuntimeTickResult
from .signal_identity import SignalIdentity, claim_id
from .signal_knowledge import (SignalKnowledgeEngine, SignalProfile, Claim, KnowledgeEvent,
                               EvidenceWindow, MAX_KNOWLEDGE_CHECKPOINT_BYTES,
                               MIN_VALIDATION_TRIALS, EPOCH_TICKS, MIN_EPOCH_TRIALS)
from .signal_knowledge_types import SignalObservation, SignalObservationBatch
from .signal_prediction import BoundedPredictor, RidgePredictor, PredictionTrial, absolute_loss, baseline_predictions, scaled_squared_loss, improvement_class
from .signal_knowledge_checkpoint import validate_checkpoint
from .trust import SourceTrustModel, TrustSnapshot, agreement_score, observe_capsule_trust
from .metabolism import MetabolicLedger, MetabolicSnapshot, ResourcePressure
from .assimilation import AssimilationAction, AssimilationDecision, InformationAssimilator
from .degradation import DegradationQueue, RetainedItem, RetentionState
from .homeostasis import HomeostaticAction, HomeostaticController, HomeostaticSnapshot
from .lifecycle import LifeState, ViabilityController
from .birth_authority import BirthRecord, DeathRecord, HabitatBirthAuthority
import sys as _sys
from . import birth_authority as _birth_authority
_sys.modules[__name__ + ".lineage"] = _birth_authority
from .reproduction import ReproductivePressure, ReproductiveStatus, clonal_bud, paired_reproduce
from .heredity import HeritableGenome, recombine_loci
from .inheritance import CulturalArtifact, EpigeneticPrior, InheritanceChannels, mutate_genome
from .ecology import HabitatSnapshot, SharedHabitat
from .interactions import Allocation, EcologicalResourcePool
from .exchange import ExchangeEnvelope, ExchangeReplayGuard, MAX_EXCHANGE_BYTES
from .evidence_trust import EvidenceTrust
from .collective_revision import RevisionResult, revise_claim
from .communication import ConsentBoundChannel, SignedMessage
from .adversarial import AdversarialAssessment, AdversarialEcology
from .development import DevelopmentalPhase, DevelopmentalSnapshot, DevelopmentalTracker

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
    "ReproductivePressure", "ReproductiveStatus", "clonal_bud", "paired_reproduce",
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
    "apply_heritage", "attend_to_host", "create_capsule", "distill_heritage", "fingerprint",
    "load_advisory_log", "mean", "narrate_capability", "narrate_host", "observe_capsule_trust",
    "uncertainty_from_baseline", "verify_capsule",
    "SignalIdentity", "SignalKnowledgeEngine", "SignalProfile", "Claim", "KnowledgeEvent",
    "EvidenceWindow", "MIN_VALIDATION_TRIALS", "EPOCH_TICKS", "MIN_EPOCH_TRIALS",
    "SignalObservation", "SignalObservationBatch", "claim_id",
    "MAX_KNOWLEDGE_CHECKPOINT_BYTES",
    "validate_checkpoint",
    "PhysiologyController", "PhysiologySnapshot", "VitalState",
    "InteractionOutcome", "RelationLedger", "RelationValence", "SocialHabitat", "SocialInteractionEngine", "SocialRelation", "SocialPresence", "SocialCompetitionRequest",
    "BoundedPredictor", "PredictionTrial", "absolute_loss",
    "baseline_predictions",
    "RidgePredictor",
    "scaled_squared_loss", "improvement_class",
]
from .body import (
    ActivationConsequence,
    Body,
    BodyPhysiology,
    EffectorPort,
    ReceptorPort,
    create_standard_body,
)
from .embodiment import EmbodimentSession, PortBinding, implant
from .agency import (
    AgencyModel,
    InferredBodyRegion,
    InferredBodySchema,
    InferredSelfModel,
    PerceptualStructure,
    SensorimotorModel,
)
from .symbiont import Symbiont
from .individual import Individual, IndividualTickRecord, create_individual

from .germline import (
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
    "InferredBodyRegion",
    "InferredBodySchema",
    "InferredSelfModel",
    "PerceptualStructure",
    "SensorimotorModel",
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
