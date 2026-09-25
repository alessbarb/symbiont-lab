from __future__ import annotations

import hashlib
import io
import math
from dataclasses import dataclass
from typing import Any

from symbiont.modeling.authority import (
    ModelArtifactManifest,
    ModelTrainingAuthority,
    TrainingAuthorization,
    TrainingRequest,
)

from .architectures import (
    architecture_spec_from_manifest,
    build_model,
    count_parameters,
    resolve_architecture_spec,
)
from .artifacts import ModelArtifact
from .dataset import EncodedCorpus, EncodedSplit


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    learning_rate: float = 3e-4
    batch_size: int = 16
    weight_decay: float = 0.01
    gradient_clip: float = 1.0
    patience: int = 4

    def __post_init__(self) -> None:
        for name, value, low, high in (
            ("learning_rate", self.learning_rate, 1e-6, 0.1),
            ("weight_decay", self.weight_decay, 0.0, 1.0),
            ("gradient_clip", self.gradient_clip, 0.01, 100.0),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not low <= float(value) <= high
            ):
                raise ValueError(f"{name} outside supported bounds")
        if (
            isinstance(self.batch_size, bool)
            or not isinstance(self.batch_size, int)
            or not 1 <= self.batch_size <= 512
        ):
            raise ValueError("batch_size must be within [1, 512]")
        if (
            isinstance(self.patience, bool)
            or not isinstance(self.patience, int)
            or not 1 <= self.patience <= 64
        ):
            raise ValueError("patience must be within [1, 64]")


@dataclass(frozen=True, slots=True)
class TrainingMetrics:
    mean_log_loss: float
    accuracy: float
    predictions: int


@dataclass(frozen=True, slots=True)
class TrainingResult:
    request: TrainingRequest
    authorization: TrainingAuthorization
    artifact: ModelArtifact
    train_metrics: TrainingMetrics
    validation_metrics: TrainingMetrics
    epochs_completed: int
    steps_completed: int
    validation_trace: tuple[TrainingMetrics, ...] = ()


def _torch() -> Any:
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "private-model training requires the optional 'modeling' dependency (torch)"
        ) from exc
    return torch, F


def _batch_tensors(sequences, *, pad_id: int, context_window: int, device, torch):
    usable = [tuple(sequence[: context_window + 1]) for sequence in sequences if len(sequence) >= 2]
    if not usable:
        raise ValueError("training batch contains no usable sequences")
    max_len = max(len(sequence) for sequence in usable)
    inputs = torch.full((len(usable), max_len - 1), pad_id, dtype=torch.long, device=device)
    targets = torch.full((len(usable), max_len - 1), -100, dtype=torch.long, device=device)
    mask = torch.zeros((len(usable), max_len - 1), dtype=torch.bool, device=device)
    for row, sequence in enumerate(usable):
        source = sequence[:-1]
        target = sequence[1:]
        inputs[row, : len(source)] = torch.tensor(source, dtype=torch.long, device=device)
        targets[row, : len(target)] = torch.tensor(target, dtype=torch.long, device=device)
        mask[row, : len(source)] = True
    return inputs, targets, mask


def evaluate_model(
    model, split: EncodedSplit, *, pad_id: int, context_window: int, device=None
) -> TrainingMetrics:
    """Evaluate only causal outcome targets, never record grammar."""
    torch, F = _torch()
    if device is None:
        device = next(model.parameters()).device
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total = 0
    with torch.no_grad():
        for sequence, positions in zip(split.sequences, split.outcome_target_positions):
            bounded = tuple(sequence[: context_window + 1])
            valid_positions = tuple(
                position for position in positions if 0 <= position < len(bounded) - 1
            )
            if not valid_positions:
                continue
            inputs = torch.tensor([bounded[:-1]], dtype=torch.long, device=device)
            attention = torch.ones_like(inputs, dtype=torch.bool)
            logits = model(inputs, attention_mask=attention)[0]
            indices = torch.tensor(valid_positions, dtype=torch.long, device=device)
            selected_logits = logits.index_select(0, indices)
            targets = torch.tensor(
                [bounded[position + 1] for position in valid_positions],
                dtype=torch.long,
                device=device,
            )
            losses = F.cross_entropy(selected_logits, targets, reduction="sum")
            total_loss += float(losses.item())
            predictions = selected_logits.argmax(dim=-1)
            total_correct += int((predictions == targets).sum().item())
            total += len(valid_positions)
    if total < 1:
        raise ValueError("evaluation split contains no outcome predictions")
    return TrainingMetrics(total_loss / total, total_correct / total, total)


def _serialize_weights(model) -> bytes:
    torch, _ = _torch()
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    return buffer.getvalue()


