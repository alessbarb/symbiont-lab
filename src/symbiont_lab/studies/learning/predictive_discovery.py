"""Preregistered counter-experiment: predictive STRUCTURE DISCOVERY, not precabling.

``predictive_utility.py`` hardcodes a single SENSE node, a single PREDICTOR
node with ``predicts_node_id`` already set, and a single edge whose sign is
already correct -- there is no structure for the organism to discover.  This
module gives the organism several candidate SENSE signals (one genuinely
predictive of the target, the rest decoys with matching numeric scale) and no
predictor at all; the organism must find which candidate predicts the target
using the existing, already-implemented ``ShadowPrediction`` /
``promote_shadow_prediction`` machinery (``symbiont/cognition/learning.py``,
``symbiont/core/cognition_bridge.py``).

Promotion now materializes the validated lag-1 hypothesis atomically: the
PREDICTOR node plus one learned PREDICTIVE input from the discovered SENSE
source. The study never constructs that edge itself; it only verifies after
promotion that production materialized the same source selected by shadow
evidence. Generalization remains evaluated against frozen fresh-seed data using
the discovered source's one-step loss versus persistence.
"""

from __future__ import annotations

import ast
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from symbiont.core.cognition_bridge import CognitiveBridge

from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.graph import CognitiveGraph, KernelLimits, PlasticNode
from symbiont.cognition.learning import huber_loss
from symbiont.cognition.metaplasticity import SafetyState
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont_lab.evaluation.holdout import DevelopmentPhase, FrozenEvaluationPhase, SeedLedger

_SOURCE = Path(__file__)
_STUDY_ID = "learning.predictive-discovery"
_CANDIDATE_IDS = ("s_true", "decoy_indep", "decoy_wronglag", "decoy_antiphase")
_TARGET_ID = "t"
LOSS_GAIN_THRESHOLD = (
    0.0002  # calibrated against a pilot run (observed s_true gain ~0.00043-0.00046,
)
# best-decoy gain negative ~-0.002 to -0.004); see audit methods section


@dataclass(frozen=True, slots=True)
class PredictiveDiscoverySeedResult:
    development_seed: int
    evaluation_seed: int
    promoted_source_id: str | None
    pd1_correct_source_promoted: bool
    pd2_no_decoy_promoted: bool
    evaluation_persist_loss: float
    evaluation_source_loss: float
    evaluation_source_gain: float
    evaluation_best_decoy_id: str
    evaluation_best_decoy_loss: float
    evaluation_best_decoy_gain: float
    pd3_holdout_loss_gain: bool
    pd4_decoy_control_fails_margin: bool
    pd6_learned_predictor_input: bool
    replay_deterministic: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PredictiveDiscoveryStudy:
    development_seeds: tuple[int, ...]
    evaluation_seeds: tuple[int, ...]
    per_seed: tuple[PredictiveDiscoverySeedResult, ...]
    pd1_correct_source_promoted: bool
    pd2_no_decoy_promoted: bool
    pd3_holdout_loss_gain: bool
    pd4_decoy_control_fails_margin: bool
    pd5_no_precabled_structure: bool
    pd6_learned_predictor_input: bool
    replay_deterministic: bool
    all_gates_pass: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "development_seeds": list(self.development_seeds),
            "evaluation_seeds": list(self.evaluation_seeds),
            "per_seed": [item.as_dict() for item in self.per_seed],
            "pd1_correct_source_promoted": self.pd1_correct_source_promoted,
            "pd2_no_decoy_promoted": self.pd2_no_decoy_promoted,
            "pd3_holdout_loss_gain": self.pd3_holdout_loss_gain,
            "pd4_decoy_control_fails_margin": self.pd4_decoy_control_fails_margin,
            "pd5_no_precabled_structure": self.pd5_no_precabled_structure,
            "pd6_learned_predictor_input": self.pd6_learned_predictor_input,
            "replay_deterministic": self.replay_deterministic,
            "all_gates_pass": self.all_gates_pass,
        }


