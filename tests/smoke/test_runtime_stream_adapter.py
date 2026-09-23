from __future__ import annotations

import json

from symbiont_lab.workbench import WEB_ROOT
from symbiont_lab.observation.physics3d import Physics3DObservationBridge
from symbiont_lab.observation.projection import (
    mind_snapshot_from_rich_state,
    runtime_tick_events,
)
from symbiont_lab.observation.bus import ObservationBus


def test_stream_runtime_tick_emits_compatible_body_cognition_vitals() -> None:
    events = runtime_tick_events(
        {
            "tick": 12,
            "instance_id": "0123456789abcdef",
            "run_id": "run-12",
            "sequence": 7,
            "alive": True,
            "base_position": [0.2, 1.1, 0.4],
            "base_orientation": [0.0, 0.0, 0.2, 0.98],
            "schema_confidence": 0.81,
            "schema_parts": 33,
            "schema_sensory_parts": 12,
            "schema_cognitive_regions": 8,
            "predictor_count": 17,
            "prediction_error": 0.11,
            "joint_motion": 0.18,
            "contact_count": 2,
            "mechanical_work_joules": 1.2,
            "metabolic_work_cost": 0.02,
            "slm_active": True,
            "motor_origin": "cognition",
            "resource_progress": 0.64,
            "metabolic_reserve_ratio": 0.72,
            "prospective_selected": True,
            "prospective_expected_value": 0.88,
            "joints": [
                {"name": "left_shoulder_pitch", "position": 0.5},
                {"name": "right_shoulder_pitch", "position": -0.5},
            ],
        }
    )

    assert len(events) == 3
    joined = "\n".join(json.dumps(event, separators=(",", ":")) for event in events)
    assert '"type":"body"' in joined
    assert '"type":"cognition"' in joined
    assert '"type":"vitals"' in joined
    assert '"motor_origin":"cognition"' in joined
    assert '"prospective_expected_value":0.88' in joined
    assert '"instance_id":"0123456789abcdef"' in joined
    assert '"run_id":"run-12"' in joined
    assert '"sequence":7' in joined


def test_stream_does_not_invent_absent_observations() -> None:
    events = list(runtime_tick_events({"tick": 3}))
    by_type = {event["type"]: event for event in events}

    assert by_type["body"] == {"type": "body", "tick": 3}
    assert by_type["cognition"] == {"type": "cognition", "tick": 3}
    assert by_type["vitals"] == {"type": "vitals", "tick": 3}
    assert "alive" not in by_type["vitals"]
    assert "metabolic_reserve" not in by_type["body"]
    assert "source" not in by_type["body"]


def test_stream_drops_stale_backlog_for_slow_consumers() -> None:
    stream = ObservationBus(queue_size=2)
    queue = stream.subscribe()

    stream.push({"type": "vitals", "tick": 1})
    stream.push({"type": "vitals", "tick": 2})
    stream.push({"type": "vitals", "tick": 3})

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    assert len(events) == 2
    assert '"tick":1' not in events
    assert '"tick":2' in events[0]
    assert '"tick":3' in events[1]



def test_mind_projection_preserves_completely_absent_sections() -> None:
    snapshot = mind_snapshot_from_rich_state({"tick": 9})

    assert snapshot == {"tick": 9}
    assert "cognition" not in snapshot
    assert "senses" not in snapshot
    assert "beliefs" not in snapshot
    assert "topology" not in snapshot
    assert "observer_analysis" not in snapshot
    assert "sampling" not in snapshot


def test_physics3d_bridge_projects_passive_viewer_frames() -> None:
    stream = ObservationBus()
    bridge = Physics3DObservationBridge(stream)
    queue = stream.subscribe()

    bridge.publish(
        {
            "tick": 21,
            "symbiont_id": "symbiont:3d:test",
            "alive": False,
            "schema_confidence": 0.73,
            "schema_parts": 9,
            "schema_sensory_parts": 4,
            "schema_cognitive_regions": 3,
            "predictor_count": 5,
            "prediction_error": 0.2,
            "joint_motion": 0.4,
            "contact_count": 2,
            "mechanical_work_joules": 1.5,
            "metabolic_work_cost": 0.1,
            "metabolic_reserve_ratio": 0.8,
            "resource_progress": 0.3,
            "displacement_from_origin": 0.2,
            "motor_origin": "cognition",
            "slm_active": False,
        },
        physical_state={
            "base_position": [1.0, 2.0, 0.9],
            "base_orientation": [0.0, 0.0, 0.0, 1.0],
            "joints": [
                {"joint_index": 7, "position": 0.42},
            ],
        },
    )

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    joined = "\n".join(events)

    assert '"source":"physics3d"' in joined
    assert '"alive":false' in joined
    assert '"base_position":[1.0,2.0,0.9]' in joined
    assert '"name":"left_shoulder_pitch"' in joined
    assert '"position":0.42' in joined



def test_physics3d_bridge_emits_stop_command_on_shutdown() -> None:
    bridge = Physics3DObservationBridge(ObservationBus())
    assert bridge.poll_commands() == []

    bridge.request_stop()

    assert bridge.poll_stop() is True
    assert bridge.poll_commands() == [{"type": "stop"}]



