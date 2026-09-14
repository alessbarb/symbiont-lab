from __future__ import annotations

import math
from typing import Any

from .activation import MIN_NORMALIZER_SAMPLES, SensoryNormalizer
from .genome import Genome, GenomeCodec, GenomeError, _genome_to_plain_dict
from .graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode
from .limits import KernelLimits
from .metaplasticity import SafetyState
from .types import WEIGHT_RANGE

_WEIGHT_CLASSES = 16
_ELIGIBILITY_CLASSES = 16
_ELIGIBILITY_RANGE = (-10.0, 10.0)  # matches learning.py's ELIGIBILITY_BOUND


def _quantize_signed(value: float, bounds: tuple[float, float], num_classes: int) -> int:
    low, high = bounds
    clipped = max(low, min(high, value))
    ratio = (clipped - low) / (high - low)
    return round(ratio * (num_classes - 1))


def _dequantize_signed(class_id: int, bounds: tuple[float, float], num_classes: int) -> float:
    low, high = bounds
    ratio = class_id / (num_classes - 1)
    return low + ratio * (high - low)


def export_genome_checkpoint(genome: Genome | None) -> dict[str, Any] | None:
    """None in, None out -- an organism with no genome checkpoints
    nothing new here. Genome content is small, bounded, declarative
    config, not raw telemetry, so it is persisted in full (roadmap
    v0.55 design spec §3.5)."""
    if genome is None:
        return None
    payload = _genome_to_plain_dict(genome)
    payload["genome_hash"] = genome.genome_hash
    return payload


def restore_genome_checkpoint(
    payload: dict[str, Any] | None,
    *,
    kernel_limits: KernelLimits,
    running_version: tuple[int, int, int],
) -> Genome | None:
    """Re-validates fully (load + validate) on restore -- a checkpoint is
    untrusted input, same discipline as every other restore path in this
    codebase. Also recomputes genome_hash from the restored fields and
    rejects a mismatch against the persisted hash, defending against a
    hand-edited or corrupted checkpoint claiming a genome it doesn't
    actually match."""
    if payload is None:
        return None
    if not isinstance(payload, dict) or "genome_hash" not in payload:
        raise GenomeError("genome checkpoint payload must be an object with a genome_hash")
    persisted_hash = payload["genome_hash"]
    genome_fields = {key: value for key, value in payload.items() if key != "genome_hash"}
    codec = GenomeCodec()
    genome = codec.load(genome_fields)
    if genome.genome_hash != persisted_hash:
        raise GenomeError("genome checkpoint hash mismatch -- payload may be corrupted or tampered")
    codec.validate(genome, kernel_limits, running_version=running_version)
    return genome


def _require_finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise GraphError(f"{field} must be finite")
    return number


def export_graph_checkpoint(graph: CognitiveGraph | None) -> dict[str, Any] | None:
    """None in, None out. Bias/tau/plasticity/delay are static
    construction-time values (never mutated by any code in this
    codebase) and are exported exactly. weight and eligibility are
    continuously updated from real activations every tick, so -- same
    discipline as core/selfmodel.py's checkpoint quantization -- they
    are quantized into bins rather than exported as raw floats,
    preventing two consecutive checkpoints from being differenced to
    recover a near-exact recent activation (CLAUDE.md: raw telemetry
    is not persisted). support/age_ticks/last_use_tick are organism-
    relative tick counters, the same category already accepted as
    exact ints elsewhere in this codebase (e.g. saved_at_tick)."""
    if graph is None:
        return None
    return {
        "nodes": [
            {
                "node_id": node.node_id,
                "kind": node.kind.value,
                "bias": node.bias,
                "tau": node.tau,
                "predicts_node_id": node.predicts_node_id,
            }
            for node in graph.nodes
        ],
        "edges": [
            {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "kind": edge.kind.value,
                "weight_class": _quantize_signed(edge.weight, WEIGHT_RANGE, _WEIGHT_CLASSES),
                "plasticity": edge.plasticity,
                "delay_ticks": edge.delay_ticks,
                "eligibility_class": _quantize_signed(edge.eligibility, _ELIGIBILITY_RANGE, _ELIGIBILITY_CLASSES),
                "support": edge.support,
                "age_ticks": edge.age_ticks,
                "stable_ticks": edge.stable_ticks,
                "last_use_tick": edge.last_use_tick,
            }
            for edge in graph.edges
        ],
    }


