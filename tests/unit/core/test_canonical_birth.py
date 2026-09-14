from __future__ import annotations

from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind
from symbiont.core.canonical_birth import restore_resident_with_canonical_cognition
from symbiont.core.runtime import OrganismRuntime


def test_legacy_checkpoint_adopts_canonical_cognition_without_resetting_tick():
    legacy = OrganismRuntime(bootstrap_semantic_senses=False).checkpoint()
    legacy["saved_at_tick"] = 37
    assert legacy["genome"] is None
    assert legacy["cognitive_bridge"] is None

    restored = restore_resident_with_canonical_cognition(
        legacy,
        bootstrap_semantic_senses=False,
    )

    assert restored.tick_count == 37
    assert restored.genome is not None
    assert restored.genome.genome_id == "genome_symbiont_base_v1"
    assert restored.cognitive_bridge is not None
    assert restored.cognitive_bridge.graph.nodes == ()
    assert restored.cognitive_bridge.graph.edges == ()

    adopted_checkpoint = restored.checkpoint()
    assert adopted_checkpoint["genome"] is not None
    assert adopted_checkpoint["cognitive_bridge"] is not None


def test_existing_cognitive_checkpoint_is_never_replaced_by_adoption_helper():
    limits = KernelLimits()
    genome = load_base_genome(kernel_limits=limits, running_version=(0, 59, 4))
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id="owner_sense", kind=NodeKind.SENSE),),
        edges=(),
        kernel_limits=limits,
    )
    original = OrganismRuntime(
        bootstrap_semantic_senses=False,
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
    )

    restored = restore_resident_with_canonical_cognition(
        original.checkpoint(),
        bootstrap_semantic_senses=False,
    )

    assert restored.genome is not None
    assert restored.genome.genome_hash == genome.genome_hash
    assert restored.cognitive_bridge is not None
    assert {node.node_id for node in restored.cognitive_bridge.graph.nodes} == {"owner_sense"}


def test_generic_runtime_restore_remains_exact_for_historical_reproduction():
    legacy = OrganismRuntime(bootstrap_semantic_senses=False).checkpoint()

    restored = OrganismRuntime.from_checkpoint(
        legacy,
        bootstrap_semantic_senses=False,
    )

    assert restored.genome is None
    assert restored.cognitive_bridge is None
