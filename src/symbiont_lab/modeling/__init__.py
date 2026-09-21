"""Laboratory-owned training and evaluation apparatus for private Symbiont models."""

from .architectures import ArchitectureSpec, architecture_spec, build_model, count_parameters
from .artifacts import FileArtifactStore, ModelArtifact
from .baselines import BaselineMetrics, evaluate_frequency_baseline, evaluate_persistence_baseline, evaluate_uniform_baseline
from .dataset import EncodedCorpus, EncodedSplit, encode_corpus
from .context_tree import DecayedVariableOrderMarkov
from .reservoir import SparseEchoStateRegressor
from .evaluation import CandidateEvaluation, PromotionDecision, PromotionPolicy, evaluate_candidate
from .factory import FactoryResult, PrivateModelFactory
from .gateway import ArtifactInferenceGateway
from .study import (
    CrossIndividualResult,
    ModelFamilyResult,
    PrivateModelStudyResult,
    RegimeShiftResult,
    cross_evaluate_individual_models,
    evaluate_regime_shift,
    remap_encoded_corpus,
    run_model_family_study,
)
from .trainer import TrainingConfig, TrainingResult, adapt_private_model, train_private_model

__all__ = [
    "ArchitectureSpec",
    "ArtifactInferenceGateway",
    "BaselineMetrics",
    "CandidateEvaluation",
    "CrossIndividualResult",
    "EncodedCorpus",
    "EncodedSplit",
    "DecayedVariableOrderMarkov",
    "FactoryResult",
    "FileArtifactStore",
    "ModelArtifact",
    "ModelFamilyResult",
    "PrivateModelFactory",
    "PrivateModelStudyResult",
    "PromotionDecision",
    "PromotionPolicy",
    "RegimeShiftResult",
    "SparseEchoStateRegressor",
    "TrainingConfig",
    "TrainingResult",
    "architecture_spec",
    "adapt_private_model",
    "build_model",
    "count_parameters",
    "cross_evaluate_individual_models",
    "encode_corpus",
    "evaluate_candidate",
    "evaluate_frequency_baseline",
    "evaluate_persistence_baseline",
    "evaluate_regime_shift",
    "evaluate_uniform_baseline",
    "remap_encoded_corpus",
    "run_model_family_study",
    "train_private_model",
]
