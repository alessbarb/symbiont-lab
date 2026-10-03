from __future__ import annotations

from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind
from symbiont.core.orchestration.canonical_birth import restore_resident_with_canonical_cognition
from symbiont.core.orchestration.runtime import OrganismRuntime


def test_existing_cognitive_checkpoint_is_never_replaced_by_adoption_helper():
    limits = KernelLimits()
    genome = load_base_genome(kernel_limits=limits, running_version=(0, 85, 0))
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


def test_an_organism_born_under_the_current_schema_records_no_legacy_origin():
    born = OrganismRuntime(bootstrap_semantic_senses=False)
    restarted = OrganismRuntime.from_checkpoint(born.checkpoint(), bootstrap_semantic_senses=False)

    lineage = restarted.checkpoint()["checkpoint_lineage"]
    assert "unverified_legacy_origin" not in lineage
    assert "transforms" not in lineage
