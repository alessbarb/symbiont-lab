import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parent


class ObservatoryContractTests(unittest.TestCase):
    def test_observatory_is_standalone_and_passive(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "app.js").read_text(encoding="utf-8")

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
        """Roadmap safety finding A08: the demo/replay animation timer must
        never mutate the real ingested tick once real data has arrived, and
        the on-screen/exported tick must reflect that real value, not a
        demo-only 0-59 animation slot."""
        app = (ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("realTick", app)
        self.assertIn("state.realTick = projection.tick", app)
        # The live-mode branch of the animation interval must be gated on
        # still being in demo (no real snapshot received yet) — verified
        # live in-browser via Playwright during development of this fix.
        self.assertIn('state.mode === "live" && state.source === "demo"', app)
        self.assertIn("state.realTick ?? state.tick", app)

    def test_inspector_selection_re_resolves_against_the_new_snapshot(self) -> None:
        """Roadmap safety finding B07: when a belief with the same id survives
        into a new snapshot, the Inspector must show its *new* certainty/
        evidence, not silently keep displaying the previous snapshot's now-stale
        object just because the id still matched."""
        app = (ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("beliefs.find(item => item.id === state.selected?.id) ?? beliefs[0] ?? null", app)
        self.assertNotIn("beliefs.some(item => item.id === state.selected?.id) ? state.selected", app)

    def test_snapshot_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["enum"], [1, 2])
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

    def test_snapshot_schema_version_gates_cognition_presence(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["enum"], [1, 2])
        organism = schema["properties"]["organism"]
        self.assertIn("cognition", organism["properties"])
        self.assertIn("if", schema)
        self.assertIn("then", schema)
        self.assertIn("else", schema)

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

    def test_frontend_has_a_v1_v2_snapshot_normalizer(self) -> None:
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("function normalizeSnapshot(", app)
        self.assertIn("schema_version", app)

    def test_frontend_has_a_fleet_sidebar_and_cognition_tab(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="fleet-panel"', index)
        self.assertIn('data-tab="cognition"', index)
        self.assertIn("new EventSource(", app)
        self.assertIn("/fleet", app)
        self.assertIn("/instance/", app)

    def test_replay_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "replay.schema.json").read_text(encoding="utf-8"))
        snapshots = schema["properties"]["snapshots"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(snapshots["minItems"], 1)
        self.assertEqual(snapshots["maxItems"], 10000)
        self.assertEqual(snapshots["items"]["$ref"], "./snapshot.schema.json")

    def test_frontend_preserves_live_sensory_projection_and_relations(self) -> None:
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("sensoryDevelopment", app)
        self.assertIn("sensoryRelations", app)
        self.assertIn("sampling", app)
        self.assertIn("organism.sensory_development", app)
        self.assertIn("organism.sensory_relations", app)
        self.assertIn("organism.sampling", app)
        self.assertNotIn("Math.sin(i * 1.8", app)
        self.assertIn("state.senseHistory", app)

    def test_frontend_live_events_do_not_fall_back_to_demo_events(self) -> None:
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("liveEvents", app)
        self.assertIn('state.source !== "demo" ? state.liveEvents : demoEvents', app)
        self.assertNotIn("const focus = beliefs[(state.tick + 7) % beliefs.length]", app)
        self.assertNotIn("205 + i * 80", app)
        self.assertIn("Structural cognition not configured", app)

    def test_resident_prioritizes_active_and_probing_states(self) -> None:
        resident = (ROOT / "resident.py").read_text(encoding="utf-8")
        self.assertIn("active_states + probing_states + dormant_states", resident)


if __name__ == "__main__":
    unittest.main()
