from __future__ import annotations

import copy
import random
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from symbiont.core.cognition_bridge import CognitiveBridge

from symbiont.cognition.graph import CognitiveGraph, KernelLimits, PlasticEdge, PlasticNode
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.genetics.migration import GenomeMigrationCodec as GenomeCodec

_BASE_GENOME_PAYLOAD = {
    "schema_version": 1,
    "genome_id": "genome_continuity_study0000000",
    "parent_ids": [],
    "kernel_compatibility": ">=0.55,<0.60",
    "development": {
        "initial_concepts": 2,
        "soft_node_budget": 64,
        "soft_edge_budget": 128,
        "consolidation_interval_ticks": 16,
    },
    "plasticity": {
        "learning_rate": {"initial": 0.05, "min": 0.001, "max": 0.08},
        "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
        "eligibility_decay": 0.9,
    },
    "structure": {
        "grow_threshold": 0.10,
        "prune_threshold": 0.01,
        "minimum_support": 2,
        "tentative_lifetime_ticks": 10,
    },
    "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
}


@dataclass(slots=True, frozen=True)
class Level1Outcome:
    condition_b_max_diff: float
    condition_c_max_diff: float
    condition_c_converged: bool
    condition_c_ticks_to_converge: int | None
    condition_c_late_mean_diff: float
    condition_d_max_diff: float
    condition_d_converged: bool
    condition_d_ticks_to_converge: int | None
    condition_d_late_mean_diff: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class Level2Outcome:
    condition_b_weight_diff: float
    condition_b_eligibility_diff: float
    condition_c_weight_diff: float
    condition_c_eligibility_diff: float
    condition_d_weight_diff: float
    condition_d_eligibility_diff: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class Level3Outcome:
    condition_b_divergence_tick: int | None
    condition_c_divergence_tick: int | None
    condition_d_divergence_tick: int | None
    condition_a_final_revision: int
    condition_b_final_revision: int
    condition_c_final_revision: int
    condition_d_final_revision: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class RestorationContinuityOutcome:
    seed: int
    level1: Level1Outcome
    level2: Level2Outcome
    level3: Level3Outcome

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "level1": self.level1.as_dict(),
            "level2": self.level2.as_dict(),
            "level3": self.level3.as_dict(),
        }


@dataclass(slots=True, frozen=True)
class RestorationContinuityStudyResult:
    seeds: tuple[int, ...]
    outcomes: tuple[RestorationContinuityOutcome, ...]
    level1_d_mean_ticks_to_converge: float
    level1_c_converged_fraction: float
    level1_c_mean_late_error: float
    level2_c_mean_weight_drift: float
    level2_d_mean_weight_drift: float
    level3_c_immediate_divergence_rate: float
    level3_b_parity_rate: float

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "outcomes": [o.as_dict() for o in self.outcomes],
            "level1_d_mean_ticks_to_converge": self.level1_d_mean_ticks_to_converge,
            "level1_c_converged_fraction": self.level1_c_converged_fraction,
            "level1_c_mean_late_error": self.level1_c_mean_late_error,
            "level2_c_mean_weight_drift": self.level2_c_mean_weight_drift,
            "level2_d_mean_weight_drift": self.level2_d_mean_weight_drift,
            "level3_c_immediate_divergence_rate": self.level3_c_immediate_divergence_rate,
            "level3_b_parity_rate": self.level3_b_parity_rate,
        }


def _build_fixed_bridge(
    genome_payload: dict[str, object],
) -> tuple[CognitiveBridge, CognitiveGraph, KernelLimits]:
    genome = GenomeCodec().load(genome_payload)
    limits = KernelLimits(max_nodes=64, max_edges=128)
    s1 = PlasticNode(node_id="s1", kind=NodeKind.SENSE)
    s2 = PlasticNode(node_id="s2", kind=NodeKind.SENSE)
    c1 = PlasticNode(node_id="c1", kind=NodeKind.CONCEPT, bias=0.0, tau=1.0)
    r1 = PlasticNode(node_id="r1", kind=NodeKind.READOUT, bias=0.0, tau=1.0)

    e1 = PlasticEdge(
        source_id="s1",
        target_id="c1",
        kind=EdgeKind.EXCITATORY,
        weight=0.35,
        plasticity=0.5,
        delay_ticks=0,
    )
    e2 = PlasticEdge(
        source_id="s2",
        target_id="c1",
        kind=EdgeKind.EXCITATORY,
        weight=-0.45,
        plasticity=0.5,
        delay_ticks=0,
    )
    e3 = PlasticEdge(
        source_id="c1",
        target_id="r1",
        kind=EdgeKind.EXCITATORY,
        weight=0.6,
        plasticity=0.5,
        delay_ticks=1,
    )
    e4 = PlasticEdge(
        source_id="c1",
        target_id="c1",
        kind=EdgeKind.EXCITATORY,
        weight=0.4,
        plasticity=0.5,
        delay_ticks=1,
    )

    graph = CognitiveGraph(nodes=(s1, s2, c1, r1), edges=(e1, e2, e3, e4), kernel_limits=limits)
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits, develop_senses=False)
    return bridge, graph, limits


