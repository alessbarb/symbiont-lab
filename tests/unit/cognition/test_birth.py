from __future__ import annotations

from symbiont.cognition.birth import load_base_cognition, load_base_genome, load_base_graph
from symbiont.cognition.limits import KernelLimits


def test_base_genome_is_semantics_free_and_within_kernel_limits():
    limits = KernelLimits()
    genome = load_base_genome(kernel_limits=limits, running_version=(0, 59, 4))

    assert genome.genome_id == "genome_symbiont_base_v1"
    assert genome.parent_ids == ()
    assert genome.development.initial_concepts == 0
    assert genome.development.soft_node_budget == 64
    assert genome.development.soft_edge_budget == 384
    assert genome.development.consolidation_interval_ticks == 32
    assert genome.structure.minimum_support == 16
    assert genome.structure.grow_threshold == 0.18
    assert genome.structure.prune_threshold == 0.01
    assert genome.structure.tentative_lifetime_ticks == 128
    assert genome.development.soft_node_budget <= limits.max_nodes
    assert genome.development.soft_edge_budget <= limits.max_edges


def test_base_graph_is_a_true_tabula_rasa():
    graph = load_base_graph(kernel_limits=KernelLimits())

    assert graph.nodes == ()
    assert graph.edges == ()


def test_base_cognition_pairs_the_same_genome_and_germinal_graph():
    genome, graph = load_base_cognition(
        kernel_limits=KernelLimits(),
        running_version=(0, 59, 4),
    )

    assert genome.genome_id == "genome_symbiont_base_v1"
    assert graph.nodes == ()
    assert graph.edges == ()