def _load_parent_state(
    parent: ModelArtifact, *, request: TrainingRequest, corpus: EncodedCorpus, model, torch
) -> None:
    manifest = parent.manifest
    if manifest.organism_id != request.organism_id:
        raise ValueError("parent model belongs to a different organism")
    if request.parent_model_id != manifest.model_id:
        raise ValueError("parent model id does not match the supplied artifact")
    if manifest.architecture_id is not request.architecture_id:
        raise ValueError("parent architecture is incompatible")
    if manifest.objective is not request.objective:
        raise ValueError("parent objective is incompatible")
    if (
        manifest.tokenizer_hash != request.tokenizer_hash
        or manifest.tokenizer_hash != corpus.tokenizer_hash
    ):
        raise ValueError("parent tokenizer is incompatible")
    if manifest.context_window != request.context_window:
        raise ValueError("parent context window is incompatible")
    if manifest.parameter_count != count_parameters(model):
        raise ValueError("parent parameter shape is incompatible")
    buffer = io.BytesIO(parent.weights)
    try:
        state = torch.load(buffer, map_location="cpu", weights_only=True)
    except TypeError:  # pragma: no cover - older supported torch variants
        buffer.seek(0)
        state = torch.load(buffer, map_location="cpu")  # nosec B614
    except Exception as exc:
        raise ValueError("parent model weights are corrupt or not loadable") from exc
    try:
        model.load_state_dict(state, strict=True)
    except (TypeError, RuntimeError, ValueError) as exc:
        raise ValueError("parent model weights are structurally incompatible") from exc


