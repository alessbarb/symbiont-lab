"""End-to-end runtime shadow-promotion gate (evaluator-only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.cognition_bridge import CognitiveBridge
from symbiont.core.runtime import OrganismRuntime

from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.genetics.migration import GenomeMigrationCodec as GenomeCodec

_GENOME = {
    "schema_version": 1,
    "genome_id": "genome_runtime_promotion",
    "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.81",
    "development": {
        "initial_concepts": 1,
        "soft_node_budget": 16,
        "soft_edge_budget": 64,
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


@dataclass(frozen=True, slots=True)
class RuntimePredictionPromotionStudy:
    trials: int
    signal_samples: int
    signal_gain: float
    signal_promoted: bool
    noise_samples: int
    noise_gain: float
    noise_promoted: bool
    checkpoint_replay_equal: bool = False
    restored_signal_promoted: bool = False
    signal_status: str = "candidate"
    noise_status: str = "candidate"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _runtime(
    organism_id: str,
    source: str,
    target: str,
    *,
    edge_weight: float = 0.5,
) -> OrganismRuntime:
    genome = GenomeCodec().load(_GENOME)
    graph = CognitiveGraph(
        nodes=(
            PlasticNode(node_id=source, kind=NodeKind.SENSE),
            PlasticNode(node_id=target, kind=NodeKind.CONCEPT),
        ),
        # The study evaluates a one-step-ahead hypothesis.  The apparatus
        # graph must therefore use the same lag that ShadowPrediction scores;
        # a zero-delay edge would make the target depend on the current source
        # while the evaluator compares it with the previous source frame.
        edges=(
            PlasticEdge(
                source_id=source,
                target_id=target,
                kind=EdgeKind.EXCITATORY,
                weight=edge_weight,
                plasticity=0.5,
                delay_ticks=1,
            ),
        ),
        kernel_limits=KernelLimits(),
    )
    bridge = CognitiveBridge(
        graph=graph, genome=genome, kernel_limits=KernelLimits(), develop_senses=True
    )
    return OrganismRuntime(
        organism_id=organism_id,
        genome=genome,
        cognitive_graph=graph,
        cognitive_bridge=bridge,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )


def run_runtime_prediction_promotion_study(*, trials: int = 32) -> RuntimePredictionPromotionStudy:
    if trials < 8:
        raise ValueError("trials must be at least 8")
    signal = _runtime("signal-runtime", "s", "t")
    noise = _runtime("noise-runtime", "n", "m", edge_weight=0.0)
    noise_status = "candidate"
    noise_gain = 0.0
    noise_retired = False
    for tick in range(1, trials + 1):
        source = float(tick % 2)
        # Target follows the source one step later; the noise target is constant.
        signal.cognitive_bridge.tick({"s": source, "t": float((tick + 1) % 2)}, tick=tick)
        noise.cognitive_bridge.tick({"n": source, "m": 0.0}, tick=tick)
        observed_noise = next(
            (p for p in noise.shadow_predictions if (p.source_id, p.target_id) == ("n", "m")),
            None,
        )
        if observed_noise is not None and not noise_retired:
            noise_status = observed_noise.status
            noise_gain = observed_noise.predictive_gain
        elif observed_noise is None and noise_status == "contradicted":
            # The bridge removes a retired candidate during the same tick in
            # which it crosses the retirement threshold.
            noise_status = "retired"
            noise_retired = True
    signal_candidate = next(
        (p for p in signal.shadow_predictions if (p.source_id, p.target_id) == ("s", "t")), None
    )
    noise_candidate = next(
        (p for p in noise.shadow_predictions if (p.source_id, p.target_id) == ("n", "m")), None
    )
    restored = OrganismRuntime.from_checkpoint(
        signal.checkpoint(), bootstrap_semantic_senses=False, discover_senses=False
    )
    restored_candidate = next(
        (p for p in restored.shadow_predictions if (p.source_id, p.target_id) == ("s", "t")), None
    )
    checkpoint_replay_equal = (
        restored_candidate is not None
        and signal_candidate is not None
        and restored_candidate.samples == signal_candidate.samples
        and restored_candidate.predictive_gain == signal_candidate.predictive_gain
    )
    signal_promoted = signal.promote_shadow_prediction("s", "t")
    noise_promoted = noise.promote_shadow_prediction("n", "m")
    restored_signal_promoted = restored.promote_shadow_prediction("s", "t")
    return RuntimePredictionPromotionStudy(
        trials,
        signal_candidate.samples if signal_candidate else 0,
        signal_candidate.predictive_gain if signal_candidate else 0.0,
        signal_promoted,
        # Contradicted shadows are intentionally retired and pruned from the
        # live bridge. The study still reports the complete evidence window,
        # while retaining the final lifecycle status and gain observed before
        # pruning.
        trials - 1 if noise_candidate is not None else 0,
        noise_gain,
        noise_promoted,
        checkpoint_replay_equal,
        restored_signal_promoted,
        signal_candidate.status if signal_candidate else "candidate",
        noise_status,
    )


__all__ = ["RuntimePredictionPromotionStudy", "run_runtime_prediction_promotion_study"]
