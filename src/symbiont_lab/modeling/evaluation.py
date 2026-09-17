from __future__ import annotations

from dataclasses import dataclass
import math

from .artifacts import ModelArtifact
from .baselines import (
    BaselineMetrics,
    evaluate_frequency_baseline,
    evaluate_persistence_baseline,
    evaluate_uniform_baseline,
)
from .dataset import EncodedCorpus
from .gateway import load_artifact_model
from .trainer import TrainingMetrics, evaluate_model


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    model_id: str
    candidate: TrainingMetrics
    uniform: BaselineMetrics
    frequency: BaselineMetrics
    persistence: BaselineMetrics
    recurrent_reference_loss: float | None = None
    cognitive_reference_loss: float | None = None

    @property
    def best_trivial_loss(self) -> float:
        return min(self.uniform.mean_log_loss, self.frequency.mean_log_loss, self.persistence.mean_log_loss)

    @property
    def gain_over_trivial(self) -> float:
        return self.best_trivial_loss - self.candidate.mean_log_loss


@dataclass(frozen=True, slots=True)
class PromotionPolicy:
    minimum_log_loss_gain: float = 0.01
    require_cognitive_reference_gain: bool = False

    def __post_init__(self) -> None:
        if (isinstance(self.minimum_log_loss_gain, bool)
                or not isinstance(self.minimum_log_loss_gain, (int, float))
                or not math.isfinite(float(self.minimum_log_loss_gain))
                or self.minimum_log_loss_gain < 0.0):
            raise ValueError("minimum_log_loss_gain must be finite and non-negative")
        if not isinstance(self.require_cognitive_reference_gain, bool):
            raise ValueError("require_cognitive_reference_gain must be boolean")


@dataclass(frozen=True, slots=True)
class PromotionDecision:
    promote: bool
    reason: str
    gain_over_trivial: float

    def summary_classes(self) -> tuple[int, ...]:
        """Bounded checkpoint-safe evaluator summary, not raw test metrics."""
        gain_class = max(-7, min(7, int(round(self.gain_over_trivial * 10))))
        return (1 if self.promote else 0, gain_class)


def evaluate_candidate(
    artifact: ModelArtifact,
    corpus: EncodedCorpus,
    *,
    policy: PromotionPolicy | None = None,
    recurrent_reference_loss: float | None = None,
    cognitive_reference_loss: float | None = None,
    device: str = "cpu",
) -> tuple[CandidateEvaluation, PromotionDecision]:
    if artifact.manifest.corpus_hash != corpus.corpus_hash or artifact.manifest.tokenizer_hash != corpus.tokenizer_hash:
        raise ValueError("artifact provenance does not match evaluation corpus")
    selected_policy = policy or PromotionPolicy()
    model = load_artifact_model(
        artifact,
        vocab_size=corpus.vocab_size,
        pad_id=corpus.pad_id,
        device=device,
    )
    candidate_metrics = evaluate_model(
        model,
        corpus.test,
        pad_id=corpus.pad_id,
        context_window=artifact.manifest.context_window,
    )
    uniform = evaluate_uniform_baseline(corpus.test, vocab_size=corpus.vocab_size)
    frequency = evaluate_frequency_baseline(corpus.train, corpus.test, vocab_size=corpus.vocab_size)
    persistence = evaluate_persistence_baseline(corpus.test, vocab_size=corpus.vocab_size)
    evaluation = CandidateEvaluation(
        model_id=artifact.manifest.model_id,
        candidate=candidate_metrics,
        uniform=uniform,
        frequency=frequency,
        persistence=persistence,
        recurrent_reference_loss=recurrent_reference_loss,
        cognitive_reference_loss=cognitive_reference_loss,
    )
    gain = evaluation.gain_over_trivial
    if gain < selected_policy.minimum_log_loss_gain:
        return evaluation, PromotionDecision(False, "insufficient_held_out_gain", gain)
    if recurrent_reference_loss is not None:
        if not math.isfinite(recurrent_reference_loss) or recurrent_reference_loss < 0.0:
            raise ValueError("recurrent_reference_loss must be finite and non-negative")
    if cognitive_reference_loss is not None:
        if not math.isfinite(cognitive_reference_loss) or cognitive_reference_loss < 0.0:
            raise ValueError("cognitive_reference_loss must be finite and non-negative")
        if selected_policy.require_cognitive_reference_gain and candidate_metrics.mean_log_loss >= cognitive_reference_loss:
            return evaluation, PromotionDecision(False, "no_gain_over_cognitive_reference", gain)
    return evaluation, PromotionDecision(True, "held_out_gain", gain)