def test_physics3d_rich_state_projects_into_mind_contract() -> None:
    snapshot = mind_snapshot_from_rich_state({
        "tick": 33,
        "organism_id": "symbiont:3d:test",
        "runtime": {
            "percepts": [
                {"name": "rec.0", "quality": "nominal"},
                {"name": "rec.1", "quality": "unavailable"},
            ],
            "narrative": [
                {
                    "capability_id": "rec.0",
                    "summary": "stable signal",
                    "uncertainty": 0.2,
                    "evidence_gathered": 4,
                    "contested": False,
                }
            ],
            "sensory_phenotype": {"status": "developing"},
            "development": {"stage": "nascent"},
            "evidence_gathered": 4,
            "homeostatic_deviation": 0.12,
        },
        "cognition": {
            "activations": {"concept.1": 0.5},
            "readouts": {"readout.1": 0.3},
            "prediction_errors": [
                {"target_id": "concept.1", "error": 0.08},
            ],
            "topology_health": "connected",
            "frozen": False,
            "consecutive_failures": 0,
            "stranded_concepts": [],
            "predictive_gain": 0.2,
            "topology_revision": 7,
        },
        "cognitive_topology": {
            "nodes": [
                {"node_id": "concept.1", "kind": "concept"},
                {"node_id": "readout.1", "kind": "readout"},
            ],
            "edges": [
                {
                    "source_id": "concept.1",
                    "target_id": "readout.1",
                    "kind": "excitatory",
                }
            ],
        },
        "body_schema": {"status": "developing"},
        "post": {
            "metabolism": {"reserve": {"energy": 0.8}},
            "physiology": {"state": "alive"},
        },
    })

    assert snapshot["tick"] == 33
    assert snapshot["display_id"] == "symbiont:3d:test"
    assert snapshot["senses"][0]["id"] == "rec.0"
    assert "active" not in snapshot["senses"][0]
    assert "active" not in snapshot["senses"][1]
    assert snapshot["beliefs"][0]["certainty"] == 0.8
    assert snapshot["cognition"]["topologyHealth"] == "connected"
    assert snapshot["observer_analysis"]["predictionErrors"]["concept.1"] == "medium"
    assert snapshot["observer_analysis"]["activationClasses"]["concept.1"] == 8
    assert "observer_analysis.predictionErrors" in snapshot["provenance"]["observerDerived"]
    assert snapshot["topology"]["nodes"][0]["id"] == "concept.1"
    assert snapshot["topology"]["edges"][0]["sourceId"] == "concept.1"


def test_physics3d_bridge_publishes_rich_mind_snapshot() -> None:
    stream = ObservationBus()
    bridge = Physics3DObservationBridge(stream)
    queue = stream.subscribe()

    bridge.publish_rich_state({
        "tick": 44,
        "organism_id": "symbiont:3d:test",
        "runtime": {"percepts": [{"name": "rec.0", "quality": "nominal"}]},
        "cognition": {},
        "post": {},
    })

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    joined = "\n".join(events)
    assert '"type":"mind_snapshot"' in joined
    assert '"source":"physics3d"' in joined
    assert '"tick":44' in joined
    assert '"rec.0"' in joined



def test_physics3d_topology_projection_keeps_nodes_beyond_128() -> None:
    from types import SimpleNamespace
    from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

    nodes = [
        SimpleNamespace(node_id=f"sensor.{index}", kind=SimpleNamespace(value="sense"))
        for index in range(128)
    ]
    nodes.extend([
        SimpleNamespace(node_id="concept.1", kind=SimpleNamespace(value="concept")),
        SimpleNamespace(node_id="predictor.1", kind=SimpleNamespace(value="predictor")),
        SimpleNamespace(node_id="readout_core", kind=SimpleNamespace(value="readout")),
    ])
    edges = [
        SimpleNamespace(
            source_id="sensor.0",
            target_id="concept.1",
            kind=SimpleNamespace(value="excitatory"),
        ),
        SimpleNamespace(
            source_id="concept.1",
            target_id="readout_core",
            kind=SimpleNamespace(value="excitatory"),
        ),
    ]
    bridge = SimpleNamespace(graph=SimpleNamespace(nodes=tuple(nodes), edges=tuple(edges)))

    payload = PyBulletEmbodimentRuntime._cognitive_topology_payload(bridge)

    assert payload is not None
    assert len(payload["nodes"]) == 131
    ids = {node["node_id"] for node in payload["nodes"]}
    assert {"concept.1", "predictor.1", "readout_core"} <= ids
    assert len(payload["edges"]) == 2



def test_mind_asset_uses_body_schema_class_contract() -> None:
    asset = (WEB_ROOT / "views" / "mind.js").read_text(encoding="utf-8")

    assert "existence_confidence_class" in asset
    assert "health_class" in asset
    assert "confidence_class" in asset
    assert "maturity_class" in asset
    assert "dep.source_id" in asset
    assert "dep.target_id" in asset
    assert "part.part_id" in asset


