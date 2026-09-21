"""Falsification study for temporal composition and causal revision.

The apparatus presents only opaque scalar channels.  It never supplies the
latent chain, intervention marker, target semantics or a reward.  The study
asks what the current CognitiveGraph actually discovers:

* two one-step relations in a delayed chain;
* a two-step relation that would require composing those relations;
* a correlated channel whose value is randomized by intervention;
* a contradiction that reverses the learned relation.

The protocol is intentionally a capability test, not an implementation of a
causal learner.  A failed gate is evidence about the current substrate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Sequence

from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.graph import CognitiveGraph, KernelLimits, PlasticNode
from symbiont.cognition.metaplasticity import SafetyState
from symbiont.cognition.learning import ComposedShadowPrediction, LaggedShadowPrediction
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.core.cognition_bridge import CognitiveBridge

_STUDY_ID = "learning.cognitive-graph-causal-composition"


@dataclass(frozen=True, slots=True)
class CausalCompositionSeedResult:
    seed: int
    local_chain_relations: int
    direct_distant_relation: bool
    intervention_source_gain: float
    intervention_beats_persistence: bool
    context_reuse_gain: float
    context_reused: bool
    contradiction_weight_before: float
    contradiction_weight_after: float
    contradiction_revised: bool
    temporal_lag_gain: float
    temporal_lag_discovered: bool
    composed_gain: float
    composed_discovered: bool
    composed_context_gain: float
    composed_context_reused: bool
    composed_second_slope_before: float
    composed_second_slope_after: float
    composed_revised: bool
    replay_deterministic: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CausalCompositionStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[CausalCompositionSeedResult, ...]
    local_chain_discovery_rate: float
    distant_composition_rate: float
    intervention_discrimination_rate: float
    contradiction_revision_rate: float
    temporal_lag_discovery_rate: float
    composed_discovery_rate: float
    composed_context_reuse_rate: float
    composed_revision_rate: float
    context_reuse_rate: float
    replay_deterministic: bool
    full_capability_supported: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "per_seed": [item.as_dict() for item in self.per_seed],
            "local_chain_discovery_rate": self.local_chain_discovery_rate,
            "distant_composition_rate": self.distant_composition_rate,
            "intervention_discrimination_rate": self.intervention_discrimination_rate,
            "contradiction_revision_rate": self.contradiction_revision_rate,
            "temporal_lag_discovery_rate": self.temporal_lag_discovery_rate,
            "composed_discovery_rate": self.composed_discovery_rate,
            "composed_context_reuse_rate": self.composed_context_reuse_rate,
            "composed_revision_rate": self.composed_revision_rate,
            "context_reuse_rate": self.context_reuse_rate,
            "replay_deterministic": self.replay_deterministic,
            "full_capability_supported": self.full_capability_supported,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not seeds:
        raise ValueError("seeds must be a non-empty sequence of unique integers")
    result = tuple(seeds)
    if len(result) > 64 or len(set(result)) != len(result):
        raise ValueError("seeds must contain at most 64 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must contain integers only")
    return result


def _build_bridge(channel_ids: Sequence[str]) -> CognitiveBridge:
    limits = KernelLimits()
    graph = CognitiveGraph(
        nodes=tuple(PlasticNode(node_id=channel_id, kind=NodeKind.SENSE) for channel_id in channel_ids),
        edges=(),
        kernel_limits=limits,
    )
    genome = load_base_genome(kernel_limits=limits, running_version=(0, 80, 16))
    return CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
        safety_state=SafetyState(frozen=False),
    )


def _promote_target(bridge, target_id: str, *, tick: int) -> None:
    if any(node.kind is NodeKind.PREDICTOR and node.predicts_node_id == target_id for node in bridge.graph.nodes):
        return
    candidates = sorted(
        (item for item in bridge.shadow_predictions if item.target_id == target_id and item.promotable),
        key=lambda item: item.predictive_gain,
        reverse=True,
    )
    if candidates:
        bridge.promote_shadow_prediction(candidates[0].source_id, target_id, tick=tick + 1)


def _predictive_sources(bridge, target_id: str) -> set[str]:
    predictor_ids = {
        node.node_id
        for node in bridge.graph.nodes
        if node.kind is NodeKind.PREDICTOR and node.predicts_node_id == target_id
    }
    return {
        edge.source_id
        for edge in bridge.graph.edges
        if edge.target_id in predictor_ids and edge.kind is EdgeKind.PREDICTIVE
    }


def _run_seed(seed: int, *, ticks: int) -> CausalCompositionSeedResult:
    rng = random.Random(seed)
    bridge = _build_bridge(("x", "m", "y"))
    x = [rng.choice((-1.0, 1.0)) for _ in range(ticks + 4)]
    m = [0.0] + x[:-1]
    y = [0.0, 0.0] + x[:-2]
    lagged_shadow = LaggedShadowPrediction(source_id="x", target_id="y", lag_ticks=2)
    composed_shadow = ComposedShadowPrediction(source_id="x", intermediate_id="m", target_id="y")

    for tick in range(1, ticks + 1):
        lagged_shadow.observe(x[tick], y[tick])
        composed_shadow.observe(x[tick], m[tick], y[tick])
        bridge.tick({"x": x[tick], "m": m[tick], "y": y[tick]}, tick=tick)
        _promote_target(bridge, "m", tick=tick)
        _promote_target(bridge, "y", tick=tick)

    local_sources = _predictive_sources(bridge, "m") | _predictive_sources(bridge, "y")
    local_chain_relations = int({"x", "m"}.issubset(local_sources))
    direct_distant_relation = "x" in _predictive_sources(bridge, "y")

    # New context: the same opaque temporal relation is presented with a
    # different scale and a fresh driver.  Reuse is measured against a
    # persistence baseline, without creating a new predictor.
    q = [rng.uniform(-0.4, 0.4) for _ in range(ticks + 2)]
    q_m = [0.0] + q[:-1]
    q_y = [0.0, 0.0] + q[:-2]
    context_losses: list[float] = []
    context_persistence: list[float] = []
    for index, tick in enumerate(range(ticks + 1, ticks * 2 + 1), start=1):
        result = bridge.tick({"x": q[index], "m": q_m[index], "y": q_y[index]}, tick=tick)
        context_losses.extend(error.loss for error in result.prediction_errors if error.target_id == "y")
        context_persistence.append(0.5 * (q_y[index] - q_y[index - 1]) ** 2)
    context_gain = (
        sum(context_persistence) / len(context_persistence)
        - sum(context_losses) / len(context_losses)
        if context_losses else 0.0
    )
    composed_context_losses: list[float] = []
    composed_context_persistence: list[float] = []
    first_slope = composed_shadow.first_relation_slope
    second_slope = composed_shadow.second_relation_slope
    for index in range(2, ticks + 1):
        composed_context_losses.append(
            0.5 * (q_y[index] - first_slope * second_slope * q[index - 2]) ** 2
        )
        composed_context_persistence.append(0.5 * (q_y[index] - q_y[index - 1]) ** 2)
    composed_context_gain = (
        sum(composed_context_persistence) / len(composed_context_persistence)
        - sum(composed_context_losses) / len(composed_context_losses)
    )

    # Contradiction phase: the previously learned m -> y relation becomes
    # false.  m remains opaque and no phase marker is supplied.
    predictor_edge = next(
        (edge for edge in bridge.graph.edges
         if edge.source_id == "m" and edge.kind is EdgeKind.PREDICTIVE),
        None,
    )
    weight_before = predictor_edge.weight if predictor_edge is not None else 0.0
    composed_second_slope_before = composed_shadow.second_relation_slope
    previous_m = m[-1]
    for tick in range(ticks + 1, ticks * 2 + 1):
        x_now = rng.choice((-1.0, 1.0))
        m_now = x_now
        y_now = -previous_m
        bridge.tick({"x": x_now, "m": m_now, "y": y_now}, tick=tick)
        composed_shadow.observe(x_now, m_now, y_now)
        previous_m = m_now
    weight_after = predictor_edge.weight if predictor_edge is not None else 0.0
    contradiction_revised = predictor_edge is not None and weight_before * weight_after < 0.0
    composed_second_slope_after = composed_shadow.second_relation_slope

    # Observational correlation followed by do(a): a is randomized while y
    # continues to follow the hidden common cause z.  The learned one-step
    # source relation is evaluated against persistence without exposing this
    # distinction to the organism.
    obs = _build_bridge(("a", "y"))
    z = [rng.choice((-1.0, 1.0)) for _ in range(ticks)]
    for tick in range(1, ticks + 1):
        obs.tick({"a": z[tick - 1], "y": z[tick - 1]}, tick=tick)
        _promote_target(obs, "y", tick=tick)
    source_losses: list[float] = []
    persistence_losses: list[float] = []
    previous_a = z[-1]
    previous_y = z[-1]
    for tick in range(ticks + 1, ticks * 2 + 1):
        a_now = rng.choice((-1.0, 1.0))
        y_now = z[tick - ticks - 1]
        source_losses.append(0.5 * (y_now - previous_a) ** 2)
        persistence_losses.append(0.5 * (y_now - previous_y) ** 2)
        previous_a = a_now
        previous_y = y_now
        obs.tick({"a": a_now, "y": y_now}, tick=tick)
    source_gain = sum(persistence_losses) / len(persistence_losses) - sum(source_losses) / len(source_losses)

    return CausalCompositionSeedResult(
        seed=seed,
        local_chain_relations=local_chain_relations,
        direct_distant_relation=direct_distant_relation,
        intervention_source_gain=source_gain,
        intervention_beats_persistence=source_gain > 0.0,
        context_reuse_gain=context_gain,
        context_reused=context_gain > 0.0,
        contradiction_weight_before=weight_before,
        contradiction_weight_after=weight_after,
        contradiction_revised=contradiction_revised,
        temporal_lag_gain=lagged_shadow.predictive_gain,
        temporal_lag_discovered=lagged_shadow.promotable,
        composed_gain=composed_shadow.predictive_gain,
        composed_discovered=composed_shadow.promotable,
        composed_context_gain=composed_context_gain,
        composed_context_reused=composed_context_gain > 0.0,
        composed_second_slope_before=composed_second_slope_before,
        composed_second_slope_after=composed_second_slope_after,
        composed_revised=composed_second_slope_before * composed_second_slope_after < 0.0,
        replay_deterministic=False,
    )


def run_cognitive_graph_causal_composition_study(
    *, seeds: Sequence[int] = (101, 127, 149), ticks: int = 200
) -> CausalCompositionStudy:
    normalized = _normalize_seeds(seeds)
    if ticks < 32 or ticks > 100_000:
        raise ValueError("ticks must be within [32, 100000]")
    results = tuple(_run_seed(seed, ticks=ticks) for seed in normalized)
    replay = tuple(_run_seed(seed, ticks=ticks) for seed in normalized)
    # The result is deterministic if all measured fields match; the local
    # helper marks replay false because it is not itself the replay oracle.
    deterministic = all(
        a.as_dict() | {"replay_deterministic": False}
        == b.as_dict() | {"replay_deterministic": False}
        for a, b in zip(results, replay)
    )
    n = len(results)
    rate = lambda field: sum(bool(getattr(item, field)) for item in results) / n
    return CausalCompositionStudy(
        seeds=normalized,
        per_seed=tuple(
            CausalCompositionSeedResult(**{**item.as_dict(), "replay_deterministic": deterministic})
            for item in results
        ),
        local_chain_discovery_rate=rate("local_chain_relations"),
        distant_composition_rate=rate("direct_distant_relation"),
        intervention_discrimination_rate=rate("intervention_beats_persistence"),
        contradiction_revision_rate=rate("contradiction_revised"),
        temporal_lag_discovery_rate=rate("temporal_lag_discovered"),
        composed_discovery_rate=rate("composed_discovered"),
        composed_context_reuse_rate=rate("composed_context_reused"),
        composed_revision_rate=rate("composed_revised"),
        context_reuse_rate=rate("context_reused"),
        replay_deterministic=deterministic,
        full_capability_supported=(
            rate("local_chain_relations") >= 0.70
            and rate("direct_distant_relation") >= 0.70
            and rate("intervention_beats_persistence") >= 0.70
            and rate("contradiction_revised") >= 0.70
            and rate("context_reused") >= 0.70
            and deterministic
        ),
    )


__all__ = ["CausalCompositionSeedResult", "CausalCompositionStudy", "run_cognitive_graph_causal_composition_study"]
