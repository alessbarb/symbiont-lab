import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class SnapshotNormalizerContractTests(unittest.TestCase):
    def test_normalizer_only_fills_absent_legacy_fields(self):
        source = (ROOT / "projection" / "snapshot.js").read_text(encoding="utf-8")
        self.assertIn("cognition: organism.cognition ?? null", source)
        self.assertIn("body_schema: organism.body_schema ?? null", source)
        self.assertNotIn("cognition: null, body_schema: null", source)

    def test_bounded_snapshot_still_rejects_forbidden_version_fields(self):
        source = (ROOT / "projection" / "snapshot.js").read_text(encoding="utf-8")
        self.assertIn('snapshot.schema_version === 1 && (organism.cognition != null || organism.body_schema != null)', source)
        self.assertIn('snapshot.schema_version === 2 && (!cognition || organism.body_schema != null)', source)
        self.assertIn('snapshot.schema_version === 3 && (!bodySchema || (organism.cognition != null && !cognition))', source)

    def test_bounded_social_relations_preserves_rejections(self):
        source = (ROOT / "projection" / "snapshot.js").read_text(encoding="utf-8")
        self.assertIn(
            "rejections: Math.max(0, Number.parseInt(item.rejections, 10) || 0)",
            source,
        )

    def test_bounded_snapshot_preserves_social_resource_evidence(self):
        source = (ROOT / "projection" / "snapshot.js").read_text(encoding="utf-8")
        self.assertIn("boundedSocialResourceEvidence", source)
        self.assertIn("socialResourceEvidence: boundedSocialResourceEvidence", source)


if __name__ == "__main__":
    unittest.main()
