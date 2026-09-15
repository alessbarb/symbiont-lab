import json
from pathlib import Path
import tempfile
import unittest

from observatory.manifest import (
    CaptureManifest,
    create_capture_manifest,
    verify_capture_manifest,
    write_capture_manifest,
)
from observatory.registry import write_heartbeat, read_registry
from observatory.schema_validate import validate
from symbiont.core.runtime import OrganismRuntime


class ManifestTests(unittest.TestCase):
    def test_create_and_write_manifest_round_trips_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            instances_dir = base_dir / "instances"
            instances_dir.mkdir(parents=True)

            ckpt_path = base_dir / "organism.checkpoint.json"
            ckpt_path.write_text('{"tick": 42, "organism_id": "org_123"}', encoding="utf-8")

            topo_path = instances_dir / "inst1.topology.json"
            topo_path.write_text('{"schema_version": 1, "nodes": []}', encoding="utf-8")

            manifests_dir = base_dir / "manifests"
            manifest_path = manifests_dir / "inst1.manifest.json"

            manifest = create_capture_manifest(
                organism_id="org_123",
                instance_id="inst1",
                run_id="run_abc",
                last_sequence=105,
                tick=42,
                topology_revision=7,
                schema_version=3,
                kernel_version="0.53.0",
                checkpoint_path=ckpt_path,
                topology_path=topo_path,
                effective_config={"attention_budget": 5, "discover_senses": True},
            )

            written_path = write_capture_manifest(manifest_path, manifest)
            self.assertEqual(written_path, manifest_path)
            self.assertTrue(manifest_path.is_file())

            # Verify no temporary files left behind
            temp_files = list(instances_dir.glob(".*"))
            self.assertEqual(temp_files, [])

            # Verify manifest content
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(data["organism_id"], "org_123")
            self.assertEqual(data["instance_id"], "inst1")
            self.assertEqual(data["last_sequence"], 105)
            self.assertEqual(data["tick"], 42)
            self.assertEqual(data["topology_revision"], 7)
            self.assertIsNotNone(data["checkpoint_sha256"])
            self.assertIsNotNone(data["topology_sha256"])

            # Verify capture manifest verifies cleanly
            valid, errors = verify_capture_manifest(manifest_path, base_dir=instances_dir)
            self.assertTrue(valid, f"Verification failed with errors: {errors}")
            self.assertEqual(errors, [])

    def test_detects_eventual_or_in_flight_checkpoint_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            instances_dir = base_dir / "instances"
            instances_dir.mkdir(parents=True)

            ckpt_path = base_dir / "organism.checkpoint.json"
            ckpt_path.write_text('{"tick": 42, "organism_id": "org_123"}', encoding="utf-8")

            topo_path = instances_dir / "inst1.topology.json"
            topo_path.write_text('{"schema_version": 1, "nodes": []}', encoding="utf-8")

            manifests_dir = base_dir / "manifests"
            manifest_path = manifests_dir / "inst1.manifest.json"

            manifest = create_capture_manifest(
                organism_id="org_123",
                instance_id="inst1",
                run_id="run_abc",
                last_sequence=105,
                tick=42,
                topology_revision=7,
                schema_version=3,
                kernel_version="0.53.0",
                checkpoint_path=ckpt_path,
                topology_path=topo_path,
                effective_config={},
            )
            write_capture_manifest(manifest_path, manifest)

            # Mutate checkpoint (simulating uncoordinated subsequent write or in-flight copy)
            ckpt_path.write_text('{"tick": 43, "organism_id": "org_123", "mutated": true}', encoding="utf-8")

            valid, errors = verify_capture_manifest(manifest_path, base_dir=base_dir, topology_path=topo_path)
            self.assertFalse(valid)
            self.assertTrue(any("Checkpoint SHA256 mismatch" in err for err in errors))

    def test_detects_topology_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            instances_dir = base_dir / "instances"
            instances_dir.mkdir(parents=True)

            ckpt_path = base_dir / "organism.checkpoint.json"
            ckpt_path.write_text('{"tick": 42}', encoding="utf-8")

            topo_path = instances_dir / "inst1.topology.json"
            topo_path.write_text('{"schema_version": 1, "nodes": []}', encoding="utf-8")

            manifests_dir = base_dir / "manifests"
            manifest_path = manifests_dir / "inst1.manifest.json"

            manifest = create_capture_manifest(
                organism_id="org_123",
                instance_id="inst1",
                run_id="run_abc",
                last_sequence=105,
                tick=42,
                topology_revision=7,
                schema_version=3,
                kernel_version="0.53.0",
                checkpoint_path=ckpt_path,
                topology_path=topo_path,
                effective_config={},
            )
            write_capture_manifest(manifest_path, manifest)

            # Mutate topology
            topo_path.write_text('{"schema_version": 1, "nodes": [{"id": "n1"}]}', encoding="utf-8")

            valid, errors = verify_capture_manifest(
                manifest_path, base_dir=base_dir, checkpoint_path=ckpt_path, topology_path=topo_path
            )
            self.assertFalse(valid)
            self.assertTrue(any("Topology SHA256 mismatch" in err for err in errors))

    def test_write_heartbeat_with_organism_id_validates_against_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            observatory_dir = Path(directory)
            write_heartbeat(
                observatory_dir,
                instance_id="b" * 16,
                run_id="run-2",
                pid=456,
                display_id="worker-test",
                started_at="2026-09-15T12:00:00+00:00",
                topology_revision=5,
                organism_id="org_persistent_abc",
            )
            records = read_registry(observatory_dir)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["organism_id"], "org_persistent_abc")

            # Validate against instance.schema.json
            payload = json.loads((observatory_dir / "instances" / f"{'b' * 16}.json").read_text(encoding="utf-8"))
            schema = json.loads((Path(__file__).parent / "instance.schema.json").read_text(encoding="utf-8"))
            validate(payload, schema)

    def test_runtime_organism_id_and_effective_configuration_provenance(self):
        runtime = OrganismRuntime(organism_id="org_origin_42")
        self.assertEqual(runtime.organism_id, "org_origin_42")

        config = runtime.effective_configuration()
        self.assertEqual(config["organism_id"], "org_origin_42")
        self.assertIn("attention_budget", config)
        self.assertIn("discover_senses", config)

        # Round-trip through export and restore
        exported = runtime.checkpoint()
        self.assertEqual(exported["organism_id"], "org_origin_42")
        self.assertEqual(exported["effective_config"]["organism_id"], "org_origin_42")

        restored = OrganismRuntime.from_checkpoint(exported)
        self.assertEqual(restored.organism_id, "org_origin_42")
        self.assertEqual(restored.effective_configuration()["organism_id"], "org_origin_42")