def _generate(seed: int, ticks: int) -> dict[str, list[float]]:
    """Generating process: only ``s_true`` (lagged) predicts ``t``.

    - s_true: persistent AR(1), s_true_t = 0.9 * s_true_{t-1} + noise.
    - t:      s_true_{t-1} + small eps -- the law to be discovered.
    - decoy_indep:    independent AR(1), same scale, unrelated to t.
    - decoy_wronglag: lag of an independent driver -- genuine autocorrelation, zero relation to t.
    - decoy_antiphase: -s_true_{t-1} scaled -- tests sign-sensitivity of promotion.
    """
    rng = random.Random(seed)
    s_true = [0.0]
    decoy_indep = [0.0]
    driver = [0.0]
    decoy_wronglag = [0.0]
    t_series = [0.0]
    for _ in range(ticks):
        s_prev = s_true[-1]
        s_next = max(-1.0, min(1.0, 0.9 * s_prev + rng.uniform(-0.05, 0.05)))
        s_true.append(s_next)

        d_prev = decoy_indep[-1]
        decoy_indep.append(max(-1.0, min(1.0, 0.9 * d_prev + rng.uniform(-0.05, 0.05))))

        drv_prev = driver[-1]
        drv_next = max(-1.0, min(1.0, 0.9 * drv_prev + rng.uniform(-0.05, 0.05)))
        driver.append(drv_next)
        decoy_wronglag.append(drv_prev)

        t_series.append(max(-1.0, min(1.0, s_prev + rng.uniform(-0.01, 0.01))))

    decoy_antiphase = [max(-1.0, min(1.0, -0.6 * value)) for value in s_true]
    return {
        "s_true": s_true[1:],
        "decoy_indep": decoy_indep[1:],
        "decoy_wronglag": decoy_wronglag[1:],
        "decoy_antiphase": decoy_antiphase[1:],
        "t": t_series[1:],
    }


def _genome():
    limits = KernelLimits()
    return load_base_genome(kernel_limits=limits, running_version=(0, 80, 16))


def _build_bridge(*, frozen: bool = False) -> CognitiveBridge:
    limits = KernelLimits()
    nodes = tuple(PlasticNode(node_id=node_id, kind=NodeKind.SENSE) for node_id in _CANDIDATE_IDS)
    nodes += (PlasticNode(node_id=_TARGET_ID, kind=NodeKind.SENSE),)
    graph = CognitiveGraph(nodes=nodes, edges=(), kernel_limits=limits)
    genome = _genome()
    return CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
        safety_state=SafetyState(frozen=frozen),
    )


def _run_development(
    seed: int, *, ticks: int
) -> tuple[CognitiveBridge, str | None, tuple[str, ...]]:
    bridge = _build_bridge(frozen=False)
    series = _generate(seed, ticks)
    promoted_source: str | None = None
    for tick in range(1, ticks + 1):
        values = {node_id: series[node_id][tick - 1] for node_id in (*_CANDIDATE_IDS, _TARGET_ID)}
        bridge.tick(values, tick=tick, plasticity_enabled=True)
        already_promoted = any(
            node.kind is NodeKind.PREDICTOR and node.predicts_node_id == _TARGET_ID
            for node in bridge.graph.nodes
        )
        if already_promoted:
            continue
        # Multiple candidates can become simultaneously promotable; ranking by
        # predictive_gain (rather than the source-id-alphabetical iteration
        # order `shadow_predictions` happens to return) avoids an arbitrary
        # naming bias deciding which one wins the single available PREDICTOR
        # slot for this target.
        candidates = sorted(
            (
                item
                for item in bridge.shadow_predictions
                if item.target_id == _TARGET_ID and item.promotable
            ),
            key=lambda item: item.predictive_gain,
            reverse=True,
        )
        for candidate in candidates:
            if bridge.promote_shadow_prediction(
                candidate.source_id, candidate.target_id, tick=tick + 1
            ):
                promoted_source = candidate.source_id
                break
    decoy_status = tuple(
        p.status
        for p in bridge.shadow_predictions
        if p.target_id == _TARGET_ID and p.source_id != "s_true"
    )
    return bridge, promoted_source, decoy_status


