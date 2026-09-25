from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from hashlib import sha256
from statistics import mean, pstdev
from typing import Iterable

from symbiont.environment.rng import derive_seed
from symbiont.simulation import EventContext, run_simulation
from symbiont_lab.studies.attention.causal import NOVELTY_MIN_HISTORY
from symbiont_lab.studies.attention.retrospective import (
    _score_events,
    _ScoredEvent,
)
from symbiont_lab.studies.common.causal_selection import OrderStatisticHistory, online_indices

from .second_look import (
    base_probability,
    entropy,
    posterior_probability,
    second_look_measurement,
)

DIRECTED_STRATEGIES = ("risk", "novelty", "risk_novelty")
REFERENCE_STRATEGY = "random"
ACTIVE_METRICS = (
    "post_recall",
    "post_precision",
    "post_false_positive_rate",
    "post_stealth_recall",
    "brier_gain",
    "net_correction_rate",
    "selected_threat_recall",
    "stealth_selection_recall",
)


@dataclass(slots=True, frozen=True)
class CausalEvidenceOutcome:
    strategy: str
    exploration_fraction: float
    budget: int
    selected: int
    exploration_selected: int
    exploitation_selected: int
    forced_exploitation: int
    selected_event_digest: str
    selected_threat_recall: float | None
    selected_precision: float | None
    stealth_selection_recall: float | None
    exploration_threat_share: float | None
    exploration_stealth_selected: int
    pre_recall: float | None
    post_recall: float | None
    recall_delta: float | None
    pre_precision: float | None
    post_precision: float | None
    precision_delta: float | None
    pre_false_positive_rate: float | None
    post_false_positive_rate: float | None
    false_positive_delta: float | None
    pre_stealth_recall: float | None
    post_stealth_recall: float | None
    stealth_recall_delta: float | None
    pre_brier: float | None
    post_brier: float | None
    brier_gain: float | None
    mean_entropy_reduction: float | None
    corrected_errors: int
    introduced_errors: int

    @property
    def net_corrections(self) -> int:
        return self.corrected_errors - self.introduced_errors

    @property
    def net_correction_rate(self) -> float | None:
        return _rate(self.net_corrections, self.selected)

    @property
    def condition(self) -> str:
        return _condition(self.strategy, self.exploration_fraction)

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["condition"] = self.condition
        payload["net_corrections"] = self.net_corrections
        payload["net_correction_rate"] = self.net_correction_rate
        return payload


@dataclass(slots=True, frozen=True)
class CausalEvidenceRun:
    seed: int
    hosts: int
    steps: int
    events: int
    eligible_events: int
    budget: int
    budget_per_1000: float
    sensor_noise: float
    world_digest: str
    outcomes: tuple[CausalEvidenceOutcome, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "hosts": self.hosts,
            "steps": self.steps,
            "events": self.events,
            "eligible_events": self.eligible_events,
            "budget": self.budget,
            "budget_per_1000": self.budget_per_1000,
            "sensor_noise": self.sensor_noise,
            "world_digest": self.world_digest,
            "outcomes": [item.as_dict() for item in self.outcomes],
        }


@dataclass(slots=True, frozen=True)
class ActiveMetricSummary:
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    defined_runs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ActivePairedDelta:
    budget_per_1000: float
    condition: str
    reference: str
    metric: str
    mean: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    direction_agreement: float | None
    pairs: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ActiveConditionSummary:
    budget_per_1000: float
    condition: str
    runs: int
    metrics: dict[str, ActiveMetricSummary]

    def as_dict(self) -> dict[str, object]:
        return {
            "budget_per_1000": self.budget_per_1000,
            "condition": self.condition,
            "runs": self.runs,
            "metrics": {name: value.as_dict() for name, value in self.metrics.items()},
        }


