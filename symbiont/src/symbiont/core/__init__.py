"""Core cognitive and biological models of the Symbiont organism."""

from .cognition.attention import (
    AttentionAllocation,
    AttentionBudget,
    AttentionCandidate,
    attend_to_host,
    uncertainty_from_baseline,
)
from .cognition.evidence import DissentRecord, EvidenceRevisionLedger, EvidenceRevisionResult
from .cognition.memory import AgentMemory, Episode, SemanticMemory
from .embodiment.assimilation import (
    AssimilationAction,
    AssimilationDecision,
    InformationAssimilator,
)
from .embodiment.degradation import DegradationQueue, RetainedItem, RetentionState
from .embodiment.development import DevelopmentalPhase, DevelopmentalSnapshot, DevelopmentalTracker
from .embodiment.homeostasis import HomeostaticAction, HomeostaticController, HomeostaticSnapshot
from .embodiment.lifecycle import LifeState, ViabilityController
from .embodiment.metabolism import MetabolicLedger, MetabolicSnapshot, ResourcePressure
from .embodiment.ontogeny import OntogenyController, OntogenySnapshot, PhysicalLifeStage
from .embodiment.physiology import (
    LivingBodyState,
    PhysiologyController,
    PhysiologySnapshot,
    VitalState,
)
from .foundation.narrative import NarrativeEntry, narrate_capability, narrate_host
from .host.advisory import (
    AdvisoryConsentRequiredError,
    AdvisorySignal,
    DefensiveAdvisor,
    DefensiveAdvisory,
    append_advisories_to_log,
    load_advisory_log,
)
from .lineage.heritage import HeritagePattern, SpeciesHeritage, apply_heritage, distill_heritage
from .lineage.inheritance import (
    CulturalArtifact,
    EpigeneticPrior,
    InheritanceChannels,
)
from .orchestration.governor import (
    ConsentRevokedError,
    GovernedOrganism,
    RateLimitedError,
    TickBudgetExhaustedError,
)
from .orchestration.resident import ResidentConfig, ResidentOrganism
from .orchestration.runtime import (
    ActionExecutionResult,
    OrganismDeadError,
    OrganismRuntime,
    RuntimeTickResult,
)
from .signals.identity import SignalIdentity, claim_id
from .signals.knowledge import (
    EPOCH_TICKS,
    MAX_KNOWLEDGE_CHECKPOINT_BYTES,
    MIN_EPOCH_TRIALS,
    MIN_VALIDATION_TRIALS,
    Claim,
    EvidenceWindow,
    KnowledgeEvent,
    SignalKnowledgeEngine,
    SignalProfile,
)
from .signals.knowledge_checkpoint import validate_checkpoint
from .signals.knowledge_types import SignalObservation, SignalObservationBatch
from .signals.prediction import (
    BoundedPredictor,
    PredictionTrial,
    RidgePredictor,
    absolute_loss,
    baseline_predictions,
    improvement_class,
    scaled_squared_loss,
)
from .social.adversarial import AdversarialAssessment, AdversarialEcology
from .social.capsule import (
    CAPSULE_SCHEMA_VERSION,
    CapsuleKeyPair,
    KnowledgeCapsule,
    create_capsule,
    verify_capsule,
)
from .social.communication import ConsentBoundChannel, SignedMessage
from .social.ecology import HabitatSnapshot, SharedHabitat
from .social.evidence_trust import EvidenceTrust
from .social.exchange import MAX_EXCHANGE_BYTES, ExchangeEnvelope, ExchangeReplayGuard
from .social.interactions import Allocation, EcologicalResourcePool
from .social.relations import (
    InteractionOutcome,
    RelationLedger,
    RelationValence,
    SocialCompetitionRequest,
    SocialHabitat,
    SocialInteractionEngine,
    SocialPresence,
    SocialRelation,
)
from .social.source_evidence import SourceEvidenceOutcome, SourceEvidenceSample, SourceEvidenceState

