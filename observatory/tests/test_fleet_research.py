import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class FleetResearchContractTests(unittest.TestCase):
    def test_fleet_projection_carries_research_fields_without_global_relationships(self):
        population = read("transport", "fleet-population.js")
        for field in ("schemaVersion", "physiology", "organismState", "acclimation", "attentionConcentration", "activeSenses"):
            self.assertIn(field, population)
        self.assertIn("fleetRelationships: []", population)

    def test_fleet_table_supports_search_filters_and_sorting(self):
        module = read("ui", "observability.js")
        for control in ("fleet-liveness-filter", "fleet-schema-filter", "fleet-physiology-filter"):
            self.assertIn(control, module)
        self.assertIn("compareFleetRows", module)
        self.assertIn('cell.setAttribute("aria-sort"', module)
        self.assertIn("fleetView.query", module)

    def test_missing_fleet_metrics_are_explicit_not_zero_filled(self):
        population = read("transport", "fleet-population.js")
        self.assertIn("pressure: local?.pressure ?? null", population)
        self.assertIn("knowledge: local?.knowledge ?? null", population)
        self.assertIn("contested: local?.contested ?? null", population)
        module = read("ui", "observability.js")
        self.assertIn('return value == null', module)
        self.assertIn('"not published"', module)

    def test_shortlist_compares_up_to_four_without_scoring(self):
        module = read("ui", "observability.js")
        self.assertIn("fleetView.pinned.size < 4", module)
        self.assertIn("Fleet shortlist", module)
        self.assertIn("no aggregate trust, health or fitness score is computed", module)

    def test_global_relationship_absence_is_explained(self):
        module = read("ui", "observability.js")
        self.assertIn("Fleet relationships are intentionally not synthesized", module)
        self.assertIn("not globally addressable", module)


if __name__ == "__main__":
    unittest.main()
