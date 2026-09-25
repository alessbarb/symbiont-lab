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


def test_build_cognitive_atlas_attaches_prediction_error_to_predictor_nodes():
    snapshot = _snapshot()
    snapshot["observer_analysis"] = {
        "activationValues": {"concept.1": 0.6, "predictor.1": 0.2},
        "predictionErrorValues": {"predictor.1": 0.08},
    }

    atlas = build_cognitive_atlas(snapshot)

    nodes_by_id = {node.id: node for node in atlas.nodes}
    assert nodes_by_id["predictor.1"].metadata["predictionError"] == 0.08
    assert nodes_by_id["predictor.1"].metadata["activation"] == 0.2
    assert nodes_by_id["concept.1"].metadata["activation"] == 0.6
    # concept nodes never carry a prediction error, only predictors do
    assert "predictionError" not in nodes_by_id["concept.1"].metadata

    assert atlas.metrics["prediction"] == {"predictors": 1, "pressure": 0.08}


def test_build_cognitive_atlas_prediction_metrics_default_when_no_errors_observed():
    atlas = build_cognitive_atlas(_snapshot())

    assert atlas.metrics["prediction"] == {"predictors": 1, "pressure": 0.0}


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


def test_build_cognitive_atlas_materializes_controllers_distinct_from_competences():
    atlas = build_cognitive_atlas(_snapshot())

    kinds = {node.id: node.kind for node in atlas.nodes}
    assert kinds["controller.2"] == "controller"
    assert kinds["controller.9"] == "controller"
    # controller is its own node, never folded into the competence node
    assert kinds["controller.2"] != kinds["competence.7"]

    controller_2 = next(node for node in atlas.nodes if node.id == "controller.2")
    assert controller_2.metadata["competence_count"] == 1

    edge_kinds = {(edge.source_id, edge.target_id): edge.kind for edge in atlas.edges}
    assert edge_kinds[("competence.7", "controller.2")] == "requires"
    assert edge_kinds[("competence.8", "controller.9")] == "requires"


def test_build_cognitive_atlas_controllers_absent_without_competences():
    atlas = build_cognitive_atlas({"tick": 1})

    assert not any(node.kind == "controller" for node in atlas.nodes)


def test_build_cognitive_atlas_derives_competence_state_from_real_fields():
    atlas = build_cognitive_atlas(_snapshot())

    states = {node.id: node.metadata["state"] for node in atlas.nodes if node.kind == "motor_competence"}
    # established maturity + reliability 0.6 (>=0.5) with a binding -> usable
    assert states["competence.7"] == "usable"
    # candidate maturity, no binding at all -> unbound
    assert states["competence.8"] == "unbound"


def test_build_cognitive_atlas_competence_state_calibrating_and_degraded():
    snapshot = _snapshot()
    # established but bound with low reliability -> degraded, not usable
    snapshot["embodiment"]["bindings"][0]["reliability"] = 0.2
    degraded_atlas = build_cognitive_atlas(snapshot)
    degraded_states = {node.id: node.metadata["state"] for node in degraded_atlas.nodes if node.kind == "motor_competence"}
    assert degraded_states["competence.7"] == "degraded"

    snapshot2 = _snapshot()
    # bound but still candidate maturity -> calibrating, not usable
    snapshot2["motor_competences"][0]["maturity"] = "emerging"
    calibrating_atlas = build_cognitive_atlas(snapshot2)
    calibrating_states = {node.id: node.metadata["state"] for node in calibrating_atlas.nodes if node.kind == "motor_competence"}
    assert calibrating_states["competence.7"] == "calibrating"


def _body_schema_snapshot():
    return {
        "tick": 1,
        "body_schema": {
            "schema_version": 1,
            "state": "developing",
            "parts": [
                {
                    "part_id": "part.sense.aaaa",
                    "kind": "sense",
                    "existence_confidence_class": 3,
                    "health_class": 2,
                    "confidence_class": 2,
                    "cost_class": 1,
                    "maturity_class": 1,
                    "recency_class": "recent",
                },
                {
                    "part_id": "part.region.bbbb",
                    "kind": "cognitive_region",
                    "existence_confidence_class": 2,
                    "confidence_class": 1,
                    "activity_class": 1,
                    "maturity_class": 0,
                    "recency_class": "stale",
                },
            ],
            "dependencies": [
                {
                    "source_id": "part.sense.aaaa",
                    "target_id": "part.region.bbbb",
                    "relation": "co_acts_with",
                    "confidence_class": 2,
                    "support_class": 1,
                },
            ],
            "global_state": {},
        },
    }