__all__ = [
    "AdvisoryConsentRequiredError",
    "AdvisorySignal",
    "AgentMemory",
    "AttentionAllocation",
    "AttentionBudget",
    "AttentionCandidate",
    "CAPSULE_SCHEMA_VERSION",
    "CapsuleKeyPair",
    "ConsentRevokedError",
    "DefensiveAdvisor",
    "DefensiveAdvisory",
    "DissentRecord",
    "Episode",
    "EvidenceRevisionLedger",
    "EvidenceRevisionResult",
    "GovernedOrganism",
    "HeritagePattern",
    "KnowledgeCapsule",
    "NarrativeEntry",
    "OrganismRuntime",
    "RateLimitedError",
    "ResidentConfig",
    "ResidentOrganism",
    "RuntimeTickResult",
    "OrganismDeadError",
    "SemanticMemory",
    "SpeciesHeritage",
    "TickBudgetExhaustedError",
    "append_advisories_to_log",
    "MetabolicLedger",
    "MetabolicSnapshot",
    "ResourcePressure",
    "AssimilationAction",
    "AssimilationDecision",
    "InformationAssimilator",
    "DegradationQueue",
    "RetainedItem",
    "RetentionState",
    "HomeostaticAction",
    "HomeostaticController",
    "HomeostaticSnapshot",
    "LifeState",
    "ViabilityController",
    "CulturalArtifact",
    "EpigeneticPrior",
    "InheritanceChannels",
    "HabitatSnapshot",
    "SharedHabitat",
    "Allocation",
    "EcologicalResourcePool",
    "ExchangeEnvelope",
    "ExchangeReplayGuard",
    "MAX_EXCHANGE_BYTES",
    "EvidenceTrust",
    "ConsentBoundChannel",
    "SignedMessage",
    "AdversarialAssessment",
    "AdversarialEcology",
    "ActionExecutionResult",
    "DevelopmentalPhase",
    "DevelopmentalSnapshot",
    "DevelopmentalTracker",
    "OntogenyController",
    "OntogenySnapshot",
    "PhysicalLifeStage",
    "apply_heritage",
    "attend_to_host",
    "create_capsule",
    "distill_heritage",
    "load_advisory_log",
    "narrate_capability",
    "narrate_host",
    "uncertainty_from_baseline",
    "verify_capsule",
    "SignalIdentity",
    "SignalKnowledgeEngine",
    "SignalProfile",
    "Claim",
    "KnowledgeEvent",
    "EvidenceWindow",
    "MIN_VALIDATION_TRIALS",
    "EPOCH_TICKS",
    "MIN_EPOCH_TRIALS",
    "SignalObservation",
    "SignalObservationBatch",
    "claim_id",
    "MAX_KNOWLEDGE_CHECKPOINT_BYTES",
    "validate_checkpoint",
    "LivingBodyState",
    "PhysiologyController",
    "PhysiologySnapshot",
    "VitalState",
    "InteractionOutcome",
    "RelationLedger",
    "RelationValence",
    "SocialHabitat",
    "SocialInteractionEngine",
    "SocialRelation",
    "SocialPresence",
    "SocialCompetitionRequest",
    "BoundedPredictor",
    "PredictionTrial",
    "absolute_loss",
    "baseline_predictions",
    "RidgePredictor",
    "scaled_squared_loss",
    "improvement_class",
]
from ..actuation.model import AgencyModel, CompetenceEffectModel, ControllabilityModel
from .embodiment.body import (
    ActivationConsequence,
    Body,
    BodyPhysiology,
    EffectorPort,
    ReceptorPort,
    create_standard_body,
)
from .embodiment.body_schema import BodySchemaEngine
from .embodiment.dynamics import SensorimotorDynamicsModel
from .embodiment.session import EmbodimentSession, PortBinding, implant
from .lineage.germline import (
    STANDARD_COGNITIVE_LOCI,
    EpigeneticMark,
    GermlineState,
    InheritancePackage,
    LocusSpec,
    LocusType,
    SymbiontGenome,
    create_standard_genome,
)
from .orchestration.clean_embodiment_seed import CleanEmbodimentSeed
from .orchestration.individual import Individual, IndividualTickRecord, create_individual

__all__.extend(
    [
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
        "CleanEmbodimentSeed",
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
        "create_standard_genome",
    ]
)
