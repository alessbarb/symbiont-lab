import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read_js_bundle() -> str:
    """All Observatory frontend JS modules concatenated, for contract
    assertions whose intent ("this string must appear/never appear in the
    frontend") is unaffected by exactly which module a line lives in after
    the module split (state/projection/transport/render/ui)."""
    parts = [(ROOT / "app.js").read_text(encoding="utf-8")]
    for sub in ("state", "projection", "transport", "render", "ui"):
        directory = ROOT / sub
        if directory.is_dir():
            for path in sorted(directory.glob("*.js")):
                if path.name == "exports.js":
                    continue
                parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


class ObservatoryContractTests(unittest.TestCase):
    def test_snapshot_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["enum"], [1, 2, 3])
        organism = schema["properties"]["organism"]
        self.assertFalse(organism["additionalProperties"])
        self.assertEqual(organism["properties"]["percepts"]["maxItems"], 32)
        self.assertEqual(organism["properties"]["beliefs"]["maxItems"], 128)
        events = organism["properties"]["events"]
        self.assertEqual(events["maxItems"], 64)
        self.assertFalse(events["items"]["additionalProperties"])
        self.assertEqual(events["items"]["properties"]["causal_chain"]["maxItems"], 8)
        self.assertEqual(organism["properties"]["memory"]["maxItems"], 32)
        self.assertEqual(organism["properties"]["open_questions"]["maxItems"], 16)
        self.assertEqual(organism["properties"]["investigations"]["maxItems"], 16)
        self.assertEqual(organism["properties"]["regime_changes"]["maxItems"], 16)
        self.assertFalse(organism["properties"]["resource_budget"]["additionalProperties"])
        self.assertEqual(
            schema["properties"]["population"]["properties"]["members"]["maxItems"], 500
        )
        relationships = schema["properties"]["population"]["properties"]["relationships"]
        self.assertEqual(relationships["maxItems"], 1000)
        self.assertFalse(relationships["items"]["additionalProperties"])
        self.assertEqual(relationships["items"]["properties"]["strength"]["maximum"], 1)

    def test_snapshot_schema_version_gates_cognition_and_body_schema_independently(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["enum"], [1, 2, 3])
        organism = schema["properties"]["organism"]
        self.assertIn("cognition", organism["properties"])
        self.assertIn("body_schema", organism["properties"])
        self.assertEqual(organism["properties"]["body_schema"]["$ref"], "./body_schema.schema.json")
        self.assertEqual(len(schema["allOf"]), 3)
        serialized = json.dumps(schema["allOf"])
        self.assertIn('"const": 1', serialized)
        self.assertIn('"const": 2', serialized)
        self.assertIn('"const": 3', serialized)
        v3_rule = next(
            rule
            for rule in schema["allOf"]
            if rule["if"]["properties"]["schema_version"].get("const") == 3
        )
        self.assertEqual(v3_rule["then"]["properties"]["organism"]["required"], ["body_schema"])

    def test_body_schema_contract_is_closed_bounded_and_versioned(self) -> None:
        schema = json.loads((ROOT / "body_schema.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["enum"], [1, 2])
        self.assertEqual(
            schema["properties"]["state"]["enum"],
            ["undeveloped", "partial", "developing", "established", "revising"],
        )
        self.assertEqual(schema["properties"]["parts"]["maxItems"], 288)
        part = schema["properties"]["parts"]["items"]
        self.assertFalse(part["additionalProperties"])
        self.assertEqual(part["properties"]["kind"]["enum"], ["sense", "cognitive_region"])
        dependencies = schema["properties"]["dependencies"]
        self.assertEqual(dependencies["maxItems"], 256)
        self.assertFalse(dependencies["items"]["additionalProperties"])
        self.assertEqual(
            dependencies["items"]["properties"]["relation"]["enum"], ["co_acts_with", "precedes"]
        )
        self.assertFalse(schema["properties"]["global_state"]["additionalProperties"])
        self.assertEqual(schema["properties"]["global_state"]["maxProperties"], 0)
        serialized = json.dumps(schema)
        self.assertIn('"const": 1', serialized)
        self.assertIn('"maxItems": 256', serialized)
        self.assertIn("part\\\\.sense", serialized)
        self.assertIn("part\\\\.region", serialized)
        for forbidden in ("id_salt", "cognitive_learning", "channel.cognition"):
            self.assertNotIn(forbidden, serialized)

    def test_cognition_state_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "cognition_state.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["prediction_errors"]["additionalProperties"]["enum"],
            ["zero", "trace", "low", "medium", "high", "extreme"],
        )
        self.assertEqual(schema["properties"]["mutations"]["maxItems"], 8)
        self.assertFalse(schema["properties"]["safety_state"]["additionalProperties"])

    def test_topology_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "topology.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["nodes"]["maxItems"], 128)
        self.assertEqual(schema["properties"]["edges"]["maxItems"], 1024)
        self.assertFalse(schema["properties"]["nodes"]["items"]["additionalProperties"])
        self.assertFalse(schema["properties"]["edges"]["items"]["additionalProperties"])
        self.assertNotIn("weight", schema["properties"]["edges"]["items"]["properties"])

    def test_instance_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "instance.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        for field in (
            "instance_id",
            "run_id",
            "display_id",
            "started_at",
            "last_heartbeat",
            "topology_revision",
        ):
            self.assertIn(field, schema["required"])
        self.assertEqual(schema["properties"]["instance_id"]["pattern"], "^[0-9a-f]{16}$")

    def test_replay_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "replay.schema.json").read_text(encoding="utf-8"))
        snapshots = schema["properties"]["snapshots"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(snapshots["minItems"], 1)
        self.assertEqual(snapshots["maxItems"], 10000)
        self.assertEqual(snapshots["items"]["$ref"], "./snapshot.schema.json")

    def test_resident_prioritizes_active_and_probing_states(self) -> None:
        resident = (ROOT.parent / "cli" / "observed_resident.py").read_text(encoding="utf-8")
        self.assertIn("active_states + probing_states + dormant_states", resident)

    def test_resident_publishes_only_observer_safe_body_schema(self) -> None:
        resident = (ROOT.parent / "cli" / "observed_resident.py").read_text(encoding="utf-8")
        self.assertIn("runtime.body_schema.export_representation", resident)
        self.assertNotIn("runtime.body_schema.export(current_tick", resident)


class ObserverProvenanceContractTests(unittest.TestCase):
    def test_observer_provenance_is_top_level_only(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))
        self.assertIn("observer", schema["properties"])
        organism = schema["properties"]["organism"]
        self.assertNotIn("observer", organism["properties"])


class SensoryWorldMapContractTests(unittest.TestCase):
    def test_sensory_snapshot_extension_is_optional_for_replay_compatibility(self) -> None:
        schema = json.loads((ROOT / "schemas" / "snapshot.schema.json").read_text(encoding="utf-8"))
        sensory = schema["properties"]["organism"]["properties"]["sensory_phenotype"]
        modality = sensory["properties"]["modalities"]["items"]
        sensor = sensory["properties"]["sensors"]["items"]

        self.assertIn("allowed_transductions", modality["properties"])
        self.assertNotIn("allowed_transductions", modality["required"])
        self.assertIn("sample_geometry", sensor["properties"])
        self.assertIn("transduction", sensor["properties"])
        self.assertNotIn("sample_geometry", sensor["required"])
        self.assertNotIn("transduction", sensor["required"])


if __name__ == "__main__":
    unittest.main()
