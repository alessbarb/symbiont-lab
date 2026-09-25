"""Canonical embodiment domain.

EmbodimentSession is the apparatus/transduction coupling. EmbodimentEpisode is
its persistent biological/cognitive domain counterpart.
"""
from .session import EmbodimentSession, PortBinding, implant, implant_body
from .contract import (
    EmbodimentContract,
    PerceptualChannel,
    PerceptualSurface,
    TimingContract,
)
from .episode import (
    ContractTransition,
    EmbodimentEndReason,
    EmbodimentEpisode,
    EmbodimentState,
)
from .adaptation import AdaptationSnapshot, EmbodimentAdaptation
from .dynamics import (
    EvidenceProvenance,
    PredictionResidual,
    SensorimotorDynamicsModel,
)
from .history import EmbodimentEpisodeSummary
from .memory import BodySpecificMemory, EmbodimentArchive, archive_episode_checkpoint
from .reachability import ReachabilityModel, ReachabilityRelation
from .reembodiment import (
    ReembodimentPrior,
    begin_reembodiment,
    replace_body,
    select_prior,
)

__all__ = [
    "AdaptationSnapshot",
    "BodySpecificMemory",
    "ContractTransition",
    "EmbodimentAdaptation",
    "EmbodimentArchive",
    "EmbodimentContract",
    "EmbodimentEndReason",
    "EmbodimentEpisode",
    "EmbodimentEpisodeSummary",
    "EmbodimentSession",
    "EmbodimentState",
    "EvidenceProvenance",
    "PerceptualChannel",
    "PerceptualSurface",
    "PortBinding",
    "PredictionResidual",
    "ReachabilityModel",
    "ReachabilityRelation",
    "ReembodimentPrior",
    "SensorimotorDynamicsModel",
    "TimingContract",
    "archive_episode_checkpoint",
    "begin_reembodiment",
    "implant",
    "implant_body",
    "replace_body",
    "select_prior",
]
