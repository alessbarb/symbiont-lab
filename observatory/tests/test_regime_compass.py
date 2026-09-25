import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class RegimeCompassViewTests(unittest.TestCase):
    def test_markup_contains_regime_compass_elements(self):
        index = read("index.html")
        self.assertIn('data-organism-view="regimes"', index)
        self.assertIn('id="regime-compass-wrap"', index)
        self.assertIn('id="regime-compass-canvas"', index)
        self.assertIn('id="compass-status-card"', index)
        self.assertIn('id="compass-unexplored-alert"', index)
        self.assertIn('id="open-regime-compass"', index)
        self.assertIn('id="compass-contour-toggle"', index)
        self.assertIn('id="compass-trail-toggle"', index)
        self.assertIn('id="compass-reset"', index)

    def test_individual_perspective_dispatches_to_regime_compass(self):
        individual = read("render", "individual.js")
        self.assertIn('import { renderRegimeCompass } from "./regime-compass.js";', individual)
        self.assertIn('state.organismView === "regimes"', individual)
        self.assertIn("renderRegimeCompass();", individual)

    def test_controls_manage_regime_compass(self):
        controls = read("ui", "controls.js")
        self.assertIn('state.organismView === "regimes"', controls)
        self.assertIn(
            'document.querySelector("#regime-compass-wrap")?.classList.toggle("hidden", !isRegimes);',
            controls,
        )
        self.assertIn(
            'document.querySelector("#open-regime-compass")?.addEventListener("click"', controls
        )

    def test_regime_compass_module_exports_and_logic(self):
        compass = read("render", "regime-compass.js")
        self.assertIn(
            "export { renderRegimeCompass, REGIMES, computeHostCoordinates, evaluateRegimes };",
            compass,
        )
        self.assertIn("Quiescencia Nocturna", compass)
        self.assertIn("Carga Sostenida / Trabajo Regular", compass)
        self.assertIn("Transición Concurrente / Ráfagas E/S", compass)
        self.assertIn("Desincronización / Estrés Ambiental", compass)
        self.assertIn("computeHostCoordinates", compass)
        self.assertIn("evaluateRegimes", compass)
        self.assertIn("isUnexplored", compass)
        self.assertIn("noveltyPct", compass)
        self.assertIn("updateTrail", compass)
        self.assertIn("sonarPhase", compass)

    def test_css_styles_regime_compass(self):
        css = read("styles.css")
        self.assertIn(".regime-compass-wrap", css)
        self.assertIn("#regime-compass-canvas", css)
        self.assertIn(".compass-hud", css)
        self.assertIn(".compass-card", css)
        self.assertIn(".compass-badge", css)
        self.assertIn(".compass-alert", css)


if __name__ == "__main__":
    unittest.main()
