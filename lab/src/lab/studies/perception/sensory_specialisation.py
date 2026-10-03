from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from statistics import mean

from symbiont.host.readings import (
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
)
from symbiont.sensory import SensorySystem


@dataclass(slots=True, frozen=True)
class IdentityEquivalenceResult:
    samples: int
    max_absolute_error: float
    sensor_count: int

    @property
    def equivalent(self) -> bool:
        return self.max_absolute_error <= 1e-12 and self.sensor_count == 1

    def as_dict(self) -> dict[str, object]:
        return asdict(self) | {"equivalent": self.equivalent}


@dataclass(slots=True, frozen=True)
class DeltaDiscoveryResult:
    seed: int
    samples: int
    identity_mae: float
    specialised_mae: float
    improvement: float
    specialised_sensor_id: str
    modality_id: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class TemporalSpecialisationResult:
    seed: int
    samples: int
    alpha_fast_mae: float
    beta_fast_mae: float
    alpha_slow_mae: float
    beta_slow_mae: float
    fast_specialisation_gain: float
    slow_specialisation_gain: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _reading(value: float, *, source_id: str = "source.opaque") -> SensorReading:
    return SensorReading(
        capability_id=source_id,
        source="synthetic-evaluator",
        value=float(value),
        unit=Unit.RATIO,
        monotonic_timestamp_ns=0,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def _mae(predictions: list[float], targets: list[float]) -> float:
    if len(predictions) != len(targets) or not predictions:
        raise ValueError("MAE requires equal non-empty vectors")
    return mean(abs(a - b) for a, b in zip(predictions, targets))


def run_identity_equivalence(samples: int = 64) -> IdentityEquivalenceResult:
    if samples < 2:
        raise ValueError("samples must be at least 2")
    system = SensorySystem(plasticity_enabled=False)
    errors: list[float] = []
    for tick in range(1, samples + 1):
        value = math.sin(tick / 7.0) + 0.1 * math.cos(tick / 3.0)
        percepts = system.transduce(
            [_reading(value)],
            percept_names={"source.opaque": "signal.opaque"},
            tick=tick,
        )
        errors.append(abs(float(percepts[0].value) - value))
    return IdentityEquivalenceResult(
        samples=samples,
        max_absolute_error=max(errors),
        sensor_count=len(system.sensors),
    )


def run_adaptive_delta_discovery(
    seed: int = 101,
    *,
    samples: int = 96,
) -> DeltaDiscoveryResult:
    """Evaluator-side characterization of a receptor discovered by bounded exploration.

    The evaluator target is never supplied to SensorySystem.  The organism-side
    mechanism only sees the source history and its own developmental clock.
    """
    if samples < 32:
        raise ValueError("samples must be at least 32")
    rng = random.Random(seed)
    system = SensorySystem(plasticity_enabled=True)
    value = 0.0
    previous = None
    identity_predictions: list[float] = []
    specialised_predictions: list[float] = []
    targets: list[float] = []
    specialised_id: str | None = None
    identity_id: str | None = None
    modality_id = ""

    for tick in range(1, samples + 1):
        value += rng.gauss(0.0, 0.35)
        percepts = system.transduce(
            [_reading(value)],
            percept_names={"source.opaque": "signal.opaque"},
            tick=tick,
        )
        if identity_id is None:
            identity_id = next(
                sensor.sensor_id
                for sensor in system.sensors
                if sensor.sensor_id.startswith("sensor.identity.")
                and sensor.source_ids == ("source.opaque",)
            )
        if tick == 16:
            system.plastic_step(tick=tick)
            variants = [
                sensor
                for sensor in system.sensors
                if not sensor.sensor_id.startswith("sensor.identity.")
            ]
            specialised_id = variants[0].sensor_id
            modality_id = variants[0].modality_id
            previous = value
            continue
        if specialised_id is None or previous is None:
            previous = value
            continue
        by_name = {item.name: item for item in percepts}
        if specialised_id not in by_name:
            previous = value
            continue
        target = value - previous
        if identity_id is None:
            raise RuntimeError("identity receptor was not expressed")
        identity_predictions.append(float(by_name[identity_id].value))
        specialised_predictions.append(float(by_name[specialised_id].value))
        targets.append(target)
        previous = value

    if specialised_id is None or not targets:
        raise RuntimeError("sensory exploration produced no specialised receptor")
    identity_mae = _mae(identity_predictions, targets)
    specialised_mae = _mae(specialised_predictions, targets)
    return DeltaDiscoveryResult(
        seed=seed,
        samples=len(targets),
        identity_mae=identity_mae,
        specialised_mae=specialised_mae,
        improvement=identity_mae - specialised_mae,
        specialised_sensor_id=specialised_id,
        modality_id=modality_id,
    )


def run_temporal_scale_specialisation(
    seed: int = 101,
    *,
    samples: int = 128,
) -> TemporalSpecialisationResult:
    """Characterize distinct fast and slow receptors over the same source.

    Alpha/beta receptor creation is organism-side.  The evaluator computes
    fast/slow targets only after outputs exist and never feeds them back.
    """
    if samples < 48:
        raise ValueError("samples must be at least 48")
    rng = random.Random(seed)
    system = SensorySystem(plasticity_enabled=True)
    previous_value: float | None = None
    slow_target = 0.0
    alpha_id: str | None = None
    beta_id: str | None = None
    alpha_fast: list[float] = []
    beta_fast: list[float] = []
    alpha_slow: list[float] = []
    beta_slow: list[float] = []
    fast_targets: list[float] = []
    slow_targets: list[float] = []

    for tick in range(1, samples + 1):
        value = 0.8 * math.sin(tick / 18.0) + rng.gauss(0.0, 0.18)
        percepts = system.transduce(
            [_reading(value)],
            percept_names={"source.opaque": "signal.opaque"},
            tick=tick,
        )
        if tick == 16:
            system.plastic_step(tick=16)
            alpha_id = next(
                sensor.sensor_id
                for sensor in system.sensors
                if sensor.modality_id == "modality.alpha"
            )
        if tick == 32:
            system.plastic_step(tick=32)
            beta_id = next(
                sensor.sensor_id
                for sensor in system.sensors
                if sensor.modality_id == "modality.beta"
            )
        by_name = {item.name: item for item in percepts}
        slow_target = 0.85 * slow_target + 0.15 * value
        if previous_value is not None and alpha_id in by_name and beta_id in by_name:
            fast = value - previous_value
            alpha_fast.append(float(by_name[alpha_id].value))
            beta_fast.append(float(by_name[beta_id].value))
            alpha_slow.append(float(by_name[alpha_id].value))
            beta_slow.append(float(by_name[beta_id].value))
            fast_targets.append(fast)
            slow_targets.append(slow_target)
        previous_value = value

    if alpha_id is None or beta_id is None or not fast_targets:
        raise RuntimeError("temporal specialisation receptors were not expressed")

    alpha_fast_mae = _mae(alpha_fast, fast_targets)
    beta_fast_mae = _mae(beta_fast, fast_targets)
    alpha_slow_mae = _mae(alpha_slow, slow_targets)
    beta_slow_mae = _mae(beta_slow, slow_targets)
    return TemporalSpecialisationResult(
        seed=seed,
        samples=len(fast_targets),
        alpha_fast_mae=alpha_fast_mae,
        beta_fast_mae=beta_fast_mae,
        alpha_slow_mae=alpha_slow_mae,
        beta_slow_mae=beta_slow_mae,
        fast_specialisation_gain=beta_fast_mae - alpha_fast_mae,
        slow_specialisation_gain=alpha_slow_mae - beta_slow_mae,
    )


@dataclass(slots=True, frozen=True)
class SensoryProtocolResult:
    protocol: str
    seeds: tuple[int, ...]
    runs: tuple[dict[str, object], ...]
    summary: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "seeds": list(self.seeds),
            "runs": [dict(item) for item in self.runs],
            "summary": dict(self.summary),
        }


