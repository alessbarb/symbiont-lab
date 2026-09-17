from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random

from symbiont.modeling.authority import ArchitectureId, ModelObjective, ModelTrainingAuthority, TrainingRequest
from symbiont.modeling.corpus import TrainingCorpus
from symbiont.modeling.tokenizer import NativeTokenizer

from .dataset import EncodedCorpus, EncodedSplit, encode_corpus
from .evaluation import CandidateEvaluation, PromotionDecision, PromotionPolicy, evaluate_candidate
from .gateway import load_artifact_model
from .outcome_metrics import evaluate_outcome_model
from .trainer import TrainingConfig, TrainingResult, train_private_model


@dataclass(frozen=True, slots=True)
class ModelFamilyResult:
    architecture_id: ArchitectureId
    training: TrainingResult
    evaluation: CandidateEvaluation
    promotion: PromotionDecision


@dataclass(frozen=True, slots=True)
class PrivateModelStudyResult:
    organism_id: str
    corpus_hash: str
    tokenizer_hash: str
    families: tuple[ModelFamilyResult, ...]

    @property
    def promoted(self) -> tuple[ModelFamilyResult, ...]:
        return tuple(item for item in self.families if item.promotion.promote)


@dataclass(frozen=True, slots=True)
class CrossIndividualResult:
    model_a_on_a: float
    model_a_on_b: float
    model_b_on_b: float
    model_b_on_a: float


@dataclass(frozen=True, slots=True)
class RegimeShiftResult:
    pre_shift_loss: float
    post_shift_loss_before_retraining: float
    post_shift_loss_after_retraining: float | None


def _request(corpus: TrainingCorpus, tokenizer: NativeTokenizer, *, architecture_id: ArchitectureId,
             seed: int, context_window: int, epochs: int, steps: int,
             requested_parameters: int, parent_model_id: str | None = None) -> TrainingRequest:
    return TrainingRequest(
        organism_id=corpus.manifest.organism_id,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        architecture_id=architecture_id,
        objective=ModelObjective.NEXT_TOKEN,
        seed=seed,
        context_window=context_window,
        requested_parameters=requested_parameters,
        requested_epochs=epochs,
        requested_steps=steps,
        created_tick_class=corpus.manifest.last_tick_class,
        parent_model_id=parent_model_id,
    )


def run_model_family_study(corpus: TrainingCorpus, *, seed: int = 7, context_window: int = 128,
                           epochs: int = 16, steps: int = 10_000, parameter_ceiling: int = 5_000_000,
                           training_config: TrainingConfig | None = None,
                           promotion_policy: PromotionPolicy | None = None,
                           device: str = "cpu") -> PrivateModelStudyResult:
    tokenizer = NativeTokenizer.from_records(corpus.train)
    encoded = encode_corpus(corpus, tokenizer, context_window=context_window)
    authority = ModelTrainingAuthority()
    trained: dict[ArchitectureId, TrainingResult] = {}
    for architecture_id in (ArchitectureId.GRU_V1, ArchitectureId.TRANSFORMER_V1):
        request = _request(corpus, tokenizer, architecture_id=architecture_id, seed=seed,
                           context_window=context_window, epochs=epochs, steps=steps,
                           requested_parameters=parameter_ceiling)
        trained[architecture_id] = train_private_model(
            request=request, corpus=encoded, authority=authority,
            config=training_config, device=device,
        )

    gru_model = load_artifact_model(trained[ArchitectureId.GRU_V1].artifact,
                                    vocab_size=encoded.vocab_size, pad_id=encoded.pad_id, device=device)
    recurrent_loss = evaluate_outcome_model(
        gru_model, encoded.test, pad_id=encoded.pad_id, context_window=context_window
    ).mean_log_loss
    results: list[ModelFamilyResult] = []
    for architecture_id in (ArchitectureId.GRU_V1, ArchitectureId.TRANSFORMER_V1):
        evaluation, decision = evaluate_candidate(
            trained[architecture_id].artifact, encoded, policy=promotion_policy,
            recurrent_reference_loss=recurrent_loss, device=device,
        )
        results.append(ModelFamilyResult(architecture_id, trained[architecture_id], evaluation, decision))
    return PrivateModelStudyResult(corpus.manifest.organism_id, corpus.manifest.corpus_hash,
                                   tokenizer.tokenizer_hash, tuple(results))


