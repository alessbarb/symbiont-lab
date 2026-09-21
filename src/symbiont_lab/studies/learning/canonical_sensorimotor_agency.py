"""Canonical-organism test for opaque sensorimotor agency.

This protocol exercises the real physics3d constitution rather than a lab-only
predictor.  The experiment records evaluator telemetry after each organism
tick; no labels, rewards, anatomy names, or evaluator measurements enter the
organism.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime


@dataclass(frozen=True, slots=True)
class SensorimotorAgencyTrial:
    seed: int
    ticks_requested: int
    ticks_completed: int
    alive: bool
    motor_patterns: int
    motor_primitives: int
    cognitive_motor_primitives: int
    primitive_verification_ticks: int
    replay_ticks: int
    investigation_ticks: int
    passive_baseline_samples: int
    best_controllability: float
    best_directional_consistency: float
    first_cognitive_primitive_tick: int | None

    @property
    def body_model_discovery_validated(self) -> bool:
        """Whether the organism passed the pre-control discovery gate."""
        return (
            self.ticks_completed > 0
            and self.motor_primitives > 0
            and self.cognitive_motor_primitives > 0
            and self.primitive_verification_ticks > 0
            and self.best_controllability > 0.002
            and self.best_directional_consistency >= 0.60
        )

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["body_model_discovery_validated"] = (
            self.body_model_discovery_validated
        )
        return payload


@dataclass(frozen=True, slots=True)
class SensorimotorAgencyStudy:
    seeds: tuple[int, ...]
    ticks: int
    trials: tuple[SensorimotorAgencyTrial, ...]

    @property
    def validated_trials(self) -> int:
        return sum(trial.body_model_discovery_validated for trial in self.trials)

    @property
    def validated(self) -> bool:
        """Require every independent seed to pass the same discovery gate."""
        return bool(self.trials) and self.validated_trials == len(self.trials)

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "ticks": self.ticks,
            "trials": [trial.as_dict() for trial in self.trials],
            "validated_trials": self.validated_trials,
            "validated": self.validated,
        }


def run_sensorimotor_agency_trial(
    seed: int,
    *,
    ticks: int = 128,
    physics_substeps_per_tick: int = 1,
) -> SensorimotorAgencyTrial:
    """Run one fresh canonical organism with opaque motor babbling."""
    if ticks < 1:
        raise ValueError("ticks must be positive")
    with PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        physics_substeps_per_tick=physics_substeps_per_tick,
    ) as runtime:
        completed = 0
        verification_ticks = 0
        replay_ticks = 0
        investigation_ticks = 0
        first_cognitive_tick: int | None = None
        last = None
        for _ in range(ticks):
            last = runtime.step()
            completed += 1
            verification_ticks += int(last.motor_origin_detail == "primitive_verification")
            replay_ticks += int(last.primitive_replay_active)
            investigation_ticks += int(last.motor_investigation_active)
            if (
                first_cognitive_tick is None
                and last.cognitive_motor_primitives > 0
            ):
                first_cognitive_tick = last.tick
            if not last.alive:
                break

        if last is None:
            raise RuntimeError("canonical trial produced no ticks")
        return SensorimotorAgencyTrial(
            seed=int(seed),
            ticks_requested=int(ticks),
            ticks_completed=completed,
            alive=last.alive,
            motor_patterns=last.sensorimotor_patterns,
            motor_primitives=last.motor_primitives,
            cognitive_motor_primitives=last.cognitive_motor_primitives,
            primitive_verification_ticks=verification_ticks,
            replay_ticks=replay_ticks,
            investigation_ticks=investigation_ticks,
            passive_baseline_samples=last.passive_baseline_samples,
            best_controllability=last.best_motor_controllability,
            best_directional_consistency=last.best_motor_directional_consistency,
            first_cognitive_primitive_tick=first_cognitive_tick,
        )


def run_sensorimotor_agency_study(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    ticks: int = 128,
    physics_substeps_per_tick: int = 1,
    steps: int | None = None,
) -> SensorimotorAgencyStudy:
    """Run the same falsifiable gate across independent newborn organisms."""
    # ``steps`` keeps the protocol compatible with the generic study CLI and
    # declarative experiment runner, which use that common budget name.
    if steps is not None:
        ticks = int(steps)
    normalized_seeds = tuple(int(seed) for seed in seeds)
    trials = tuple(
        run_sensorimotor_agency_trial(
            seed,
            ticks=ticks,
            physics_substeps_per_tick=physics_substeps_per_tick,
        )
        for seed in normalized_seeds
    )
    return SensorimotorAgencyStudy(
        seeds=normalized_seeds,
        ticks=int(ticks),
        trials=trials,
    )


__all__ = [
    "SensorimotorAgencyStudy",
    "SensorimotorAgencyTrial",
    "run_sensorimotor_agency_study",
    "run_sensorimotor_agency_trial",
]