def _develop_two_source_system(
    seed: int, samples: int
) -> tuple[SensorySystem, list[tuple[float, float, tuple[object, ...]]]]:
    if samples < 48:
        raise ValueError("samples must be at least 48")
    rng = random.Random(seed)
    system = SensorySystem(plasticity_enabled=True)
    trace: list[tuple[float, float, tuple[object, ...]]] = []
    for tick in range(1, samples + 1):
        x = math.sin(tick / 11.0) + rng.gauss(0.0, 0.10)
        y = math.cos(tick / 17.0) + rng.gauss(0.0, 0.10)
        percepts = system.transduce(
            [_reading(x, source_id="source.a"), _reading(y, source_id="source.b")],
            percept_names={"source.a": "signal.a", "source.b": "signal.b"},
            tick=tick,
        )
        trace.append((x, y, tuple(percepts)))
        if tick % system.limits.mutation_window_ticks == 0:
            system.plastic_step(tick=tick)
    return system, trace


def run_modality_specialisation(seed: int = 101, *, samples: int = 128) -> dict[str, object]:
    temporal = run_temporal_scale_specialisation(seed=seed, samples=max(48, samples))
    system, trace = _develop_two_source_system(seed, max(48, samples))
    gamma = next(
        (
            sensor
            for sensor in system.sensors
            if sensor.modality_id == "modality.gamma" and len(sensor.source_ids) == 2
        ),
        None,
    )
    if gamma is None:
        raise RuntimeError("multisource modality was not expressed")
    identity_a = next(
        sensor.sensor_id
        for sensor in system.sensors
        if sensor.sensor_id.startswith("sensor.identity.") and sensor.source_ids == ("source.a",)
    )
    gamma_values: list[float] = []
    single_values: list[float] = []
    targets: list[float] = []
    for x, y, percepts in trace:
        by_name = {item.name: item for item in percepts}
        if gamma.sensor_id not in by_name:
            continue
        gamma_values.append(float(by_name[gamma.sensor_id].value))
        single_values.append(float(by_name[identity_a].value))
        targets.append((x + y) / 2.0)
    gamma_mae = _mae(gamma_values, targets)
    single_mae = _mae(single_values, targets)
    return {
        "seed": seed,
        "fast_alpha_mae": temporal.alpha_fast_mae,
        "fast_beta_mae": temporal.beta_fast_mae,
        "slow_alpha_mae": temporal.alpha_slow_mae,
        "slow_beta_mae": temporal.beta_slow_mae,
        "distributed_gamma_mae": gamma_mae,
        "distributed_single_mae": single_mae,
        "fast_niche": temporal.alpha_fast_mae < temporal.beta_fast_mae,
        "slow_niche": temporal.beta_slow_mae < temporal.alpha_slow_mae,
        "distributed_niche": gamma_mae < single_mae,
    }


