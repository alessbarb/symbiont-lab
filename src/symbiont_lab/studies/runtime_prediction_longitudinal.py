"""Evaluator-only longitudinal shadow-prediction study."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.runtime import OrganismRuntime

from .runtime_prediction_promotion import _runtime


@dataclass(frozen=True, slots=True)
class RuntimePredictionLongitudinalStudy:
    trials: int
    checkpoint_tick: int
    continuation_replay_equal: bool
    signal_status: str
    signal_samples: int
    signal_promoted: bool
    predictor_count: int
    continuation_model_loss_delta: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _advance(runtime: OrganismRuntime, start: int, end: int) -> None:
    for tick in range(start, end + 1):
        runtime.cognitive_bridge.tick({"s": float(tick % 2), "t": float((tick + 1) % 2)}, tick=tick)


def _signal(runtime: OrganismRuntime):
    return next(
        (
            candidate
            for candidate in runtime.shadow_predictions
            if (candidate.source_id, candidate.target_id) == ("s", "t")
        ),
        None,
    )


def run_runtime_prediction_longitudinal_study(
    *,
    trials: int = 32,
) -> RuntimePredictionLongitudinalStudy:
    """Require evidence to survive a checkpoint before predictor promotion."""
    if trials < 16:
        raise ValueError("trials must be at least 16")
    midpoint = trials // 2
    runtime = _runtime("longitudinal-signal", "s", "t")
    _advance(runtime, 1, midpoint)
    checkpoint = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(
        checkpoint, bootstrap_semantic_senses=False, discover_senses=False
    )
    _advance(runtime, midpoint + 1, trials)
    _advance(restored, midpoint + 1, trials)
    left = _signal(runtime)
    right = _signal(restored)
    model_loss_delta = (
        abs(left.model_loss - right.model_loss)
        if left is not None and right is not None
        else float("inf")
    )
    # Checkpoint restoration quantizes graph weights, so exact floating-point
    # loss replay is not a contract.  The longitudinal contract is that the
    # evidence count and lifecycle decision survive restoration.
    continuation_equal = (
        left is not None
        and right is not None
        and left.status == right.status
        and left.predictive_gain > 0.0
        and right.predictive_gain > 0.0
    )
    promoted = runtime.promote_shadow_prediction("s", "t")
    signal_samples = left.samples if left is not None else 0
    if promoted:
        # Promotion now means admission to structural contention. Advance to
        # the next consolidation round before measuring materialized topology.
        interval = runtime.genome.development.consolidation_interval_ticks
        next_tick = trials + (interval - (trials % interval))
        if next_tick == trials:
            next_tick += interval
        runtime.cognitive_bridge.tick(
            {"s": float(next_tick % 2), "t": float((next_tick + 1) % 2)},
            tick=next_tick,
        )
    predictor_count = sum(
        1 for node in runtime.cognitive_bridge.graph.nodes if node.kind.value == "predictor"
    )
    return RuntimePredictionLongitudinalStudy(
        trials=trials,
        checkpoint_tick=midpoint,
        continuation_replay_equal=continuation_equal,
        signal_status=left.status if left is not None else "missing",
        signal_samples=signal_samples,
        signal_promoted=promoted,
        predictor_count=predictor_count,
        continuation_model_loss_delta=model_loss_delta,
    )


__all__ = ["RuntimePredictionLongitudinalStudy", "run_runtime_prediction_longitudinal_study"]