def _has_learned_predictor_input(
    bridge: CognitiveBridge,
    source_id: str | None,
) -> bool:
    if source_id is None:
        return False
    predictors = [
        node
        for node in bridge.graph.nodes
        if node.kind is NodeKind.PREDICTOR and node.predicts_node_id == _TARGET_ID
    ]
    if len(predictors) != 1:
        return False
    predictor_id = predictors[0].node_id
    return any(
        edge.source_id == source_id
        and edge.target_id == predictor_id
        and edge.kind is EdgeKind.PREDICTIVE
        and edge.delay_ticks == 0
        for edge in bridge.graph.edges
    )


def _holdout_losses(evaluation_seed: int, *, ticks: int) -> dict[str, float]:
    series = _generate(evaluation_seed, ticks)
    t_series = series[_TARGET_ID]
    persist_losses: list[float] = []
    candidate_losses: dict[str, list[float]] = {node_id: [] for node_id in _CANDIDATE_IDS}
    for tick in range(1, ticks):
        target_current = t_series[tick]
        target_previous = t_series[tick - 1]
        persist_losses.append(huber_loss(target_current - target_previous))
        for node_id in _CANDIDATE_IDS:
            candidate_losses[node_id].append(huber_loss(target_current - series[node_id][tick - 1]))
    persist_loss = sum(persist_losses) / len(persist_losses)
    result = {"persist": persist_loss}
    for node_id, losses in candidate_losses.items():
        result[node_id] = sum(losses) / len(losses)
    return result


def _trial_result(
    development_seed: int,
    evaluation_seed: int,
    *,
    development_ticks: int = 400,
    evaluation_ticks: int = 200,
) -> PredictiveDiscoverySeedResult:
    bridge, promoted_source, decoy_status = _run_development(
        development_seed, ticks=development_ticks
    )
    replay_bridge, replay_source, replay_status = _run_development(
        development_seed, ticks=development_ticks
    )
    learned_input = _has_learned_predictor_input(bridge, promoted_source)
    replay_learned_input = _has_learned_predictor_input(replay_bridge, replay_source)
    replay_deterministic = (
        promoted_source == replay_source
        and decoy_status == replay_status
        and learned_input == replay_learned_input
    )

    losses = _holdout_losses(evaluation_seed, ticks=evaluation_ticks)
    persist_loss = losses["persist"]
    source_loss = losses.get(promoted_source, float("inf")) if promoted_source else float("inf")
    source_gain = persist_loss - source_loss

    decoy_losses = {
        node_id: losses[node_id] for node_id in _CANDIDATE_IDS if node_id != promoted_source
    }
    best_decoy_id = (
        min(decoy_losses, key=lambda node_id: decoy_losses[node_id]) if decoy_losses else ""
    )
    best_decoy_loss = decoy_losses.get(best_decoy_id, float("inf"))
    best_decoy_gain = persist_loss - best_decoy_loss

    return PredictiveDiscoverySeedResult(
        development_seed=development_seed,
        evaluation_seed=evaluation_seed,
        promoted_source_id=promoted_source,
        pd1_correct_source_promoted=(promoted_source == "s_true"),
        pd2_no_decoy_promoted=not any(
            status not in ("contradicted", "retired", "candidate") for status in decoy_status
        )
        if promoted_source == "s_true"
        else False,
        evaluation_persist_loss=persist_loss,
        evaluation_source_loss=source_loss,
        evaluation_source_gain=source_gain,
        evaluation_best_decoy_id=best_decoy_id,
        evaluation_best_decoy_loss=best_decoy_loss,
        evaluation_best_decoy_gain=best_decoy_gain,
        pd3_holdout_loss_gain=(source_gain >= LOSS_GAIN_THRESHOLD),
        pd4_decoy_control_fails_margin=(best_decoy_gain < LOSS_GAIN_THRESHOLD),
        pd6_learned_predictor_input=learned_input,
        replay_deterministic=replay_deterministic,
    )


