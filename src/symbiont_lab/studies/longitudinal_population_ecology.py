"""Bounded discovery campaign for long-duration population behaviour.

This module composes existing evaluator protocols only.  It deliberately does
not add a runtime policy, a reward, a message type, or a lifecycle rule.  The
canonical simulator provides long runs and the existing social-runtime study
provides a separately reported multi-generation lifecycle probe; they are not
presented as one integrated organism when the repository does not provide that
integration.
"""

from __future__ import annotations

import hashlib
import json
import math
import resource
from dataclasses import asdict, dataclass
from typing import Any, Sequence

from symbiont.simulation import SimulationSnapshot, run_simulation

from .social_runtime_generations import run_social_runtime_generations_study

SEEDS = (101, 127, 149)
STAGES = (1_000, 10_000)
MAX_STAGE_TICKS = 100_000
MAX_HOSTS = 32
MAX_GENERATIONS = 50


@dataclass(frozen=True, slots=True)
class LongitudinalStageResult:
    seed: int
    hosts: int
    ticks: int
    final_population: int
    final_collective_patterns: int
    final_forgotten_episodes: int
    final_consolidated_episodes: int
    final_drift_adaptations: int
    peak_open_questions: int
    snapshot_count: int
    finite_state: bool
    counters_bounded: bool
    replay_equal: bool
    rss_start_bytes: int | None
    rss_end_bytes: int | None
    anomaly_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LongitudinalPopulationEcologyStudy:
    protocol: str
    seeds: tuple[int, ...]
    stages: tuple[int, ...]
    hosts: int
    stage_results: tuple[LongitudinalStageResult, ...]
    multigeneration: dict[str, object]
    discovery_only: bool
    organism_capabilities_changed: bool
    integrated_multigeneration_communication: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "seeds": list(self.seeds),
            "stages": list(self.stages),
            "hosts": self.hosts,
            "stage_results": [result.as_dict() for result in self.stage_results],
            "multigeneration": self.multigeneration,
            "discovery_only": self.discovery_only,
            "organism_capabilities_changed": self.organism_capabilities_changed,
            "integrated_multigeneration_communication": self.integrated_multigeneration_communication,
        }


def _rss_bytes() -> int | None:
    try:
        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (AttributeError, OSError):
        return None
    # Linux reports KiB; macOS reports bytes.  The study is primarily run on
    # Linux, while keeping the fallback conservative makes the field portable.
    return value * 1024 if value < 10_000_000 else value


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _snapshot_summary(snapshot: SimulationSnapshot) -> tuple[Any, ...]:
    return (
        snapshot.step,
        snapshot.pathogen_events,
        snapshot.benign_events,
        snapshot.investigated,
        snapshot.collective_patterns,
        snapshot.open_questions,
        snapshot.forgotten_episodes,
        snapshot.consolidated_episodes,
        snapshot.drift_adaptations,
        snapshot.calibration_error,
        snapshot.brier_score,
        snapshot.mean_uncertainty,
    )


