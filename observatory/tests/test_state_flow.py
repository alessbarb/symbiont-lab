import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class StateFlowTests(unittest.TestCase):
    def test_initial_state_has_topology_cognition_instance_id_fields(self):
        demo_state = read("state", "demo-state.js")
        self.assertIn("topology: null", demo_state)
        self.assertIn("cognition: null", demo_state)
        self.assertIn("instanceId: null", demo_state)

    def test_initial_state_has_organism_view_and_body_schema_fields(self):
        demo_state = read("state", "demo-state.js")
        self.assertIn('organismView: "phenotype"', demo_state)
        self.assertIn("bodySchema: null", demo_state)

    def test_connect_instance_resets_topology_cognition_and_self_before_opening_stream(self):
        instance_stream = read("transport", "instance-stream.js")
        reset_topology = instance_stream.index("resetInstanceProjection();")
        reset_cognition = reset_topology
        reset_body_schema = reset_topology
        opens_stream = instance_stream.index("new EventSource(")
        set_instance_id = instance_stream.index("updateUiState({ instanceId });")
        self.assertLess(set_instance_id, opens_stream)
        self.assertLess(reset_topology, opens_stream)
        self.assertLess(reset_cognition, opens_stream)
        self.assertLess(reset_body_schema, opens_stream)

    def test_instance_stream_stores_bounded_topology_and_rerenders(self):
        instance_stream = read("transport", "instance-stream.js")
        self.assertIn("import { boundedTopology }", instance_stream)
        self.assertIn("const topology = boundedTopology(payload.topology);", instance_stream)
        self.assertIn("updateUiState({ topology });", instance_stream)
        self.assertIn("renderCognitionTopology(payload.topology)", instance_stream)
        self.assertIn(
            "if (currentInstanceHasSnapshot) renderIndividualPerspective();", instance_stream
        )

    def test_instance_stream_gates_topology_render_on_this_instances_own_snapshot(self):
        instance_stream = read("transport", "instance-stream.js")
        declaration = instance_stream.index("let currentInstanceHasSnapshot = false;")
        reset_in_connect = instance_stream.index(
            "currentInstanceHasSnapshot = false;", instance_stream.index("function connectInstance")
        )
        opens_stream = instance_stream.index("new EventSource(")
        set_true = instance_stream.index("currentInstanceHasSnapshot = true;")
        ingest_call = instance_stream.index("ingestSnapshot(payload.snapshot)")
        self.assertLess(declaration, reset_in_connect)
        self.assertLess(reset_in_connect, opens_stream)
        self.assertLess(set_true, ingest_call)

    def test_load_replay_file_resets_privileged_and_self_state_before_first_ingest(self):
        replay = read("transport", "replay.js")
        ingest_index = replay.index("ingestSnapshot(state.replay[0], false)")
        reset_index = replay.index("resetInstanceProjection();")
        self.assertLess(reset_index, ingest_index)

    def test_ingest_snapshot_assigns_cognition_and_self_before_rendering_individual_perspective(
        self,
    ):
        snapshot = read("projection", "snapshot.js")
        commit = read("state", "commit.js")
        cognition_assignment = commit.index("state.cognition = projection.cognition;")
        body_schema_assignment = commit.index("state.bodySchema = projection.bodySchema;")
        render_call = snapshot.index("return projection;")
        render_cycle = read("app.js").index("renderSnapshotCycle(projection.cognition);")
        cycle = read("ui", "render-cycle.js")
        individual_call = cycle.index("renderIndividualPerspective();")
        cognition_call = cycle.index("renderCognitionState(cognition);")
        self.assertLess(cognition_assignment, render_call)
        self.assertLess(body_schema_assignment, render_call)
        self.assertLess(render_cycle, len(read("app.js")))
        self.assertLess(individual_call, cognition_call)

    def test_snapshot_uses_the_single_pure_body_schema_normalizer(self):
        snapshot = read("projection", "snapshot.js")
        self.assertIn('import { boundedBodySchema } from "./body-schema.js";', snapshot)
        self.assertEqual(snapshot.count("function boundedBodySchema("), 0)
        self.assertIn("const bodySchema = boundedBodySchema(organism.body_schema);", snapshot)

    def test_bounded_cognition_carries_topology_health_and_recovering(self):
        snapshot = read("projection", "snapshot.js")
        start = snapshot.index("function boundedCognition(")
        end = snapshot.index("\nfunction ", start + 1)
        body = snapshot[start:end]
        self.assertIn("topologyHealth", body)
        self.assertIn("recovering", body)
        self.assertIn("cognition.topology_health", body)
        self.assertIn("cognition.recovering", body)

    def test_app_boot_uses_the_single_individual_dispatcher(self):
        app_js = read("app.js")
        self.assertIn(
            'import { renderIndividualPerspective } from "./render/individual.js";', app_js
        )
        self.assertNotIn('import { renderOrganism } from "./render/organism.js";', app_js)
        self.assertIn("renderIndividualPerspective();", app_js)
        self.assertNotIn("renderOrganism();", app_js)

    def test_switch_view_uses_the_single_individual_dispatcher(self):
        controls_js = read("ui", "controls.js")
        self.assertIn("else renderIndividualPerspective();", controls_js)

    def test_advance_uses_the_single_individual_dispatcher_unconditionally(self):
        controls_js = read("ui", "controls.js")
        self.assertIn(
            "renderTimeline(); renderInspector(); renderIndividualPerspective();", controls_js
        )
        self.assertNotIn('if (state.view === "individual") renderOrganism();', controls_js)

    def test_organism_belief_click_uses_the_single_individual_dispatcher(self):
        organism_js = read("render", "organism.js")
        self.assertIn("renderIndividualPerspective();", organism_js)
        self.assertIn('import { renderIndividualPerspective } from "./individual.js";', organism_js)

    def test_senses_click_uses_the_single_individual_dispatcher(self):
        senses_js = read("render", "senses.js")
        self.assertIn("renderIndividualPerspective();", senses_js)
        self.assertIn('import { renderIndividualPerspective } from "./individual.js";', senses_js)
        self.assertNotIn('import { renderOrganism } from "./organism.js";', senses_js)

    def test_render_organism_gates_structure_on_topology_revision_match(self):
        organism_js = read("render", "organism.js")
        self.assertIn(
            "state.topology.topologyRevision === state.cognition.topologyRevision", organism_js
        )
        self.assertIn(
            'topologyIsCurrent ? state.topology.nodes.filter(n => n.kind === "sense") : []',
            organism_js,
        )
        self.assertIn("topologyIsCurrent ? state.topology.nodes : []", organism_js)
        self.assertIn("topologyIsCurrent ? state.topology.edges : []", organism_js)

    def test_apply_individual_canvas_visibility_called_from_switch_view_and_switch_organism_view(
        self,
    ):
        controls_js = read("ui", "controls.js")
        define_index = controls_js.index("function applyIndividualCanvasVisibility(")
        switch_organism_view_start = controls_js.index("function switchOrganismView(")
        switch_view_start = controls_js.index("function switchView(")
        switch_view_end = controls_js.index("\n}", switch_view_start)
        switch_view_body = controls_js[switch_view_start:switch_view_end]
        self.assertLess(define_index, switch_organism_view_start)
        self.assertLess(define_index, switch_view_start)
        self.assertIn("applyIndividualCanvasVisibility();", switch_view_body)

    def test_switch_organism_view_sets_state_before_applying_visibility(self):
        controls_js = read("ui", "controls.js")
        start = controls_js.index("function switchOrganismView(")
        end = controls_js.index("\n}", start)
        body = controls_js[start:end]
        set_index = body.index("updateUiState({ organismView });")
        visibility_index = body.index("applyIndividualCanvasVisibility();")
        render_index = body.index("renderIndividualPerspective();")
        persist_index = body.index('localStorage.setItem("symbiont-observatory-organism-view"')
        self.assertLess(set_index, visibility_index)
        self.assertLess(visibility_index, render_index)
        self.assertLess(render_index, persist_index)

    def test_apply_individual_canvas_visibility_covers_self_epistemic_boundary(self):
        controls_js = read("ui", "controls.js")
        start = controls_js.index("function applyIndividualCanvasVisibility(")
        end = controls_js.index("\n}", start)
        body = controls_js[start:end]
        self.assertIn('document.querySelector("#organism-canvas")', body)
        self.assertIn('document.querySelector("#self-panel")', body)
        self.assertIn('document.querySelector("#sensory-map-wrap")', body)
        self.assertIn('document.querySelector("#organism-view-toggle")', body)
        self.assertIn('document.querySelector(".canvas-legend")', body)
        self.assertIn('document.querySelector(".canvas-heading")', body)
        self.assertIn('const isSensory = isIndividual && state.organismView === "sensory";', body)
        self.assertIn('classList.toggle("hidden", isSelf || isSensory)', body)

    def test_switch_view_uses_real_state_labels_not_demo_literals(self):
        controls_js = read("ui", "controls.js")
        self.assertIn("function formatOrganismState()", controls_js)
        self.assertIn("function formatPopulationState()", controls_js)
        self.assertIn(
            'view === "individual" ? formatOrganismState() : formatPopulationState()', controls_js
        )
        self.assertNotIn('"Active · Exploring"', controls_js)
        self.assertNotIn('"18 organisms · 3 ecologies"', controls_js)

    def test_organism_view_option_buttons_get_aria_pressed_updates(self):
        controls_js = read("ui", "controls.js")
        self.assertIn('b.setAttribute("aria-pressed", String(active));', controls_js)

    def test_app_restores_stored_organism_view_on_boot(self):
        app_js = read("app.js")
        self.assertIn('localStorage.getItem("symbiont-observatory-organism-view")', app_js)
        self.assertIn(
            '["phenotype", "sensory", "self", "cognition", "regimes"].includes(storedOrganismView)',
            app_js,
        )


if __name__ == "__main__":
    unittest.main()
