import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class ObservatoryConsolidationTests(unittest.TestCase):
    def test_trends_do_not_coerce_missing_values_to_zero(self):
        module = read("ui", "history-trends.js")
        self.assertIn('if (value === null || value === undefined || value === "") return null;', module)
        self.assertLess(
            module.index('if (value === null || value === undefined || value === "") return null;'),
            module.index('const number = Number(value);'),
        )

    def test_fleet_transport_routes_shared_state_through_transition_boundary(self):
        module = read("transport", "fleet-population.js")
        self.assertIn('import { updateUiState } from "../state/transition.js";', module)
        self.assertIn('updateUiState({ fleetConnected: true, fleetInstances: instances });', module)
        self.assertIn('fleetRelationships: []', module)
        self.assertNotIn('state.fleetPopulation =', module)
        self.assertNotIn('state.fleetRelationships =', module)
        self.assertNotIn('state.fleetConnected =', module)
        self.assertNotIn('state.fleetInstances =', module)


if __name__ == "__main__":
    unittest.main()