def _train_private_model(
    *,
    request: TrainingRequest,
    corpus: EncodedCorpus,
    authority: ModelTrainingAuthority,
    config: TrainingConfig | None = None,
    device: str = "cpu",
    parent_artifact: ModelArtifact | None = None,
) -> TrainingResult:
    """Train one deterministic private candidate, optionally from a verified parent."""

    if corpus.corpus_hash != request.corpus_hash or corpus.tokenizer_hash != request.tokenizer_hash:
        raise ValueError("request hashes do not match encoded corpus")
    authorization = authority.authorize(
        request,
        corpus_records=len(corpus.train.sequences)
        + len(corpus.validation.sequences)
        + len(corpus.test.sequences),
    )
    selected_config = config or TrainingConfig()
    torch, F = _torch()
    torch.manual_seed(request.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(request.seed)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except TypeError:  # pragma: no cover - older supported torch variants
        torch.use_deterministic_algorithms(True)

    resolved_device = torch.device(device)
    resolved_spec = (
        architecture_spec_from_manifest(parent_artifact.manifest)
        if parent_artifact is not None
        else resolve_architecture_spec(
            request.architecture_id,
            vocab_size=corpus.vocab_size,
            parameter_ceiling=authorization.parameter_ceiling,
        )
    )
    model = build_model(
        request.architecture_id,
        vocab_size=corpus.vocab_size,
        context_window=request.context_window,
        pad_id=corpus.pad_id,
        spec=resolved_spec,
    ).to(resolved_device)
    parameter_count = count_parameters(model)
    if parameter_count > authorization.parameter_ceiling:
        raise ValueError(
            f"architecture parameter count {parameter_count} exceeds authorized ceiling {authorization.parameter_ceiling}"
        )
    if parent_artifact is not None:
        _load_parent_state(
            parent_artifact, request=request, corpus=corpus, model=model, torch=torch
        )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(selected_config.learning_rate),
        weight_decay=float(selected_config.weight_decay),
    )
    generator = torch.Generator(device="cpu")
    generator.manual_seed(request.seed)
    best_state: dict[str, Any] | None = None
    best_validation = float("inf")
    stale_checks = 0
    validation_trace: list[TrainingMetrics] = []
    steps = 0
    epochs_completed = 0
    last_validation_step = 0
    stop_requested = False
    validation_interval_steps = (
        max(1, min(12, authorization.step_ceiling // 4 or 1))
        if request.autonomous_stopping
        else None
    )

    def capture_validation() -> bool:
        nonlocal best_validation, best_state, stale_checks, last_validation_step
        validation = evaluate_model(
            model,
            corpus.validation,
            pad_id=corpus.pad_id,
            context_window=request.context_window,
            device=resolved_device,
        )
        validation_trace.append(validation)
        last_validation_step = steps
        min_gain = (
            float(request.requested_min_validation_gain) if request.autonomous_stopping else 1e-9
        )
        patience = (
            int(request.requested_patience)
            if request.autonomous_stopping
            else int(selected_config.patience)
        )
        if validation.mean_log_loss + min_gain < best_validation:
            best_validation = validation.mean_log_loss
            best_state = {
                name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()
            }
            stale_checks = 0
            return False
        stale_checks += 1
        return stale_checks >= patience

    train_sequences = corpus.train.sequences
    for epoch in range(authorization.epoch_ceiling):
        if steps >= authorization.step_ceiling:
            break
        order = torch.randperm(len(train_sequences), generator=generator).tolist()
        model.train()
        for start in range(0, len(order), selected_config.batch_size):
            if steps >= authorization.step_ceiling:
                break
            batch_indices = order[start : start + selected_config.batch_size]
            batch = tuple(train_sequences[index] for index in batch_indices)
            batch_positions = tuple(
                corpus.train.outcome_target_positions[index] for index in batch_indices
            )
            inputs, targets, mask = _batch_tensors(
                batch,
                pad_id=corpus.pad_id,
                context_window=request.context_window,
                device=resolved_device,
                torch=torch,
            )
            outcome_mask = torch.zeros_like(targets, dtype=torch.bool)
            for row, positions in enumerate(batch_positions):
                for position in positions:
                    if 0 <= position < outcome_mask.size(1):
                        outcome_mask[row, position] = True
            valid = outcome_mask & (targets != -100)
            if not bool(valid.any()):
                continue
            optimizer.zero_grad(set_to_none=True)
            logits = model(inputs, attention_mask=mask)
            loss = F.cross_entropy(
                logits[valid],
                targets[valid],
            )
            if not bool(torch.isfinite(loss).item()):
                raise RuntimeError("non-finite private model training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(selected_config.gradient_clip))
            optimizer.step()
            steps += 1
            if (
                request.autonomous_stopping
                and validation_interval_steps is not None
                and (steps % validation_interval_steps == 0 or steps >= authorization.step_ceiling)
            ):
                if capture_validation():
                    stop_requested = True
                    break

        epochs_completed = epoch + 1
        if request.autonomous_stopping:
            if steps > last_validation_step and capture_validation():
                stop_requested = True
            if stop_requested:
                break
        else:
            if capture_validation():
                break

    if best_state is None:
        raise RuntimeError("private model training did not produce a finite validation checkpoint")
    model.load_state_dict(best_state)
    model.to(resolved_device)
    train_metrics = evaluate_model(
        model,
        corpus.train,
        pad_id=corpus.pad_id,
        context_window=request.context_window,
        device=resolved_device,
    )
    validation_metrics = evaluate_model(
        model,
        corpus.validation,
        pad_id=corpus.pad_id,
        context_window=request.context_window,
        device=resolved_device,
    )
    weights = _serialize_weights(model.to("cpu"))
    if len(weights) > authorization.artifact_byte_ceiling:
        raise ValueError("trained model artifact exceeds authority byte ceiling")
    weights_hash = hashlib.sha256(weights).hexdigest()
    manifest = ModelArtifactManifest.build(
        request=request,
        parameter_count=parameter_count,
        weights_hash=weights_hash,
        artifact_bytes=len(weights),
        parent=parent_artifact.manifest if parent_artifact is not None else None,
        authorization=authorization,
        adaptation_cost_epochs=epochs_completed if parent_artifact is not None else 0,
        adaptation_cost_steps=steps if parent_artifact is not None else 0,
        resolved_embedding_dim=resolved_spec.embedding_dim,
        resolved_hidden_dim=resolved_spec.hidden_dim,
        resolved_layers=resolved_spec.layers,
        resolved_heads=resolved_spec.heads,
        resolved_feedforward_dim=resolved_spec.feedforward_dim,
    )
    artifact = ModelArtifact(manifest=manifest, weights=weights)
    return TrainingResult(
        request=request,
        authorization=authorization,
        artifact=artifact,
        train_metrics=train_metrics,
        validation_metrics=validation_metrics,
        epochs_completed=epochs_completed,
        steps_completed=steps,
        validation_trace=tuple(validation_trace),
    )


def train_private_model(
    *,
    request: TrainingRequest,
    corpus: EncodedCorpus,
    authority: ModelTrainingAuthority,
    config: TrainingConfig | None = None,
    device: str = "cpu",
) -> TrainingResult:
    """Train from a cold start; parent-bearing requests use ``adapt_private_model``."""

    if request.parent_model_id is not None:
        raise ValueError("parent-bearing requests must use adapt_private_model")
    return _train_private_model(
        request=request, corpus=corpus, authority=authority, config=config, device=device
    )


def adapt_private_model(
    *,
    request: TrainingRequest,
    corpus: EncodedCorpus,
    parent_artifact: ModelArtifact,
    authority: ModelTrainingAuthority,
    config: TrainingConfig | None = None,
    device: str = "cpu",
) -> TrainingResult:
    """Boundedly update a same-organism parent artifact using permitted new evidence."""

    if request.parent_model_id is None:
        raise ValueError("adaptation requires a parent_model_id")
    if request.adaptation_reason is None:
        raise ValueError("adaptation requires an explicit reason")
    if not isinstance(parent_artifact, ModelArtifact):
        raise ValueError("parent_artifact must be a verified ModelArtifact")
    return _train_private_model(
        request=request,
        corpus=corpus,
        authority=authority,
        config=config,
        device=device,
        parent_artifact=parent_artifact,
    )