def test_build_cognitive_atlas_materializes_body_schema_parts_not_anatomy():
    atlas = build_cognitive_atlas(_body_schema_snapshot())

    kinds = {node.id: node.kind for node in atlas.nodes}
    assert kinds["part.sense.aaaa"] == "body_schema"
    assert kinds["part.region.bbbb"] == "body_schema"
    # no anatomical/physical name leaked into the cognitive node id
    for node_id in kinds:
        assert "hip" not in node_id and "knee" not in node_id and "joint" not in node_id

    edges = {(edge.source_id, edge.target_id): edge for edge in atlas.edges}
    edge = edges[("part.sense.aaaa", "part.region.bbbb")]
    assert edge.kind == "co_acts_with"
    assert edge.metadata["evidence"]["source"] == "body_schema_dependency_evidence"
    assert edge.metadata["evidence"]["confidence_class"] == 2


def test_build_cognitive_atlas_body_schema_absent_when_no_data():
    atlas = build_cognitive_atlas({"tick": 1})

    assert not any(node.kind == "body_schema" for node in atlas.nodes)


def test_build_cognitive_atlas_body_schema_drops_dependency_to_unknown_part():
    snapshot = _body_schema_snapshot()
    snapshot["body_schema"]["dependencies"].append(
        {"source_id": "part.sense.aaaa", "target_id": "part.sense.unknown", "relation": "precedes"}
    )

    atlas = build_cognitive_atlas(snapshot)

    edge_targets = {edge.target_id for edge in atlas.edges}
    assert "part.sense.unknown" not in edge_targets


def test_diff_cognitive_atlas_detects_strengthened_and_weakened_edges():
    before_snapshot = _snapshot()
    before_snapshot["motor_competences"][0]["reproducibility"] = 0.5
    before = build_cognitive_atlas(before_snapshot)

    after_snapshot = _snapshot()
    after_snapshot["topology"]["edges"][0]["weight"] = 0.9  # up from 0.4
    after_snapshot["motor_competences"][0]["reproducibility"] = 0.2  # down from 0.5
    after = build_cognitive_atlas(after_snapshot)

    diff = diff_cognitive_atlas(before, after)

    assert "edge.topology.predictor.1.concept.1" in diff.edges_strengthened
    assert "edge.produces.competence.7.effect.3" in diff.edges_weakened


def test_diff_cognitive_atlas_no_strength_change_when_not_comparable():
    atlas = build_cognitive_atlas(_snapshot())

    diff = diff_cognitive_atlas(atlas, atlas)

    assert diff.edges_strengthened == ()
    assert diff.edges_weakened == ()


def test_build_cognitive_atlas_materializes_action_dimensions():
    snapshot = _snapshot()
    snapshot["action_dimensions"] = [
        {
            "dimension_id": "action.dimension.aaaa",
            "actuator_slot_id": "slot.0",
            "availability": True,
            "controllability": 0.4,
            "confidence": 0.3,
            "usage_count": 5,
            "embodiment_bound": True,
        },
    ]

    atlas = build_cognitive_atlas(snapshot)

    kinds = {node.id: node.kind for node in atlas.nodes}
    assert kinds["action.dimension.aaaa"] == "action_dimension"
    node = next(n for n in atlas.nodes if n.id == "action.dimension.aaaa")
    assert node.metadata["usage_count"] == 5
    assert node.metadata["embodiment_bound"] is True


def test_build_cognitive_atlas_action_dimensions_absent_when_no_data():
    atlas = build_cognitive_atlas({"tick": 1})

    assert not any(node.kind == "action_dimension" for node in atlas.nodes)


def test_build_cognitive_atlas_knowledge_coverage_reports_separate_domain_counts():
    snapshot = _snapshot()
    snapshot["action_dimensions"] = [
        {"dimension_id": "action.dimension.aaaa", "actuator_slot_id": "slot.0"},
        {"dimension_id": "action.dimension.bbbb", "actuator_slot_id": "slot.1"},
    ]

    atlas = build_cognitive_atlas(snapshot)

    coverage = atlas.metrics["knowledge_coverage"]
    assert coverage["action_dimensions"] == 2
    assert coverage["motor_competences"] == 2
    assert coverage["controllers"] == 2
    assert coverage["embodiment_bindings"] == 1
    assert coverage["predictors"] == 1
    # never a single fabricated "knowledge %" -- always per-domain counts
    assert "knowledge_percent" not in coverage
