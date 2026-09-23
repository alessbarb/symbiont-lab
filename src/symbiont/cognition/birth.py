"""Canonical first-birth cognition for resident Symbionts.

The genome supplies inherited developmental rules. The germinal graph is
intentionally empty: opaque SENSE nodes are admitted from developed host
percepts during life, and higher-order structure is learned from there.
Checkpoints always take precedence after first birth.
"""

from __future__ import annotations

from importlib import resources
import json
from typing import Any

from symbiont.actuation.constitution import ActuatorConstitution, derive_actuator_constitution

from .genome import Genome, GenomeCodec, legacy_validation_version
from .graph import CognitiveGraph, load_graph_definition
from .limits import KernelLimits

_DEFAULTS_PACKAGE = "symbiont.cognition"
_DEFAULTS_DIR = "defaults"


def _load_default_json(filename: str) -> dict[str, Any]:
    text = (
        resources.files(_DEFAULTS_PACKAGE)
        .joinpath(_DEFAULTS_DIR)
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"canonical cognition resource {filename!r} must contain a JSON object")
    return payload


def load_base_genome(
    *, kernel_limits: KernelLimits, running_version: tuple[int, int, int]
) -> Genome:
    """Load and validate the canonical inherited genome."""
    codec = GenomeCodec()
    genome = codec.load(_load_default_json("base-genome.json"))
    # NOTE(migration): Explicitly migrate the checked-in pre-0.60 canonical genome at birth.
    # It remains byte/hash compatible for historical studies, while direct
    # GenomeCodec validation stays strict for arbitrary user payloads.
    validation_version = legacy_validation_version(genome.kernel_compatibility, running_version)
    codec.validate(genome, kernel_limits, running_version=validation_version)
    return genome


def load_base_graph(*, kernel_limits: KernelLimits) -> CognitiveGraph:
    """Load the canonical tabula-rasa graph."""
    return load_graph_definition(
        _load_default_json("base-graph.json"),
        kernel_limits=kernel_limits,
    )


def load_base_cognition(
    *, kernel_limits: KernelLimits, running_version: tuple[int, int, int]
) -> tuple[Genome, CognitiveGraph]:
    """Return the canonical genome and germinal graph for a first birth."""
    return (
        load_base_genome(kernel_limits=kernel_limits, running_version=running_version),
        load_base_graph(kernel_limits=kernel_limits),
    )


def load_actuator_constitution(genome: Genome) -> ActuatorConstitution:
    """Derive this organism's fixed motor body from its own genome.

    Unlike ``load_base_genome``/``load_base_cognition``, this is not
    canonical-first-birth-only: it must be called for every organism,
    including descendants, using that organism's own (possibly mutated)
    genome — the constitution is constitutional per-individual, not a
    shared canonical default.
    """
    return derive_actuator_constitution(genome.motor)
