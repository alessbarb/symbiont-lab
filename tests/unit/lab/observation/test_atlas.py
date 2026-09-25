import copy

import pytest

from symbiont_lab.observation.atlas import build_cognitive_atlas, diff_cognitive_atlas


def _snapshot():
    return {
        "tick": 77,
        "topology": {
            "nodes": [
                {"id": "concept.1", "kind": "concept"},
                {"id": "predictor.1", "kind": "predictor", "predictsNodeId": "concept.1"},
            ],
            "edges": [
                {"sourceId": "predictor.1", "targetId": "concept.1", "kind": "excitatory", "weight": 0.4},
            ],
        },
        "motor_competences": [
            {
                "competence_id": "competence.7",
                "controller_id": "controller.2",
                "effect_id": "effect.3",
                "maturity": "established",
                "support": 12,
            },
            {
                "competence_id": "competence.8",
                "controller_id": "controller.9",
                "effect_id": None,
                "maturity": "candidate",
                "support": 1,
            },
        ],
        "effects": [
            {"effect_id": "effect.3", "feature_refs": ["signal.1"], "support": 12, "confidence": 0.7},
        ],
        "embodiment": {
            "bindings": [
                {
                    "competence_id": "competence.7",
                    "surface_fingerprint": "humanoid:v1",
                    "effect_id": "effect.3",
                    "reliability": 0.6,
                    "controllability": 0.5,
                    "last_evidence_tick": 76,
                },
            ],
        },
    }


def test_build_cognitive_atlas_classifies_every_domain():
    atlas = build_cognitive_atlas(_snapshot())

    kinds = {node.id: node.kind for node in atlas.nodes}
    assert kinds["concept.1"] == "concept"
    assert kinds["predictor.1"] == "predictor"
    assert kinds["competence.7"] == "motor_competence"
    assert kinds["competence.8"] == "motor_competence"
    assert kinds["effect.3"] == "effect"
    assert kinds["binding.competence.7"] == "embodiment_binding"

    edge_kinds = {(edge.source_id, edge.target_id): edge.kind for edge in atlas.edges}
    assert edge_kinds[("predictor.1", "concept.1")] == "excitatory"
    assert edge_kinds[("competence.7", "effect.3")] == "produces"
    assert edge_kinds[("binding.competence.7", "competence.7")] == "bound_to"
    # competence.8 has no resolved effect -> no fabricated produces edge
    assert ("competence.8", None) not in edge_kinds

    edges_by_id = {(edge.source_id, edge.target_id): edge for edge in atlas.edges}
    produces_evidence = edges_by_id[("competence.7", "effect.3")].metadata["evidence"]
    assert produces_evidence["source"] == "sensorimotor_model"
    assert produces_evidence["observations"] == 12
    bound_evidence = edges_by_id[("binding.competence.7", "competence.7")].metadata["evidence"]
    assert bound_evidence["source"] == "embodiment_execution_binding"
    assert bound_evidence["last_tick"] == 76


def test_build_cognitive_atlas_motor_capability_metric_is_known_vs_bound():
    atlas = build_cognitive_atlas(_snapshot())

    assert atlas.metrics["motor_capability"] == {"supported": True, "known": 2, "bound": 1}


def test_build_cognitive_atlas_distinguishes_absent_from_empty_motor_knowledge():
    absent = build_cognitive_atlas({"tick": 1})
    assert absent.metrics["motor_capability"] == {"supported": False, "known": None, "bound": None}

    empty = build_cognitive_atlas({"tick": 1, "motor_competences": []})
    assert empty.metrics["motor_capability"] == {"supported": True, "known": 0, "bound": 0}


def test_build_cognitive_atlas_never_mutates_input_snapshot():
    snapshot = _snapshot()
    before = copy.deepcopy(snapshot)

    build_cognitive_atlas(snapshot)

    assert snapshot == before


def test_build_cognitive_atlas_rejects_non_mapping():
    with pytest.raises(TypeError):
        build_cognitive_atlas([])


def _reembodiment_snapshots():
    before = build_cognitive_atlas(_snapshot())

    after_raw = {
        "tick": 200,
        "motor_competences": [
            {"competence_id": "competence.7", "effect_id": "effect.3", "maturity": "established", "support": 12},
            {"competence_id": "competence.8", "effect_id": None, "maturity": "candidate", "support": 1},
            {"competence_id": "competence.9", "effect_id": "effect.3", "maturity": "candidate", "support": 2},
        ],
        "effects": [
            {"effect_id": "effect.3", "feature_refs": ["signal.1"], "support": 14, "confidence": 0.8},
        ],
        "embodiment": {
            # competence.7's binding did not survive the body swap; a fresh
            # one was discovered for the newly-emerged competence.9.
            "bindings": [
                {
                    "competence_id": "competence.9",
                    "surface_fingerprint": "crawler:v1",
                    "effect_id": "effect.3",
                    "reliability": 0.4,
                    "controllability": 0.3,
                    "last_evidence_tick": 199,
                },
            ],
        },
    }
    after = build_cognitive_atlas(after_raw)
    return before, after


def test_diff_cognitive_atlas_reembodiment_preserves_knowledge_but_not_bindings():
    before, after = _reembodiment_snapshots()

    diff = diff_cognitive_atlas(before, after)

    assert "competence.9" in diff.nodes_added
    assert "binding.competence.7" in diff.nodes_removed

    assert diff.metrics["knowledge_preserved"] == {"count": 2, "ratio": 1.0}
    assert diff.metrics["embodiment_mappings_preserved"] == {"count": 0, "ratio": 0.0}
    assert diff.metrics["competences_immediately_usable"] == {"count": 0, "ratio": 0.0}
    assert diff.metrics["competences_requiring_remapping"] == {"count": 2, "ratio": 1.0}


def test_diff_cognitive_atlas_identical_snapshots_report_no_changes():
    atlas = build_cognitive_atlas(_snapshot())

    diff = diff_cognitive_atlas(atlas, atlas)

    assert diff.nodes_added == ()
    assert diff.nodes_removed == ()
    assert diff.edges_added == ()
    assert diff.edges_removed == ()
    assert diff.metrics["knowledge_preserved"]["ratio"] == 1.0


def test_diff_cognitive_atlas_handles_no_prior_competences():
    empty = build_cognitive_atlas({"tick": 0})
    atlas = build_cognitive_atlas(_snapshot())

    diff = diff_cognitive_atlas(empty, atlas)

    assert diff.metrics["knowledge_preserved"] == {"count": 0, "ratio": None}