def cross_evaluate_individual_models(*, result_a: TrainingResult, corpus_a: EncodedCorpus,
                                     result_b: TrainingResult, corpus_b: EncodedCorpus,
                                     device: str = "cpu") -> CrossIndividualResult:
    if corpus_a.vocab_size != corpus_b.vocab_size or corpus_a.tokenizer_hash != corpus_b.tokenizer_hash:
        raise ValueError("cross-individual evaluation requires a shared frozen tokenizer")
    model_a = load_artifact_model(result_a.artifact, vocab_size=corpus_a.vocab_size, pad_id=corpus_a.pad_id, device=device)
    model_b = load_artifact_model(result_b.artifact, vocab_size=corpus_b.vocab_size, pad_id=corpus_b.pad_id, device=device)
    context_a = result_a.artifact.manifest.context_window
    context_b = result_b.artifact.manifest.context_window
    return CrossIndividualResult(
        evaluate_outcome_model(model_a, corpus_a.test, pad_id=corpus_a.pad_id, context_window=context_a).mean_log_loss,
        evaluate_outcome_model(model_a, corpus_b.test, pad_id=corpus_b.pad_id, context_window=context_a).mean_log_loss,
        evaluate_outcome_model(model_b, corpus_b.test, pad_id=corpus_b.pad_id, context_window=context_b).mean_log_loss,
        evaluate_outcome_model(model_b, corpus_a.test, pad_id=corpus_a.pad_id, context_window=context_b).mean_log_loss,
    )


def remap_encoded_corpus(corpus: EncodedCorpus, *, seed: int, reserved_prefix: int = 5) -> EncodedCorpus:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if not 0 <= reserved_prefix < corpus.vocab_size:
        raise ValueError("reserved_prefix outside vocabulary")
    mutable = list(range(reserved_prefix, corpus.vocab_size))
    shuffled = mutable.copy()
    random.Random(seed).shuffle(shuffled)
    mapping = {source: target for source, target in zip(mutable, shuffled)}
    mapping.update({index: index for index in range(reserved_prefix)})

    def remap(split: EncodedSplit) -> EncodedSplit:
        return EncodedSplit(
            sequences=tuple(tuple(mapping[token] for token in sequence) for sequence in split.sequences),
            record_ids=split.record_ids,
            outcome_target_positions=split.outcome_target_positions,
        )

    remap_hash = hashlib.sha256(f"{corpus.tokenizer_hash}:{seed}".encode("utf-8")).hexdigest()
    return EncodedCorpus(remap(corpus.train), remap(corpus.validation), remap(corpus.test),
                         corpus.corpus_hash, remap_hash, corpus.vocab_size, corpus.pad_id)


def evaluate_regime_shift(*, trained: TrainingResult, pre_shift: EncodedCorpus,
                          post_shift: EncodedCorpus, retrained: TrainingResult | None = None,
                          device: str = "cpu") -> RegimeShiftResult:
    if pre_shift.vocab_size != post_shift.vocab_size:
        raise ValueError("regime shift corpora must use the same vocabulary size")
    model = load_artifact_model(trained.artifact, vocab_size=pre_shift.vocab_size, pad_id=pre_shift.pad_id, device=device)
    window = trained.artifact.manifest.context_window
    pre = evaluate_outcome_model(model, pre_shift.test, pad_id=pre_shift.pad_id, context_window=window).mean_log_loss
    post = evaluate_outcome_model(model, post_shift.test, pad_id=post_shift.pad_id, context_window=window).mean_log_loss
    recovered = None
    if retrained is not None:
        updated = load_artifact_model(retrained.artifact, vocab_size=post_shift.vocab_size, pad_id=post_shift.pad_id, device=device)
        recovered = evaluate_outcome_model(
            updated, post_shift.test, pad_id=post_shift.pad_id,
            context_window=retrained.artifact.manifest.context_window,
        ).mean_log_loss
    return RegimeShiftResult(pre, post, recovered)
