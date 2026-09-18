from __future__ import annotations

from dataclasses import dataclass
import math
import random
from statistics import mean

from symbiont.sensory import SensorySystem, TransductionKind
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

from .sensory_specialisation import SensoryProtocolResult


def _reading(source_id: str, value: float) -> SensorReading:
    return SensorReading(
        capability_id=source_id,
        source="synthetic-evaluator",
        value=float(value),
        unit=Unit.RATIO,
        monotonic_timestamp_ns=0,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def _fit_affine(xs: list[float], ys: list[float]) -> tuple[float, float]:
    if len(xs) != len(ys) or len(xs) < 4:
        raise ValueError("affine fit requires at least four paired observations")
    mx = mean(xs)
    my = mean(ys)
    variance = sum((x - mx) ** 2 for x in xs)
    if variance <= 1e-12:
        return 0.0, my
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / variance
    return slope, my - slope * mx


def _holdout_mae(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 24:
        raise ValueError("holdout MAE requires at least 24 paired observations")
    split = max(8, int(len(xs) * 0.67))
    slope, intercept = _fit_affine(xs[:split], ys[:split])
    predictions = [intercept + slope * value for value in xs[split:]]
    return mean(abs(prediction - target) for prediction, target in zip(predictions, ys[split:]))


@dataclass(slots=True)
class CandidatePool:
    system: SensorySystem
    candidate_ids: tuple[str, ...]
    roles: dict[str, str]
    frozen_id: str
    random_id: str


def _candidate_pool(seed: int) -> CandidatePool:
    system = SensorySystem(plasticity_enabled=True)
    system.transduce(
        [_reading("source.driver", 0.0), _reading("source.outcome", 0.0)],
        percept_names={"source.driver": "signal.driver", "source.outcome": "signal.outcome"},
        tick=1,
    )
    driver_identity = next(
        sensor for sensor in system.sensors
        if sensor.sensor_id.startswith("sensor.identity.")
        and sensor.source_ids == ("source.driver",)
    )

    specs = [
        ("difference", "modality.alpha", TransductionKind.DIFFERENCE),
        ("integrate", "modality.beta", TransductionKind.INTEGRATE),
        ("threshold", "modality.alpha", TransductionKind.THRESHOLD),
    ]
    order_rng = random.Random(seed + 40_001)
    order_rng.shuffle(specs)

    roles: dict[str, str] = {}
    created: list[str] = []
    for role, modality, transduction in specs:
        sensor = system.duplicate(
            driver_identity.sensor_id,
            modality_id=modality,
            transduction=transduction,
            tick=1,
        )
        # Candidate order must not secretly change the functional hypothesis.
        sensor.gain = 1.0
        if transduction is TransductionKind.INTEGRATE:
            sensor.decay = 0.85
        if transduction is TransductionKind.THRESHOLD:
            sensor.threshold = 0.0
        roles[sensor.sensor_id] = role
        created.append(sensor.sensor_id)

    frozen_id = created[0]
    random_id = random.Random(seed + 90_001).choice(created)
    return CandidatePool(
        system=system,
        candidate_ids=tuple(created),
        roles=roles,
        frozen_id=frozen_id,
        random_id=random_id,
    )


def _preferred(pool: CandidatePool) -> str:
    candidates = [
        sensor for sensor in pool.system.sensors if sensor.sensor_id in pool.candidate_ids
    ]
    return max(
        candidates,
        key=lambda sensor: (
            sensor.utility,
            pool.system.selection_credits.get(sensor.sensor_id, 0.0),
            -sensor.transduction_cost,
            sensor.sensor_id,
        ),
    ).sensor_id


def _candidate_utilities(pool: CandidatePool) -> dict[str, float]:
    return {
        pool.roles[sensor.sensor_id]: sensor.utility
        for sensor in pool.system.sensors
        if sensor.sensor_id in pool.candidate_ids
    }


def run_autonomous_sensory_selection(seed: int = 101, *, samples: int = 192) -> dict[str, object]:
    if samples < 128:
        raise ValueError("samples must be at least 128")
    rng = random.Random(seed)
    pool = _candidate_pool(seed)

    previous_driver = 0.0
    previous_previous_driver = 0.0
    previous_outputs: dict[str, float] = {}
    xs: dict[str, list[float]] = {sensor_id: [] for sensor_id in pool.candidate_ids}
    ys: list[float] = []

    for tick in range(2, samples + 2):
        driver = previous_driver + rng.gauss(0.0, 0.35)
        outcome = previous_driver - previous_previous_driver
        percepts = pool.system.transduce(
            [_reading("source.driver", driver), _reading("source.outcome", outcome)],
            percept_names={"source.driver": "signal.driver", "source.outcome": "signal.outcome"},
            tick=tick,
        )
        pool.system.update_downstream_utility({})
        by_sensor = {
            percept.sensor_id: float(percept.value)
            for percept in percepts
            if percept.sensor_id is not None and percept.value is not None
        }
        if previous_outputs:
            for sensor_id in pool.candidate_ids:
                if sensor_id in previous_outputs:
                    xs[sensor_id].append(previous_outputs[sensor_id])
            ys.append(outcome)
        previous_outputs = {
            sensor_id: by_sensor[sensor_id]
            for sensor_id in pool.candidate_ids
            if sensor_id in by_sensor
        }
        previous_previous_driver = previous_driver
        previous_driver = driver

    evaluator_mae = {
        sensor_id: _holdout_mae(values, ys[: len(values)])
        for sensor_id, values in xs.items()
    }
    selected_id = _preferred(pool)
    best_id = min(evaluator_mae, key=evaluator_mae.get)

    return {
        "seed": seed,
        "samples": samples,
        "selected_sensor_id": selected_id,
        "selected_role": pool.roles[selected_id],
        "evaluator_best_sensor_id": best_id,
        "evaluator_best_role": pool.roles[best_id],
        "selection_matches_best": selected_id == best_id,
        "selected_mae": evaluator_mae[selected_id],
        "best_mae": evaluator_mae[best_id],
        "frozen_role": pool.roles[pool.frozen_id],
        "frozen_mae": evaluator_mae[pool.frozen_id],
        "random_role": pool.roles[pool.random_id],
        "random_mae": evaluator_mae[pool.random_id],
        "beats_frozen": evaluator_mae[selected_id] < evaluator_mae[pool.frozen_id] - 1e-9,
        "beats_random": evaluator_mae[selected_id] < evaluator_mae[pool.random_id] - 1e-9,
        "utilities": _candidate_utilities(pool),
        "selection_credits": {
            pool.roles[sensor_id]: pool.system.selection_credits.get(sensor_id, 0.0)
            for sensor_id in pool.candidate_ids
        },
    }


def run_sensory_regime_reversal(seed: int = 101, *, samples: int = 320) -> dict[str, object]:
    if samples < 256:
        raise ValueError("samples must be at least 256")
    shift_tick = 128
    rng = random.Random(seed)
    pool = _candidate_pool(seed)

    previous_driver = 0.0
    previous_previous_driver = 0.0
    slow_state = 0.0
    previous_slow_state = 0.0
    preference_before: str | None = None
    preference_after: str | None = None
    first_integrate_tick: int | None = None

    for tick in range(2, samples + 2):
        driver = previous_driver + rng.gauss(0.0, 0.35)
        slow_state = 0.85 * slow_state + 0.15 * driver
        protocol_tick = tick - 1
        if protocol_tick <= shift_tick:
            outcome = previous_driver - previous_previous_driver
        else:
            outcome = previous_slow_state

        pool.system.transduce(
            [_reading("source.driver", driver), _reading("source.outcome", outcome)],
            percept_names={"source.driver": "signal.driver", "source.outcome": "signal.outcome"},
            tick=tick,
        )
        pool.system.update_downstream_utility({})
        preferred_id = _preferred(pool)
        preferred_role = pool.roles[preferred_id]
        if protocol_tick == shift_tick:
            preference_before = preferred_role
        if protocol_tick > shift_tick and preferred_role == "integrate" and first_integrate_tick is None:
            first_integrate_tick = protocol_tick

        previous_previous_driver = previous_driver
        previous_driver = driver
        previous_slow_state = slow_state

    preference_after = pool.roles[_preferred(pool)]
    return {
        "seed": seed,
        "samples": samples,
        "shift_tick": shift_tick,
        "preference_before": preference_before,
        "preference_after": preference_after,
        "first_integrate_tick": first_integrate_tick,
        "switch_delay": (
            None if first_integrate_tick is None
            else first_integrate_tick - shift_tick
        ),
        "switched_delta_to_integrate": (
            preference_before == "difference" and preference_after == "integrate"
        ),
        "final_utilities": _candidate_utilities(pool),
        "final_selection_credits": {
            pool.roles[sensor_id]: pool.system.selection_credits.get(sensor_id, 0.0)
            for sensor_id in pool.candidate_ids
        },
    }


def run_sensory_null_selection(seed: int = 101, *, samples: int = 256) -> dict[str, object]:
    if samples < 192:
        raise ValueError("samples must be at least 192")
    driver_rng = random.Random(seed)
    outcome_rng = random.Random(seed + 1_000_003)
    pool = _candidate_pool(seed)

    for tick in range(2, samples + 2):
        driver = driver_rng.gauss(0.0, 1.0)
        outcome = outcome_rng.gauss(0.0, 1.0)
        pool.system.transduce(
            [_reading("source.driver", driver), _reading("source.outcome", outcome)],
            percept_names={"source.driver": "signal.driver", "source.outcome": "signal.outcome"},
            tick=tick,
        )
        pool.system.update_downstream_utility({})

    utilities = _candidate_utilities(pool)
    credits = {
        pool.roles[sensor_id]: pool.system.selection_credits.get(sensor_id, 0.0)
        for sensor_id in pool.candidate_ids
    }
    max_utility = max(utilities.values(), default=0.0)
    max_credit = max(credits.values(), default=0.0)
    return {
        "seed": seed,
        "samples": samples,
        "utilities": utilities,
        "selection_credits": credits,
        "max_utility": max_utility,
        "max_selection_credit": max_credit,
        "no_strong_false_specialisation": max_utility < 0.25 and max_credit < 0.25,
    }


def run_experience_conditioned_phenotype(seed: int = 101, *, samples: int = 256) -> dict[str, object]:
    if samples < 192:
        raise ValueError("samples must be at least 192")
    world_rng = random.Random(seed)
    latent: list[tuple[float, float]] = []
    previous = 0.0
    previous_previous = 0.0
    slow = 0.0
    previous_slow = 0.0
    for _ in range(samples):
        driver = previous + world_rng.gauss(0.0, 0.30)
        slow = 0.85 * slow + 0.15 * driver
        # Deliberately near-balanced: neither fast nor slow structure is
        # labelled as preferred by the world definition.
        outcome = 0.5 * (previous - previous_previous) + 0.5 * previous_slow
        latent.append((driver, outcome))
        previous_previous = previous
        previous = driver
        previous_slow = slow

    preferred_roles: list[str] = []
    utility_vectors: list[dict[str, float]] = []
    for organism_index in range(6):
        pool = _candidate_pool(seed)
        experience_rng = random.Random(seed + 70_000 + organism_index)
        for tick, (driver, outcome) in enumerate(latent, start=2):
            perceived_driver = driver + experience_rng.gauss(0.0, 0.035)
            perceived_outcome = outcome + experience_rng.gauss(0.0, 0.035)
            pool.system.transduce(
                [
                    _reading("source.driver", perceived_driver),
                    _reading("source.outcome", perceived_outcome),
                ],
                percept_names={"source.driver": "signal.driver", "source.outcome": "signal.outcome"},
                tick=tick,
            )
            pool.system.update_downstream_utility({})
        preferred_roles.append(pool.roles[_preferred(pool)])
        utility_vectors.append(_candidate_utilities(pool))

    unique_roles = sorted(set(preferred_roles))
    return {
        "seed": seed,
        "samples": samples,
        "organisms": len(preferred_roles),
        "preferred_roles": preferred_roles,
        "unique_preferred_roles": unique_roles,
        "unique_role_count": len(unique_roles),
        "diverged": len(unique_roles) > 1,
        "converged": len(unique_roles) == 1,
        "utility_vectors": utility_vectors,
    }


def run_autonomous_sensory_selection_study(
    seeds=(101, 127, 149), steps: int = 192
) -> SensoryProtocolResult:
    runs = tuple(run_autonomous_sensory_selection(int(seed), samples=max(128, steps)) for seed in seeds)
    return SensoryProtocolResult(
        "perception.autonomous-sensory-selection",
        tuple(int(seed) for seed in seeds),
        runs,
        {
            "all_match_evaluator_best": all(bool(run["selection_matches_best"]) for run in runs),
            "all_beat_random": all(bool(run["beats_random"]) for run in runs),
            "beat_frozen_runs": sum(bool(run["beats_frozen"]) for run in runs),
        },
    )


def run_sensory_regime_reversal_study(
    seeds=(101, 127, 149), steps: int = 320
) -> SensoryProtocolResult:
    runs = tuple(run_sensory_regime_reversal(int(seed), samples=max(256, steps)) for seed in seeds)
    return SensoryProtocolResult(
        "perception.sensory-regime-reversal",
        tuple(int(seed) for seed in seeds),
        runs,
        {
            "all_switched": all(bool(run["switched_delta_to_integrate"]) for run in runs),
            "max_switch_delay": max(
                (int(run["switch_delay"]) for run in runs if run["switch_delay"] is not None),
                default=None,
            ),
        },
    )


def run_sensory_null_selection_study(
    seeds=(101, 127, 149), steps: int = 256
) -> SensoryProtocolResult:
    runs = tuple(run_sensory_null_selection(int(seed), samples=max(192, steps)) for seed in seeds)
    return SensoryProtocolResult(
        "perception.sensory-null-selection",
        tuple(int(seed) for seed in seeds),
        runs,
        {
            "all_reject_false_specialisation": all(
                bool(run["no_strong_false_specialisation"]) for run in runs
            ),
        },
    )


def run_experience_conditioned_phenotype_study(
    seeds=(101, 127, 149), steps: int = 256
) -> SensoryProtocolResult:
    runs = tuple(run_experience_conditioned_phenotype(int(seed), samples=max(192, steps)) for seed in seeds)
    return SensoryProtocolResult(
        "perception.experience-conditioned-phenotype",
        tuple(int(seed) for seed in seeds),
        runs,
        {
            "diverged_runs": sum(bool(run["diverged"]) for run in runs),
            "converged_runs": sum(bool(run["converged"]) for run in runs),
        },
    )
