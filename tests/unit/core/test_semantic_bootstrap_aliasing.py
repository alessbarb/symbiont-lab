"""Regression test for the architectural decision behind resident.py's
--semantic-bootstrap flag: the native resident stays label-free by default
(discover_senses=True, bootstrap_semantic_senses=False), so an owner-authored
graph declaring semantic SENSE node ids like "system_load" legitimately never
receives a value unless the owner opts in -- at which point the semantic name
becomes a CognitiveBridge alias for the opaque developed identity (see
runtime.py's cognitive_aliases construction)."""

from __future__ import annotations

import json
from pathlib import Path

from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.graph import load_graph_definition
from symbiont.cognition.limits import KernelLimits
from symbiont.core.runtime import OrganismRuntime

_EXAMPLES = Path(__file__).resolve().parents[3] / "examples" / "cognition"


def _genome():
    payload = json.loads((_EXAMPLES / "genome.json").read_text(encoding="utf-8"))
    return GenomeCodec().load(payload)


def _graph():
    payload = json.loads((_EXAMPLES / "graph.json").read_text(encoding="utf-8"))
    return load_graph_definition(payload, kernel_limits=KernelLimits())


def _readouts_over_ticks(*, bootstrap_semantic_senses: bool, ticks: int) -> list[float]:
    runtime = OrganismRuntime(
        genome=_genome(),
        cognitive_graph=_graph(),
        discover_senses=True,
        bootstrap_semantic_senses=bootstrap_semantic_senses,
    )
    readouts = []
    for _ in range(ticks):
        result = runtime.tick()
        assert result.cognition is not None
        readouts.append(result.cognition.readouts.get("readout_pressure", 0.0))
    return readouts


def test_without_semantic_bootstrap_the_example_graph_stays_legitimately_disconnected():
    readouts = _readouts_over_ticks(bootstrap_semantic_senses=False, ticks=5)
    assert readouts == [0.0] * 5


def test_with_semantic_bootstrap_system_load_reaches_the_bridge():
    readouts = _readouts_over_ticks(bootstrap_semantic_senses=True, ticks=20)
    assert any(value != 0.0 for value in readouts)
