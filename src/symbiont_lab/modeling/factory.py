from __future__ import annotations

from dataclasses import dataclass, replace

from symbiont.modeling import (
    ArchitectureId,
    ModeledOrganismRuntime,
    ModelState,
    ModelTrainingAuthority,
    NativeTokenizer,
    TrainingCorpus,
    TrainingRequest,
)

from .artifacts import FileArtifactStore
from .dataset import encode_corpus
from .evaluation import CandidateEvaluation, PromotionDecision, PromotionPolicy, evaluate_candidate
from .gateway import load_artifact_model
from .outcome_metrics import evaluate_outcome_model
from .trainer import TrainingConfig, TrainingResult, adapt_private_model, train_private_model


@dataclass(frozen=True, slots=True)
class FactoryResult:
    training: TrainingResult
    evaluation: CandidateEvaluation
    decision: PromotionDecision
    recurrent_reference: TrainingResult | None = None


class PrivateModelFactory:
    """External authority that trains, evaluates and stores models without evaluator leakage."""

    def __init__(
        self,
        *,
        store: FileArtifactStore,
        authority: ModelTrainingAuthority | None = None,
        promotion_policy: PromotionPolicy | None = None,
        training_config: TrainingConfig | None = None,
        device: str = "cpu",
    ) -> None:
        self._store = store
        self._authority = authority or ModelTrainingAuthority()
        self._promotion_policy = promotion_policy or PromotionPolicy()
        self._training_config = training_config or TrainingConfig()
        self._device = device

    def build(
        self,
        *,
        request: TrainingRequest,
        corpus: TrainingCorpus,
        tokenizer: NativeTokenizer,
        cognitive_reference_loss: float | None = None,
        train_recurrent_reference: bool = True,
    ) -> FactoryResult:
        if request.organism_id != corpus.manifest.organism_id:
            raise ValueError("training request and corpus belong to different organisms")
        if request.corpus_hash != corpus.manifest.corpus_hash:
            raise ValueError("training request corpus hash mismatch")
        if request.tokenizer_hash != tokenizer.tokenizer_hash:
            raise ValueError("training request tokenizer hash mismatch")
        encoded = encode_corpus(corpus, tokenizer, context_window=request.context_window)
        candidate = train_private_model(
            request=request,
            corpus=encoded,
            authority=self._authority,
            config=self._training_config,
            device=self._device,
        )

        recurrent_result: TrainingResult | None = None
        if request.architecture_id is ArchitectureId.GRU_V1:
            recurrent_loss = evaluate_outcome_model(
                load_artifact_model(
                    candidate.artifact,
                    vocab_size=encoded.vocab_size,
                    pad_id=encoded.pad_id,
                    device=self._device,
                ),
                encoded.test,
                pad_id=encoded.pad_id,
                context_window=request.context_window,
            ).mean_log_loss
        elif train_recurrent_reference:
            recurrent_request = replace(
                request,
                architecture_id=ArchitectureId.GRU_V1,
                parent_model_id=None,
            )
            recurrent_result = train_private_model(
                request=recurrent_request,
                corpus=encoded,
                authority=self._authority,
                config=self._training_config,
                device=self._device,
            )
            recurrent_loss = evaluate_outcome_model(
                load_artifact_model(
                    recurrent_result.artifact,
                    vocab_size=encoded.vocab_size,
                    pad_id=encoded.pad_id,
                    device=self._device,
                ),
                encoded.test,
                pad_id=encoded.pad_id,
                context_window=recurrent_request.context_window,
            ).mean_log_loss
        else:
            recurrent_loss = None

        evaluation, decision = evaluate_candidate(
            candidate.artifact,
            encoded,
            policy=self._promotion_policy,
            recurrent_reference_loss=recurrent_loss,
            cognitive_reference_loss=cognitive_reference_loss,
            device=self._device,
        )
        self._store.put(candidate.artifact)
        if recurrent_result is not None:
            self._store.put(recurrent_result.artifact)
        return FactoryResult(candidate, evaluation, decision, recurrent_result)

    def adopt(self, runtime: ModeledOrganismRuntime, result: FactoryResult):
        """Adopt every candidate as SHADOW; activate only a passed held-out gate."""

        if runtime.organism_id != result.training.artifact.manifest.organism_id:
            raise ValueError("factory result belongs to a different organism")
        summary = result.decision.summary_classes()
        record = runtime.adopt_private_model(result.training.artifact.manifest, evaluation_summary=summary)
        if result.decision.promote:
            record = runtime.activate_private_model(
                record.model_id,
                promotion_authorized=True,
                evaluation_summary=summary,
            )
        if record.state not in {ModelState.SHADOW, ModelState.ACTIVE}:
            raise RuntimeError("factory adoption produced invalid model state")
        return record

    def adapt(
        self,
        *,
        request: TrainingRequest,
        corpus: TrainingCorpus,
        tokenizer: NativeTokenizer,
        adaptation_reason: str | None = None,
        cognitive_reference_loss: float | None = None,
    ) -> FactoryResult:
        """Create a candidate successor from a verified same-organism parent.

        The parent remains untouched in the registry and artifact store until the
        caller independently accepts the returned promotion decision.
        """
        if request.parent_model_id is None:
            raise ValueError("adaptation request requires parent_model_id")
        if adaptation_reason is not None and adaptation_reason != request.adaptation_reason:
            raise ValueError("adaptation reason does not match request")
        if request.organism_id != corpus.manifest.organism_id:
            raise ValueError("training request and corpus belong to different organisms")
        if request.corpus_hash != corpus.manifest.corpus_hash:
            raise ValueError("training request corpus hash mismatch")
        if request.tokenizer_hash != tokenizer.tokenizer_hash:
            raise ValueError("training request tokenizer hash mismatch")
        parent = self._store.get(request.parent_model_id)
        if parent.manifest.organism_id != request.organism_id:
            raise ValueError("parent model belongs to a different organism")
        encoded = encode_corpus(corpus, tokenizer, context_window=request.context_window)
        candidate = adapt_private_model(
            request=request,
            corpus=encoded,
            parent_artifact=parent,
            authority=self._authority,
            config=self._training_config,
            device=self._device,
        )
        evaluation, decision = evaluate_candidate(
            candidate.artifact,
            encoded,
            policy=self._promotion_policy,
            cognitive_reference_loss=cognitive_reference_loss,
            device=self._device,
        )
        self._store.put(candidate.artifact)
        return FactoryResult(candidate, evaluation, decision)
