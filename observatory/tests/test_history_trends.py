import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class HistoryTrendsContractTests(unittest.TestCase):
    def test_live_history_is_bounded_and_replay_is_read_directly(self):
        module = read("ui", "history-trends.js")
        self.assertIn("const MAX_LIVE_SAMPLES = 500", module)
        self.assertIn("slice(-MAX_LIVE_SAMPLES)", module)
        self.assertIn("state.replay.length ? state.replay.map(sampleFromRaw)", module)

    def test_history_has_events_trends_and_topology_diff_views(self):
        module = read("ui", "history-trends.js")
        self.assertIn('["events", "Events"]', module)
        self.assertIn('["trends", "Trends"]', module)
        self.assertIn('["topology", "Topology diff"]', module)
        timeline = read("render", "timeline.js")
        self.assertIn("renderHistoryExplorer();", timeline)

    def test_trends_preserve_missing_measurements_instead_of_inventing_values(self):
        module = read("ui", "history-trends.js")
        self.assertIn('empty.textContent = "Not published in this window."', module)
        self.assertIn("if (!Number.isFinite(value)) { contiguous = false; return; }", module)
        self.assertIn("Descriptive difference only", module)

    def test_replay_ab_comparison_covers_multiple_dimensions(self):
        module = read("ui", "history-trends.js")
        for label in (
            "Acclimation",
            "Active senses",
            "Attention concentration",
            "Contested beliefs",
            "Structural pressure",
            "Relation churn",
        ):
            self.assertIn(label, module)
        self.assertIn("state.compareA", module)
        self.assertIn("state.compareB", module)

    def test_topology_diff_uses_real_revision_snapshots(self):
        module = read("ui", "history-trends.js")
        self.assertIn("recordTopologyRevision(topology)", module)
        self.assertIn("Nodes +${addedNodes.length}/−${removedNodes.length}", module)
        stream = read("transport", "instance-stream.js")
        self.assertIn("recordTopologyRevision(topology);", stream)

    def test_switching_instance_clears_longitudinal_state(self):
        transition = read("state", "transition.js")
        self.assertIn("liveTrendSamples: []", transition)
        self.assertIn("topologyHistory: []", transition)


if __name__ == "__main__":
    unittest.main()
