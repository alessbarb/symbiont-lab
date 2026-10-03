"""Laboratory-owned training and evaluation apparatus for private Symbiont models."""

from lab.modeling.architectures import (
    ArchitectureSpec,
    architecture_spec,
    build_model,
    count_parameters,
)
from lab.modeling.artifacts import FileArtifactStore, ModelArtifact
from lab.modeling.baselines import (
    BaselineMetrics,
    evaluate_frequency_baseline,
    evaluate_persistence_baseline,
    evaluate_uniform_baseline,
)
from lab.modeling.context_tree import DecayedVariableOrderMarkov
from lab.modeling.dataset import EncodedCorpus, EncodedSplit, encode_corpus
from lab.modeling.evaluation import (
    CandidateEvaluation,
    PromotionDecision,
    PromotionPolicy,
    evaluate_candidate,
)
from lab.modeling.factory import FactoryResult, PrivateModelFactory
from lab.modeling.gateway import ArtifactInferenceGateway
from lab.modeling.reservoir import SparseEchoStateRegressor
from lab.modeling.study import (
    CrossIndividualResult,
    ModelFamilyResult,
    PrivateModelStudyResult,
    RegimeShiftResult,
    cross_evaluate_individual_models,
    evaluate_regime_shift,
    remap_encoded_corpus,
    run_model_family_study,
)
from lab.modeling.temporal_evaluation import DiscreteTemporalMetrics, evaluate_vomm_challenger
from lab.modeling.trainer import (
    TrainingConfig,
    TrainingResult,
    adapt_private_model,
    train_private_model,
)

__all__ = [
    "ArchitectureSpec",
    "ArtifactInferenceGateway",
    "BaselineMetrics",
    "CandidateEvaluation",
    "CrossIndividualResult",
    "EncodedCorpus",
    "EncodedSplit",
    "DecayedVariableOrderMarkov",
    "DiscreteTemporalMetrics",
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
    "evaluate_vomm_challenger",
    "remap_encoded_corpus",
    "run_model_family_study",
    "train_private_model",
]
