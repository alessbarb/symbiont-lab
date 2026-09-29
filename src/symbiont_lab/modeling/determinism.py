"""Deterministic private-model training settings shared by runtime and equivalence tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrainingDeterminism:
    seed: int
    cpu_threads: int | None = None
    interop_threads: int | None = None
    deterministic_algorithms: bool = True


def configure_training_determinism(config: TrainingDeterminism) -> dict[str, object]:
    """Apply the Lab deterministic PyTorch contract and return effective settings."""
    import torch

    if config.cpu_threads is not None:
        torch.set_num_threads(int(config.cpu_threads))
    if config.interop_threads is not None:
        try:
            torch.set_num_interop_threads(int(config.interop_threads))
        except RuntimeError:
            pass

    torch.manual_seed(int(config.seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(config.seed))

    if config.deterministic_algorithms:
        try:
            torch.use_deterministic_algorithms(True, warn_only=False)
        except TypeError:  # pragma: no cover
            torch.use_deterministic_algorithms(True)

    return {
        "seed": int(config.seed),
        "cpu_threads": int(torch.get_num_threads()),
        "interop_threads": int(torch.get_num_interop_threads()),
        "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
    }
