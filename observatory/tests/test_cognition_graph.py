import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class CognitionGraphViewTests(unittest.TestCase):
    def test_markup_contains_cognition_option_and_canvas(self):
        index = read("index.html")
        self.assertIn('data-organism-view="cognition"', index)
        self.assertIn('id="cognition-graph-wrap"', index)
        self.assertIn('id="cognition-graph-canvas"', index)
        self.assertIn('id="open-cognition-graph"', index)
        self.assertIn('id="graph-zoom-in"', index)
        self.assertIn('id="graph-zoom-out"', index)
        self.assertIn('id="graph-reset"', index)

    def test_individual_perspective_dispatches_to_cognition_graph(self):
        individual = read("render", "individual.js")
        self.assertIn('import { renderCognitionGraph } from "./cognition-graph.js";', individual)
        self.assertIn('state.organismView === "cognition"', individual)
        self.assertIn("renderCognitionGraph();", individual)

    def test_controls_toggle_cognition_graph_visibility(self):
        controls = read("ui", "controls.js")
        self.assertIn('state.organismView === "cognition"', controls)
        self.assertIn('document.querySelector("#cognition-graph-wrap")?.classList.toggle("hidden", !isCognition);', controls)
        self.assertIn('document.querySelector("#open-cognition-graph")?.addEventListener("click"', controls)

    def test_cognition_graph_module_has_physics_and_interaction(self):
        graph = read("render", "cognition-graph.js")
        self.assertIn("stepPhysics", graph)
        self.assertIn("renderCanvas", graph)
        self.assertIn("installCanvasListeners", graph)
        self.assertIn("renderCognitionGraph", graph)
        # Pan and zoom
        self.assertIn('canvas.addEventListener("wheel"', graph)
        # Hover & Drag
        self.assertIn('canvas.addEventListener("mousedown"', graph)
        self.assertIn('window.addEventListener("mousemove"', graph)
        self.assertIn('window.addEventListener("mouseup"', graph)

    def test_cognition_graph_enriches_learning_dynamics(self):
        graph = read("render", "cognition-graph.js")
        self.assertIn("sensoryDevelopment", graph)
        self.assertIn("sensoryRelations", graph)
        self.assertIn("dev.utility", graph)
        self.assertIn("topRelation", graph)
        self.assertIn("arrowLen", graph)
        self.assertIn("state.selectedNodeId", graph)
        self.assertIn("Anticipates", graph)

    def test_inspector_renders_cognitive_nodes_with_causal_laws(self):
        inspector = read("render", "inspector.js")
        self.assertIn("renderNodeInspector", inspector)
        self.assertIn("Learned Utility", inspector)
        self.assertIn("Discovered Causal & Correlative Dynamics", inspector)
        self.assertIn("Cognitive Convergence", inspector)
        self.assertIn("Convergent Senses", inspector)
        self.assertIn("Prediction Error", inspector)


if __name__ == "__main__":
    unittest.main()
