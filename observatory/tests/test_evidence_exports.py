import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(*parts):
    return (ROOT / Path(*parts)).read_text(encoding="utf-8")


class EvidenceExportContractTests(unittest.TestCase):
    def test_export_actions_cover_snapshot_csv_manifest_and_bundle(self):
        module = read("ui", "exports.js")
        for label in ("Export snapshot", "Export research CSV", "Export projected manifest", "Export evidence bundle"):
            self.assertIn(label, module)
        app = read("app.js")
        self.assertIn("installExportActions();", app)

    def test_manifest_and_summary_reads_are_same_origin_get_only(self):
        module = read("ui", "exports.js")
        self.assertIn('method: "GET"', module)
        self.assertIn('credentials: "same-origin"', module)
        self.assertIn('/manifest', module)
        self.assertIn('/history-summary', module)
        self.assertNotIn('method: "POST"', module)
        self.assertNotIn('method: "PUT"', module)
        self.assertNotIn('method: "DELETE"', module)

    def test_evidence_bundle_declares_and_preserves_passive_boundary(self):
        module = read("ui", "exports.js")
        self.assertIn('scope: "bounded Observatory evidence only"', module)
        self.assertIn("It excludes checkpoint contents, raw host readings and control surfaces.", module)
        self.assertIn("history_summary: historySummary", module)
        self.assertIn("manifest", module)
        self.assertIn("topology", module)


if __name__ == "__main__":
    unittest.main()
