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

    def test_snapshot_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        organism = schema["properties"]["organism"]
        self.assertFalse(organism["additionalProperties"])
        self.assertEqual(organism["properties"]["percepts"]["maxItems"], 32)
        self.assertEqual(organism["properties"]["beliefs"]["maxItems"], 128)
        self.assertEqual(schema["properties"]["population"]["properties"]["members"]["maxItems"], 500)


if __name__ == "__main__":
    unittest.main()
