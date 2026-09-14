import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as Obj

from observatory.adapter import envelope, project_tick, project_topology, write_replay

_GENOME_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_adapter00000000000000000",
    "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.60",
    "development": {
        "initial_concepts": 4,
        "soft_node_budget": 64,
        "soft_edge_budget": 384,
        "consolidation_interval_ticks": 4,
    },
    "plasticity": {
        "learning_rate": {"initial": 0.05, "min": 0.001, "max": 0.08},
        "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
        "eligibility_decay": 0.9,
    },
    "structure": {
        "grow_threshold": 0.18,
        "prune_threshold": 0.01,
        "minimum_support": 16,
        "tentative_lifetime_ticks": 128,
    },
    "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
}


def _minimal_genome_payload():
    return _GENOME_PAYLOAD


class AdapterTests(unittest.TestCase):
    def result(self):
        dissent = Obj(capability_id="compute.logical_cpu")
        narrative = Obj(capability_id="compute.logical_cpu", summary="Still learning this host.", uncertainty=3.0, evidence_gathered=2, dissent=dissent, contested=True)
        return Obj(tick=7, percepts=(Obj(name="system_load", quality=Obj(value="nominal")),), allocations=(Obj(name="compute.logical_cpu"),), investigated_capability="compute.logical_cpu", drift_observations={"system_load": Obj(kind=Obj(value="regime_shift"))}, dissent=dissent, narrative=(narrative,))

    def test_projects_only_bounded_abstract_state(self):
        acclimation = Obj(known_capabilities=("cpu", "disk"), acclimated_capabilities=("cpu",))
        snapshot = project_tick(self.result(), acclimation=acclimation, display_id="A-17", ticks_remaining=4)
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(snapshot["organism"]["state"], "reflecting")
        self.assertEqual(snapshot["organism"]["acclimation"], 0.5)
        self.assertEqual(snapshot["organism"]["resource_budget"], {"ticks_remaining": 4})
        self.assertNotIn("value", snapshot["organism"]["percepts"][0])
        self.assertTrue(all(len(event["id"]) <= 64 for event in snapshot["organism"]["events"]))
        self.assertTrue(all(len(item) <= 200 for item in snapshot["organism"]["memory"]))
        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value)) if value else set()
            return set()
        self.assertTrue({"hostname", "username", "timestamp", "source", "provider_id", "raw_value", "threat", "command"}.isdisjoint(keys(snapshot)))

    def test_envelope_matches_browser_contract(self):
        wrapped = envelope(project_tick(self.result()))
        self.assertEqual(wrapped["type"], "symbiont-observatory-snapshot")
        self.assertEqual(wrapped["snapshot"]["tick"], 7)

    def test_loss_class_buckets_huber_loss_magnitudes(self):
        from observatory.adapter import loss_class
        from symbiont.cognition.learning import huber_loss

        self.assertEqual(loss_class(huber_loss(0.0)), "zero")
        self.assertEqual(loss_class(huber_loss(0.02)), "trace")
        self.assertEqual(loss_class(huber_loss(0.2)), "low")
        self.assertEqual(loss_class(huber_loss(0.6)), "medium")
        self.assertEqual(loss_class(huber_loss(1.5)), "high")
        self.assertEqual(loss_class(huber_loss(5.0)), "extreme")
        order = ["zero", "trace", "low", "medium", "high", "extreme"]
        errors = [0.0, 0.02, 0.2, 0.6, 1.5, 5.0]
        classes = [loss_class(huber_loss(error)) for error in errors]
        self.assertEqual([order.index(item) for item in classes], sorted(order.index(item) for item in classes))

    def test_project_tick_without_genome_keeps_v1_shape(self):
        snapshot = project_tick(self.result())
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertNotIn("cognition", snapshot["organism"])

    def test_project_tick_with_cognition_emits_v2_cognition_state(self):
        from symbiont.cognition.genome import GenomeCodec
        from symbiont.cognition.learning import PredictionError
        from symbiont.cognition.structure import Mutation
        from symbiont.core.cognition_bridge import CognitiveBridgeResult

        genome = GenomeCodec().load(_minimal_genome_payload())
        cognition = CognitiveBridgeResult(
            tick=7,
            activations={"concept_a": 0.4},
            readouts={"readout_pressure": 0.4},
            prediction_errors=(PredictionError(predictor_id="predictor_a", target_id="concept_a", error=0.02, loss=0.0002),),
            structural_mutations_applied=1,
            frozen=False,
            topology_revision=1,
            mutations=(Mutation(kind="add_edge", payload={"source_id": "sense_a", "target_id": "concept_a", "kind": "excitatory"}),),
        )
        result = self.result()
        result.cognition = cognition
        snapshot = project_tick(result, genome=genome)
        self.assertEqual(snapshot["schema_version"], 2)
        cognition_block = snapshot["organism"]["cognition"]
        self.assertEqual(cognition_block["topology_revision"], 1)
        self.assertEqual(cognition_block["readouts"]["readout_pressure"], 0.4)
        self.assertEqual(cognition_block["prediction_errors"]["predictor_a"], "trace")
        self.assertEqual(cognition_block["mutations"], [{"kind": "add_edge", "edge_id": "sense_a->concept_a"}])
        self.assertEqual(cognition_block["safety_state"], {"consecutive_failures": 0, "frozen": False})

    def test_project_topology_is_structural_only(self):
        from symbiont.cognition.genome import GenomeCodec
        from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
        from symbiont.cognition.limits import KernelLimits
        from symbiont.cognition.types import EdgeKind, NodeKind

        genome = GenomeCodec().load(_minimal_genome_payload())
        limits = KernelLimits()
        nodes = (PlasticNode(node_id="sense_a", kind=NodeKind.SENSE), PlasticNode(node_id="concept_a", kind=NodeKind.CONCEPT))
        edges = (PlasticEdge(source_id="sense_a", target_id="concept_a", kind=EdgeKind.EXCITATORY, weight=1.7, plasticity=0.5, delay_ticks=0),)
        graph = CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=limits)

        topology = project_topology(graph, genome=genome, kernel_version="0.59.3")
        self.assertEqual(topology["genome_id"], genome.genome_id)
        self.assertEqual(topology["kernel_version"], "0.59.3")
        self.assertNotIn("weight", topology["edges"][0])
        self.assertEqual(topology["edges"][0], {"source_id": "sense_a", "target_id": "concept_a", "kind": "excitatory"})

    def test_replay_is_atomic_and_bounded(self):
        snapshot = project_tick(self.result())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.json"
            write_replay(path, [snapshot])
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["snapshots"][0]["tick"], 7)
            with self.assertRaises(ValueError):
                write_replay(path, [])


if __name__ == "__main__":
    unittest.main()
