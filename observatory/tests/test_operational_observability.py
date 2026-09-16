import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class OperationalObservabilityContractTests(unittest.TestCase):
    def test_operational_strip_exposes_provenance_and_freshness_fields(self):
        module = read("ui", "observability.js")
        for field in (
            "telemetry-schema",
            "telemetry-run",
            "telemetry-revision",
            "telemetry-liveness",
        ):
            self.assertIn(field, module)
        self.assertIn("formatAge(state.lastSnapshotAt)", module)
        self.assertIn("window.setInterval(refreshOperationalStatus, 1000)", module)

    def test_data_availability_uses_explicit_non_inferential_states(self):
        module = read("ui", "observability.js")
        for state_name in (
            "Observed",
            "Not published",
            "Not yet developed",
            "Not in schema",
            "Not received",
            "Stale",
            "Rejected",
        ):
            self.assertIn(state_name, module)
        self.assertIn("Observatory never fills missing data by inference", module)

    def test_return_to_live_changes_browser_state_only(self):
        module = read("ui", "observability.js")
        start = module.index("function returnToLive()")
        end = module.index("\nfunction refreshOperationalStatus", start)
        body = module[start:end]
        self.assertIn('updateUiState({ mode: "live", playing: true })', body)
        self.assertIn("renderTimeline();", body)
        self.assertNotIn("fetch(", body)
        self.assertNotIn("XMLHttpRequest", body)
        self.assertNotIn("WebSocket", body)

    def test_ingestion_records_acceptance_and_rejection(self):
        app = read("app.js")
        stream = read("transport", "instance-stream.js")
        observability = read("ui", "observability.js")
        self.assertIn("recordAcceptedSnapshot();", app)
        self.assertIn("recordRejectedSnapshot();", app)
        self.assertIn("recordAcceptedSnapshot();", stream)
        self.assertIn("recordRejectedSnapshot", stream)
        self.assertIn("acceptedSnapshots", observability)
        self.assertIn("rejectedSnapshots", observability)

    def test_invalid_instance_snapshot_revokes_render_gate(self):
        stream = read("transport", "instance-stream.js")
        ingest = stream.index("const projection = ingestSnapshot(payload.snapshot);")
        rejection = stream.index("currentInstanceHasSnapshot = false;", ingest)
        render = stream.index("renderSnapshotCycle(projection.cognition);", ingest)
        self.assertLess(ingest, rejection)
        self.assertLess(rejection, render)
        self.assertIn("if (!projection)", stream[ingest:render])

    def test_switching_instance_clears_operational_projection_status(self):
        transition = read("state", "transition.js")
        self.assertIn("lastProjectionStatus: null", transition)
        self.assertIn("lastProjectionReason: null", transition)
        self.assertIn("operationalConnection: null", transition)


if __name__ == "__main__":
    unittest.main()