def _evaluate_level_1(
    *,
    seed: int,
    warmup_ticks: int = 50,
    eval_ticks: int = 50,
    convergence_tol: float = 1e-4,
) -> Level1Outcome:
    rng = random.Random(seed)
    bridge_a, _, limits = _build_fixed_bridge(_BASE_GENOME_PAYLOAD)
    genome = bridge_a._genome

    inputs_seq: list[dict[str, float]] = []
    total_ticks = warmup_ticks + eval_ticks
    for _ in range(total_ticks):
        inputs_seq.append({"s1": rng.uniform(-1.0, 1.0), "s2": rng.uniform(-1.0, 1.0)})

    for tick in range(1, warmup_ticks + 1):
        bridge_a.tick(inputs_seq[tick - 1], tick=tick)

    # Condition B: Deepcopy
    bridge_b = copy.deepcopy(bridge_a)

    # Condition C: Real Checkpoint (quantized weights, cold dynamic start)
    ckpt_c = bridge_a.export_checkpoint()
    bridge_c = CognitiveBridge.restore(ckpt_c, genome=genome, kernel_limits=limits)
    if bridge_c is None:
        raise RuntimeError("Failed to restore bridge_c from checkpoint")

    # Condition D: Extended Checkpoint (exact weights, cold dynamic start)
    bridge_d = copy.deepcopy(bridge_a)
    bridge_d._previous_frame = {}
    for edge in bridge_d._graph.edges:
        edge.eligibility = 0.0

    # Freeze plasticity across all conditions
    bridge_a._safety_state.frozen = True
    bridge_b._safety_state.frozen = True
    bridge_c._safety_state.frozen = True
    bridge_d._safety_state.frozen = True

    diffs_b: list[float] = []
    diffs_c: list[float] = []
    diffs_d: list[float] = []

    for tick in range(warmup_ticks + 1, total_ticks + 1):
        res_a = bridge_a.tick(inputs_seq[tick - 1], tick=tick)
        res_b = bridge_b.tick(inputs_seq[tick - 1], tick=tick)
        res_c = bridge_c.tick(inputs_seq[tick - 1], tick=tick)
        res_d = bridge_d.tick(inputs_seq[tick - 1], tick=tick)

        y_a = res_a.activations["r1"]
        diffs_b.append(abs(res_b.activations["r1"] - y_a))
        diffs_c.append(abs(res_c.activations["r1"] - y_a))
        diffs_d.append(abs(res_d.activations["r1"] - y_a))

    def _convergence_info(diffs: Sequence[float]) -> tuple[bool, int | None]:
        for i in range(len(diffs)):
            if all(d < convergence_tol for d in diffs[i:]):
                return True, i + 1
        return False, None

    c_conv, c_ticks = _convergence_info(diffs_c)
    d_conv, d_ticks = _convergence_info(diffs_d)

    late_window = min(20, len(diffs_c))
    c_late_mean = sum(diffs_c[-late_window:]) / late_window
    d_late_mean = sum(diffs_d[-late_window:]) / late_window

    return Level1Outcome(
        condition_b_max_diff=max(diffs_b) if diffs_b else 0.0,
        condition_c_max_diff=max(diffs_c) if diffs_c else 0.0,
        condition_c_converged=c_conv,
        condition_c_ticks_to_converge=c_ticks,
        condition_c_late_mean_diff=c_late_mean,
        condition_d_max_diff=max(diffs_d) if diffs_d else 0.0,
        condition_d_converged=d_conv,
        condition_d_ticks_to_converge=d_ticks,
        condition_d_late_mean_diff=d_late_mean,
    )


