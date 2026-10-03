"""Checkpoint codecs for Genome v2, expression and germline."""

from __future__ import annotations

from typing import Any, Mapping

from .expression import GeneExpressionState, restore_expression_state
from .genome import Genome, GenomeCodec, GenomeError, _genome_to_plain_dict
from .germline import EpigeneticMark, GermlineState
from .schema import DEFAULT_GENOME_SCHEMA, GenomeSchema


def export_genome(genome: Genome) -> dict[str, Any]:
    payload = _genome_to_plain_dict(genome)
    payload["genome_hash"] = genome.genome_hash
    payload["genotype_hash"] = genome.genotype_hash
    return payload


def restore_genome(
    payload: Mapping[str, object],
    *,
    kernel_limits: Any,
    running_version: tuple[int, int, int],
    schema: GenomeSchema = DEFAULT_GENOME_SCHEMA,
) -> Genome:
    if not isinstance(payload, Mapping):
        raise GenomeError("genome checkpoint must be an object")
    persisted_hash = payload.get("genome_hash")
    persisted_genotype = payload.get("genotype_hash")
    if not isinstance(persisted_hash, str) or not isinstance(persisted_genotype, str):
        raise GenomeError("genome checkpoint hashes are required")
    fields = {
        key: value for key, value in payload.items() if key not in {"genome_hash", "genotype_hash"}
    }
    genome = GenomeCodec(schema).load(fields)
    if genome.genome_hash != persisted_hash:
        raise GenomeError("genome checkpoint hash mismatch")
    if genome.genotype_hash != persisted_genotype:
        raise GenomeError("genotype checkpoint hash mismatch")
    GenomeCodec(schema).validate(genome, kernel_limits, running_version=running_version)
    return genome


def export_expression(state: GeneExpressionState) -> dict[str, object]:
    return state.as_dict()


def restore_expression(payload: Mapping[str, object], genome: Genome) -> GeneExpressionState:
    return restore_expression_state(payload, genome)


def _mark_to_dict(mark: EpigeneticMark) -> dict[str, object]:
    return {
        "locus": mark.locus,
        "delta": mark.delta,
        "strength": mark.strength,
        "generations_left": mark.generations_left,
    }


def _mark_from_dict(payload: Mapping[str, object]) -> EpigeneticMark:
    required = {"locus", "delta", "strength", "generations_left"}
    if set(payload) != required:
        raise ValueError("epigenetic mark keys mismatch")
    locus = payload["locus"]
    delta = payload["delta"]
    strength = payload["strength"]
    generations = payload["generations_left"]
    if not isinstance(locus, str):
        raise ValueError("epigenetic locus must be a string")
    if isinstance(delta, bool) or not isinstance(delta, (int, float)):
        raise ValueError("epigenetic delta must be numeric")
    if isinstance(strength, bool) or not isinstance(strength, (int, float)):
        raise ValueError("epigenetic strength must be numeric")
    if isinstance(generations, bool) or not isinstance(generations, int):
        raise ValueError("generations_left must be int")
    return EpigeneticMark(
        locus=locus,
        delta=float(delta),
        strength=float(strength),
        generations_left=generations,
    )


def export_germline(state: GermlineState) -> dict[str, object]:
    return {
        "birth_expression": dict(state.birth_expression),
        "inherited_marks": [
            _mark_to_dict(mark) for _, mark in sorted(state.inherited_marks.items())
        ],
        "acquired_marks": [_mark_to_dict(mark) for _, mark in sorted(state.acquired_marks.items())],
        "acquired_capture_enabled": state.acquired_capture_enabled,
    }


def restore_germline(
    payload: Mapping[str, object],
    genome: Genome,
    *,
    schema: GenomeSchema = DEFAULT_GENOME_SCHEMA,
) -> GermlineState:
    required = {
        "birth_expression",
        "inherited_marks",
        "acquired_marks",
        "acquired_capture_enabled",
    }
    if set(payload) != required:
        raise ValueError("germline checkpoint keys mismatch")
    birth = payload["birth_expression"]
    inherited = payload["inherited_marks"]
    acquired = payload["acquired_marks"]
    enabled = payload["acquired_capture_enabled"]
    if (
        not isinstance(birth, Mapping)
        or not isinstance(inherited, list)
        or not isinstance(acquired, list)
    ):
        raise ValueError("malformed germline checkpoint")
    if not isinstance(enabled, bool):
        raise ValueError("acquired_capture_enabled must be bool")
    schema.validate_flat(birth)
    inherited_marks = tuple(
        _mark_from_dict(item) for item in inherited if isinstance(item, Mapping)
    )
    acquired_marks = tuple(_mark_from_dict(item) for item in acquired if isinstance(item, Mapping))
    for mark in (*inherited_marks, *acquired_marks):
        if not schema.spec(mark.locus).regulable:
            raise ValueError(f"epigenetic mark targets non-regulable locus {mark.locus!r}")
    state = GermlineState.from_genome(
        genome,
        inherited_marks=inherited_marks,
        acquired_capture_enabled=enabled,
    )
    state.birth_expression = {str(k): v for k, v in birth.items()}
    state.acquired_marks = {mark.locus: mark for mark in acquired_marks}
    return state


__all__ = [
    "export_expression",
    "export_genome",
    "export_germline",
    "restore_expression",
    "restore_genome",
    "restore_germline",
]
