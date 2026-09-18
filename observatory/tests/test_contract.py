import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


def _read_js_bundle() -> str:
    """All Observatory frontend JS modules concatenated, for contract
    assertions whose intent ("this string must appear/never appear in the
    frontend") is unaffected by exactly which module a line lives in after
    the module split (state/projection/transport/render/ui)."""
    parts = [(ROOT / "app.js").read_text(encoding="utf-8")]
    for sub in ("state", "projection", "transport", "render", "ui"):
        directory = ROOT / sub
        if directory.is_dir():
            for path in sorted(directory.glob("*.js")):
                if path.name == "exports.js":
                    continue
                parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


class ObservatoryContractTests(unittest.TestCase):
    def test_observatory_is_standalone_and_passive(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        app = _read_js_bundle()

        self.assertIn('./styles.css', index)
        self.assertIn('./app.js', index)
        self.assertNotIn('from "symbiont', app)
        self.assertNotIn("fetch(", app)
        self.assertIn("symbiont-observatory-snapshot", app)
        self.assertIn("event.origin !== window.location.origin", app)
        for element_id in ("welcome", "replay-dialog", "replay-file", "audit-drawer", "export-replay", "history-search", "history-panel", "event-detail", "mark-a", "mark-b", "population-tools", "population-inspector", "organism-comparison", "summary-profile", "organism-profile", "research-profile", "help-drawer", "accessible-table"):
            self.assertIn(f'id="{element_id}"', index)
        self.assertIn("5 * 1024 * 1024", app)
        self.assertIn("snapshots.length > 10000", app)
        self.assertIn('new BroadcastChannel("symbiont-observatory-v1")', app)

    def test_live_tick_never_drifts_from_the_last_real_snapshot(self) -> None:
        snapshot_js = (ROOT / "projection" / "snapshot.js").read_text(encoding="utf-8")
        commit_js = (ROOT / "state" / "commit.js").read_text(encoding="utf-8")
        timeline_js = (ROOT / "render" / "timeline.js").read_text(encoding="utf-8")
        app = (ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("realTick", commit_js)
        self.assertIn("state.realTick = projection.tick", commit_js)
        self.assertIn('state.mode === "live" && state.source === "demo"', app)
        self.assertIn("state.realTick ?? state.tick", timeline_js)

    def test_inspector_selection_re_resolves_against_the_new_snapshot(self) -> None:
        commit_js = (ROOT / "state" / "commit.js").read_text(encoding="utf-8")

        self.assertIn("state.beliefs.find(item => item.id === state.selected?.id) ?? state.beliefs[0] ?? null", commit_js)
        self.assertNotIn("beliefs.some(item => item.id === state.selected?.id) ? state.selected", commit_js)

    def test_snapshot_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["enum"], [1, 2, 3])
        organism = schema["properties"]["organism"]
        self.assertFalse(organism["additionalProperties"])
        self.assertEqual(organism["properties"]["percepts"]["maxItems"], 32)
        self.assertEqual(organism["properties"]["beliefs"]["maxItems"], 128)
        events = organism["properties"]["events"]
        self.assertEqual(events["maxItems"], 64)
        self.assertFalse(events["items"]["additionalProperties"])
        self.assertEqual(events["items"]["properties"]["causal_chain"]["maxItems"], 8)
        self.assertEqual(organism["properties"]["memory"]["maxItems"], 32)
        self.assertEqual(organism["properties"]["open_questions"]["maxItems"], 16)
        self.assertEqual(organism["properties"]["investigations"]["maxItems"], 16)
        self.assertEqual(organism["properties"]["regime_changes"]["maxItems"], 16)
        self.assertFalse(organism["properties"]["resource_budget"]["additionalProperties"])
        self.assertEqual(schema["properties"]["population"]["properties"]["members"]["maxItems"], 500)
        relationships = schema["properties"]["population"]["properties"]["relationships"]
        self.assertEqual(relationships["maxItems"], 1000)
        self.assertFalse(relationships["items"]["additionalProperties"])
        self.assertEqual(relationships["items"]["properties"]["strength"]["maximum"], 1)

    def test_snapshot_schema_version_gates_cognition_and_body_schema_independently(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["enum"], [1, 2, 3])
        organism = schema["properties"]["organism"]
        self.assertIn("cognition", organism["properties"])
        self.assertIn("body_schema", organism["properties"])
        self.assertEqual(organism["properties"]["body_schema"]["$ref"], "./body_schema.schema.json")
        self.assertEqual(len(schema["allOf"]), 3)
        serialized = json.dumps(schema["allOf"])
        self.assertIn('"const": 1', serialized)
        self.assertIn('"const": 2', serialized)
        self.assertIn('"const": 3', serialized)
        v3_rule = next(rule for rule in schema["allOf"] if rule["if"]["properties"]["schema_version"].get("const") == 3)
        self.assertEqual(v3_rule["then"]["properties"]["organism"]["required"], ["body_schema"])

    def test_body_schema_contract_is_closed_bounded_and_versioned(self) -> None:
        schema = json.loads((ROOT / "body_schema.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["enum"], [1, 2])
        self.assertEqual(schema["properties"]["state"]["enum"], ["undeveloped", "partial"])
        self.assertEqual(schema["properties"]["parts"]["maxItems"], 288)
        part = schema["properties"]["parts"]["items"]
        self.assertFalse(part["additionalProperties"])
        self.assertEqual(part["properties"]["kind"]["enum"], ["sense", "cognitive_region"])
        dependencies = schema["properties"]["dependencies"]
        self.assertEqual(dependencies["maxItems"], 256)
        self.assertFalse(dependencies["items"]["additionalProperties"])
        self.assertEqual(dependencies["items"]["properties"]["relation"]["enum"], ["co_acts_with", "precedes"])
        self.assertFalse(schema["properties"]["global_state"]["additionalProperties"])
        self.assertEqual(schema["properties"]["global_state"]["maxProperties"], 0)
        serialized = json.dumps(schema)
        self.assertIn('"const": 1', serialized)
        self.assertIn('"maxItems": 256', serialized)
        self.assertIn("part\\\\.sense", serialized)
        self.assertIn("part\\\\.region", serialized)
        for forbidden in ("id_salt", "cognitive_learning", "channel.cognition"):
            self.assertNotIn(forbidden, serialized)

    def test_cognition_state_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "cognition_state.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["prediction_errors"]["additionalProperties"]["enum"],
            ["zero", "trace", "low", "medium", "high", "extreme"],
        )
        self.assertEqual(schema["properties"]["mutations"]["maxItems"], 8)
        self.assertFalse(schema["properties"]["safety_state"]["additionalProperties"])

    def test_topology_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "topology.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["nodes"]["maxItems"], 128)
        self.assertEqual(schema["properties"]["edges"]["maxItems"], 1024)
        self.assertFalse(schema["properties"]["nodes"]["items"]["additionalProperties"])
        self.assertFalse(schema["properties"]["edges"]["items"]["additionalProperties"])
        self.assertNotIn("weight", schema["properties"]["edges"]["items"]["properties"])

    def test_instance_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "instance.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        for field in ("instance_id", "run_id", "display_id", "started_at", "last_heartbeat", "topology_revision"):
            self.assertIn(field, schema["required"])
        self.assertEqual(schema["properties"]["instance_id"]["pattern"], "^[0-9a-f]{16}$")

    def test_frontend_has_a_v1_v2_v3_snapshot_normalizer(self) -> None:
        snapshot_js = (ROOT / "projection" / "snapshot.js").read_text(encoding="utf-8")
        body_js = (ROOT / "projection" / "body-schema.js").read_text(encoding="utf-8")
        self.assertIn("function normalizeSnapshot(", snapshot_js)
        self.assertIn("[1, 2, 3]", snapshot_js)
        self.assertIn('import { boundedBodySchema } from "./body-schema.js";', snapshot_js)
        self.assertIn("function boundedBodySchema(", body_js)
        self.assertIn("function bodySchemaToWire(", body_js)
        self.assertIn("cognitive_region", body_js)
        self.assertIn("co_acts_with", body_js)
        self.assertIn("precedes", body_js)

    def test_cell_path_is_gone_and_morphology_projector_is_wired_in(self) -> None:
        bundle = _read_js_bundle()
        self.assertNotIn("cellPath", bundle)
        self.assertNotIn(".membrane", (ROOT / "styles.css").read_text(encoding="utf-8"))
        organism_js = (ROOT / "render" / "organism.js").read_text(encoding="utf-8")
        morphology_js = (ROOT / "projection" / "morphology.js").read_text(encoding="utf-8")
        topology_js = (ROOT / "projection" / "topology.js").read_text(encoding="utf-8")
        self.assertIn("import { projectPhenotypeMorphology }", organism_js)
        self.assertIn("function projectPhenotypeMorphology(", morphology_js)
        self.assertIn("function boundedTopology(", topology_js)
        self.assertIn(".phenotype-boundary", (ROOT / "styles.css").read_text(encoding="utf-8"))

    def test_phenotype_self_toggle_markup_exists(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="organism-view-toggle"', index)
        self.assertIn('data-organism-view="phenotype"', index)
        self.assertIn('data-organism-view="self"', index)
        self.assertIn('id="self-panel"', index)

    def test_frontend_has_a_fleet_sidebar_and_cognition_tab(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        fleet_js = (ROOT / "transport" / "fleet-stream.js").read_text(encoding="utf-8")
        instance_js = (ROOT / "transport" / "instance-stream.js").read_text(encoding="utf-8")
        self.assertIn('id="fleet-panel"', index)
        self.assertIn('data-tab="cognition"', index)
        self.assertIn("new EventSource(", fleet_js)
        self.assertIn("/fleet", fleet_js)
        self.assertIn("new EventSource(", instance_js)
        self.assertIn("/instance/", instance_js)

    def test_replay_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "replay.schema.json").read_text(encoding="utf-8"))
        snapshots = schema["properties"]["snapshots"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(snapshots["minItems"], 1)
        self.assertEqual(snapshots["maxItems"], 10000)
        self.assertEqual(snapshots["items"]["$ref"], "./snapshot.schema.json")

    def test_frontend_preserves_live_sensory_projection_and_relations(self) -> None:
        app = _read_js_bundle()
        self.assertIn("sensoryDevelopment", app)
        self.assertIn("sensoryRelations", app)
        self.assertIn("socialRelations", app)
        self.assertIn("Social evidence", app)
        self.assertIn("organism.social_relations", app)
        self.assertIn('"Social evidence"', app)
        self.assertIn("sampling", app)
        self.assertIn("organism.sensory_development", app)
        self.assertIn("organism.sensory_relations", app)
        self.assertIn("organism.sampling", app)
        self.assertNotIn("Math.sin(i * 1.8", app)
        self.assertIn("state.senseHistory", app)

    def test_frontend_live_events_do_not_fall_back_to_demo_events(self) -> None:
        app = _read_js_bundle()
        self.assertIn("liveEvents", app)
        self.assertIn('state.source !== "demo" ? state.liveEvents : demoEvents', app)
        self.assertNotIn("const focus = beliefs[(state.tick + 7) % beliefs.length]", app)
        self.assertNotIn("205 + i * 80", app)
        self.assertIn("Structural cognition not configured", app)

    def test_resident_prioritizes_active_and_probing_states(self) -> None:
        resident = (ROOT / "resident.py").read_text(encoding="utf-8")
        self.assertIn("active_states + probing_states + dormant_states", resident)

    def test_resident_publishes_only_observer_safe_body_schema(self) -> None:
        resident = (ROOT / "resident.py").read_text(encoding="utf-8")
        self.assertIn("runtime.body_schema.export_representation", resident)
        self.assertNotIn("runtime.body_schema.export(current_tick", resident)

    def test_render_self_exists_and_consumes_body_schema(self) -> None:
        self_js = (ROOT / "render" / "self.js").read_text(encoding="utf-8")
        self.assertIn("function renderSelf(", self_js)
        self.assertIn("Body schema not yet developed", self_js)
        self.assertIn("Self-known functional body", self_js)
        self.assertIn("Cognitive regions", self_js)
        self.assertIn("Functional dependencies", self_js)
        self.assertIn('import { projectSelfSchema }', self_js)
        self.assertIn("projectSelfSchema(state.bodySchema)", self_js)

    def test_render_self_never_reads_privileged_phenotype_state(self) -> None:
        self_js = (ROOT / "render" / "self.js").read_text(encoding="utf-8")
        for forbidden in ("state.topology", "state.cognition", "state.senses", "state.beliefs"):
            self.assertNotIn(forbidden, self_js)

    def test_replay_export_preserves_self_without_reconstructing_cognition(self) -> None:
        replay_js = (ROOT / "transport" / "replay.js").read_text(encoding="utf-8")
        self.assertIn('import { bodySchemaToWire } from "../projection/body-schema.js";', replay_js)
        self.assertIn("schema_version: bodySchema ? 3 : 1", replay_js)
        self.assertNotIn("state.cognition", replay_js[replay_js.index("function currentSnapshot("):])

    def test_render_individual_perspective_is_the_single_dispatcher(self) -> None:
        individual_js = (ROOT / "render" / "individual.js").read_text(encoding="utf-8")
        self.assertIn("function renderIndividualPerspective(", individual_js)
        self.assertIn('if (state.view !== "individual") return;', individual_js)
        self.assertIn('if (state.organismView === "self") renderSelf(); else renderOrganism();', individual_js)

    def test_phenotype_internal_anchors_support_distinct_morphologies(self) -> None:
        organism_js = (ROOT / "render" / "organism.js").read_text(encoding="utf-8")
        styles_css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn('case "state":', organism_js)
        self.assertIn('case "predictor":', organism_js)
        self.assertIn('case "gate":', organism_js)
        self.assertIn('case "readout":', organism_js)
        self.assertNotIn('"modulatory"', organism_js)
        self.assertIn(".internal-anchor-state", styles_css)
        self.assertIn(".internal-anchor-predictor", styles_css)
        self.assertIn(".internal-anchor-gate", styles_css)


class SensoryWorldMapContractTests(unittest.TestCase):
    def test_sensory_world_map_is_wired_and_passive(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        renderer = (ROOT / "render" / "sensory-map.js").read_text(encoding="utf-8")
        individual = (ROOT / "render" / "individual.js").read_text(encoding="utf-8")
        controls = (ROOT / "ui" / "controls.js").read_text(encoding="utf-8")

        self.assertIn('data-organism-view="sensory"', index)
        self.assertIn('id="sensory-map-wrap"', index)
        self.assertIn('id="sensory-world-canvas"', index)
        self.assertIn('id="sensory-modality-filter"', index)
        self.assertIn("renderSensoryMap", individual)
        self.assertIn('state.organismView === "sensory"', individual)
        self.assertIn('"#sensory-map-wrap"', controls)
        self.assertIn("World → receptor → cognition", index)
        self.assertNotIn("fetch(", renderer)
        self.assertNotIn("WebSocket", renderer)
        self.assertNotIn("EventSource", renderer)

    def test_sensory_map_uses_world_sensor_downstream_contract(self) -> None:
        renderer = (ROOT / "render" / "sensory-map.js").read_text(encoding="utf-8")
        self.assertIn("sensor.signalIds", renderer)
        self.assertIn("sensor.transduction", renderer)
        self.assertIn("sensor.sampleGeometry", renderer)
        self.assertIn("sensor.downstreamName", renderer)
        self.assertIn("sensor.selectionCredit", renderer)
        self.assertIn("state.sensoryRelations", renderer)
        self.assertIn("derived modalities: not yet available (M07)", renderer)

    def test_sensory_snapshot_extension_is_optional_for_replay_compatibility(self) -> None:
        schema = json.loads((ROOT / "schemas" / "snapshot.schema.json").read_text(encoding="utf-8"))
        sensory = schema["properties"]["organism"]["properties"]["sensory_phenotype"]
        modality = sensory["properties"]["modalities"]["items"]
        sensor = sensory["properties"]["sensors"]["items"]

        self.assertIn("allowed_transductions", modality["properties"])
        self.assertNotIn("allowed_transductions", modality["required"])
        self.assertIn("sample_geometry", sensor["properties"])
        self.assertIn("transduction", sensor["properties"])
        self.assertNotIn("sample_geometry", sensor["required"])
        self.assertNotIn("transduction", sensor["required"])


if __name__ == "__main__":
    unittest.main()
