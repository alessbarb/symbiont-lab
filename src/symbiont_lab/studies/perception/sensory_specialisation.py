from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import random
from statistics import mean

from symbiont.host.readings import (
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
)
from symbiont.sensory import SensorySystem, TransductionKind


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
    modality_id = ""

    for tick in range(1, samples + 1):
        value += rng.gauss(0.0, 0.35)
        percepts = system.transduce(
            [_reading(value)],
            percept_names={"source.opaque": "signal.opaque"},
            tick=tick,
        )
        if tick == 16:
            system.plastic_step(tick=tick)
            variants = [
                sensor for sensor in system.sensors
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
        identity_predictions.append(float(by_name["signal.opaque"].value))
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
                sensor.sensor_id for sensor in system.sensors
                if sensor.modality_id == "modality.alpha"
            )
        if tick == 32:
            system.plastic_step(tick=32)
            beta_id = next(
                sensor.sensor_id for sensor in system.sensors
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
