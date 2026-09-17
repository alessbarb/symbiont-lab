"""Laboratory-owned training and evaluation apparatus for private Symbiont models."""

from .architectures import ArchitectureSpec, architecture_spec, build_model, count_parameters
from .artifacts import FileArtifactStore, ModelArtifact
from .baselines import BaselineMetrics, evaluate_frequency_baseline, evaluate_persistence_baseline, evaluate_uniform_baseline
from .dataset import EncodedCorpus, EncodedSplit, encode_corpus
from .evaluation import CandidateEvaluation, PromotionDecision, PromotionPolicy, evaluate_candidate
from .gateway import ArtifactInferenceGateway
from .trainer import TrainingConfig, TrainingResult, train_private_model

__all__ = [
    "ArchitectureSpec",
    "ArtifactInferenceGateway",
    "BaselineMetrics",
    "CandidateEvaluation",
    "EncodedCorpus",
    "EncodedSplit",
    "FileArtifactStore",
    "ModelArtifact",
    "PromotionDecision",
    "PromotionPolicy",
    "TrainingConfig",
    "TrainingResult",
    "architecture_spec",
    "build_model",
    "count_parameters",
    "encode_corpus",
    "evaluate_candidate",
    "evaluate_frequency_baseline",
    "evaluate_persistence_baseline",
    "evaluate_uniform_baseline",
    "train_private_model",
]
