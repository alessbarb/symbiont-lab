import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class PopulationDynamicsTests(unittest.TestCase):
    def test_markup_contains_population_canvas_and_action_controls(self):
        index = read("index.html")
        self.assertIn('id="population-canvas"', index)
        self.assertIn('<canvas id="population-canvas"', index)
        self.assertIn('id="population-tools"', index)
        self.assertIn('id="population-traffic-toggle"', index)
        self.assertIn('id="population-reset"', index)

    def test_population_module_exports_and_dynamic_capabilities(self):
        pop = read("render", "population.js")
        self.assertIn("export { renderPopulation, selectPopulationMember, renderPopulationInspector };", pop)
        self.assertIn("stepPhysics", pop)
        self.assertIn("trafficPhase", pop)
        self.assertIn("trafficEnabled", pop)
        self.assertIn("renderCanvasFrame", pop)
        self.assertIn("renderMiniSvg", pop)
        self.assertIn("installPopulationCanvasListeners", pop)
        self.assertIn("CLUSTER_COLORS", pop)

    def test_demo_state_provides_rich_social_relationships(self):
        demo = read("state", "demo-state.js")
        self.assertIn("support", demo)
        self.assertIn("harm", demo)
        self.assertIn("valence", demo)
        self.assertIn("reliability", demo)
        self.assertIn("freshness", demo)
        self.assertIn("channel", demo)

    def test_css_styles_population_action_buttons(self):
        css = read("styles.css")
        self.assertIn(".population-btn", css)

    def test_dyad_mutualism_dial_analysis_and_styles(self):
        pop = read("render", "population.js")
        self.assertIn("Dial de Mutualismo", pop)
        self.assertIn("Mutualismo Simbiótico", pop)
        self.assertIn("Antagonismo / Conflicto", pop)
        self.assertIn("Comensalismo Asimétrico", pop)
        self.assertIn("distToSegment", pop)
        self.assertIn("dyad-card", pop)
        css = read("styles.css")
        self.assertIn(".dyad-card", css)
        self.assertIn(".dyad-archetype-badge", css)


if __name__ == "__main__":
    unittest.main()
