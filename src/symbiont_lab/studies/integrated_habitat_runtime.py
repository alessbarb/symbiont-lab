"""Small technical smoke study for the canonical integrated habitat.

This is an integration artifact, not evidence for a new organism capability.
The lifecycle probe only exercises existing birth/death APIs so that the
single runtime path is covered deterministically.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont_lab.integration import IntegratedHabitatConfig, IntegratedHabitatRuntime

SEEDS = (101, 127, 149)


class _DisabledTelemetry:
    """Inert sink used only for the observer-equivalence control.

    It deliberately implements the outbound sink surface without retaining
    events.  The integrated runtime still executes the same organism and
    transport paths; only the observational sink is removed.
    """

    events: tuple[object, ...] = ()

    def record(self, _event: object) -> bool:
        return False

    def record_grounding(self, _event: object) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class IntegratedHabitatRun:
    seed: int
    ticks: int
    births: int
    deaths: int
    live_population: int
    communication_events: int
    grounding_exposures: int
    private_model_records: int
    claims: int
    composites: int
    finite_state: bool
    bounded: bool
    checkpoint_round_trip: bool
    replay_equal: bool
    observer_equivalent: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_integrated_habitat_smoke(
    *, seeds: Sequence[int] = SEEDS, ticks: int = 8
) -> tuple[IntegratedHabitatRun, ...]:
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be non-empty integers")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or not 1 <= ticks <= 1000:
        raise ValueError("ticks must be between 1 and 1000")
    results: list[IntegratedHabitatRun] = []
    for seed in seeds:
        observer_on = IntegratedHabitatRuntime(
            IntegratedHabitatConfig(
                seed=seed,
                trigger_lifecycle_probe=True,
            )
        )
        observer_off = IntegratedHabitatRuntime(
            IntegratedHabitatConfig(
                seed=seed,
                trigger_lifecycle_probe=True,
            )
        )
        observer_off.telemetry = _DisabledTelemetry()
        observer_off.sequence_channel.telemetry = observer_off.telemetry
        observer_on.run(ticks)
        observer_off.run(ticks)
        config = IntegratedHabitatConfig(seed=seed, trigger_lifecycle_probe=True)
        habitat = IntegratedHabitatRuntime(config)
        # Capture after the controlled lifecycle probe has completed.  A
        # checkpoint taken between a metabolic debit and the next physiology
        # transition is intentionally not a valid habitat boundary.
        split = max(1, min(ticks - 1, 5))
        habitat.run(split)
        checkpoint = habitat.checkpoint()
        restored = IntegratedHabitatRuntime.from_checkpoint(checkpoint)
        checkpoint_round_trip = (
            restored.tick_count == habitat.tick_count
            and tuple(sorted(restored.population)) == tuple(sorted(habitat.population))
            and restored.checkpoint()["schema_version"] == habitat.SCHEMA_VERSION
        )
        restored.run(ticks)
        habitat.run(ticks)
        replay_equal = _continuation_signature(habitat) == _continuation_signature(restored)
        observer_equivalent = _observer_signature(observer_on) == _observer_signature(observer_off)
        summaries = habitat.history
        run = IntegratedHabitatRun(
            seed=seed,
            ticks=habitat.tick_count,
            births=sum(len(item.births) for item in summaries),
            deaths=sum(len(item.deaths) for item in summaries),
            live_population=len(habitat.population),
            communication_events=len(habitat.telemetry.events),
            grounding_exposures=sum(item.grounding_exposures for item in summaries),
            private_model_records=sum(item.private_model_records for item in summaries),
            claims=sum(item.claims for item in summaries),
            composites=sum(item.composites for item in summaries),
            finite_state=_is_finite(habitat.checkpoint()),
            bounded=len(habitat.population) <= config.max_population
            and len(habitat.telemetry.events) <= config.telemetry_max_events,
            checkpoint_round_trip=checkpoint_round_trip,
            replay_equal=replay_equal,
            observer_equivalent=observer_equivalent,
        )
        results.append(run)
    return tuple(results)


def _is_finite(value: object) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_is_finite(key) and _is_finite(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_is_finite(item) for item in value)
    return True


def _continuation_signature(habitat: IntegratedHabitatRuntime) -> str:
    payload = {
        "tick": habitat.tick_count,
        "population": sorted(habitat.population),
        "dead": sorted(habitat.dead),
        "history": [asdict(item) for item in habitat.history],
        "telemetry": [event for event in habitat.telemetry.events],
        "deliveries": habitat.sequence_channel.deliveries,
    }
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


def _observer_signature(habitat: IntegratedHabitatRuntime) -> str:
    payload = {
        "tick": habitat.tick_count,
        "population": sorted(habitat.population),
        "dead": sorted(habitat.dead),
        "history": [
            {key: value for key, value in asdict(item).items() if key != "communication_events"}
            for item in habitat.history
        ],
        "population_state": [
            runtime.checkpoint()
            for runtime in sorted(habitat.population.values(), key=lambda item: item.organism_id)
        ],
    }
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


__all__ = ["IntegratedHabitatRun", "SEEDS", "run_integrated_habitat_smoke"]
