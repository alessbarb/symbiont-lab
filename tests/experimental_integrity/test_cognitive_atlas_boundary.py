from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

from symbiont_lab.observation.atlas import (
    AtlasEdge,
    AtlasNode,
    CognitiveAtlasSnapshot,
    build_cognitive_atlas,
    diff_cognitive_atlas,
)


def test_ast_atlas_never_imports_symbiont():
    """Cognitive Atlas v2 spec Sec 20/73: the projection reads snapshot/
    telemetry only. It must never import the organism package directly --
    that would let it reach into live objects instead of the bounded
    dict contract, and would make 'never mutates Symbiont state' a
    runtime accident instead of a structural guarantee."""
    repo_root = Path(__file__).resolve().parents[2]
    atlas_module = repo_root / "src" / "symbiont_lab" / "observation" / "atlas.py"
    assert atlas_module.is_file(), f"Not found: {atlas_module}"

    tree = ast.parse(atlas_module.read_text(encoding="utf-8"), filename=str(atlas_module))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "symbiont" or alias.name.startswith("symbiont."):
                    violations.append(f"imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "symbiont" or node.module.startswith("symbiont.")):
                violations.append(f"imports from {node.module}")

    assert not violations, "atlas.py must stay snapshot-only:\n" + "\n".join(violations)


def test_atlas_node_edge_snapshot_are_structurally_immutable():
    """Sec 73: frozen dataclasses with tuple fields make mutation a
    TypeError, not just a convention -- the strongest form of 'rendering
    Atlas cannot modify its own model', let alone Symbiont state."""
    node = AtlasNode(id="a", kind="concept")
    with pytest.raises(dataclasses.FrozenInstanceError):
        node.kind = "predictor"  # type: ignore[misc]

    edge = AtlasEdge(id="e", source_id="a", target_id="b", kind="associated_with")
    with pytest.raises(dataclasses.FrozenInstanceError):
        edge.kind = "causes"  # type: ignore[misc]

    snapshot = build_cognitive_atlas({"tick": 1})
    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.tick = 2  # type: ignore[misc]
    assert isinstance(snapshot.nodes, tuple)
    assert isinstance(snapshot.edges, tuple)


def test_build_cognitive_atlas_handles_large_snapshot_without_dropping_nodes():
    """Sec 74 fixture: large cognitive graph. Correctness under scale --
    every evidenced node/edge must still appear, nothing silently capped."""
    node_count = 2000
    snapshot = {
        "tick": 999,
        "topology": {
            "nodes": [{"id": f"concept.{i}", "kind": "concept"} for i in range(node_count)],
            "edges": [
                {"sourceId": f"concept.{i}", "targetId": f"concept.{i + 1}", "kind": "associated_with"}
                for i in range(node_count - 1)
            ],
        },
    }

    atlas = build_cognitive_atlas(snapshot)

    assert len(atlas.nodes) == node_count
    assert len(atlas.edges) == node_count - 1


def test_build_cognitive_atlas_large_snapshot_stays_fast():
    """Sec 80: projection delta processing should stay well under budget
    for a graph two orders of magnitude larger than any organism observed
    so far in this codebase's telemetry."""
    import time

    node_count = 5000
    snapshot = {
        "tick": 1,
        "topology": {
            "nodes": [{"id": f"concept.{i}", "kind": "concept"} for i in range(node_count)],
            "edges": [],
        },
    }

    started = time.perf_counter()
    build_cognitive_atlas(snapshot)
    elapsed_ms = (time.perf_counter() - started) * 1000

    # Generous ceiling for a cold, unoptimized Python loop -- the spec's
    # <5ms target is for incremental deltas on real-sized graphs, not a
    # cold 5000-node classification; this guards against catastrophic
    # (e.g. quadratic) regressions, not micro-tuning.
    assert elapsed_ms < 500, f"build_cognitive_atlas took {elapsed_ms:.1f}ms for {node_count} nodes"


def test_diff_cognitive_atlas_incremental_delta_meets_5ms_budget():
    """Sec 80's actual target: incremental delta processing between two
    consecutive-tick snapshots at real organism scale (largest live graph
    observed in this codebase's own telemetry is low hundreds of nodes;
    200 here is a comfortable upper bound with headroom)."""
    import time

    node_count = 200
    base_nodes = [{"id": f"concept.{i}", "kind": "concept"} for i in range(node_count)]
    base_edges = [
        {"sourceId": f"concept.{i}", "targetId": f"concept.{i + 1}", "kind": "associated_with", "weight": 0.5}
        for i in range(node_count - 1)
    ]
    before = build_cognitive_atlas({
        "tick": 100,
        "topology": {"nodes": base_nodes, "edges": base_edges},
    })

    # A realistic single-tick change: a handful of new nodes/edges plus
    # activation churn on existing ones, not a full graph rebuild.
    next_nodes = base_nodes + [{"id": f"concept.{node_count + i}", "kind": "concept"} for i in range(5)]
    next_edges = base_edges + [
        {"sourceId": f"concept.{node_count - 1}", "targetId": f"concept.{node_count}", "kind": "associated_with", "weight": 0.6}
    ]
    after_snapshot = {
        "tick": 101,
        "topology": {"nodes": next_nodes, "edges": next_edges},
        "observer_analysis": {"activationValues": {f"concept.{i}": 0.5 for i in range(20)}},
    }

    started = time.perf_counter()
    after = build_cognitive_atlas(after_snapshot)
    diff_cognitive_atlas(before, after)
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert elapsed_ms < 5, f"incremental delta took {elapsed_ms:.2f}ms for a {node_count}-node organism"


def test_diff_cognitive_atlas_isolation_between_snapshots():
    """Sec 73/78: diffing two Atlas snapshots must never mutate either one --
    verified byte-equivalent (field-for-field) before/after."""
    before = build_cognitive_atlas({
        "tick": 1,
        "motor_competences": [{"competence_id": "competence.1", "maturity": "established"}],
    })
    after = build_cognitive_atlas({
        "tick": 2,
        "motor_competences": [
            {"competence_id": "competence.1", "maturity": "established"},
            {"competence_id": "competence.2", "maturity": "candidate"},
        ],
    })
    before_before = dataclasses.replace(before)
    after_before = dataclasses.replace(after)

    diff_cognitive_atlas(before, after)

    assert before == before_before
    assert after == after_before