def run_duplication_divergence(seed: int = 101, *, samples: int = 96) -> dict[str, object]:
    rng = random.Random(seed)
    system = SensorySystem(plasticity_enabled=True)
    mutation_counts: dict[int, int] = {}
    value = 0.0
    for tick in range(1, max(64, samples) + 1):
        value += rng.gauss(0.0, 0.25)
        system.transduce(
            [_reading(value)],
            percept_names={"source.opaque": "signal.opaque"},
            tick=tick,
        )
        if tick % system.limits.mutation_window_ticks == 0:
            mutations = system.plastic_step(tick=tick)
            mutation_counts[tick] = len(mutations)
    variants = [
        sensor for sensor in system.sensors if not sensor.sensor_id.startswith("sensor.identity.")
    ]
    return {
        "seed": seed,
        "variant_count": len(variants),
        "modalities": sorted({sensor.modality_id for sensor in variants}),
        "transductions": sorted({sensor.transduction.value for sensor in variants}),
        "lineage_links": sum(bool(sensor.parent_sensor_ids) for sensor in variants),
        "max_mutations_per_window": max(mutation_counts.values(), default=0),
        "mutation_budget": system.limits.max_sensor_mutations_per_window,
        "bounded": max(mutation_counts.values(), default=0)
        <= system.limits.max_sensor_mutations_per_window,
        "diverged": len({sensor.transduction for sensor in variants}) >= 2,
    }