@dataclass(slots=True, frozen=True)
class ReplicatedCausalEvidenceStudy:
    seeds: tuple[int, ...]
    budgets_per_1000: tuple[float, ...]
    exploration_fractions: tuple[float, ...]
    sensor_noise: float
    conditions: tuple[str, ...]
    summaries: dict[float, dict[str, ActiveConditionSummary]]
    paired_vs_random: dict[float, dict[str, dict[str, ActivePairedDelta]]]
    paired_vs_no_exploration: dict[float, dict[str, dict[str, ActivePairedDelta]]]
    absolute_budgets: dict[float, tuple[int, ...]]
    world_digests: dict[int, str]

    @property
    def world_digest(self) -> str:
        digest = sha256()
        for seed in self.seeds:
            digest.update(f"{seed}|{self.world_digests[seed]}\n".encode("utf-8"))
        return digest.hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": self.seeds,
            "budgets_per_1000": self.budgets_per_1000,
            "exploration_fractions": self.exploration_fractions,
            "sensor_noise": self.sensor_noise,
            "conditions": self.conditions,
            "world_digest": self.world_digest,
            "world_digests": {str(seed): digest for seed, digest in self.world_digests.items()},
            "summaries": {
                str(budget): {
                    condition: summary.as_dict() for condition, summary in conditions.items()
                }
                for budget, conditions in self.summaries.items()
            },
            "paired_vs_random": {
                str(budget): {
                    condition: {metric: delta.as_dict() for metric, delta in metrics.items()}
                    for condition, metrics in conditions.items()
                }
                for budget, conditions in self.paired_vs_random.items()
            },
            "paired_vs_no_exploration": {
                str(budget): {
                    condition: {metric: delta.as_dict() for metric, delta in metrics.items()}
                    for condition, metrics in conditions.items()
                }
                for budget, conditions in self.paired_vs_no_exploration.items()
            },
            "absolute_budgets": {
                str(budget): values for budget, values in self.absolute_budgets.items()
            },
        }


def _rate(numerator: int | float, denominator: int | float) -> float | None:
    return numerator / denominator if denominator else None


