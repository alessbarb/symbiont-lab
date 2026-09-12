from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from math import exp, log
import random

from .budget import _ScoredEvent, _score_events
from .rng import derive_seed
from .simulation import EventContext, run_simulation


@dataclass(slots=True, frozen=True)
class SecondLookOutcome:
    strategy: str
    selected: int
    selected_event_digest: str
    investigations_per_1000: float
    selected_threat_share: float | None
    pre_brier: float | None
    post_brier: float | None
    brier_gain: float | None
    mean_entropy_reduction: float | None
    corrected_errors: int
    introduced_errors: int
    stealth_selected: int
    stealth_corrected: int
    mean_measurement: float | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class SecondLookStudy:
    seed: int
    hosts: int
    steps: int
    budget: int
    budget_per_1000: float
    sensor_noise: float
    world_digest: str
    outcomes: tuple[SecondLookOutcome, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "hosts": self.hosts,
            "steps": self.steps,
            "budget": self.budget,
            "budget_per_1000": self.budget_per_1000,
            "sensor_noise": self.sensor_noise,
            "world_digest": self.world_digest,
            "outcomes": [item.as_dict() for item in self.outcomes],
        }


def _clamp(value: float, low: float = 1e-6, high: float = 1.0 - 1e-6) -> float:
    return min(high, max(low, value))


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + exp(-value))
    ev = exp(value)
    return ev / (1.0 + ev)


def _logit(probability: float) -> float:
    probability = _clamp(probability)
    return log(probability / (1.0 - probability))


def _entropy(probability: float) -> float:
    probability = _clamp(probability)
    return -probability * log(probability) - (1.0 - probability) * log(1.0 - probability)


def _base_probability(item: _ScoredEvent) -> float:
    score = 0.82 * item.risk + 0.18 * item.novelty
    return _sigmoid((score - 0.43) * 7.0)


def _relevance(item: _ScoredEvent) -> float:
    obs = item.event.observation
    return min(
        1.0,
        0.15 * obs.cpu
        + 0.15 * obs.network
        + 0.35 * obs.file_changes
        + 0.10 * obs.new_processes
        + 0.25 * obs.persistence_changes,
    )


def _shadow_curiosity(item: _ScoredEvent) -> float:
    probability = _base_probability(item)
    ambiguity = 1.0 - abs(probability - 0.5) * 2.0
    return item.novelty * item.novelty * max(ambiguity, 0.0) * max(_relevance(item), 0.05)


_SENSOR_MEANS = {
    "benign:normal": 0.24,
    "benign:update": 0.42,
    "benign:backup": 0.40,
    "benign:build": 0.46,
    "pathogen:ransom_sim": 0.76,
    "pathogen:bot_sim": 0.72,
    "pathogen:stealth_sim": 0.66,
}


def second_look_measurement(event: EventContext, *, seed: int, noise: float = 0.18) -> float:
    """Return one noisy synthetic auxiliary measurement.

    The simulator uses the latent synthetic family only to generate an overlapping
    sensor distribution. The returned scalar contains no label and is never fed
    to an agent. Noise is derived per event, so selection order cannot change
    measurements.
    """
    mean = _SENSOR_MEANS.get(event.truth_label, 0.50)
    rng = random.Random(
        derive_seed(seed, f"second-look:{event.step}:{event.host_index}")
    )
    return min(1.0, max(0.0, rng.gauss(mean, max(0.01, float(noise)))))


def _posterior_probability(base_probability: float, measurement: float) -> float:
    sensor_probability = _sigmoid((measurement - 0.50) * 4.0)
    posterior_log_odds = _logit(base_probability) + 0.70 * _logit(sensor_probability)
    return _clamp(_sigmoid(posterior_log_odds), 0.02, 0.98)


def _selection_key(strategy: str, item: _ScoredEvent) -> float:
    if strategy == "risk":
        return item.risk
    if strategy == "novelty":
        return item.novelty
    if strategy == "risk_novelty":
        return item.risk_novelty
    if strategy == "shadow_curiosity":
        return _shadow_curiosity(item)
    if strategy == "random":
        return item.random_score
    raise ValueError(f"unsupported second-look selector: {strategy}")


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _identity_digest(events: list[EventContext]) -> str:
    digest = sha256()
    for step, host_index in sorted((event.step, event.host_index) for event in events):
        digest.update(f"{step}|{host_index}\n".encode())
    return digest.hexdigest()