def run_sensory_ablation(seed: int = 101, *, samples: int = 128) -> dict[str, object]:
    if samples < 64:
        samples = 64
    rng = random.Random(seed)
    system = SensorySystem(plasticity_enabled=True)
    value = 0.0
    previous: float | None = None
    alpha_id: str | None = None
    beta_id: str | None = None
    identity_id: str | None = None
    intact: list[float] = []
    matched: list[float] = []
    fallback: list[float] = []
    targets: list[float] = []
    for tick in range(1, samples + 1):
        value += rng.gauss(0.0, 0.30)
        percepts = system.transduce(
            [_reading(value)],
            percept_names={"source.opaque": "signal.opaque"},
            tick=tick,
        )
        if identity_id is None:
            identity_id = next(
                sensor.sensor_id
                for sensor in system.sensors
                if sensor.sensor_id.startswith("sensor.identity.")
                and sensor.source_ids == ("source.opaque",)
            )
        if tick % 16 == 0:
            system.plastic_step(tick=tick)
            alpha_id = alpha_id or next(
                (
                    sensor.sensor_id
                    for sensor in system.sensors
                    if sensor.modality_id == "modality.alpha"
                ),
                None,
            )
            beta_id = beta_id or next(
                (
                    sensor.sensor_id
                    for sensor in system.sensors
                    if sensor.modality_id == "modality.beta"
                ),
                None,
            )
        by_name = {item.name: item for item in percepts}
        if previous is not None and alpha_id in by_name and beta_id in by_name:
            targets.append(value - previous)
            intact.append(float(by_name[alpha_id].value))
            matched.append(float(by_name[beta_id].value))
            if identity_id is None:
                raise RuntimeError("identity receptor was not expressed")
            fallback.append(float(by_name[identity_id].value))
        previous = value
    if not targets:
        raise RuntimeError("ablation study did not reach mature comparison window")
    intact_mae = _mae(intact, targets)
    matched_mae = _mae(matched, targets)
    fallback_mae = _mae(fallback, targets)
    return {
        "seed": seed,
        "samples": len(targets),
        "intact_mae": intact_mae,
        "matched_control_mae": matched_mae,
        "ablated_fallback_mae": fallback_mae,
        "targeted_ablation_effect": fallback_mae - intact_mae,
        "matched_control_gap": matched_mae - intact_mae,
        "causal_support": fallback_mae > intact_mae and matched_mae > intact_mae,
    }