def _run_stage(*, seed: int, hosts: int, ticks: int) -> LongitudinalStageResult:
    snapshots: list[SimulationSnapshot] = []
    anomalies: set[str] = set()
    rss_start = _rss_bytes()
    result, _ = run_simulation(
        hosts=hosts,
        steps=ticks,
        seed=seed,
        on_snapshot=snapshots.append,
    )
    rss_end = _rss_bytes()
    previous: tuple[int, ...] | None = None
    for snapshot in snapshots:
        values = snapshot.as_dict()
        numeric = [
            value
            for value in values.values()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        if any(not _finite(value) for value in numeric):
            anomalies.add("NON_FINITE_NUMERIC")
        counters = (
            snapshot.pathogen_events,
            snapshot.benign_events,
            snapshot.investigated,
            snapshot.collective_patterns,
            snapshot.open_questions,
            snapshot.forgotten_episodes,
            snapshot.consolidated_episodes,
            snapshot.drift_adaptations,
        )
        if any(value < 0 or value > hosts * ticks for value in counters):
            anomalies.add("COUNTER_CEILING")
        if previous is not None and snapshot.step <= previous[0]:
            anomalies.add("NON_MONOTONIC_TICK")
        previous = (snapshot.step,)

    # A second run is a replay-equivalent deterministic control, not a claim
    # that macro-population outcomes must be identical across seeds.
    replay: list[SimulationSnapshot] = []
    replay_result, _ = run_simulation(
        hosts=hosts, steps=ticks, seed=seed, on_snapshot=replay.append
    )
    replay_equal = [_snapshot_summary(item) for item in snapshots] == [
        _snapshot_summary(item) for item in replay
    ] and asdict(result) == asdict(replay_result)
    if not replay_equal:
        anomalies.add("REPLAY_MISMATCH")
    counters_bounded = not {"COUNTER_CEILING", "NON_MONOTONIC_TICK"} & anomalies
    finite_state = "NON_FINITE_NUMERIC" not in anomalies
    return LongitudinalStageResult(
        seed=seed,
        hosts=hosts,
        ticks=ticks,
        final_population=hosts,
        final_collective_patterns=snapshots[-1].collective_patterns if snapshots else 0,
        final_forgotten_episodes=snapshots[-1].forgotten_episodes if snapshots else 0,
        final_consolidated_episodes=snapshots[-1].consolidated_episodes if snapshots else 0,
        final_drift_adaptations=snapshots[-1].drift_adaptations if snapshots else 0,
        peak_open_questions=max((item.open_questions for item in snapshots), default=0),
        snapshot_count=len(snapshots),
        finite_state=finite_state,
        counters_bounded=counters_bounded,
        replay_equal=replay_equal,
        rss_start_bytes=rss_start,
        rss_end_bytes=rss_end,
        anomaly_codes=tuple(sorted(anomalies)),
    )


def run_longitudinal_population_ecology_study(
    *,
    seeds: Sequence[int] = SEEDS,
    stages: Sequence[int] = STAGES,
    hosts: int = 4,
    include_multigeneration: bool = True,
) -> LongitudinalPopulationEcologyStudy:
    """Run the preregistered bounded discovery campaign.

    Stages are deliberately capped and validated before execution.  This is a
    discovery artifact: no phenomenon is considered confirmed by these runs.
    """
    normalized_seeds = tuple(seeds)
    normalized_stages = tuple(stages)
    if not normalized_seeds or any(
        isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized_seeds
    ):
        raise ValueError("seeds must be non-empty integers")
    if not normalized_stages or any(
        isinstance(ticks, bool) or not isinstance(ticks, int) for ticks in normalized_stages
    ):
        raise ValueError("stages must be non-empty integers")
    if any(ticks < 1 or ticks > MAX_STAGE_TICKS for ticks in normalized_stages):
        raise ValueError(f"stages must be between 1 and {MAX_STAGE_TICKS} ticks")
    if hosts < 1 or hosts > MAX_HOSTS:
        raise ValueError(f"hosts must be between 1 and {MAX_HOSTS}")
    if len(normalized_stages) != len(set(normalized_stages)):
        raise ValueError("stages must not contain duplicates")

    stage_results = tuple(
        _run_stage(seed=seed, hosts=hosts, ticks=ticks)
        for ticks in normalized_stages
        for seed in normalized_seeds
    )
    multigeneration: dict[str, object] = {"executed": False}
    if include_multigeneration:
        # This is the existing social-runtime lifecycle probe.  It is reported
        # separately because the canonical simulator has no birth/death loop.
        multigeneration = {
            "executed": True,
            **run_social_runtime_generations_study(generations=8).as_dict(),
        }
    return LongitudinalPopulationEcologyStudy(
        protocol="learning.longitudinal-population-ecology",
        seeds=normalized_seeds,
        stages=normalized_stages,
        hosts=hosts,
        stage_results=stage_results,
        multigeneration=multigeneration,
        discovery_only=True,
        organism_capabilities_changed=False,
        integrated_multigeneration_communication=False,
    )


def study_digest(study: LongitudinalPopulationEcologyStudy) -> str:
    payload = json.dumps(
        study.as_dict(), sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "LongitudinalPopulationEcologyStudy",
    "LongitudinalStageResult",
    "run_longitudinal_population_ecology_study",
    "study_digest",
    "SEEDS",
    "STAGES",
]
