"""Canonical embodiment domain.

EmbodimentSession is the apparatus/transduction coupling. EmbodimentEpisode is
its persistent biological/cognitive domain counterpart.
"""

from .adaptation import AdaptationSnapshot, EmbodimentAdaptation
from .contract import (
    EmbodimentContract,
    PerceptualChannel,
    PerceptualSurface,
    TimingContract,
)
from .dynamics import (
    EvidenceProvenance,
    PredictionResidual,
    SensorimotorDynamicsModel,
)
from .episode import (
    ContractTransition,
    EmbodimentEndReason,
    EmbodimentEpisode,
    EmbodimentState,
)
from .history import EmbodimentEpisodeSummary
from .memory import (
    BodySpecificMemory,
    EmbodimentArchive,
    EmbodimentPrior,
    archive_episode_checkpoint,
)
from .reachability import ReachabilityModel, ReachabilityRelation
from .reembodiment import (
    begin_reembodiment,
    replace_body,
    select_prior,
)
from .session import EmbodimentSession, PortBinding, implant, implant_body

__all__ = [
    "AdaptationSnapshot",
    "BodySpecificMemory",
    "ContractTransition",
    "EmbodimentAdaptation",
    "EmbodimentArchive",
    "EmbodimentPrior",
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
    "SensorimotorDynamicsModel",
    "TimingContract",
    "archive_episode_checkpoint",
    "begin_reembodiment",
    "implant",
    "implant_body",
    "replace_body",
    "select_prior",
]