def _normalize_seeds(seeds: Sequence[int], *, label: str) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError(f"{label} must contain unique integer entries")
    result = tuple(seeds)
    if not result or len(result) > 16 or len(set(result)) != len(result):
        raise ValueError(f"{label} must contain between 1 and 16 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError(f"{label} must be integers")
    return result


def _static_no_precabled_structure_check() -> bool:
    """pd5: static evidence this module never constructs a PREDICTOR node or edge
    at graph-construction time (it may only *read* ``NodeKind.PREDICTOR`` off
    nodes the organism itself promoted -- that is inspection, not precabling)."""
    tree = ast.parse(_SOURCE.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "predicts_node_id":
            return False
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "PlasticEdge"
        ):
            return False
        if (
            isinstance(node, ast.keyword)
            and node.arg == "kind"
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "PREDICTOR"
        ):
            return False
    return True


def run_predictive_discovery_study(
    *,
    development_seeds: Sequence[int] = (11, 23, 37),
    evaluation_seeds: Sequence[int] = (211, 233, 257),
    development_ticks: int = 400,
    evaluation_ticks: int = 200,
    ledger: SeedLedger | None = None,
) -> PredictiveDiscoveryStudy:
    dev_seeds = _normalize_seeds(development_seeds, label="development_seeds")
    eval_seeds = _normalize_seeds(evaluation_seeds, label="evaluation_seeds")
    if len(dev_seeds) != len(eval_seeds):
        raise ValueError("development_seeds and evaluation_seeds must pair one-to-one")
    if set(dev_seeds) & set(eval_seeds):
        raise ValueError("evaluation_seeds must be disjoint from development_seeds")

    # Mechanically enforce "never touched during development" against this
    # study's full historical record, not just the seeds passed in this call.
    active_ledger = ledger if ledger is not None else SeedLedger()
    development_phase = DevelopmentPhase(study_id=_STUDY_ID, seeds=dev_seeds)
    evaluation_phase = FrozenEvaluationPhase(study_id=_STUDY_ID, seeds=eval_seeds)
    evaluation_phase.validate_disjoint(active_ledger)
    active_ledger.record_development(development_phase)

    results = tuple(
        _trial_result(
            dev, ev, development_ticks=development_ticks, evaluation_ticks=evaluation_ticks
        )
        for dev, ev in zip(dev_seeds, eval_seeds)
    )
    pd5 = _static_no_precabled_structure_check()
    gate_fields = (
        "pd1_correct_source_promoted",
        "pd2_no_decoy_promoted",
        "pd3_holdout_loss_gain",
        "pd4_decoy_control_fails_margin",
        "pd6_learned_predictor_input",
    )
    return PredictiveDiscoveryStudy(
        development_seeds=dev_seeds,
        evaluation_seeds=eval_seeds,
        per_seed=results,
        pd1_correct_source_promoted=all(item.pd1_correct_source_promoted for item in results),
        pd2_no_decoy_promoted=all(item.pd2_no_decoy_promoted for item in results),
        pd3_holdout_loss_gain=all(item.pd3_holdout_loss_gain for item in results),
        pd4_decoy_control_fails_margin=all(item.pd4_decoy_control_fails_margin for item in results),
        pd5_no_precabled_structure=pd5,
        pd6_learned_predictor_input=all(item.pd6_learned_predictor_input for item in results),
        replay_deterministic=all(item.replay_deterministic for item in results),
        all_gates_pass=(
            all(
                all(getattr(item, field) for field in gate_fields) and item.replay_deterministic
                for item in results
            )
            and pd5
        ),
    )


__all__ = [
    "PredictiveDiscoverySeedResult",
    "PredictiveDiscoveryStudy",
    "run_predictive_discovery_study",
]