def test_mind_regime_is_explicitly_observer_side_and_finite_safe() -> None:
    asset = (WEB_ROOT / "views" / "mind.js").read_text(encoding="utf-8")

    assert "Observer Map" in asset
    assert "OBSERVER MODEL" in asset
    assert "observer-side projection" in asset
    assert "function finiteNumber(" in asset
    assert "learned attractors" not in asset


def test_mind_sensory_map_uses_real_cognitive_topology() -> None:
    asset = (WEB_ROOT / "views" / "mind.js").read_text(encoding="utf-8")

    assert "Body-derived sensory topology" in asset
    assert "topology.edges" in asset
    assert "lines are learned graph edges, not inferred UI links" in asset



def test_mind_cognition_layout_is_relationship_aware() -> None:
    asset = (WEB_ROOT / "views" / "mind.js").read_text(encoding="utf-8")
    graph_model = (WEB_ROOT / "views" / "mind" / "graph-model.js").read_text(encoding="utf-8")

    assert "enrichGraphModel" in asset
    assert "deriveLocalCommunities" in graph_model
    assert "shared downstream/upstream partners" in asset
    assert "sameCommunity" in asset
    assert "communityCenters" in asset
    assert "visualValue" in graph_model
    assert "degreeNorm" in graph_model


def test_mind_self_is_organism_owned_self_portrait() -> None:
    asset = (WEB_ROOT / "views" / "mind.js").read_text(encoding="utf-8")

    assert "How it represents itself" in asset
    assert "Organism-owned BodySchema only" in asset
    assert "organism-inferred functional dependencies" in asset
    assert "epistemic envelope, not anatomy" in asset
    assert "part.existence_confidence_class" in asset
    assert "region.activity_class" in asset



def test_mind_compares_phenotype_and_self_side_by_side() -> None:
    asset = (WEB_ROOT / "views" / "mind.js").read_text(encoding="utf-8")

    assert "{ id: 'phenotype',  label: 'Identity' }" in asset
    assert "mind-identity-wrap" in asset
    assert "Observed organism" in asset
    assert "Self-model" in asset
    assert "{ id: 'self'" not in asset
    assert "renderPhenotype();" in asset
    assert "renderIdentityGap();" in asset
    assert "renderSelf();" in asset



def test_mind_identity_view_surfaces_comparable_gap_without_deanonymizing_self() -> None:
    asset = (WEB_ROOT / "views" / "mind.js").read_text(encoding="utf-8")

    assert "Observed organism" in asset
    assert "Self-model" in asset
    assert "function renderIdentityGap()" in asset
    assert "Self representation coverage" in asset
    assert "Internal structure" in asset
    assert "How certain is the self-model?" in asset
    assert "Recent self-model change" in asset
    assert "Per-sensor identity correspondence is intentionally unknown" in asset
    assert "source_receptor_id" not in asset



def test_mind_cognition_supports_filtered_views_and_route_tracing() -> None:
    asset = (WEB_ROOT / "views" / "mind.js").read_text(encoding="utf-8")
    graph_selection = (WEB_ROOT / "views" / "mind" / "graph-selection.js").read_text(encoding="utf-8")

    assert "viewMode:       'connected'" in asset
    assert "['full','Full']" in asset
    assert "['connected','Connected']" in asset
    assert "['core','Core']" in asset
    assert "export function graphSubgraphIds(" in graph_selection
    assert "export function filterGraphForView(" in graph_selection
    assert "pathDepth:      2" in asset
    assert "selectCognitiveNode(node.id)" in asset
    assert "motor-output edges" in asset


def test_mind_tracks_cognitive_structure_over_time() -> None:
    asset = (WEB_ROOT / "views" / "mind.js").read_text(encoding="utf-8")

    assert "const _mindHistory = []" in asset
    assert "function recordMindHistory()" in asset
    assert "Δ since t" in asset
    assert "Cognitive structure" in asset


def test_body_and_mind_use_resource_delta_as_distance_not_percent() -> None:
    root = WEB_ROOT / "views"
    mind = (root / "mind.js").read_text(encoding="utf-8")
    body = (root / "body.js").read_text(encoding="utf-8")

    assert "Resource Δ" in mind
    assert "Resource Δdistance" in body
    assert "resourceProgress.toFixed(2)} m" in mind
    assert "data.resource_progress.toFixed(2)} m" in body
    assert "resource_progress * 100" not in body


def test_stream_exposes_cognitive_and_sensorimotor_learning_counts() -> None:
    events = runtime_tick_events({
        "tick": 5,
        "predictor_count": 7,
        "sensorimotor_patterns": 13,
        "motor_primitives": 4,
        "cognitive_motor_primitives": 2,
    })
    joined = "\n".join(json.dumps(event, separators=(",", ":")) for event in events)
    assert '"predictor_count":7' in joined
    assert '"sensorimotor_patterns":13' in joined
    assert '"motor_primitives":4' in joined
    assert '"cognitive_motor_primitives":2' in joined
