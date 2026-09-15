import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class StateFlowTests(unittest.TestCase):
    def test_initial_state_has_topology_cognition_instance_id_fields(self):
        demo_state = read("state", "demo-state.js")
        self.assertIn("topology: null", demo_state)
        self.assertIn("cognition: null", demo_state)
        self.assertIn("instanceId: null", demo_state)

    def test_connect_instance_resets_topology_and_cognition_before_opening_stream(self):
        instance_stream = read("transport", "instance-stream.js")
        reset_topology = instance_stream.index("state.topology = null;")
        reset_cognition = instance_stream.index("state.cognition = null;")
        opens_stream = instance_stream.index("new EventSource(")
        set_instance_id = instance_stream.index("state.instanceId = instanceId;")
        self.assertLess(set_instance_id, opens_stream)
        self.assertLess(reset_topology, opens_stream)
        self.assertLess(reset_cognition, opens_stream)

    def test_instance_stream_stores_bounded_topology_and_rerenders(self):
        instance_stream = read("transport", "instance-stream.js")
        self.assertIn("import { boundedTopology }", instance_stream)
        self.assertIn("state.topology = boundedTopology(payload.topology);", instance_stream)
        self.assertIn("renderCognitionTopology(payload.topology)", instance_stream)
        self.assertIn('if (currentInstanceHasSnapshot && state.view === "individual") renderOrganism();', instance_stream)

    def test_instance_stream_gates_topology_render_on_this_instances_own_snapshot(self):
        """A topology(B) message arriving before B's own first snapshot must
        not repaint the organism using A's still-current senses/beliefs --
        the readiness flag must be reset on connect and only flip true once
        this instance's own snapshot branch has actually run."""
        instance_stream = read("transport", "instance-stream.js")
        declaration = instance_stream.index("let currentInstanceHasSnapshot = false;")
        reset_in_connect = instance_stream.index("currentInstanceHasSnapshot = false;", instance_stream.index("function connectInstance"))
        opens_stream = instance_stream.index("new EventSource(")
        set_true = instance_stream.index("currentInstanceHasSnapshot = true;")
        ingest_call = instance_stream.index("ingestSnapshot(payload.snapshot);")
        self.assertLess(declaration, reset_in_connect)
        self.assertLess(reset_in_connect, opens_stream)
        self.assertLess(set_true, ingest_call)

    def test_load_replay_file_resets_topology_before_first_ingest(self):
        replay = read("transport", "replay.js")
        reset_index = replay.index("state.topology = null;")
        ingest_index = replay.index("ingestSnapshot(state.replay[0], false);")
        self.assertLess(reset_index, ingest_index)

    def test_ingest_snapshot_assigns_cognition_before_rendering_organism(self):
        snapshot = read("projection", "snapshot.js")
        cognition_assignment = snapshot.index("state.cognition = projection.cognition;")
        render_organism_call = snapshot.index("renderOrganism();")
        render_cognition_state_call = snapshot.index("renderCognitionState(projection.cognition);")
        self.assertLess(cognition_assignment, render_organism_call)
        self.assertLess(render_organism_call, render_cognition_state_call)

    def test_bounded_cognition_carries_topology_health_and_recovering(self):
        snapshot = read("projection", "snapshot.js")
        start = snapshot.index("function boundedCognition(")
        end = snapshot.index("\nfunction ", start + 1)
        body = snapshot[start:end]
        self.assertIn("topologyHealth", body)
        self.assertIn("recovering", body)
        self.assertIn('cognition.topology_health', body)
        self.assertIn('cognition.recovering', body)

    def test_render_organism_gates_structure_on_topology_revision_match(self):
        organism_js = read("render", "organism.js")
        self.assertIn("state.topology.topologyRevision === state.cognition.topologyRevision", organism_js)
        self.assertIn('topologyIsCurrent ? state.topology.nodes.filter(n => n.kind === "sense") : []', organism_js)
        self.assertIn('topologyIsCurrent ? state.topology.nodes.filter(n => n.kind !== "sense") : []', organism_js)
        self.assertIn("topologyIsCurrent ? state.topology.edges : []", organism_js)


if __name__ == "__main__":
    unittest.main()
