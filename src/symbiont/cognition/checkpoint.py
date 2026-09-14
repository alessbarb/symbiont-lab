from __future__ import annotations

from typing import Any

from .genome import Genome, GenomeCodec, GenomeError, _genome_to_plain_dict
from .limits import KernelLimits


def export_genome_checkpoint(genome: Genome | None) -> dict[str, Any] | None:
    """None in, None out -- an organism with no genome checkpoints
    nothing new here. Genome content is small, bounded, declarative
    config, not raw telemetry, so it is persisted in full (roadmap
    v0.55 design spec §3.5)."""
    if genome is None:
        return None
    payload = _genome_to_plain_dict(genome)
    payload["genome_hash"] = genome.genome_hash
    return payload


def restore_genome_checkpoint(
    payload: dict[str, Any] | None,
    *,
    kernel_limits: KernelLimits,
    running_version: tuple[int, int, int],
) -> Genome | None:
    """Re-validates fully (load + validate) on restore -- a checkpoint is
    untrusted input, same discipline as every other restore path in this
    codebase. Also recomputes genome_hash from the restored fields and
    rejects a mismatch against the persisted hash, defending against a
    hand-edited or corrupted checkpoint claiming a genome it doesn't
    actually match."""
    if payload is None:
        return None
    if not isinstance(payload, dict) or "genome_hash" not in payload:
        raise GenomeError("genome checkpoint payload must be an object with a genome_hash")
    persisted_hash = payload["genome_hash"]
    genome_fields = {key: value for key, value in payload.items() if key != "genome_hash"}
    codec = GenomeCodec()
    genome = codec.load(genome_fields)
    if genome.genome_hash != persisted_hash:
        raise GenomeError("genome checkpoint hash mismatch -- payload may be corrupted or tampered")
    codec.validate(genome, kernel_limits, running_version=running_version)
    return genome
