"""Canonical first-birth cognition for resident Symbionts.

Genome v2 supplies inherited developmental rules. The germinal cognitive graph
is intentionally empty; body surfaces are connected independently after birth.
"""
from __future__ import annotations

from importlib import resources
import json
from typing import Any

from symbiont.genetics.genome import Genome, GenomeCodec

from .graph import CognitiveGraph, load_graph_definition
from .limits import KernelLimits

_COGNITION_PACKAGE = "symbiont.cognition"
_GENETICS_PACKAGE = "symbiont.genetics"


def _load_json(package: str, relative: str) -> dict[str, Any]:
    text = resources.files(package).joinpath(relative).read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"canonical resource {relative!r} must contain a JSON object")
    return payload


def load_base_genome(
    *, kernel_limits: KernelLimits, running_version: tuple[int, int, int]
) -> Genome:
    codec = GenomeCodec()
    genome = codec.load(_load_json(_GENETICS_PACKAGE, "defaults/base-genome-v2.json"))
    codec.validate(genome, kernel_limits, running_version=running_version)
    return genome


def load_base_graph(*, kernel_limits: KernelLimits) -> CognitiveGraph:
    return load_graph_definition(
        _load_json(_COGNITION_PACKAGE, "defaults/base-graph.json"),
        kernel_limits=kernel_limits,
    )


def load_base_cognition(
    *, kernel_limits: KernelLimits, running_version: tuple[int, int, int]
) -> tuple[Genome, CognitiveGraph]:
    return (
        load_base_genome(kernel_limits=kernel_limits, running_version=running_version),
        load_base_graph(kernel_limits=kernel_limits),
    )


__all__ = ["load_base_cognition", "load_base_genome", "load_base_graph"]