def run_multisource_specialisation(seed: int = 101, *, samples: int = 128) -> dict[str, object]:
    system, trace = _develop_two_source_system(seed, max(64, samples))
    gamma = next(
        (
            sensor
            for sensor in system.sensors
            if sensor.modality_id == "modality.gamma" and len(sensor.source_ids) == 2
        ),
        None,
    )
    if gamma is None:
        raise RuntimeError("adaptive multisource receptor was not expressed")

    identity_by_source = {
        sensor.source_ids[0]: sensor.sensor_id
        for sensor in system.sensors
        if sensor.sensor_id.startswith("sensor.identity.") and len(sensor.source_ids) == 1
    }
    adaptive: list[float] = []
    single_a: list[float] = []
    single_b: list[float] = []
    targets: list[float] = []
    for x, y, percepts in trace:
        by_name = {item.name: item for item in percepts}
        if gamma.sensor_id not in by_name:
            continue
        adaptive.append(float(by_name[gamma.sensor_id].value))
        single_a.append(float(by_name[identity_by_source["source.a"]].value))
        single_b.append(float(by_name[identity_by_source["source.b"]].value))
        targets.append((x + y) / 2.0)

    frozen = SensorySystem(plasticity_enabled=False)
    frozen_sensor = frozen.create_multisource_sensor(("source.a", "source.b"), tick=1)
    frozen_values: list[float] = []
    frozen_targets: list[float] = []
    rng = random.Random(seed)
    for tick in range(1, max(64, samples) + 1):
        x = math.sin(tick / 11.0) + rng.gauss(0.0, 0.10)
        y = math.cos(tick / 17.0) + rng.gauss(0.0, 0.10)
        percepts = frozen.transduce(
            [_reading(x, source_id="source.a"), _reading(y, source_id="source.b")],
            percept_names={"source.a": "signal.a", "source.b": "signal.b"},
            tick=tick,
        )
        by_name = {item.name: item for item in percepts}
        frozen_values.append(float(by_name[frozen_sensor.sensor_id].value))
        frozen_targets.append((x + y) / 2.0)

    adaptive_mae = _mae(adaptive, targets)
    best_single_mae = min(_mae(single_a, targets), _mae(single_b, targets))
    frozen_mae = _mae(frozen_values, frozen_targets)
    return {
        "seed": seed,
        "samples": len(targets),
        "adaptive_multisource_mae": adaptive_mae,
        "best_single_source_mae": best_single_mae,
        "frozen_multisource_mae": frozen_mae,
        "gain_vs_single": best_single_mae - adaptive_mae,
        "gain_vs_frozen": frozen_mae - adaptive_mae,
        "beats_single_source": adaptive_mae < best_single_mae,
        "beats_frozen": adaptive_mae < frozen_mae,
    }


def run_same_world_phenotype_divergence(seed: int = 101, *, samples: int = 96) -> dict[str, object]:
    rng = random.Random(seed)
    world = [
        (math.sin(tick / 13.0) + rng.gauss(0.0, 0.12), math.cos(tick / 19.0) + rng.gauss(0.0, 0.12))
        for tick in range(1, max(64, samples) + 1)
    ]
    systems = [SensorySystem(plasticity_enabled=True) for _ in range(3)]
    for tick, (x, y) in enumerate(world, start=1):
        for system in systems:
            system.transduce(
                [_reading(x, source_id="source.a"), _reading(y, source_id="source.b")],
                percept_names={"source.a": "signal.a", "source.b": "signal.b"},
                tick=tick,
            )
            if tick % system.limits.mutation_window_ticks == 0:
                system.plastic_step(tick=tick)
    fingerprints = []
    for system in systems:
        payload = system.phenotype_view()
        canonical = repr(payload)
        fingerprints.append(canonical)
    return {
        "seed": seed,
        "organisms": len(systems),
        "unique_phenotypes": len(set(fingerprints)),
        "converged": len(set(fingerprints)) == 1,
        "diverged": len(set(fingerprints)) > 1,
    }


def _replicated(
    protocol: str, seeds: list[int] | tuple[int, ...], fn, *, steps: int
) -> SensoryProtocolResult:
    resolved = tuple(int(seed) for seed in seeds)
    if not resolved:
        raise ValueError("at least one seed is required")
    runs = tuple(fn(seed, samples=steps) for seed in resolved)
    return SensoryProtocolResult(protocol=protocol, seeds=resolved, runs=runs, summary={})


def run_identity_equivalence_study(seeds=(101, 127, 149), steps: int = 64) -> SensoryProtocolResult:
    runs = tuple(
        run_identity_equivalence(samples=max(2, steps)).as_dict() | {"seed": int(seed)}
        for seed in seeds
    )
    return SensoryProtocolResult(
        "perception.identity-equivalence",
        tuple(int(seed) for seed in seeds),
        runs,
        {"all_equivalent": all(bool(run["equivalent"]) for run in runs)},
    )