def _world_digest(events: list[EventContext]) -> str:
    digest = sha256()
    for event in events:
        vector = ",".join(f"{value:.12f}" for value in event.observation.vector())
        digest.update(
            (
                f"{event.step}|{event.host_index}|{event.truth_label}|{event.phase}|"
                f"{event.drift_state}|{vector}\n"
            ).encode()
        )
    return digest.hexdigest()


def _evaluate_selection(
    strategy: str,
    scored: list[_ScoredEvent],
    budget: int,
    *,
    seed: int,
    noise: float,
) -> SecondLookOutcome:
    budget = min(max(int(budget), 0), len(scored))
    ranked = sorted(
        scored,
        key=lambda item: (
            _selection_key(strategy, item),
            -item.event.step,
            -item.event.host_index,
        ),
        reverse=True,
    )
    selected = ranked[:budget]
    selected_events = [item.event for item in selected]
    selected_digest = _identity_digest(selected_events)
    if not selected:
        return SecondLookOutcome(
            strategy=strategy,
            selected=0,
            selected_event_digest=selected_digest,
            investigations_per_1000=0.0,
            selected_threat_share=None,
            pre_brier=None,
            post_brier=None,
            brier_gain=None,
            mean_entropy_reduction=None,
            corrected_errors=0,
            introduced_errors=0,
            stealth_selected=0,
            stealth_corrected=0,
            mean_measurement=None,
        )

    pre_brier = 0.0
    post_brier = 0.0
    entropy_reduction = 0.0
    corrected = 0
    introduced = 0
    stealth_selected = 0
    stealth_corrected = 0
    threats = 0
    measurement_sum = 0.0

    for item in selected:
        event = item.event
        target = 1.0 if event.is_threat else 0.0
        before = _base_probability(item)
        measurement = second_look_measurement(event, seed=seed, noise=noise)
        after = _posterior_probability(before, measurement)
        before_correct = (before >= 0.5) == event.is_threat
        after_correct = (after >= 0.5) == event.is_threat

        threats += int(event.is_threat)
        pre_brier += (before - target) ** 2
        post_brier += (after - target) ** 2
        entropy_reduction += _entropy(before) - _entropy(after)
        measurement_sum += measurement
        corrected += int(not before_correct and after_correct)
        introduced += int(before_correct and not after_correct)

        if event.truth_label == "pathogen:stealth_sim":
            stealth_selected += 1
            stealth_corrected += int(not before_correct and after_correct)

    count = len(selected)
    pre = pre_brier / count
    post = post_brier / count
    return SecondLookOutcome(
        strategy=strategy,
        selected=count,
        selected_event_digest=selected_digest,
        investigations_per_1000=1000.0 * count / max(len(scored), 1),
        selected_threat_share=_rate(threats, count),
        pre_brier=pre,
        post_brier=post,
        brier_gain=pre - post,
        mean_entropy_reduction=entropy_reduction / count,
        corrected_errors=corrected,
        introduced_errors=introduced,
        stealth_selected=stealth_selected,
        stealth_corrected=stealth_corrected,
        mean_measurement=measurement_sum / count,
    )


def run_second_look_study(
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
    budget: int | None = None,
    sensor_noise: float = 0.18,
) -> SecondLookStudy:
    events: list[EventContext] = []
    result, _ = run_simulation(
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
    scored = _score_events(events, seed)
    resolved_budget = result.investigated if budget is None else int(budget)
    resolved_budget = min(max(resolved_budget, 0), len(events))

    strategies = (
        "risk",
        "novelty",
        "risk_novelty",
        "shadow_curiosity",
        "random",
    )
    outcomes = tuple(
        _evaluate_selection(
            strategy,
            scored,
            resolved_budget,
            seed=seed,
            noise=sensor_noise,
        )
        for strategy in strategies
    )
    return SecondLookStudy(
        seed=seed,
        hosts=hosts,
        steps=steps,
        budget=resolved_budget,
        budget_per_1000=1000.0 * resolved_budget / max(len(events), 1),
        sensor_noise=float(sensor_noise),
        world_digest=_world_digest(events),
        outcomes=outcomes,
    )
