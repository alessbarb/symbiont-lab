from __future__ import annotations

from typing import Any

from .dataset import EncodedSplit
from .trainer import TrainingMetrics


def _torch() -> Any:
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "private-model evaluation requires the optional 'modeling' dependency (torch)"
        ) from exc
    return torch, F


def evaluate_outcome_model(
    model,
    split: EncodedSplit,
    *,
    pad_id: int,
    context_window: int,
    device=None,
) -> TrainingMetrics:
    """Held-out metric restricted to outcome targets, never record grammar."""

    torch, F = _torch()
    if device is None:
        device = next(model.parameters()).device
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total = 0
    with torch.no_grad():
        for sequence, positions in zip(split.sequences, split.outcome_target_positions):
            if not positions:
                continue
            bounded = tuple(sequence[: context_window + 1])
            valid_positions = tuple(
                position for position in positions if position < len(bounded) - 1
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
            loss = F.cross_entropy(selected_logits, targets, reduction="sum")
            total_loss += float(loss.item())
            total_correct += int((selected_logits.argmax(dim=-1) == targets).sum().item())
            total += len(valid_positions)
    if total < 1:
        raise ValueError("evaluation split contains no outcome predictions")
    return TrainingMetrics(total_loss / total, total_correct / total, total)


__all__ = ["evaluate_outcome_model"]
