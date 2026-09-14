from __future__ import annotations

import math
from typing import Any, Mapping

from .activation import MIN_NORMALIZER_SAMPLES, SensoryNormalizer
from .genome import Genome, GenomeCodec, GenomeError, _genome_to_plain_dict
from .graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode
from .limits import KernelLimits
from .metaplasticity import SafetyState
from .types import WEIGHT_RANGE

WEIGHT_CLASSES = 16
ELIGIBILITY_CLASSES = 16
ELIGIBILITY_RANGE = (-10.0, 10.0)
_ACTIVATION_CLASSES = 33
_ACTIVATION_RANGE = (-1.0, 1.0)


def quantize_signed(value: float, bounds: tuple[float, float], num_classes: int) -> int:
    low, high = bounds
    clipped = max(low, min(high, value))
    ratio = (clipped - low) / (high - low)
    return round(ratio * (num_classes - 1))


def dequantize_signed(class_id: int, bounds: tuple[float, float], num_classes: int) -> float:
    low, high = bounds
    ratio = class_id / (num_classes - 1)
    return low + ratio * (high - low)


def export_genome_checkpoint(genome: Genome | None) -> dict[str, Any] | None:
    """None in, None out -- declarative genome configuration is persisted exactly."""
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
    """Re-validate a genome checkpoint and reject identity mismatches."""
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


def _require_class_id(value: Any, *, field: str, num_classes: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GraphError(f"{field} must be an integer class id")
    if not 0 <= value < num_classes:
        raise GraphError(f"{field} must be within [0, {num_classes - 1}]")
    return value


def export_graph_checkpoint(graph: CognitiveGraph | None) -> dict[str, Any] | None:
    """Serialize graph structure, quantizing continuously learned edge state."""
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
                "weight_class": quantize_signed(edge.weight, WEIGHT_RANGE, WEIGHT_CLASSES),
                "plasticity": edge.plasticity,
                "delay_ticks": edge.delay_ticks,
                "eligibility_class": quantize_signed(
                    edge.eligibility, ELIGIBILITY_RANGE, ELIGIBILITY_CLASSES
                ),
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
    """Re-validate fully via CognitiveGraph's constructor."""
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
            weight=dequantize_signed(
                _require_class_id(entry["weight_class"], field="edge.weight_class", num_classes=WEIGHT_CLASSES),
                WEIGHT_RANGE,
                WEIGHT_CLASSES,
            ),
            plasticity=_require_finite(entry["plasticity"], "edge.plasticity"),
            delay_ticks=int(entry["delay_ticks"]),
            eligibility=dequantize_signed(
                _require_class_id(
                    entry["eligibility_class"],
                    field="edge.eligibility_class",
                    num_classes=ELIGIBILITY_CLASSES,
                ),
                ELIGIBILITY_RANGE,
                ELIGIBILITY_CLASSES,
            ),
            support=int(entry["support"]),
            age_ticks=int(entry["age_ticks"]),
            stable_ticks=int(entry["stable_ticks"]),
            last_use_tick=int(entry["last_use_tick"]),
        )
        for entry in raw_edges
    )
    return CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=kernel_limits)


def export_safety_state(state: SafetyState) -> dict[str, Any]:
    return {"consecutive_failures": state.consecutive_failures, "frozen": state.frozen}


def restore_safety_state(payload: dict[str, Any] | None) -> SafetyState:
    if payload is None:
        return SafetyState()
    return SafetyState(
        consecutive_failures=int(payload["consecutive_failures"]),
        frozen=bool(payload["frozen"]),
    )


def export_sensory_normalizers(normalizers: dict[str, SensoryNormalizer]) -> dict[str, Any]:
    """Export only established normalizers; younger means can equal raw readings."""
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


def export_activation_frame(frame: Mapping[str, float]) -> dict[str, int]:
    """Quantize the previous activation frame used by delay=1 edges.

    Activations are bounded to [-1, 1] by the graph. Thirty-three classes
    deliberately include an exact zero class, avoiding a restart that turns
    a true zero into a small artificial activation while still refusing to
    persist near-exact continuously updated cognitive state.
    """
    exported: dict[str, int] = {}
    for node_id, raw_value in frame.items():
        value = _require_finite(raw_value, f"previous_frame[{node_id!r}]")
        exported[str(node_id)] = quantize_signed(value, _ACTIVATION_RANGE, _ACTIVATION_CLASSES)
    return exported


def restore_activation_frame(payload: Mapping[str, Any] | None) -> dict[str, float]:
    if not payload:
        return {}
    if not isinstance(payload, Mapping):
        raise GraphError("previous_frame checkpoint must be an object")
    restored: dict[str, float] = {}
    for node_id, raw_class in payload.items():
        class_id = _require_class_id(
            raw_class,
            field=f"previous_frame[{node_id!r}]",
            num_classes=_ACTIVATION_CLASSES,
        )
        restored[str(node_id)] = dequantize_signed(
            class_id, _ACTIVATION_RANGE, _ACTIVATION_CLASSES
        )
    return restored
