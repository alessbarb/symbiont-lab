from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Iterable

from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.graph import CognitiveGraph, KernelLimits, PlasticEdge, PlasticNode
from symbiont.core.cognition_bridge import CognitiveBridge
from symbiont.cognition.types import EdgeKind, NodeKind
from symbiont.cognition.learning import huber_loss


@dataclass(slots=True, frozen=True)
class PredictiveUtilityOutcome:
    seed: int
    ticks: int
    target_id: str
    horizon_ticks: int
    early_loss: float
    late_loss: float
    zero_baseline_loss: float
    mean_baseline_loss: float
    persist_baseline_loss: float
    ablation_plasticity_loss: float
    ablation_lesion_loss: float
    loss_gain_vs_zero: float
    loss_gain_vs_mean: float
    loss_gain_vs_persist: float
    plasticity_utility_gain: float
    structural_utility_gain: float
    final_predictive_weight: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class PredictiveUtilityStudyResult:
    seeds: tuple[int, ...]
    outcomes: tuple[PredictiveUtilityOutcome, ...]
    mean_loss_gain_vs_zero: float
    mean_loss_gain_vs_mean: float
    mean_loss_gain_vs_persist: float
    mean_plasticity_gain: float
    mean_structural_gain: float

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "outcomes": [o.as_dict() for o in self.outcomes],
            "mean_loss_gain_vs_zero": self.mean_loss_gain_vs_zero,
            "mean_loss_gain_vs_mean": self.mean_loss_gain_vs_mean,
            "mean_loss_gain_vs_persist": self.mean_loss_gain_vs_persist,
            "mean_plasticity_gain": self.mean_plasticity_gain,
            "mean_structural_gain": self.mean_structural_gain,
        }


def _run_single_condition(
    *,
    seed: int,
    ticks: int,
    plasticity_enabled: bool,
    lesion: bool,
    eval_window: int,
) -> tuple[float, float, float, float, float, float]:
    rng = random.Random(seed)
    sense = PlasticNode(node_id="s", kind=NodeKind.SENSE)
    predictor = PlasticNode(node_id="p", kind=NodeKind.PREDICTOR, predicts_node_id="s", bias=0.0, tau=1.0)

    # This study deliberately uses the production bridge.  In particular,
    # predictive utility must measure the same prediction-error and plasticity
    # path as a resident, not a second Oja implementation owned by the lab.
    feed = PlasticEdge(
        source_id="s",
        target_id="p",
        kind=EdgeKind.PREDICTIVE,
        weight=0.0 if lesion else -0.35,
        plasticity=0.0 if lesion else (0.5 if plasticity_enabled else 0.0),
        delay_ticks=0,
    )
    edges = [feed]

    limits = KernelLimits()
    genome = load_base_genome(kernel_limits=limits, running_version=(0, 80, 16))
    bridge = CognitiveBridge(
        graph=CognitiveGraph(nodes=(sense, predictor), edges=tuple(edges), kernel_limits=limits),
        genome=genome,
        kernel_limits=limits,
    )

    losses: list[float] = []
    zero_losses: list[float] = []
    mean_losses: list[float] = []
    persist_losses: list[float] = []

    s_val = 0.5
    s_history: list[float] = []

    for tick in range(1, ticks + 1):
        noise = rng.gauss(0, 0.25)
        s_val = -0.82 * s_val + noise
        s_val = max(-0.95, min(0.95, s_val))

        result = bridge.tick({"s": s_val}, tick=tick, plasticity_enabled=plasticity_enabled and not lesion)
        target = result.activations.get("s", 0.0)
        if tick > 1:
            zero_losses.append(huber_loss(target - 0.0))
            running_mean = sum(s_history) / len(s_history)
            mean_losses.append(huber_loss(target - running_mean))
            persist_losses.append(huber_loss(target - s_history[-1]))

        losses.extend(error.loss for error in result.prediction_errors)

        s_history.append(target)
    if not losses:
        raise RuntimeError("predictive utility bridge produced no prediction errors")

    n_eval = min(eval_window, len(losses))
    early_loss = sum(losses[:n_eval]) / n_eval
    late_loss = sum(losses[-n_eval:]) / n_eval
    zero_loss = sum(zero_losses[-n_eval:]) / n_eval
    mean_loss = sum(mean_losses[-n_eval:]) / n_eval
    persist_loss = sum(persist_losses[-n_eval:]) / n_eval
    final_weight = feed.weight

    return early_loss, late_loss, zero_loss, mean_loss, persist_loss, final_weight


def run_predictive_utility_trial(
    seed: int,
    *,
    ticks: int = 400,
    eval_window: int = 80,
) -> PredictiveUtilityOutcome:
    early_loss, late_loss, zero_loss, mean_loss, persist_loss, final_weight = _run_single_condition(
        seed=seed,
        ticks=ticks,
        plasticity_enabled=True,
        lesion=False,
        eval_window=eval_window,
    )

    _, no_plasticity_loss, _, _, _, _ = _run_single_condition(
        seed=seed,
        ticks=ticks,
        plasticity_enabled=False,
        lesion=False,
        eval_window=eval_window,
    )

    _, lesion_loss, _, _, _, _ = _run_single_condition(
        seed=seed,
        ticks=ticks,
        plasticity_enabled=False,
        lesion=True,
        eval_window=eval_window,
    )

    return PredictiveUtilityOutcome(
        seed=seed,
        ticks=ticks,
        target_id="s",
        horizon_ticks=1,
        early_loss=early_loss,
        late_loss=late_loss,
        zero_baseline_loss=zero_loss,
        mean_baseline_loss=mean_loss,
        persist_baseline_loss=persist_loss,
        ablation_plasticity_loss=no_plasticity_loss,
        ablation_lesion_loss=lesion_loss,
        loss_gain_vs_zero=zero_loss - late_loss,
        loss_gain_vs_mean=mean_loss - late_loss,
        loss_gain_vs_persist=persist_loss - late_loss,
        plasticity_utility_gain=no_plasticity_loss - late_loss,
        structural_utility_gain=lesion_loss - late_loss,
        final_predictive_weight=final_weight,
    )


def run_predictive_utility_study(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    ticks: int = 400,
) -> PredictiveUtilityStudyResult:
    seed_list = tuple(seeds)
    outcomes = tuple(run_predictive_utility_trial(s, ticks=ticks) for s in seed_list)

    mean_vs_zero = sum(o.loss_gain_vs_zero for o in outcomes) / len(outcomes)
    mean_vs_mean = sum(o.loss_gain_vs_mean for o in outcomes) / len(outcomes)
    mean_vs_persist = sum(o.loss_gain_vs_persist for o in outcomes) / len(outcomes)
    mean_plasticity = sum(o.plasticity_utility_gain for o in outcomes) / len(outcomes)
    mean_structural = sum(o.structural_utility_gain for o in outcomes) / len(outcomes)

    return PredictiveUtilityStudyResult(
        seeds=seed_list,
        outcomes=outcomes,
        mean_loss_gain_vs_zero=mean_vs_zero,
        mean_loss_gain_vs_mean=mean_vs_mean,
        mean_loss_gain_vs_persist=mean_vs_persist,
        mean_plasticity_gain=mean_plasticity,
        mean_structural_gain=mean_structural,
    )