def _evaluate_level_2(
    *,
    seed: int,
    warmup_ticks: int = 50,
    eval_ticks: int = 50,
) -> Level2Outcome:
    rng = random.Random(seed)
    bridge_a, _, limits = _build_fixed_bridge(_BASE_GENOME_PAYLOAD)
    genome = bridge_a._genome

    inputs_seq: list[dict[str, float]] = []
    total_ticks = warmup_ticks + eval_ticks
    for _ in range(total_ticks):
        inputs_seq.append({"s1": rng.uniform(-1.0, 1.0), "s2": rng.uniform(-1.0, 1.0)})

    for tick in range(1, warmup_ticks + 1):
        bridge_a.tick(inputs_seq[tick - 1], tick=tick)

    bridge_b = copy.deepcopy(bridge_a)

    ckpt_c = bridge_a.export_checkpoint()
    bridge_c = CognitiveBridge.restore(ckpt_c, genome=genome, kernel_limits=limits)
    if bridge_c is None:
        raise RuntimeError("Failed to restore bridge_c from checkpoint")

    bridge_d = copy.deepcopy(bridge_a)
    bridge_d._previous_frame = {}
    for edge in bridge_d._graph.edges:
        edge.eligibility = 0.0

    for tick in range(warmup_ticks + 1, total_ticks + 1):
        bridge_a.tick(inputs_seq[tick - 1], tick=tick)
        bridge_b.tick(inputs_seq[tick - 1], tick=tick)
        bridge_c.tick(inputs_seq[tick - 1], tick=tick)
        bridge_d.tick(inputs_seq[tick - 1], tick=tick)

    def _diff_metrics(br_test: CognitiveBridge, br_ref: CognitiveBridge) -> tuple[float, float]:
        edges_test = sorted(
            br_test._graph.edges, key=lambda e: (e.source_id, e.target_id, e.kind.value)
        )
        edges_ref = sorted(
            br_ref._graph.edges, key=lambda e: (e.source_id, e.target_id, e.kind.value)
        )
        w_diff = sum(abs(e1.weight - e2.weight) for e1, e2 in zip(edges_test, edges_ref)) / len(
            edges_test
        )
        q_diff = sum(
            abs(e1.eligibility - e2.eligibility) for e1, e2 in zip(edges_test, edges_ref)
        ) / len(edges_test)
        return w_diff, q_diff

    bw, bq = _diff_metrics(bridge_b, bridge_a)
    cw, cq = _diff_metrics(bridge_c, bridge_a)
    dw, dq = _diff_metrics(bridge_d, bridge_a)

    return Level2Outcome(
        condition_b_weight_diff=bw,
        condition_b_eligibility_diff=bq,
        condition_c_weight_diff=cw,
        condition_c_eligibility_diff=cq,
        condition_d_weight_diff=dw,
        condition_d_eligibility_diff=dq,
    )


def _evaluate_level_3(
    *,
    seed: int,
    warmup_ticks: int = 40,
    eval_ticks: int = 60,
) -> Level3Outcome:
    rng = random.Random(seed)
    genome = GenomeCodec().load(_BASE_GENOME_PAYLOAD)
    limits = KernelLimits(max_nodes=64, max_edges=128)

    s1 = PlasticNode(node_id="s1", kind=NodeKind.SENSE)
    s2 = PlasticNode(node_id="s2", kind=NodeKind.SENSE)
    s3 = PlasticNode(node_id="s3", kind=NodeKind.SENSE)
    s4 = PlasticNode(node_id="s4", kind=NodeKind.SENSE)
    graph = CognitiveGraph(nodes=(s1, s2, s3, s4), edges=(), kernel_limits=limits)
    bridge_a = CognitiveBridge(
        graph=graph, genome=genome, kernel_limits=limits, develop_senses=True
    )

    total_ticks = warmup_ticks + eval_ticks
    inputs_seq: list[dict[str, float]] = []
    for _ in range(total_ticks):
        base = rng.uniform(-1.0, 1.0)
        inputs_seq.append(
            {
                "s1": max(-1.0, min(1.0, base + rng.gauss(0, 0.05))),
                "s2": max(-1.0, min(1.0, base + rng.gauss(0, 0.05))),
                "s3": max(-1.0, min(1.0, -base + rng.gauss(0, 0.05))),
                "s4": rng.uniform(-1.0, 1.0),
            }
        )

    for tick in range(1, warmup_ticks + 1):
        bridge_a.tick(inputs_seq[tick - 1], tick=tick)

    bridge_b = copy.deepcopy(bridge_a)

    ckpt_c = bridge_a.export_checkpoint()
    bridge_c = CognitiveBridge.restore(ckpt_c, genome=genome, kernel_limits=limits)
    if bridge_c is None:
        raise RuntimeError("Failed to restore bridge_c from checkpoint")

    bridge_d = copy.deepcopy(bridge_a)
    bridge_d._previous_frame = {}
    for edge in bridge_d._graph.edges:
        edge.eligibility = 0.0

    div_b: int | None = None
    div_c: int | None = None
    div_d: int | None = None

    for tick in range(warmup_ticks + 1, total_ticks + 1):
        bridge_a.tick(inputs_seq[tick - 1], tick=tick)
        bridge_b.tick(inputs_seq[tick - 1], tick=tick)
        bridge_c.tick(inputs_seq[tick - 1], tick=tick)
        bridge_d.tick(inputs_seq[tick - 1], tick=tick)

        nodes_a = {n.node_id for n in bridge_a._graph.nodes}
        edges_a = {(e.source_id, e.target_id) for e in bridge_a._graph.edges}

        if div_b is None:
            nodes_b = {n.node_id for n in bridge_b._graph.nodes}
            edges_b = {(e.source_id, e.target_id) for e in bridge_b._graph.edges}
            if nodes_b != nodes_a or edges_b != edges_a:
                div_b = tick

        if div_c is None:
            nodes_c = {n.node_id for n in bridge_c._graph.nodes}
            edges_c = {(e.source_id, e.target_id) for e in bridge_c._graph.edges}
            if nodes_c != nodes_a or edges_c != edges_a:
                div_c = tick

        if div_d is None:
            nodes_d = {n.node_id for n in bridge_d._graph.nodes}
            edges_d = {(e.source_id, e.target_id) for e in bridge_d._graph.edges}
            if nodes_d != nodes_a or edges_d != edges_a:
                div_d = tick

    return Level3Outcome(
        condition_b_divergence_tick=div_b,
        condition_c_divergence_tick=div_c,
        condition_d_divergence_tick=div_d,
        condition_a_final_revision=bridge_a._topology_revision,
        condition_b_final_revision=bridge_b._topology_revision,
        condition_c_final_revision=bridge_c._topology_revision,
        condition_d_final_revision=bridge_d._topology_revision,
    )