def run_adaptive_delta_discovery_study(
    seeds=(101, 127, 149), steps: int = 96
) -> SensoryProtocolResult:
    runs = tuple(
        run_adaptive_delta_discovery(int(seed), samples=max(32, steps)).as_dict() for seed in seeds
    )
    return SensoryProtocolResult(
        "perception.adaptive-delta-discovery",
        tuple(int(seed) for seed in seeds),
        runs,
        {"all_improved": all(float(run["improvement"]) > 0.0 for run in runs)},
    )


def run_temporal_scale_specialisation_study(
    seeds=(101, 127, 149), steps: int = 128
) -> SensoryProtocolResult:
    runs = tuple(
        run_temporal_scale_specialisation(int(seed), samples=max(48, steps)).as_dict()
        for seed in seeds
    )
    return SensoryProtocolResult(
        "perception.temporal-scale-specialisation",
        tuple(int(seed) for seed in seeds),
        runs,
        {
            "all_niches_distinct": all(
                float(run["fast_specialisation_gain"]) > 0.0
                and float(run["slow_specialisation_gain"]) > 0.0
                for run in runs
            )
        },
    )


def run_modality_specialisation_study(
    seeds=(101, 127, 149), steps: int = 128
) -> SensoryProtocolResult:
    runs = tuple(run_modality_specialisation(int(seed), samples=max(48, steps)) for seed in seeds)
    return SensoryProtocolResult(
        "perception.modality-specialisation",
        tuple(int(seed) for seed in seeds),
        runs,
        {
            "all_three_niches": all(
                bool(run["fast_niche"])
                and bool(run["slow_niche"])
                and bool(run["distributed_niche"])
                for run in runs
            )
        },
    )


def run_duplication_divergence_study(
    seeds=(101, 127, 149), steps: int = 96
) -> SensoryProtocolResult:
    runs = tuple(run_duplication_divergence(int(seed), samples=max(64, steps)) for seed in seeds)
    return SensoryProtocolResult(
        "perception.sensory-duplication-divergence",
        tuple(int(seed) for seed in seeds),
        runs,
        {
            "all_bounded_and_diverged": all(
                bool(run["bounded"]) and bool(run["diverged"]) for run in runs
            )
        },
    )


def run_sensory_ablation_study(seeds=(101, 127, 149), steps: int = 128) -> SensoryProtocolResult:
    runs = tuple(run_sensory_ablation(int(seed), samples=max(64, steps)) for seed in seeds)
    return SensoryProtocolResult(
        "perception.sensory-ablation",
        tuple(int(seed) for seed in seeds),
        runs,
        {"all_support_causal_role": all(bool(run["causal_support"]) for run in runs)},
    )


def run_multisource_specialisation_study(
    seeds=(101, 127, 149), steps: int = 128
) -> SensoryProtocolResult:
    runs = tuple(
        run_multisource_specialisation(int(seed), samples=max(64, steps)) for seed in seeds
    )
    return SensoryProtocolResult(
        "perception.multisource-specialisation",
        tuple(int(seed) for seed in seeds),
        runs,
        {
            "all_beat_single": all(bool(run["beats_single_source"]) for run in runs),
            "all_beat_frozen": all(bool(run["beats_frozen"]) for run in runs),
        },
    )


def run_same_world_phenotype_divergence_study(
    seeds=(101, 127, 149), steps: int = 96
) -> SensoryProtocolResult:
    runs = tuple(
        run_same_world_phenotype_divergence(int(seed), samples=max(64, steps)) for seed in seeds
    )
    return SensoryProtocolResult(
        "perception.same-world-phenotype-divergence",
        tuple(int(seed) for seed in seeds),
        runs,
        {
            "converged_runs": sum(bool(run["converged"]) for run in runs),
            "diverged_runs": sum(bool(run["diverged"]) for run in runs),
        },
    )
