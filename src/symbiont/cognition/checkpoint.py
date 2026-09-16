from __future__ import annotations

import math
from typing import Any, Mapping

from .activation import MIN_NORMALIZER_SAMPLES, SensoryNormalizer
from .genome import Genome, GenomeCodec, GenomeError, _genome_to_plain_dict
from .graph import CognitiveGraph, GraphError, PlasticEdge, PlasticNode
from .limits import KernelLimits
from .metaplasticity import SafetyState
from .types import WEIGHT_RANGE

WEIGHT_CLASSES = 17
WEIGHT_CODEC_VERSION = 2
WEIGHT_DEADBAND = 0.01
# ELIGIBILITY_CLASSES/ELIGIBILITY_RANGE are no longer used by this module's
# own checkpoint functions (eligibility is labile, design §10.3) but remain
# public: observatory/adapter.py uses them to quantize live (RAM, per-tick)
# eligibility for real-time display -- a display concern, not persistence.
ELIGIBILITY_CLASSES = 16
ELIGIBILITY_RANGE = (-10.0, 10.0)


def quantize_signed(value: float, bounds: tuple[float, float], num_classes: int) -> int:
    low, high = bounds
    clipped = max(low, min(high, value))
    ratio = (clipped - low) / (high - low)
    return round(ratio * (num_classes - 1))


def quantize_weight(value: float) -> int:
    """Quantize a weight with an exact-zero deadband (codec v2)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("weight must be finite")
    if abs(value) <= WEIGHT_DEADBAND:
        return WEIGHT_CLASSES // 2
    low, high = WEIGHT_RANGE
    magnitude = min(1.0, max(0.0, abs(value) / max(abs(low), abs(high))))
    side = round(magnitude * (WEIGHT_CLASSES // 2))
    return (WEIGHT_CLASSES // 2 + side) if value > 0 else (WEIGHT_CLASSES // 2 - side)

def dequantize_weight(class_id: int) -> float:
    if isinstance(class_id, bool) or not isinstance(class_id, int) or not 0 <= class_id < WEIGHT_CLASSES:
        raise ValueError("invalid weight class")
    if class_id == WEIGHT_CLASSES // 2:
        return 0.0
    step = max(abs(WEIGHT_RANGE[0]), abs(WEIGHT_RANGE[1])) / (WEIGHT_CLASSES // 2)
    return (class_id - WEIGHT_CLASSES // 2) * step

def dequantize_signed(class_id: int, bounds: tuple[float, float], num_classes: int) -> float:
    low, high = bounds
    ratio = class_id / (num_classes - 1)
    return low + ratio * (high - low)


def export_genome_checkpoint(genome: Genome | None) -> dict[str, Any] | None:
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


def _require_nonneg_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GraphError(f"{field} must be a non-negative integer")
    if value < 0:
        raise GraphError(f"{field} must be non-negative")
    return value


def _require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GraphError(f"{field} must be an integer")
    return value


def export_graph_checkpoint(
    graph: CognitiveGraph | None, *, weight_class_overrides: dict[tuple[str, str, str], int] | None = None
) -> dict[str, Any] | None:
    """Serialize graph structure, quantizing continuously learned edge state.

    weight_class_overrides (keyed by (source_id, target_id, kind.value)),
    when provided, supplies each edge's durable weight class -- e.g. from a
    WeightStabilityTracker -- instead of quantizing the current live weight
    directly. CognitiveBridge always passes a complete override map; a
    caller that doesn't (e.g. a standalone unit test) falls back to live
    quantization, same as before this parameter existed."""
    if graph is None:
        return None
    return {
        "weight_codec_version": WEIGHT_CODEC_VERSION,
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
                "weight_class": (
                    weight_class_overrides[(edge.source_id, edge.target_id, edge.kind.value)]
                    if weight_class_overrides is not None
                    and (edge.source_id, edge.target_id, edge.kind.value) in weight_class_overrides
                    else quantize_weight(edge.weight)
                ),
                "plasticity": edge.plasticity,
                "delay_ticks": edge.delay_ticks,
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
    """Re-validate untrusted checkpoint state fully before construction."""
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise GraphError("graph checkpoint payload must be an object")
    codec_version = payload.get("weight_codec_version", 1)
    if isinstance(codec_version, bool) or not isinstance(codec_version, int) or codec_version not in (1, WEIGHT_CODEC_VERSION):
        raise GraphError("unsupported graph weight codec version")

    from .types import EdgeKind, NodeKind

    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise GraphError("graph checkpoint payload must have list-shaped 'nodes' and 'edges'")

    try:
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
                weight=(
                    dequantize_weight(_require_class_id(entry["weight_class"], field="edge.weight_class", num_classes=WEIGHT_CLASSES))
                    if codec_version == WEIGHT_CODEC_VERSION
                    else dequantize_signed(_require_class_id(entry["weight_class"], field="edge.weight_class", num_classes=16), WEIGHT_RANGE, 16)
                ),
                plasticity=_require_finite(entry["plasticity"], "edge.plasticity"),
                delay_ticks=_require_int(entry["delay_ticks"], "edge.delay_ticks"),
                eligibility=0.0,  # labile: never restored from a checkpoint (design §10.3, P5)
                support=_require_nonneg_int(entry["support"], "edge.support"),
                age_ticks=_require_nonneg_int(entry["age_ticks"], "edge.age_ticks"),
                stable_ticks=_require_nonneg_int(entry["stable_ticks"], "edge.stable_ticks"),
                last_use_tick=_require_nonneg_int(entry["last_use_tick"], "edge.last_use_tick"),
            )
            for entry in raw_edges
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, GraphError):
            raise
        raise GraphError(f"malformed graph checkpoint: {exc}") from exc
    return CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=kernel_limits)


def export_safety_state(state: SafetyState) -> dict[str, Any]:
    return {"consecutive_failures": state.consecutive_failures, "frozen": state.frozen}


def restore_safety_state(payload: dict[str, Any] | None) -> SafetyState:
    if payload is None:
        return SafetyState()
    if not isinstance(payload, dict):
        raise GraphError("safety_state checkpoint must be an object")
    try:
        failures = _require_nonneg_int(payload["consecutive_failures"], "safety_state.consecutive_failures")
        frozen = payload["frozen"]
    except KeyError as exc:
        raise GraphError(f"malformed safety_state checkpoint: missing {exc.args[0]!r}") from exc
    if not isinstance(frozen, bool):
        raise GraphError("safety_state.frozen must be a boolean")
    return SafetyState(consecutive_failures=failures, frozen=frozen)


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
    if not isinstance(payload, dict):
        raise GraphError("sensory_normalizers checkpoint must be an object")
    restored: dict[str, SensoryNormalizer] = {}
    for sense_id, entry in payload.items():
        if not isinstance(entry, dict):
            raise GraphError(f"sensory normalizer {sense_id!r} must be an object")
        count = _require_nonneg_int(entry.get("count"), f"{sense_id}.count")
        if count < MIN_NORMALIZER_SAMPLES:
            raise GraphError(f"sensory normalizer {sense_id!r} checkpoint count below MIN_NORMALIZER_SAMPLES")
        restored[sense_id] = SensoryNormalizer(
            mean=_require_finite(entry.get("mean"), f"{sense_id}.mean"),
            variance=_require_finite(entry.get("variance"), f"{sense_id}.variance"),
            count=count,
        )
    return restored