def run_restoration_continuity_trial(
    seed: int,
    *,
    level1_warmup: int = 50,
    level1_eval: int = 50,
    level2_warmup: int = 50,
    level2_eval: int = 50,
    level3_warmup: int = 40,
    level3_eval: int = 60,
) -> RestorationContinuityOutcome:
    l1 = _evaluate_level_1(seed=seed, warmup_ticks=level1_warmup, eval_ticks=level1_eval)
    l2 = _evaluate_level_2(seed=seed, warmup_ticks=level2_warmup, eval_ticks=level2_eval)
    l3 = _evaluate_level_3(seed=seed, warmup_ticks=level3_warmup, eval_ticks=level3_eval)
    return RestorationContinuityOutcome(seed=seed, level1=l1, level2=l2, level3=l3)


def run_recurrent_restoration_study(
    seeds: Iterable[int] = (42, 123, 777),
    *,
    level1_warmup: int = 50,
    level1_eval: int = 50,
    level2_warmup: int = 50,
    level2_eval: int = 50,
    level3_warmup: int = 40,
    level3_eval: int = 60,
) -> RestorationContinuityStudyResult:
    seed_tuple = tuple(seeds)
    outcomes = tuple(
        run_restoration_continuity_trial(
            s,
            level1_warmup=level1_warmup,
            level1_eval=level1_eval,
            level2_warmup=level2_warmup,
            level2_eval=level2_eval,
            level3_warmup=level3_warmup,
            level3_eval=level3_eval,
        )
        for s in seed_tuple
    )

    d_ticks = [
        o.level1.condition_d_ticks_to_converge
        for o in outcomes
        if o.level1.condition_d_ticks_to_converge is not None
    ]
    l1_d_mean_ticks = sum(d_ticks) / len(d_ticks) if d_ticks else 0.0

    l1_c_conv_fraction = sum(1.0 for o in outcomes if o.level1.condition_c_converged) / len(
        outcomes
    )
    l1_c_mean_late = sum(o.level1.condition_c_late_mean_diff for o in outcomes) / len(outcomes)

    l2_c_mean_w = sum(o.level2.condition_c_weight_diff for o in outcomes) / len(outcomes)
    l2_d_mean_w = sum(o.level2.condition_d_weight_diff for o in outcomes) / len(outcomes)

    # In Level 3, immediate divergence means divergence at the first consolidation tick (48)
    l3_c_immediate = sum(1.0 for o in outcomes if o.level3.condition_c_divergence_tick == 48) / len(
        outcomes
    )
    l3_b_parity = sum(1.0 for o in outcomes if o.level3.condition_b_divergence_tick is None) / len(
        outcomes
    )

    return RestorationContinuityStudyResult(
        seeds=seed_tuple,
        outcomes=outcomes,
        level1_d_mean_ticks_to_converge=l1_d_mean_ticks,
        level1_c_converged_fraction=l1_c_conv_fraction,
        level1_c_mean_late_error=l1_c_mean_late,
        level2_c_mean_weight_drift=l2_c_mean_w,
        level2_d_mean_weight_drift=l2_d_mean_w,
        level3_c_immediate_divergence_rate=l3_c_immediate,
        level3_b_parity_rate=l3_b_parity,
    )