def restore_graph_checkpoint(
    payload: dict[str, Any] | None, *, kernel_limits: KernelLimits
) -> CognitiveGraph | None:
    """Re-validates fully via CognitiveGraph's own constructor -- a
    checkpoint is untrusted input, same discipline as every other
    restore path in this codebase."""
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise GraphError("graph checkpoint payload must be an object")

    from .types import EdgeKind, NodeKind

    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise GraphError("graph checkpoint payload must have list-shaped 'nodes' and 'edges'")

    nodes = tuple(
        PlasticNode(
            node_id=str(entry["node_id"]),
            kind=NodeKind(entry["kind"]),
            bias=_require_finite(entry["bias"], "node.bias"),
            tau=_require_finite(entry["tau"], "node.tau"),
            predicts_node_id=entry.get("predicts_node_id"),
        )
        for entry in raw_nodes
    )
    edges = tuple(
        PlasticEdge(
            source_id=str(entry["source_id"]),
            target_id=str(entry["target_id"]),
            kind=EdgeKind(entry["kind"]),
            weight=_dequantize_signed(entry["weight_class"], WEIGHT_RANGE, _WEIGHT_CLASSES),
            plasticity=_require_finite(entry["plasticity"], "edge.plasticity"),
            delay_ticks=int(entry["delay_ticks"]),
            eligibility=_dequantize_signed(entry["eligibility_class"], _ELIGIBILITY_RANGE, _ELIGIBILITY_CLASSES),
            support=int(entry["support"]),
            age_ticks=int(entry["age_ticks"]),
            stable_ticks=int(entry["stable_ticks"]),
            last_use_tick=int(entry["last_use_tick"]),
        )
        for entry in raw_edges
    )
    return CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=kernel_limits)


def export_safety_state(state: SafetyState) -> dict[str, Any]:
    """A restart must never silently un-freeze a legitimately frozen
    network (master doc §13 invariant 8: fail visibly, don't silently
    recover) -- consecutive_failures/frozen are exact ints/bools, not
    continuously-updated telemetry, so no quantization is needed."""
    return {"consecutive_failures": state.consecutive_failures, "frozen": state.frozen}


def restore_safety_state(payload: dict[str, Any] | None) -> SafetyState:
    if payload is None:
        return SafetyState()
    return SafetyState(consecutive_failures=int(payload["consecutive_failures"]), frozen=bool(payload["frozen"]))


def export_sensory_normalizers(normalizers: dict[str, SensoryNormalizer]) -> dict[str, Any]:
    """Only established normalizers (>= MIN_NORMALIZER_SAMPLES) are
    exported -- an unestablished one's mean is still literally its most
    recent raw reading (see SensoryNormalizer.is_established), and
    exporting it would persist raw-telemetry-equivalent state."""
    return {
        sense_id: {"mean": normalizer.mean, "variance": normalizer.variance, "count": normalizer.count}
        for sense_id, normalizer in normalizers.items()
        if normalizer.is_established
    }


def restore_sensory_normalizers(payload: dict[str, Any] | None) -> dict[str, SensoryNormalizer]:
    if not payload:
        return {}
    restored: dict[str, SensoryNormalizer] = {}
    for sense_id, entry in payload.items():
        count = int(entry["count"])
        if count < MIN_NORMALIZER_SAMPLES:
            raise GraphError(f"sensory normalizer {sense_id!r} checkpoint count below MIN_NORMALIZER_SAMPLES")
        restored[sense_id] = SensoryNormalizer(
            mean=_require_finite(entry["mean"], f"{sense_id}.mean"),
            variance=_require_finite(entry["variance"], f"{sense_id}.variance"),
            count=count,
        )
    return restored
