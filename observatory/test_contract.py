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
        for element_id in ("welcome", "replay-dialog", "replay-file", "audit-drawer", "export-replay", "history-search", "history-panel", "event-detail", "mark-a", "mark-b"):
            self.assertIn(f'id="{element_id}"', index)
        self.assertIn("5 * 1024 * 1024", app)
        self.assertIn("snapshots.length > 10000", app)

    def test_snapshot_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        organism = schema["properties"]["organism"]
        self.assertFalse(organism["additionalProperties"])
        self.assertEqual(organism["properties"]["percepts"]["maxItems"], 32)
        self.assertEqual(organism["properties"]["beliefs"]["maxItems"], 128)
        events = organism["properties"]["events"]
        self.assertEqual(events["maxItems"], 64)
        self.assertFalse(events["items"]["additionalProperties"])
        self.assertEqual(events["items"]["properties"]["causal_chain"]["maxItems"], 8)
        self.assertEqual(schema["properties"]["population"]["properties"]["members"]["maxItems"], 500)

    def test_replay_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "replay.schema.json").read_text(encoding="utf-8"))
        snapshots = schema["properties"]["snapshots"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(snapshots["minItems"], 1)
        self.assertEqual(snapshots["maxItems"], 10000)
        self.assertEqual(snapshots["items"]["$ref"], "./snapshot.schema.json")


if __name__ == "__main__":
    unittest.main()