def _delta(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None:
        return None
    return candidate - baseline


def _condition(strategy: str, exploration_fraction: float) -> str:
    return f"{strategy}@explore={exploration_fraction:.3f}"


def _score(item: _ScoredEvent, strategy: str) -> float:
    if strategy == "risk":
        return item.risk
    if strategy == "novelty":
        return item.novelty
    if strategy == "risk_novelty":
        return item.risk_novelty
    if strategy == "random":
        return item.random_score
    raise ValueError(f"unsupported causal evidence strategy: {strategy}")


def _eligible(item: _ScoredEvent) -> bool:
    event = item.event
    if event is None:
        return True
    return not (event.phase == "warmup" and event.step < NOVELTY_MIN_HISTORY)


def _fallback(strategy: str) -> float:
    if strategy == "risk":
        return 0.43
    if strategy == "novelty":
        return 0.35
    if strategy == "risk_novelty":
        return 0.43
    if strategy == "random":
        return 0.0
    raise ValueError(f"unsupported causal evidence strategy: {strategy}")


def _hybrid_indices(
    scored: list[_ScoredEvent],
    *,
    strategy: str,
    budget: int,
    exploration_fraction: float,
    seed: int,
) -> tuple[list[int], set[int], int]:
    """Causal exact-budget selector with a guaranteed exploration quota.

    Exploration slots are sampled online without replacement using an RNG stream
    independent of risk/novelty tie breaking. Remaining slots use the same exact
    online quantile semantics as the causal attention study.
    """
    if strategy == REFERENCE_STRATEGY:
        indices, forced = online_indices(
            scored,
            budget=budget,
            score=lambda item: item.random_score,
            eligible=_eligible,
            tie_break=lambda item: item.random_score,
            fallback=0.0,
            random_mode=True,
        )
        return indices, set(indices), forced
    if strategy not in DIRECTED_STRATEGIES:
        raise ValueError(f"unsupported causal evidence strategy: {strategy}")
    if not 0.0 <= exploration_fraction <= 1.0:
        raise ValueError("exploration_fraction must be between 0 and 1")

    eligible_items = [(index, item) for index, item in enumerate(scored) if _eligible(item)]
    total = len(eligible_items)
    budget = min(max(int(budget), 0), total)
    if budget == 0:
        return [], set(), 0

    exploration_budget = min(budget, round(budget * exploration_fraction))
    exploitation_budget = budget - exploration_budget
    remaining_explore = exploration_budget
    remaining_exploit = exploitation_budget
    exploration_rng = random.Random(
        derive_seed(seed, f"causal-evidence-explore:{strategy}:{exploration_fraction:.6f}")
    )
    history = OrderStatisticHistory()
    selected: list[int] = []
    explored: set[int] = set()
    forced_exploitation = 0

    for position, (index, item) in enumerate(eligible_items):
        remaining_events = total - position
        explore_here = (
            remaining_explore > 0
            and exploration_rng.random() < remaining_explore / remaining_events
        )
        current_score = _score(item, strategy)

        if explore_here:
            selected.append(index)
            explored.add(index)
            remaining_explore -= 1
        else:
            remaining_nonexplore = remaining_events - remaining_explore
            if remaining_exploit > 0:
                must_take = remaining_exploit >= remaining_nonexplore
                if must_take:
                    take = True
                    forced_exploitation += 1
                else:
                    target_rate = remaining_exploit / remaining_nonexplore
                    threshold = history.threshold(target_rate, _fallback(strategy))
                    if current_score > threshold:
                        take = True
                    elif abs(current_score - threshold) <= 1e-12:
                        take = item.random_score < target_rate
                    else:
                        take = False
                if take:
                    selected.append(index)
                    remaining_exploit -= 1

        history.add(current_score)

    if remaining_explore or remaining_exploit or len(selected) != budget:
        raise RuntimeError("hybrid selector failed to honor exploration/exploitation budget")
    return selected, explored, forced_exploitation


def _identity_digest(events: Iterable[EventContext]) -> str:
    digest = sha256()
    for event in sorted(events, key=lambda item: (item.step, item.host_index)):
        digest.update(f"{event.step}|{event.host_index}\n".encode("utf-8"))
    return digest.hexdigest()


def _world_digest(events: Iterable[EventContext]) -> str:
    digest = sha256()
    for event in events:
        vector = ",".join(f"{value:.12f}" for value in event.observation.vector())
        digest.update(
            (
                f"{event.step}|{event.host_index}|{event.truth_label}|{event.phase}|"
                f"{event.drift_state}|{vector}\n"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def _evaluate(
    scored: list[_ScoredEvent],
    selected_indices: list[int],
    explored_indices: set[int],
    *,
    strategy: str,
    exploration_fraction: float,
    budget: int,
    forced_exploitation: int,
    seed: int,
    sensor_noise: float,
) -> CausalEvidenceOutcome:
    eligible_indices = [index for index, item in enumerate(scored) if _eligible(item)]
    eligible_set = set(eligible_indices)
    selected_set = set(selected_indices)
    if not selected_set <= eligible_set:
        raise RuntimeError("selector chose an ineligible event")

    selected_events = [scored[index].event for index in selected_indices]
    total_threats = sum(scored[index].event.is_threat for index in eligible_indices)
    total_stealth = sum(
        scored[index].event.truth_label == "pathogen:stealth_sim" for index in eligible_indices
    )
    selected_threats = sum(scored[index].event.is_threat for index in selected_indices)
    selected_stealth = sum(
        scored[index].event.truth_label == "pathogen:stealth_sim" for index in selected_indices
    )
    exploration_threats = sum(scored[index].event.is_threat for index in explored_indices)
    exploration_stealth = sum(
        scored[index].event.truth_label == "pathogen:stealth_sim" for index in explored_indices
    )

    pre_tp = pre_fp = pre_fn = 0
    post_tp = post_fp = post_fn = 0
    pre_stealth_tp = post_stealth_tp = 0
    pre_brier_sum = post_brier_sum = 0.0
    entropy_reduction = 0.0
    corrected = introduced = 0

    for index in eligible_indices:
        item = scored[index]
        event = item.event
        target = 1.0 if event.is_threat else 0.0
        before = base_probability(item)
        after = before
        if index in selected_set:
            measurement = second_look_measurement(event, seed=seed, noise=sensor_noise)
            after = posterior_probability(before, measurement)
            entropy_reduction += entropy(before) - entropy(after)

        before_positive = before >= 0.5
        after_positive = after >= 0.5
        before_correct = before_positive == event.is_threat
        after_correct = after_positive == event.is_threat
        if index in selected_set:
            corrected += int(not before_correct and after_correct)
            introduced += int(before_correct and not after_correct)

        if event.is_threat:
            pre_tp += int(before_positive)
            pre_fn += int(not before_positive)
            post_tp += int(after_positive)
            post_fn += int(not after_positive)
        else:
            pre_fp += int(before_positive)
            post_fp += int(after_positive)

        if event.truth_label == "pathogen:stealth_sim":
            pre_stealth_tp += int(before_positive)
            post_stealth_tp += int(after_positive)

        pre_brier_sum += (before - target) ** 2
        post_brier_sum += (after - target) ** 2

    total = len(eligible_indices)
    benign_total = total - total_threats
    pre_precision = _rate(pre_tp, pre_tp + pre_fp)
    post_precision = _rate(post_tp, post_tp + post_fp)
    pre_brier = _rate(pre_brier_sum, total)
    post_brier = _rate(post_brier_sum, total)

    return CausalEvidenceOutcome(
        strategy=strategy,
        exploration_fraction=float(exploration_fraction),
        budget=budget,
        selected=len(selected_indices),
        exploration_selected=len(explored_indices),
        exploitation_selected=len(selected_indices) - len(explored_indices),
        forced_exploitation=forced_exploitation,
        selected_event_digest=_identity_digest(selected_events),
        selected_threat_recall=_rate(selected_threats, total_threats),
        selected_precision=_rate(selected_threats, len(selected_indices)),
        stealth_selection_recall=_rate(selected_stealth, total_stealth),
        exploration_threat_share=_rate(exploration_threats, len(explored_indices)),
        exploration_stealth_selected=exploration_stealth,
        pre_recall=_rate(pre_tp, total_threats),
        post_recall=_rate(post_tp, total_threats),
        recall_delta=_delta(_rate(post_tp, total_threats), _rate(pre_tp, total_threats)),
        pre_precision=pre_precision,
        post_precision=post_precision,
        precision_delta=_delta(post_precision, pre_precision),
        pre_false_positive_rate=_rate(pre_fp, benign_total),
        post_false_positive_rate=_rate(post_fp, benign_total),
        false_positive_delta=_delta(_rate(post_fp, benign_total), _rate(pre_fp, benign_total)),
        pre_stealth_recall=_rate(pre_stealth_tp, total_stealth),
        post_stealth_recall=_rate(post_stealth_tp, total_stealth),
        stealth_recall_delta=_delta(
            _rate(post_stealth_tp, total_stealth),
            _rate(pre_stealth_tp, total_stealth),
        ),
        pre_brier=pre_brier,
        post_brier=post_brier,
        brier_gain=_delta(pre_brier, post_brier),
        mean_entropy_reduction=_rate(entropy_reduction, len(selected_indices)),
        corrected_errors=corrected,
        introduced_errors=introduced,
    )


def run_causal_evidence_budget(
    *,
    hosts: int = 100,
    steps: int = 300,
    seed: int = 7,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    budget_per_1000: float = 12.0,
    exploration_fractions: Iterable[float] = (0.0, 0.05, 0.10, 0.20),
    sensor_noise: float = 0.18,
) -> CausalEvidenceRun:
    if budget_per_1000 < 0:
        raise ValueError("budget_per_1000 must be non-negative")
    fractions = tuple(float(value) for value in exploration_fractions)
    if not fractions:
        raise ValueError("provide at least one exploration fraction")
    if len(fractions) > 20 or len(set(fractions)) != len(fractions):
        raise ValueError("exploration fractions must be unique and limited to 20")
    if any(not 0.0 <= value <= 1.0 for value in fractions):
        raise ValueError("exploration fractions must be between 0 and 1")
    fractions = tuple(sorted(fractions))

    events: list[EventContext] = []
    run_simulation(
        hosts=hosts,
        steps=steps,
        seed=seed,
        threat_rate=threat_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        drift_step=drift_step,
        drift_fraction=drift_fraction,
        drift_magnitude=drift_magnitude,
        on_event=events.append,
    )
    scored = _score_events(events, derive_seed(seed, "causal-attention-scores"))
    eligible_events = sum(_eligible(item) for item in scored)
    requested_budget = round(len(events) * budget_per_1000 / 1000.0)
    budget = min(eligible_events, max(0, requested_budget))

    outcomes: list[CausalEvidenceOutcome] = []
    random_indices, random_explored, random_forced = _hybrid_indices(
        scored,
        strategy=REFERENCE_STRATEGY,
        budget=budget,
        exploration_fraction=0.0,
        seed=seed,
    )
    outcomes.append(
        _evaluate(
            scored,
            random_indices,
            random_explored,
            strategy=REFERENCE_STRATEGY,
            exploration_fraction=0.0,
            budget=budget,
            forced_exploitation=random_forced,
            seed=seed,
            sensor_noise=sensor_noise,
        )
    )

    for strategy in DIRECTED_STRATEGIES:
        for fraction in fractions:
            indices, explored, forced = _hybrid_indices(
                scored,
                strategy=strategy,
                budget=budget,
                exploration_fraction=fraction,
                seed=seed,
            )
            outcomes.append(
                _evaluate(
                    scored,
                    indices,
                    explored,
                    strategy=strategy,
                    exploration_fraction=fraction,
                    budget=budget,
                    forced_exploitation=forced,
                    seed=seed,
                    sensor_noise=sensor_noise,
                )
            )

    return CausalEvidenceRun(
        seed=seed,
        hosts=hosts,
        steps=steps,
        events=len(events),
        eligible_events=eligible_events,
        budget=budget,
        budget_per_1000=float(budget_per_1000),
        sensor_noise=float(sensor_noise),
        world_digest=_world_digest(events),
        outcomes=tuple(outcomes),
    )


def _metric(outcome: CausalEvidenceOutcome, name: str) -> float | None:
    if name == "net_correction_rate":
        return outcome.net_correction_rate
    value = getattr(outcome, name)
    return None if value is None else float(value)


def _summary(values: list[float]) -> ActiveMetricSummary:
    if not values:
        return ActiveMetricSummary(None, None, None, None, 0)
    return ActiveMetricSummary(
        mean=mean(values),
        stdev=pstdev(values) if len(values) > 1 else 0.0,
        minimum=min(values),
        maximum=max(values),
        defined_runs=len(values),
    )


def _direction_agreement(values: list[float]) -> float | None:
    if not values:
        return None
    avg = mean(values)
    if abs(avg) < 1e-12:
        return sum(abs(value) < 1e-12 for value in values) / len(values)
    if avg > 0:
        return sum(value > 0 for value in values) / len(values)
    return sum(value < 0 for value in values) / len(values)


def _paired_delta(
    *,
    budget: float,
    condition: str,
    reference: str,
    metric: str,
    candidates: list[CausalEvidenceOutcome],
    baselines: list[CausalEvidenceOutcome],
) -> ActivePairedDelta:
    values: list[float] = []
    for candidate, baseline in zip(candidates, baselines):
        candidate_value = _metric(candidate, metric)
        baseline_value = _metric(baseline, metric)
        if candidate_value is None or baseline_value is None:
            continue
        values.append(candidate_value - baseline_value)
    summary = _summary(values)
    return ActivePairedDelta(
        budget_per_1000=budget,
        condition=condition,
        reference=reference,
        metric=metric,
        mean=summary.mean,
        stdev=summary.stdev,
        minimum=summary.minimum,
        maximum=summary.maximum,
        direction_agreement=_direction_agreement(values),
        pairs=len(values),
    )


def run_replicated_causal_evidence_study(
    *,
    seeds: Iterable[int] = (101, 127, 149, 173, 199),
    budgets_per_1000: Iterable[float] = (5.0, 12.0, 20.0),
    exploration_fractions: Iterable[float] = (0.0, 0.05, 0.10, 0.20),
    hosts: int = 100,
    steps: int = 300,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    sensor_noise: float = 0.18,
) -> ReplicatedCausalEvidenceStudy:
    seed_tuple = tuple(int(seed) for seed in seeds)
    budget_tuple = tuple(float(value) for value in budgets_per_1000)
    fraction_tuple = tuple(sorted(float(value) for value in exploration_fractions))
    if not seed_tuple or len(seed_tuple) > 50 or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be non-empty, unique, and limited to 50")
    if not budget_tuple or len(budget_tuple) > 20 or len(set(budget_tuple)) != len(budget_tuple):
        raise ValueError("budgets must be non-empty, unique, and limited to 20")
    if any(value < 0 for value in budget_tuple):
        raise ValueError("budgets must be non-negative")
    if (
        not fraction_tuple
        or len(fraction_tuple) > 20
        or len(set(fraction_tuple)) != len(fraction_tuple)
    ):
        raise ValueError("exploration fractions must be non-empty, unique, and limited to 20")
    if any(not 0.0 <= value <= 1.0 for value in fraction_tuple):
        raise ValueError("exploration fractions must be between 0 and 1")

    conditions = (_condition(REFERENCE_STRATEGY, 0.0),) + tuple(
        _condition(strategy, fraction)
        for strategy in DIRECTED_STRATEGIES
        for fraction in fraction_tuple
    )
    by_budget: dict[float, dict[str, list[CausalEvidenceOutcome]]] = {
        budget: {condition: [] for condition in conditions} for budget in budget_tuple
    }
    absolute_budgets: dict[float, list[int]] = {budget: [] for budget in budget_tuple}
    world_digests: dict[int, str] = {}

    for budget in budget_tuple:
        for seed in seed_tuple:
            run = run_causal_evidence_budget(
                hosts=hosts,
                steps=steps,
                seed=seed,
                threat_rate=threat_rate,
                poison_fraction=poison_fraction,
                heterogeneity=heterogeneity,
                drift_step=drift_step,
                drift_fraction=drift_fraction,
                drift_magnitude=drift_magnitude,
                budget_per_1000=budget,
                exploration_fractions=fraction_tuple,
                sensor_noise=sensor_noise,
            )
            prior_digest = world_digests.setdefault(seed, run.world_digest)
            if prior_digest != run.world_digest:
                raise RuntimeError("budget changed the synthetic world")
            absolute_budgets[budget].append(run.budget)
            current = {outcome.condition: outcome for outcome in run.outcomes}
            if tuple(current) != conditions:
                raise RuntimeError("causal evidence condition set changed across paired runs")
            if {outcome.selected for outcome in run.outcomes} != {run.budget}:
                raise RuntimeError("causal evidence conditions did not receive equal capacity")
            for condition in conditions:
                by_budget[budget][condition].append(current[condition])

    summaries: dict[float, dict[str, ActiveConditionSummary]] = {}
    paired_random: dict[float, dict[str, dict[str, ActivePairedDelta]]] = {}
    paired_exploration: dict[float, dict[str, dict[str, ActivePairedDelta]]] = {}
    random_condition = _condition(REFERENCE_STRATEGY, 0.0)

    for budget in budget_tuple:
        summaries[budget] = {}
        for condition, outcomes in by_budget[budget].items():
            metrics = {
                metric: _summary(
                    [
                        value
                        for outcome in outcomes
                        if (value := _metric(outcome, metric)) is not None
                    ]
                )
                for metric in ACTIVE_METRICS
            }
            summaries[budget][condition] = ActiveConditionSummary(
                budget_per_1000=budget,
                condition=condition,
                runs=len(outcomes),
                metrics=metrics,
            )

        paired_random[budget] = {}
        random_rows = by_budget[budget][random_condition]
        for condition in conditions:
            if condition == random_condition:
                continue
            rows = by_budget[budget][condition]
            paired_random[budget][condition] = {
                metric: _paired_delta(
                    budget=budget,
                    condition=condition,
                    reference=random_condition,
                    metric=metric,
                    candidates=rows,
                    baselines=random_rows,
                )
                for metric in ACTIVE_METRICS
            }

        paired_exploration[budget] = {}
        for strategy in DIRECTED_STRATEGIES:
            baseline_condition = _condition(strategy, 0.0)
            if baseline_condition not in by_budget[budget]:
                continue
            baseline_rows = by_budget[budget][baseline_condition]
            for fraction in fraction_tuple:
                condition = _condition(strategy, fraction)
                if fraction == 0.0:
                    continue
                rows = by_budget[budget][condition]
                paired_exploration[budget][condition] = {
                    metric: _paired_delta(
                        budget=budget,
                        condition=condition,
                        reference=baseline_condition,
                        metric=metric,
                        candidates=rows,
                        baselines=baseline_rows,
                    )
                    for metric in ACTIVE_METRICS
                }

    return ReplicatedCausalEvidenceStudy(
        seeds=seed_tuple,
        budgets_per_1000=budget_tuple,
        exploration_fractions=fraction_tuple,
        sensor_noise=float(sensor_noise),
        conditions=conditions,
        summaries=summaries,
        paired_vs_random=paired_random,
        paired_vs_no_exploration=paired_exploration,
        absolute_budgets={budget: tuple(values) for budget, values in absolute_budgets.items()},
        world_digests=world_digests,
    )
