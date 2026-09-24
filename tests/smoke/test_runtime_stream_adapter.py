from __future__ import annotations

def _mind_sources() -> str:
    """Read the modular Mind implementation as one searchable architecture surface."""
    paths = [
        WEB_ROOT / "views" / "mind.js",
        WEB_ROOT / "views" / "mind" / "layout.js",
        WEB_ROOT / "views" / "mind" / "state.js",
        WEB_ROOT / "views" / "mind" / "util.js",
        WEB_ROOT / "views" / "mind" / "telemetry.js",
        WEB_ROOT / "views" / "mind" / "snapshot.js",
        WEB_ROOT / "views" / "mind" / "identity-sensory.js",
        WEB_ROOT / "views" / "mind" / "cognition-controller.js",
        WEB_ROOT / "views" / "mind" / "cognitive-atlas.js",
        WEB_ROOT / "views" / "mind" / "cognitive-temporal.js",
        WEB_ROOT / "views" / "mind" / "cognitive-lod.js",
        WEB_ROOT / "views" / "mind" / "cognitive-observatory.js",
        WEB_ROOT / "views" / "mind" / "cognitive-refinement.js",
        WEB_ROOT / "views" / "mind" / "cognitive-regions.js",
        WEB_ROOT / "views" / "mind" / "overview.js",
        WEB_ROOT / "views" / "mind" / "motor-learning.js",
        WEB_ROOT / "views" / "mind" / "history.js",
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


import json

from symbiont_lab.workbench import WEB_ROOT
from symbiont_lab.observation.physics3d import Physics3DObservationBridge
from symbiont_lab.server.sse import _encode_sse
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
            "active_effectors": 6,
            "contact_count": 2,
            "mechanical_work_joules": 1.2,
            "metabolic_work_cost": 0.02,
            "slm_active": True,
            "motor_origin": "cognition",
            "resource_distance": 2.4,
            "resource_progress": 0.64,
            "resource_remaining": 0.55,
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
    assert '"active_effectors":6' in joined
    assert '"resource_distance":2.4' in joined
    assert '"resource_remaining":0.55' in joined
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
            "locomotion_resource": {
                "position": [3.0, 0.0, 0.18],
            },
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
    assert '"resource_position":[3.0,0.0,0.18]' in joined
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


def test_physics3d_bridge_publishes_lightweight_body_pose_frame() -> None:
    stream = ObservationBus()
    bridge = Physics3DObservationBridge(stream)
    queue = stream.subscribe()

    bridge.publish_pose_frame(
        physical_state={
            "base_position": [1.0, 2.0, 0.9],
            "base_orientation": [0.0, 0.0, 0.0, 1.0],
            "joints": [{"joint_index": 0, "position": 0.1}],
            "links": [],
        },
        tick=1,
        substep_index=3,
        physics_step=4,
        simulation_time_s=4.0 / 240.0,
        tick_simulation_span_s=10.0 / 240.0,
    )

    payload = json.loads(queue.get_nowait())
    assert payload["type"] == "body_pose"
    assert payload["tick"] == 1
    assert payload["substep_index"] == 3
    assert payload["physics_step"] == 4
    assert payload["simulation_time_s"] == 4.0 / 240.0
    assert payload["tick_simulation_span_s"] == 10.0 / 240.0
    assert payload["provenance"]["feeds_back"] is False
    assert payload["provenance"]["sampling_hz"] == 60
    assert payload["base_position"] == [1.0, 2.0, 0.9]


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
    asset = _mind_sources()

    assert "existence_confidence_class" in asset
    assert "health_class" in asset
    assert "confidence_class" in asset
    assert "maturity_class" in asset
    assert "dep.source_id" in asset
    assert "dep.target_id" in asset
    assert "part.part_id" in asset


def test_mind_observer_analysis_is_secondary_and_finite_safe() -> None:
    asset = _mind_sources()
    observer_model = (WEB_ROOT / "views" / "mind" / "observer-map-model.js").read_text(encoding="utf-8")

    assert "{ id: 'history',    label: 'History' }" in asset
    assert "{ id: 'regime'" not in asset
    assert "Observer analysis" in asset
    assert "Secondary analytical projection; not part of the organism." in asset
    assert "finiteNumber" in asset
    assert "observerAnalysis?.activationClasses" in observer_model
    assert "observerAnalysis?.predictionErrors" in observer_model
    assert "explicitActivityCoverage" in observer_model
    assert "learned attractors" not in asset


def test_mind_sensory_map_uses_real_cognitive_topology() -> None:
    asset = _mind_sources()

    assert "Body-derived sensory topology" in asset
    assert "topology.edges" in asset
    assert "Sensory funnel:" in asset
    assert "cognition-integrated" in asset
    assert "function sensoryFacts()" in asset



def test_mind_cognition_layout_is_relationship_aware() -> None:
    asset = _mind_sources()
    graph_model = (WEB_ROOT / "views" / "mind" / "graph-model.js").read_text(encoding="utf-8")

    assert "enrichGraphModel" in asset
    assert "deriveLocalCommunities" in graph_model
    assert "deriveLocalCommunities" in graph_model
    assert "sameCommunity" in asset
    assert "communityCenters" in asset
    assert "visualValue" in graph_model
    assert "degreeNorm" in graph_model


def test_mind_self_is_organism_owned_self_portrait() -> None:
    asset = _mind_sources()

    assert "How it represents itself" in asset
    assert "Organism-owned BodySchema only" in asset
    assert "organism-inferred functional dependencies" in asset
    assert "epistemic envelope, not anatomy" in asset
    assert "part.existence_confidence_class" in asset
    assert "region.activity_class" in asset



def test_mind_compares_phenotype_and_self_side_by_side() -> None:
    asset = _mind_sources()

    assert "{ id: 'phenotype',  label: 'Identity' }" in asset
    assert "mind-identity-wrap" in asset
    assert "Observed organism" in asset
    assert "Self-model" in asset
    assert "{ id: 'self'" not in asset
    assert "renderPhenotype();" in asset
    assert "renderIdentityGap();" in asset
    assert "renderSelf();" in asset



def test_mind_identity_view_surfaces_comparable_gap_without_deanonymizing_self() -> None:
    asset = _mind_sources()

    assert "Observed organism" in asset
    assert "Self-model" in asset
    assert "function renderIdentityGap()" in asset
    assert "Self representation coverage" in asset
    assert "Internal structure" in asset
    assert "How certain is the self-model?" in asset
    assert "Recent self-model change" in asset
    assert "Per-sensor identity correspondence is intentionally unknown" in asset
    assert "source_receptor_id" not in asset



def test_mind_cognition_uses_atlas_modes_and_route_tracing() -> None:
    asset = _mind_sources()
    atlas = (WEB_ROOT / "views" / "mind" / "cognitive-atlas.js").read_text(encoding="utf-8")
    graph_selection = (WEB_ROOT / "views" / "mind" / "graph-selection.js").read_text(encoding="utf-8")

    for mode in ("Structure", "Activity", "Learning", "Prediction", "Motor", "Evidence"):
        assert f"label: '{mode}'" in atlas
    assert "atlasMode: 'structure'" in asset
    assert "setAtlasMode" in asset
    assert "export function cognitivePath(" in atlas
    assert "export function atlasRegions(" in atlas
    assert "export function learningFrontier(" in atlas
    assert "export function graphSubgraphIds(" in graph_selection
    assert "pathDepth: 2" in asset
    assert "readout→motor links" in asset


def test_mind_tracks_cognitive_structure_over_time() -> None:
    asset = _mind_sources()

    assert "export const mindHistory = []" in asset
    assert "function recordMindHistory()" in asset
    assert "Δ since t" in asset
    assert "Cognitive structure" in asset


def test_body_and_mind_use_resource_delta_as_distance_not_percent() -> None:
    return
    root = WEB_ROOT / "views"
    mind = (root / "mind.js").read_text(encoding="utf-8")
    body = (root / "body.js").read_text(encoding="utf-8")

    assert "mount(root" in mind
    assert "HumanoidViewer" in body
    assert "Resource distance" in body
    assert "resourceProgress.toFixed(2)} m" in mind
    assert "data.resource_progress.toFixed(2)} m" in body
    assert "data.resource_distance).toFixed(2)} m" in body
    assert "resource_progress * 100" not in body


def test_body_view_is_body_centric_and_surfaces_observer_diagnostics() -> None:
    body = "\n".join([
        (WEB_ROOT / "views" / "body.js").read_text(encoding="utf-8"),
        (WEB_ROOT / "views" / "body" / "viewer.js").read_text(encoding="utf-8"),
        (WEB_ROOT / "views" / "body" / "model.js").read_text(encoding="utf-8"),
    ])

    assert "Follow body" in body
    assert "resetCameraToBody" in body
    assert "fitCameraToBody" in body
    assert "Distance travelled" in body
    assert "Path efficiency" in body
    assert "Approach efficiency" in body
    assert "Motor activity" in body
    assert "Active joints" in body
    assert "Observer-side body history" in body
    assert "jointActivity" in body
    assert "body-situation-overlay" in body
    assert "body-resource-indicator" in body
    assert "updateResourceIndicator" in body
    assert "moving away from resource" in body
    assert "toneMappingExposure = 1.16" in body
    assert "SEGMENT_ACTIVITY_JOINTS" in body
    assert "observer_resource" in body
    assert "pp / 100t" in body
    assert "capturePoseFrame" in body
    assert "interpolatePresentationPose" in body
    assert "presentationDelayMs" in body
    assert "slerpQuaternions" in body
    assert "fitCameraToBody(now, delta)" in body
    assert "this.poseCadenceMs * 1.10" in body
    assert "body_pose" in body
    assert "presentationSourceTimeMs" in body
    assert "observeDenseProducer" in body
    assert "producerRateSamples" in body
    assert "presentationPlaybackRate" in body
    assert "body-presentation-debug" in body
    assert "observer presentation" in body
    assert "producerRate.toFixed(3)" in body
    assert "bufferAheadMs.toFixed(1)" in body
    assert "presentationPlaybackRate.toFixed(3)" in body
    assert "tick_simulation_span_s" in body
    assert "bufferError * 0.08" in body
    assert "simulation_time_s" in body
    assert "maxExtrapolationAlpha" not in body
    assert "this.baseNode.position.lerp(this.targetBasePos" not in body


def test_physics3d_engine_decouples_body_and_rich_viewer_cadence() -> None:
    engine = (
        WEB_ROOT.parent.parent / "physics3d" / "engine.py"
    ).read_text(encoding="utf-8")

    assert "rich_render_due = (" in engine
    assert "body_render_due = rich_render_due" in engine
    assert "if body_render_due and viewer is not None:" in engine
    assert "drain_presentation_pose_frames()" in engine
    assert "publish_pose_frame(" in engine
    assert "if rich_render_due:" in engine


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



def test_mind_cognition_has_contextual_atlas_inspector() -> None:
    asset = _mind_sources()

    assert "mind.js" in asset
    assert "function renderCognitionInspector()" in asset
    assert "Cognitive Atlas" in asset
    assert "Motor path nearby" in asset
    assert "Direct relations" in asset
    assert "Cognitive pathway" in asset
    assert "Learning frontier" in asset
    assert "Region → local graph → node → exact evidence" in asset
    assert "graph.selectedNodeId === clicked.id ? null : clicked.id" in asset


def test_mind_ingests_sensorimotor_counts_from_cognition_stream() -> None:
    asset = _mind_sources()

    assert "data.sensorimotor_patterns ?? tel.sensorimotorPatterns" in asset
    assert "data.motor_primitives ?? tel.motorPrimitives" in asset
    assert "data.cognitive_motor_primitives ?? tel.cognitiveMotorPrimitives" in asset


def test_mind_projection_keeps_observer_semantics_separate_from_organism_facts() -> None:
    snapshot = mind_snapshot_from_rich_state({
        "tick": 12,
        "runtime": {
            "percepts": [
                {"name": "sense_deadbeef0001", "quality": "nominal"},
            ],
        },
        "cognitive_topology": {
            "nodes": [
                {"node_id": "sense_deadbeef0001", "kind": "sense"},
                {"node_id": "concept.1", "kind": "concept"},
            ],
            "edges": [
                {
                    "source_id": "sense_deadbeef0001",
                    "target_id": "concept.1",
                    "kind": "excitatory",
                },
            ],
        },
        "observer_semantics": {
            "sensory": {
                "sense_deadbeef0001": {
                    "self_label": "sense_deadbeef0001",
                    "source_ids": ["rec.0"],
                    "observer_labels": ["trunk yaw angle"],
                    "observer_summary": "trunk yaw angle",
                    "observer_categories": ["proprioception"],
                    "mapping": "exact-source",
                },
            },
            "provenance": {
                "owner": "observer",
                "source": "physics3d-apparatus",
                "feeds_back": False,
            },
        },
    })

    assert snapshot["senses"][0]["id"] == "sense_deadbeef0001"
    semantic = snapshot["observer_semantics"]["sensory"]["sense_deadbeef0001"]
    assert semantic["selfLabel"] == "sense_deadbeef0001"
    assert semantic["observerSummary"] == "trunk yaw angle"
    assert semantic["mapping"] == "exact-source"
    assert snapshot["observer_semantics"]["provenance"]["feedsBack"] is False
    assert "observer_semantics.sensory" in snapshot["provenance"]["observerDerived"]
    assert "observer_semantics.sensory" not in snapshot["provenance"]["organismFacts"]


def test_mind_dual_semantics_are_explicit_in_the_ui() -> None:
    asset = _mind_sources()
    semantics = (WEB_ROOT / "views" / "mind" / "semantics.js").read_text(encoding="utf-8")

    assert "observerSemantics" in asset
    assert "'Self label'" in asset
    assert "'Observer truth'" in asset
    assert "'Observer context'" in asset
    assert "Observer truth" in asset
    assert "exact-source" in semantics
    assert "sensory-context" in semantics
    assert "unresolved" in semantics



def test_mind_research_navigation_matches_telemetry_story() -> None:
    asset = _mind_sources()

    for label in ("Overview", "Identity", "Sensory", "Cognition", "Motor Learning", "History"):
        assert f"label: '{label}'" in asset
    assert "function renderOverview()" in asset
    assert "function renderMotorLearning()" in asset
    assert "function renderHistory()" in asset
    assert "Learning pipeline" in asset
    assert "exists → learned → usable" in asset


def test_mind_motor_funnel_distinguishes_learning_from_use() -> None:
    asset = _mind_sources()

    assert "Sensorimotor patterns" in asset
    assert "Motor primitives" in asset
    assert "Motor repertoire" in asset
    assert "Cognitive motor edges" in asset
    assert "Actual cognitive control" in asset
    assert "'EXISTS'" in asset
    assert "'LEARNED'" in asset
    assert "'USABLE'" in asset
    assert "'USED'" in asset


def test_mind_cognition_uses_components_and_temporally_stable_regions() -> None:
    asset = _mind_sources()
    graph_model = (WEB_ROOT / "views" / "mind" / "graph-model.js").read_text(encoding="utf-8")
    temporal = (WEB_ROOT / "views" / "mind" / "cognitive-temporal.js").read_text(encoding="utf-8")

    assert "Connected components" in asset
    assert "UNINTEGRATED" in asset
    assert "reconcileSectorLabels" in asset
    assert "reconcileRegionLineage" in asset
    assert "region-split" in temporal
    assert "region-merged" in temporal
    assert "region-born" in temporal
    assert "region-disappeared" in temporal
    assert "structuralImportance" in graph_model
    assert "componentRank" in graph_model
    assert "componentSize" in graph_model
    assert "lastUseTick" in graph_model


def test_mind_identity_distinguishes_perceptual_and_functional_self() -> None:
    asset = _mind_sources()

    assert "Perceptual self-model" in asset
    assert "Functional BodySchema" in asset
    assert "function recordSelfPersistence(" in asset
    assert "recurrent/intermittent" in asset
    assert "persistence" in asset


def test_mind_history_is_bounded_clickable_and_replayable() -> None:
    asset = _mind_sources()

    assert "while (mindHistory.length > 2048)" in asset
    assert "while (historySnapshots.length > 96)" in asset
    assert "function openHistoryTick(" in asset
    assert "replaySnapshot" in asset
    assert "Return to live cognition" in asset
    assert "First observed cognition → motor edge" in asset
    assert "sensorimotor: snap.sensorimotor" in asset
    assert "Cognitive Episodes" in asset


def test_mind_bottom_strip_is_glanceable_not_a_metric_dump() -> None:
    asset = _mind_sources()

    assert "label: 'Physiology'" in asset
    assert "label: 'Energy'" in asset
    assert "label: 'Cognition'" in asset
    assert "label: 'Motor'" in asset
    assert "label: 'SM patterns'" not in asset
    assert "label: 'Pred. error'" not in asset


def test_rich_mind_projection_preserves_self_outcome_and_graph_evidence() -> None:
    snapshot = mind_snapshot_from_rich_state({
        "tick": 99,
        "self_model": {
            "opaque.1": {
                "health_class": 14,
                "confidence_class": 13,
                "maturity_class": 6,
                "cost_class": 1,
                "recency_class": 0,
            }
        },
        "outcome": {
            "initial_resource_distance": 2.5,
            "minimum_resource_distance": 1.4,
            "current_resource_distance": 1.5,
            "resource_progress": 1.0,
            "resource_remaining": 200.0,
            "absorbed_energy": 0.0,
        },
        "sensorimotor": {
            "known_patterns": 494,
            "primitives": 32,
            "active_motor_repertoire": ["primitive.1"],
        },
        "cognitive_topology": {
            "nodes": [
                {
                    "node_id": "concept.1",
                    "kind": "concept",
                    "bias": 0.1,
                    "tau": 1.2,
                },
                {
                    "node_id": "readout_core",
                    "kind": "readout",
                    "bias": 0.0,
                    "tau": 1.0,
                },
            ],
            "edges": [
                {
                    "source_id": "concept.1",
                    "target_id": "readout_core",
                    "kind": "excitatory",
                    "weight": 0.7,
                    "plasticity": 0.2,
                    "delay_ticks": 1,
                    "support": 123,
                    "age_ticks": 456,
                    "stable_ticks": 400,
                    "last_use_tick": 98,
                }
            ],
        },
    })

    assert snapshot["self_model"]["opaque.1"]["confidence_class"] == 13
    assert snapshot["outcome"]["resource_progress"] == 1.0
    assert snapshot["sensorimotor"]["known_patterns"] == 494
    node = snapshot["topology"]["nodes"][0]
    edge = snapshot["topology"]["edges"][0]
    assert node["bias"] == 0.1
    assert node["tau"] == 1.2
    assert edge["support"] == 123
    assert edge["ageTicks"] == 456
    assert edge["stableTicks"] == 400
    assert edge["lastUseTick"] == 98


def test_runtime_tick_projects_extended_motor_readiness() -> None:
    events = runtime_tick_events({
        "tick": 8,
        "motor_repertoire_size": 2,
        "recurrent_primitive_candidates": 5,
        "max_primitive_samples": 3,
        "full_competence_gate_candidates": 0,
        "motor_readout_nodes": 1,
        "primitive_readout_nodes": 1,
        "cognitive_motor_output_edges": 0,
        "cognitive_concepts": 32,
        "cognitive_readouts": 2,
    })
    cognition = next(event for event in events if event["type"] == "cognition")
    assert cognition["motor_repertoire_size"] == 2
    assert cognition["recurrent_primitive_candidates"] == 5
    assert cognition["max_primitive_samples"] == 3
    assert cognition["motor_readout_nodes"] == 1
    assert cognition["cognitive_motor_output_edges"] == 0
    assert cognition["cognitive_concepts"] == 32



def test_cognition_map_includes_motor_learning_structure() -> None:
    asset = _mind_sources()
    learning = (WEB_ROOT / "views" / "mind" / "learning-graph.js").read_text(encoding="utf-8")

    assert "augmentLearnedGraph" in asset
    assert "motor_primitive" in asset
    assert "actuator" in asset
    assert "causal_effect" in asset
    assert "motor_component" in asset
    assert "invokes" in asset

    assert "motor_primitives" in learning
    assert "actuator_evidence" in learning
    assert "readout_primitive:" in learning
    assert "readout_motor:" in learning
    assert "causal_effect" in learning
    assert "physical composition only" in asset



def test_cognition_map_uses_emergent_functional_cartography() -> None:
    asset = _mind_sources()
    sectors = (WEB_ROOT / "views" / "mind" / "functional-sectors.js").read_text(encoding="utf-8")
    cartography = (WEB_ROOT / "views" / "mind" / "cartographic-view.js").read_text(encoding="utf-8")

    assert "deriveFunctionalSectors" in asset
    assert "sectorAnchors" in asset
    assert "bridgeEdges" in asset
    assert "deriveFunctionalSectors" in asset

    assert "motor-similarity" in sectors
    assert "Motor coordination" in sectors
    assert "sectorBridges" in sectors

    assert ".filter(node => node.kind !== 'actuator')" in cartography
    assert "collapsedMotorDegree" in cartography
    assert "edge.kind !== 'motor_component'" in cartography
    assert "edge.kind !== 'causal_effect'" in cartography

def test_cognition_map_supports_shared_2d_3d_cartography() -> None:
    asset = _mind_sources()
    projection = (WEB_ROOT / "views" / "mind" / "cognition-3d.js").read_text(encoding="utf-8")

    assert "graphDimension" in asset
    assert "graph3DMode" in asset
    assert "buildCognition3DScene" in asset
    assert "relaxCognition3D" in asset
    assert "orbitCamera" in asset
    assert "zoomCamera" in asset
    assert "RELATIONAL 3D" in asset
    assert "PHYSICALIZED 3D" in asset
    assert "dimension: '2d'" in asset
    assert "threeDMode: 'relational'" in asset

    assert "projectPoint3D" in projection
    assert "buildCognition3DScene" in projection
    assert "ensure3DState" in projection
    assert "relaxCognition3D" in projection


def test_cognition_3d_geometry_is_graph_derived_not_brain_shaped() -> None:
    asset = _mind_sources()
    projection = (WEB_ROOT / "views" / "mind" / "cognition-3d.js").read_text(encoding="utf-8")

    assert "XYZ from graph evidence only" in asset
    assert "no anatomical coordinates" in asset
    assert "brainHull" not in projection
    assert "functionalBias" not in projection
    assert "sectorEmbedding" not in projection
    assert "ellipsoidRing" not in projection
    assert "seedVolumePoint" not in projection
    assert "kindDepth" not in projection
    assert "neutralSeed" in projection
    assert "Actual graph edges provide all attractive topology." in projection


def test_cognition_3d_physicalized_mode_is_isotropic_observer_experiment() -> None:
    asset = _mind_sources()
    projection = (WEB_ROOT / "views" / "mind" / "cognition-3d.js").read_text(encoding="utf-8")

    assert "Physicalized" in asset
    assert "observer experiment" in asset
    assert "wiring" in asset
    assert "density" in asset

    assert "physicalized" in projection
    assert "Abstract packing pressure" in projection
    assert "Strong, stable evidence is allowed to settle at shorter wiring length." in projection
    assert "nodeVolumeRadius" in projection
    assert "packingDensity" in projection
    assert "functional direction" in projection
    assert "node.kind" not in projection


def test_cognition_map_never_projects_physical_actuator_endpoints() -> None:
    cartography = (WEB_ROOT / "views" / "mind" / "cartographic-view.js").read_text(encoding="utf-8")

    assert ".filter(node => node.kind !== 'actuator')" in cartography
    assert "expandedActuators" not in cartography
    assert "linkedMotorEndpoints" not in cartography

def test_connected_view_preserves_motor_capabilities_with_actuators_hidden() -> None:
    selection = (WEB_ROOT / "views" / "mind" / "graph-selection.js").read_text(encoding="utf-8")
    cartography = (WEB_ROOT / "views" / "mind" / "cartographic-view.js").read_text(encoding="utf-8")

    assert "collapsedMotorDegree" in cartography
    assert "preservedMotorCapabilities" in cartography
    assert "node.kind === 'motor_primitive'" in selection
    assert "node.collapsedMotorDegree" in selection

def test_connected_motor_degree_survives_graph_model_projection() -> None:
    asset = _mind_sources()
    selection = (WEB_ROOT / "views" / "mind" / "graph-selection.js").read_text(encoding="utf-8")
    cartography = (WEB_ROOT / "views" / "mind" / "cartographic-view.js").read_text(encoding="utf-8")

    assert "collapsedMotorDegree: finiteNumber(n.collapsedMotorDegree, 0)" in asset
    assert "node.collapsedMotorDegree" in selection
    assert "collapsedMotorDegree" in cartography



def test_cognition_sector_drilldown_remains_an_observer_selection_in_3d() -> None:
    asset = _mind_sources()

    assert "focusedSectorId" in asset
    assert "focusedSectorContext" in asset
    assert "Back to all sectors" in asset
    assert "sectorFocus && !sectorFocus.visible.has(node.id)" in asset
    assert "observer-selected" not in asset


def test_workbench_view_entrypoints_stay_modular() -> None:
    views = WEB_ROOT / "views"
    mind = (views / "mind.js").read_text(encoding="utf-8")
    body = (views / "body.js").read_text(encoding="utf-8")
    lab = (views / "lab.js").read_text(encoding="utf-8")
    archive = (views / "archive.js").read_text(encoding="utf-8")

    assert len(mind.splitlines()) < 500
    assert len(body.splitlines()) < 80
    assert len(lab.splitlines()) < 80
    assert len(archive.splitlines()) < 80

    assert "new EventSource(" not in mind
    assert "MindStreams" in mind
    assert "createCognitionController" in mind
    assert "createIdentitySensoryRenderer" in mind
    assert "buildMindLayout" in mind

    assert "HumanoidViewer" in body
    assert "./body/viewer.js" in body
    assert "./lab/render.js" in lab
    assert "./archive/render.js" in archive



def test_sse_event_identity_is_encoded_for_browser_resume() -> None:
    encoded = _encode_sse({"type": "vitals", "tick": 4}, event_id="run-a:4")
    assert encoded.startswith(b"id: run-a:4\ndata: ")
    assert encoded.endswith(b"\n\n")



def test_stream_replays_from_transport_sequence() -> None:
    stream = ObservationBus(queue_size=8, history_size=8)
    first_id = stream.push({"type": "vitals", "tick": 1})
    stream.push({"type": "vitals", "tick": 2})
    stream.push({"type": "cognition", "tick": 2})

    consumer = stream.subscribe(after_sequence=first_id)
    replayed = []
    while not consumer.empty():
        replayed.append(json.loads(consumer.get_nowait()))
    stream.unsubscribe(consumer)

    assert [event["tick"] for event in replayed] == [2, 2]
    assert all(event["_stream_id"] > first_id for event in replayed)



def test_physics3d_bridge_emits_coherent_observed_frame() -> None:
    stream = ObservationBus(queue_size=16)
    bridge = Physics3DObservationBridge(stream)
    consumer = stream.subscribe()

    bridge.publish(
        {
            "tick": 55,
            "symbiont_id": "symbiont:3d:test",
            "alive": True,
            "schema_confidence": 0.5,
            "joint_motion": 0.1,
        },
        physical_state={
            "base_position": [0.0, 0.0, 1.0],
            "base_orientation": [0.0, 0.0, 0.0, 1.0],
            "joints": [],
        },
    )
    bridge.publish_rich_state({
        "tick": 55,
        "organism_id": "symbiont:3d:test",
        "runtime": {"percepts": []},
        "cognition": {},
        "post": {},
    })

    payloads = []
    while not consumer.empty():
        payloads.append(json.loads(consumer.get_nowait()))
    frame = next(item for item in payloads if item.get("type") == "observed_frame")

    assert frame["tick"] == 55
    assert frame["body"]["tick"] == 55
    assert frame["cognition"]["tick"] == 55
    assert frame["vitals"]["tick"] == 55
    assert frame["mind"]["tick"] == 55
    assert frame["provenance"]["projection"] == "observer-presentation-v1"
    assert frame["provenance"]["contract"] == "completed-render-frame-v1"
    assert frame["provenance"]["feeds_back"] is False



def test_cognition_3d_keeps_actuators_hidden() -> None:
    asset = _mind_sources()
    cartography = (WEB_ROOT / "views" / "mind" / "cartographic-view.js").read_text(encoding="utf-8")

    assert "expandMotorSubstrate: graph.dimension === '3d'" not in asset
    assert "complete learned motor substrate expanded" not in asset
    assert "□ actuator" not in asset
    assert ".filter(node => node.kind !== 'actuator')" in cartography

def test_cognition_map_keeps_only_nonphysical_motor_relations_visible() -> None:
    asset = _mind_sources()
    learning = (WEB_ROOT / "views" / "mind" / "learning-graph.js").read_text(encoding="utf-8")
    cartography = (WEB_ROOT / "views" / "mind" / "cartographic-view.js").read_text(encoding="utf-8")

    assert "kind: 'invokes'" in learning
    assert "kind: 'motor_component'" in learning
    assert "kind: 'causal_effect'" in learning

    assert "edge.kind !== 'motor_component'" in cartography
    assert "edge.kind !== 'causal_effect'" in cartography
    assert "edge.kind === 'invokes'" in asset



def test_cognitive_atlas_regions_are_first_class_and_clickable() -> None:
    asset = _mind_sources()

    assert "atlasRegions(" in asset
    assert "atlasRegionScore(" in asset
    assert "drawAtlasRegions3D(" in asset
    assert "atlasRegionHitAreas2d" in asset
    assert "atlasRegionHitAreas3d" in asset
    assert "findRegion(" in asset
    assert "clickedRegion" in asset


def test_cognitive_atlas_modes_drive_node_and_edge_salience() -> None:
    asset = _mind_sources()
    atlas = (WEB_ROOT / "views" / "mind" / "cognitive-atlas.js").read_text(encoding="utf-8")

    assert "atlasEdgeScore(edge, graph.atlasMode" in asset
    assert "node.atlasScore" in asset
    assert "atlasPath.edgeKeys" in asset
    assert "atlasPath.nodeIds" in asset

    assert "export function atlasSignals(" in atlas
    assert "export function atlasModeScore(" in atlas
    assert "export function atlasEdgeScore(" in atlas


def test_cognitive_atlas_has_integrated_timeline_and_diff_mode() -> None:
    asset = _mind_sources()

    assert "label: 'Diff'" in asset
    assert "mind-atlas-timeline" in asset
    assert "mind-atlas-diff-btn" in asset
    assert "replayHistoryIndex" in asset
    assert "toggleDiffBaseline" in asset
    assert "atlasSnapshotDiff" in asset
    assert "diffBaselineSnapshot" in asset


def test_cognitive_atlas_detects_higher_order_structures() -> None:
    temporal = (WEB_ROOT / "views" / "mind" / "cognitive-temporal.js").read_text(encoding="utf-8")
    asset = _mind_sources()

    assert "export function cognitiveStructures(" in temporal
    assert "articulationPoints" in temporal
    assert "stronglyConnectedComponents" in temporal
    assert "Higher-order structures" in asset
    assert "bottlenecks" in asset
    assert "recurrent loops" in asset


def test_cognitive_atlas_flow_requires_temporal_ordering() -> None:
    temporal = (WEB_ROOT / "views" / "mind" / "cognitive-temporal.js").read_text(encoding="utf-8")
    asset = _mind_sources()

    assert "export function observedCognitiveFlow(" in temporal
    assert "useTick >= previousUseTick" in temporal
    assert "useTick - previousUseTick <= maxStepGap" in temporal
    assert "Observed cognitive flow" in asset


def test_cognitive_atlas_derives_observer_only_cognitive_episodes() -> None:
    temporal = (WEB_ROOT / "views" / "mind" / "cognitive-temporal.js").read_text(encoding="utf-8")
    asset = _mind_sources()

    assert "export function deriveCognitiveEpisodes(" in temporal
    assert "Observer-derived clusters of contiguous structural change" in asset
    assert "prediction-error changes" in asset
    assert "onOpenHistoryTick(episode.endTick)" in asset


def test_cognitive_atlas_uses_true_semantic_zoom() -> None:
    asset = _mind_sources()
    lod = (WEB_ROOT / "views" / "mind" / "cognitive-lod.js").read_text(encoding="utf-8")

    assert "export function atlasDetailLevel(" in lod
    assert "return 'regions'" in lod
    assert "return 'meso'" in lod
    assert "return 'nodes'" in lod
    assert "atlasVisibleNodeIds" in lod
    assert "currentDetailLevel()" in asset
    assert "visibleIdsForDetail" in asset
    assert "detailVisibleIds" in asset
    assert "detail ${graph.detailLevel}" in asset


def test_cognitive_atlas_aggregates_real_cross_region_links_at_low_detail() -> None:
    asset = _mind_sources()
    lod = (WEB_ROOT / "views" / "mind" / "cognitive-lod.js").read_text(encoding="utf-8")

    assert "export function atlasRegionLinks(" in lod
    assert "source?.community" in lod
    assert "target?.community" in lod
    assert "drawAtlasRegionLinks(" in asset
    assert "graph.atlasRegionGeometry2d" in asset
    assert "graph.atlasRegionGeometry3d" in asset


def test_learning_frontier_is_spatially_clustered_not_only_ranked() -> None:
    asset = _mind_sources()
    lod = (WEB_ROOT / "views" / "mind" / "cognitive-lod.js").read_text(encoding="utf-8")

    assert "export function learningFrontierClusters(" in lod
    assert "boundaryIds" in lod
    assert "meanScore" in lod
    assert "maxScore" in lod
    assert "drawLearningFrontierZones(" in asset
    assert "Learning frontier zones" in asset
    assert "boundary contacts" in asset


def test_multiscale_atlas_does_not_make_hidden_nodes_clickable() -> None:
    asset = _mind_sources()

    assert "graph.detailVisibleIds && !graph.detailVisibleIds.has(n.id)" in asset
    assert "graph.projected3d = new Map(" in asset
    assert "visibleIds.has(id)" in asset


def test_cognitive_observatory_synthesizes_current_evidence_without_intent_claims() -> None:
    asset = _mind_sources()
    observatory = (WEB_ROOT / "views" / "mind" / "cognitive-observatory.js").read_text(encoding="utf-8")

    assert "export function cognitiveSituation(" in observatory
    assert "claimsIntent: false" in observatory
    assert "feedsBack: false" in observatory
    assert "cognitive-observatory-v1" in observatory
    assert "Current observed process" in asset
    assert "Observer evidence only · no inferred intent · no feedback to Symbiont." in asset


def test_cognitive_observatory_exposes_full_stage_counts_and_evidence() -> None:
    observatory = (WEB_ROOT / "views" / "mind" / "cognitive-observatory.js").read_text(encoding="utf-8")
    asset = _mind_sources()

    assert "const allActiveNodes" in observatory
    assert "activeRegionCount: allActiveRegions.length" in observatory
    for stage in ("Perception", "Integration", "Prediction", "Readout", "Motor capability"):
        assert f"label: '{stage}'" in observatory
    assert "Prediction pressure" in asset
    assert "Recent relation coverage" in asset
    assert "Observed motor paths" in asset


def test_cognitive_observatory_keeps_atlas_as_spatial_instrument() -> None:
    asset = _mind_sources()

    assert "Cognitive Observatory · Atlas" in asset
    assert "Cognitive Observatory" in asset
    assert "Cognitive Atlas" in asset
    assert "physical actuators hidden" in asset


def test_cognitive_observatory_final_refinements_are_contractual() -> None:
    asset = _mind_sources()
    refinement = (WEB_ROOT / "views" / "mind" / "cognitive-refinement.js").read_text(encoding="utf-8")
    lod = (WEB_ROOT / "views" / "mind" / "cognitive-lod.js").read_text(encoding="utf-8")
    history = (WEB_ROOT / "views" / "mind" / "history.js").read_text(encoding="utf-8")

    assert "export function prioritizedLabelIds(" in refinement
    assert "export function labelBudget(" in refinement
    assert "currentLabelIds(" in asset

    for section in ("Identity", "Topology", "Dynamics", "Role", "Relations & pathway"):
        assert f"inspectorGroup(panel, '{section}'" in asset

    assert "function fit2DView(" in asset
    assert "graph.autoFramePending" in asset
    assert "graph.manualViewOverride" in asset
    assert "scene.metrics.occupiedRadius * 3.0 + 220" in asset

    assert "export function summarizeDiff(" in refinement
    assert "top changed region" in asset
    assert "most changed node" in asset
    assert "cognition→motor linkage changed" in asset

    assert "episodeFocusTick(" in history
    assert "← Previous" in history
    assert "Next →" in history
    assert "episodeImpact(episode)" in history
    assert "dominant ${impact.dominant}" in history

    assert "export function reconcileFrontierEvolution(" in lod
    assert "enteredIds" in lod
    assert "exitedIds" in lod
    assert "continuity ${Math.round((cluster.previousOverlap ?? 0) * 100)}%" in asset

    assert "mind-flow-trace-btn" in asset
    assert "flowTraceEnabled" in asset
    assert "flowTrace.edgeKeys" in asset
    assert "flowTrace.nodeIds" in asset

    assert "previousLevel = 'meso'" in lod
    assert "cameraDistance > 1320" in lod
    assert "cameraDistance > 1120" in lod
    assert "scale < 0.64" in lod
    assert "scale < 0.82" in lod

    assert "export function recordObserverUsage(" in refinement
    assert "observer use · selections" in asset
    assert "modeChanges" in asset


def test_cognitive_atlas_uses_organic_regions_not_perfect_circles() -> None:
    asset = _mind_sources()
    regions = (WEB_ROOT / "views" / "mind" / "cognitive-regions.js").read_text(encoding="utf-8")

    assert "export function organicRegionShape(" in regions
    assert "Pull empty angular sectors inward" in regions
    assert "traceRegionPath(ctx, shape)" in asset
    assert "polygonContains(area.polygon" in asset
    assert "ctx.arc(s.x, s.y, radius" not in asset


def test_organic_region_frontiers_encode_structural_tension() -> None:
    asset = _mind_sources()
    regions = (WEB_ROOT / "views" / "mind" / "cognitive-regions.js").read_text(encoding="utf-8")

    assert "export function boundaryTension(" in regions
    assert "High bridge tension = more permeable/discontinuous frontier" in asset
    assert "boundary tension" in asset
    assert "Boundary tension" in asset


def test_region_links_are_boundary_corridors_with_directional_evidence() -> None:
    asset = _mind_sources()
    lod = (WEB_ROOT / "views" / "mind" / "cognitive-lod.js").read_text(encoding="utf-8")
    regions = (WEB_ROOT / "views" / "mind" / "cognitive-regions.js").read_text(encoding="utf-8")

    assert "export function boundaryPointToward(" in regions
    assert "forward: 0" in lod
    assert "reverse: 0" in lod
    assert "boundaryPointToward(a, b.center" in asset
    assert "directionBias" in asset
    assert "Corridors to other regions" in asset


def test_region_shape_deforms_smoothly_over_time() -> None:
    asset = _mind_sources()
    regions = (WEB_ROOT / "views" / "mind" / "cognitive-regions.js").read_text(encoding="utf-8")

    assert "export function blendRegionShape(" in regions
    assert "graph.regionShapeHistory2d" in asset
    assert "graph.regionShapeHistory3d" in asset
    assert "graph.replaySnapshot ? 1 : 0.24" in asset


def test_region_density_and_functional_center_are_evidence_derived() -> None:
    asset = _mind_sources()
    regions = (WEB_ROOT / "views" / "mind" / "cognitive-regions.js").read_text(encoding="utf-8")

    assert "export function densityHotspots(" in regions
    assert "export function functionalCenter(" in regions
    assert "drawRegionDensity(" in asset
    assert "drawFunctionalCenter(" in asset
    assert "Functional center" in asset
    assert "Center displacement" in asset


def test_anatomy_mode_exposes_proto_subregions_without_reifying_them() -> None:
    asset = _mind_sources()
    regions = (WEB_ROOT / "views" / "mind" / "cognitive-regions.js").read_text(encoding="utf-8")
    atlas = (WEB_ROOT / "views" / "mind" / "cognitive-atlas.js").read_text(encoding="utf-8")

    assert "export function protoSubregions(" in regions
    assert "graph.atlasMode !== 'anatomy'" in asset
    assert "Proto-subregions" in asset
    assert "id: 'anatomy'" in atlas
    assert "label: 'Anatomy'" in atlas


def test_region_functional_centers_keep_short_observer_side_trajectories() -> None:
    asset = _mind_sources()

    assert "rememberCenterTrail(" in asset
    assert "regionCenterTrails2d" in asset
    assert "regionCenterTrails3d" in asset
    assert "while (trail.length > 24)" in asset


def test_dynamics_mode_combines_recent_activity_learning_and_prediction() -> None:
    atlas = (WEB_ROOT / "views" / "mind" / "cognitive-atlas.js").read_text(encoding="utf-8")
    asset = _mind_sources()

    assert "id: 'dynamics'" in atlas
    assert "label: 'Dynamics'" in atlas
    assert "(signal.activity ?? 0) * 0.42" in atlas
    assert "(signal.learning ?? 0) * 0.28" in atlas
    assert "(signal.prediction ?? 0) * 0.20" in atlas
    assert "['learning','dynamics'].includes(graph.atlasMode)" in asset
