"""End-to-end runtime shadow-promotion gate (evaluator-only)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.cognition.genome import GenomeCodec
from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge
from symbiont.core.runtime import OrganismRuntime


_GENOME = {
    "schema_version": 1, "genome_id": "genome_runtime_promotion", "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.80",
    "development": {"initial_concepts": 1, "soft_node_budget": 16, "soft_edge_budget": 64, "consolidation_interval_ticks": 4},
    "plasticity": {"learning_rate": {"initial": 0.05, "min": 0.001, "max": 0.08}, "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005}, "eligibility_decay": 0.9},
    "structure": {"grow_threshold": 0.18, "prune_threshold": 0.01, "minimum_support": 16, "tentative_lifetime_ticks": 128},
    "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
}


@dataclass(frozen=True, slots=True)
class RuntimePredictionPromotionStudy:
    trials: int
    signal_samples: int
    signal_gain: float
    signal_promoted: bool
    noise_samples: int
    noise_gain: float
    noise_promoted: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _runtime(organism_id: str, source: str, target: str) -> OrganismRuntime:
    genome = GenomeCodec().load(_GENOME)
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id=source, kind=NodeKind.SENSE), PlasticNode(node_id=target, kind=NodeKind.CONCEPT)),
        edges=(PlasticEdge(source_id=source, target_id=target, kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0),),
        kernel_limits=KernelLimits(),
    )
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=KernelLimits(), develop_senses=True)
    return OrganismRuntime(organism_id=organism_id, genome=genome, cognitive_graph=graph,
                           cognitive_bridge=bridge, bootstrap_semantic_senses=False,
                           discover_senses=False)


def run_runtime_prediction_promotion_study(*, trials: int = 32) -> RuntimePredictionPromotionStudy:
    if trials < 8:
        raise ValueError("trials must be at least 8")
    signal = _runtime("signal-runtime", "s", "t")
    noise = _runtime("noise-runtime", "n", "m")
    for tick in range(1, trials + 1):
        source = float(tick % 2)
        # Target follows the source one step later; the noise target is constant.
        signal.cognitive_bridge.tick({"s": source, "t": float((tick + 1) % 2)}, tick=tick)
        noise.cognitive_bridge.tick({"n": source, "m": 0.0}, tick=tick)
    signal_candidate = next((p for p in signal.shadow_predictions if (p.source_id, p.target_id) == ("t", "s")), None)
    noise_candidate = next((p for p in noise.shadow_predictions if (p.source_id, p.target_id) == ("n", "m")), None)
    signal_promoted = signal.promote_shadow_prediction("t", "s")
    noise_promoted = noise.promote_shadow_prediction("n", "m")
    return RuntimePredictionPromotionStudy(
        trials, signal_candidate.samples if signal_candidate else 0,
        signal_candidate.predictive_gain if signal_candidate else 0.0, signal_promoted,
        noise_candidate.samples if noise_candidate else 0,
        noise_candidate.predictive_gain if noise_candidate else 0.0, noise_promoted,
    )


__all__ = ["RuntimePredictionPromotionStudy", "run_runtime_prediction_promotion_study"]
