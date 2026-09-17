"""Evaluator-side ablations for organism-owned interoception.

The two arms are constructed with the same genome, seed and opaque habitat.
Only the authorized interoceptive surface is removed in the control arm.  The
function returns measurements; it never reports an arm label to an organism.

The default ablation holds the founder cohort fixed by disabling reproduction
in both arms.  That isolates regulation from a confounding difference in
lineage expansion; Genesis runs with reproduction enabled remain available for
the separate autonomous-life evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace

from .genesis import build_genesis_harness
from .harness import HarnessConfig, LifeEvent, LifeMetrics, LifeTrace


@dataclass(frozen=True, slots=True)
class InteroceptionArm:
    enabled: bool
    metrics: LifeMetrics
    stress_rate: float
    regulation_rate: float
    rescue_rate: float


@dataclass(frozen=True, slots=True)
class InteroceptionAblationResult:
    with_interoception: InteroceptionArm
    without_interoception: InteroceptionArm

    @property
    def stress_rate_delta(self) -> float:
        """Control stress rate minus treatment stress rate; positive is better."""
        return (self.without_interoception.stress_rate
                - self.with_interoception.stress_rate)


@dataclass(frozen=True, slots=True)
class InteroceptionControlResult:
    """Three-arm result separating information from provider workload."""

    with_interoception: InteroceptionArm
    sham_interoception: InteroceptionArm
    without_interoception: InteroceptionArm


@dataclass(frozen=True, slots=True)
class LongitudinalInteroceptionArm:
    """Evaluator-only early/late measurements for one control arm."""

    enabled: bool
    early_repair_events: int
    late_repair_events: int
    early_rescue_events: int
    late_rescue_events: int
    early_mean_integrity: float | None
    late_mean_integrity: float | None


@dataclass(frozen=True, slots=True)
class LongitudinalInteroceptionResult:
    """Matched longitudinal evidence split at an apparatus tick boundary."""

    split_tick: int
    with_interoception: LongitudinalInteroceptionArm
    sham_interoception: LongitudinalInteroceptionArm
    without_interoception: LongitudinalInteroceptionArm


@dataclass(frozen=True, slots=True)
class ExperienceInteroceptionArm:
    """Evaluator-only training/test measurements for one enabled cohort."""

    training_repair_events: int
    test_repair_events: int
    training_rescue_events: int
    test_rescue_events: int
    test_mean_integrity: float | None

    @property
    def test_intervention_events(self) -> int:
        return self.test_repair_events + self.test_rescue_events


@dataclass(frozen=True, slots=True)
class ExperienceInteroceptionResult:
    """Experienced versus naïve enabled cohorts under the same test pressure."""

    seed: int
    split_tick: int
    experienced: ExperienceInteroceptionArm
    naive: ExperienceInteroceptionArm

    @property
    def intervention_reduction(self) -> int:
        """Positive values mean fewer test interventions after experience."""
        return self.naive.test_intervention_events - self.experienced.test_intervention_events


def _experience_arm(
    trace: LifeTrace,
    *,
    split_tick: int,
) -> ExperienceInteroceptionArm:
    arm = _longitudinal_arm(trace, enabled=True, split_tick=split_tick)
    return ExperienceInteroceptionArm(
        training_repair_events=arm.early_repair_events,
        test_repair_events=arm.late_repair_events,
        training_rescue_events=arm.early_rescue_events,
        test_rescue_events=arm.late_rescue_events,
        test_mean_integrity=arm.late_mean_integrity,
    )


def run_interoception_experience_control(
    config: HarnessConfig | None = None,
    *,
    seed: int = 7,
    training_schedule: tuple[tuple[int, float], ...] = ((8, 0.10), (16, 0.10)),
    test_schedule: tuple[tuple[int, float], ...] = ((56, 0.20), (72, 0.20), (88, 0.20)),
    split_tick: int | None = None,
    social_enabled: bool = False,
    resource_profiles: tuple[tuple[float, float, float, float], ...] | None = None,
) -> ExperienceInteroceptionResult:
    """Compare experienced and naïve enabled cohorts without arm labels.

    The experienced cohort receives a predeclared training schedule before the
    common test schedule.  The naïve cohort receives only that test schedule.
    Both cohorts start with the same genome and enabled interoceptive surface;
    only organism-acquired action/outcome history differs.  The apparatus
    reports test interventions as repair plus homeostatic-rescue events and
    never exposes the cohort label or evaluator counts to an organism.
    """
    selected = config or HarnessConfig(
        population=8, generations=1, ticks=96,
        checkpoint_interval=48, random_checkpoint_count=0,
    )
    boundary = split_tick if split_tick is not None else selected.ticks // 2
    if (isinstance(boundary, bool) or not isinstance(boundary, int)
            or not 1 <= boundary < selected.ticks):
        raise ValueError("split_tick must be within the configured run horizon")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if not training_schedule or not test_schedule:
        raise ValueError("training_schedule and test_schedule must not be empty")
    if set(tick for tick, _ in training_schedule) & set(tick for tick, _ in test_schedule):
        raise ValueError("training and test schedules must use distinct ticks")
    experienced_config = replace(
        selected, seed=seed,
        damage_pulses=(), damage_schedule=training_schedule + test_schedule,
    )
    naive_config = replace(
        selected, seed=seed,
        damage_pulses=(), damage_schedule=test_schedule,
    )
    experienced = build_genesis_harness(
        experienced_config, interoception_mode="enabled",
        reproduction_enabled=False, social_enabled=social_enabled,
        resource_profiles=resource_profiles,
    ).run()
    naive = build_genesis_harness(
        naive_config, interoception_mode="enabled",
        reproduction_enabled=False, social_enabled=social_enabled,
        resource_profiles=resource_profiles,
    ).run()
    return ExperienceInteroceptionResult(
        seed=seed, split_tick=boundary,
        experienced=_experience_arm(experienced, split_tick=boundary),
        naive=_experience_arm(naive, split_tick=boundary),
    )


def _arm(trace: LifeTrace, *, enabled: bool) -> InteroceptionArm:
    metrics = trace.metrics()
    denominator = max(1, len(trace.observations))
    stress = sum(record.event.value == "stress" for record in trace.records)
    regulation = sum(record.event.value == "internal_regulation" for record in trace.records)
    return InteroceptionArm(
        enabled=enabled,
        metrics=metrics,
        stress_rate=stress / denominator,
        regulation_rate=regulation / denominator,
        rescue_rate=metrics.homeostatic_rescue_events / denominator,
    )


def _longitudinal_arm(
    trace: LifeTrace,
    *,
    enabled: bool,
    split_tick: int,
) -> LongitudinalInteroceptionArm:
    """Project one trace into two evaluator-owned temporal windows."""
    values: dict[str, object] = {}
    for label, lower, upper in (
        ("early", 1, split_tick),
        ("late", split_tick + 1, None),
    ):
        records = [record for record in trace.records
                   if record.tick >= lower and (upper is None or record.tick <= upper)]
        observations = [observation for observation in trace.observations
                        if observation.tick >= lower
                        and (upper is None or observation.tick <= upper)
                        and observation.integrity is not None]
        values[f"{label}_repair_events"] = sum(
            record.event is LifeEvent.REPAIR for record in records
        )
        values[f"{label}_rescue_events"] = sum(
            record.event is LifeEvent.HOMEOSTATIC_RESCUE for record in records
        )
        values[f"{label}_mean_integrity"] = (
            round(sum(float(item.integrity) for item in observations) / len(observations), 6)
            if observations else None
        )
    return LongitudinalInteroceptionArm(
        enabled=enabled,
        early_repair_events=int(values["early_repair_events"]),
        late_repair_events=int(values["late_repair_events"]),
        early_rescue_events=int(values["early_rescue_events"]),
        late_rescue_events=int(values["late_rescue_events"]),
        early_mean_integrity=values["early_mean_integrity"],
        late_mean_integrity=values["late_mean_integrity"],
    )


def run_interoception_ablation(
    config: HarnessConfig | None = None,
    *,
    matched_cohort: bool = True,
) -> InteroceptionAblationResult:
    """Run matched treatment/control arms without evaluator feedback.

    The result is intentionally descriptive.  A positive delta is evidence
    for the proposed effect; this helper does not turn one run into a gate.
    Replicated runs and a predeclared analysis are required for that claim.
    """
    selected = config or HarnessConfig(
        population=8, generations=1, ticks=256,
        checkpoint_interval=64, random_checkpoint_count=0,
    )
    reproduction_enabled = not matched_cohort
    with_trace = build_genesis_harness(
        selected,
        interoception_enabled=True,
        reproduction_enabled=reproduction_enabled,
    ).run()
    without_trace = build_genesis_harness(
        selected,
        interoception_enabled=False,
        reproduction_enabled=reproduction_enabled,
    ).run()
    return InteroceptionAblationResult(
        with_interoception=_arm(with_trace, enabled=True),
        without_interoception=_arm(without_trace, enabled=False),
    )


def run_interoception_ablation_replicates(
    config: HarnessConfig | None = None,
    *,
    seeds: tuple[int, ...] = (7, 11, 19, 23, 31),
    matched_cohort: bool = True,
) -> tuple[InteroceptionAblationResult, ...]:
    """Run a predeclared set of independent, matched ablation replicates.

    Seeds are an apparatus-side execution parameter.  They are applied before
    construction and never passed as an observation or label to an organism.
    Returning individual results preserves the replicate-level evidence and
    avoids turning this helper into an unreviewed statistical gate.
    """
    if not seeds or len(seeds) > 64 or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must contain 1 to 64 unique values")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be integers")
    selected = config or HarnessConfig(
        population=8, generations=1, ticks=256,
        checkpoint_interval=64, random_checkpoint_count=0,
    )
    return tuple(
        run_interoception_ablation(
            replace(selected, seed=seed), matched_cohort=matched_cohort
        )
        for seed in seeds
    )


def run_interoception_control(
    config: HarnessConfig | None = None,
    *,
    matched_cohort: bool = True,
    social_enabled: bool = True,
    resource_profiles: tuple[tuple[float, float, float, float], ...] | None = None,
) -> InteroceptionControlResult:
    """Compare real, sham and absent interoception on the same habitat.

    The sham arm retains the provider manifest and processing path but projects
    neutral values.  This is descriptive apparatus output, not a biological
    success gate.
    """
    selected = config or HarnessConfig(
        population=8, generations=1, ticks=256,
        checkpoint_interval=64, random_checkpoint_count=0,
    )
    reproduction_enabled = not matched_cohort
    traces = {
        "enabled": build_genesis_harness(
            selected, interoception_mode="enabled",
            reproduction_enabled=reproduction_enabled, social_enabled=social_enabled,
            resource_profiles=resource_profiles,
        ).run(),
        "sham": build_genesis_harness(
            selected, interoception_mode="sham",
            reproduction_enabled=reproduction_enabled, social_enabled=social_enabled,
            resource_profiles=resource_profiles,
        ).run(),
        "absent": build_genesis_harness(
            selected, interoception_mode="absent",
            reproduction_enabled=reproduction_enabled, social_enabled=social_enabled,
            resource_profiles=resource_profiles,
        ).run(),
    }
    return InteroceptionControlResult(
        with_interoception=_arm(traces["enabled"], enabled=True),
        sham_interoception=_arm(traces["sham"], enabled=True),
        without_interoception=_arm(traces["absent"], enabled=False),
    )


def run_interoception_control_replicates(
    config: HarnessConfig | None = None,
    *,
    seeds: tuple[int, ...] = (7, 11, 19, 23, 31),
    matched_cohort: bool = True,
    social_enabled: bool = True,
    resource_profiles: tuple[tuple[float, float, float, float], ...] | None = None,
) -> tuple[InteroceptionControlResult, ...]:
    """Run independent three-arm controls without collapsing replicates."""
    if not seeds or len(seeds) > 64 or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must contain 1 to 64 unique values")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be integers")
    selected = config or HarnessConfig(
        population=8, generations=1, ticks=256,
        checkpoint_interval=64, random_checkpoint_count=0,
    )
    return tuple(
        run_interoception_control(
            replace(selected, seed=seed),
            matched_cohort=matched_cohort,
            social_enabled=social_enabled,
            resource_profiles=resource_profiles,
        )
        for seed in seeds
    )


def run_interoception_longitudinal(
    config: HarnessConfig | None = None,
    *,
    seed: int = 7,
    split_tick: int | None = None,
    social_enabled: bool = False,
    resource_profiles: tuple[tuple[float, float, float, float], ...] | None = None,
) -> LongitudinalInteroceptionResult:
    """Run a matched early/late interoception control.

    This is an apparatus-side projection only. The split, event counts and
    integrity aggregates never enter an organism decision path. Reproduction
    is disabled so temporal regulation is not confounded by changing cohort
    composition; the supplied damage schedule remains the perturbation.
    """
    selected = config or HarnessConfig(
        population=8,
        generations=1,
        ticks=256,
        checkpoint_interval=64,
        random_checkpoint_count=0,
        damage_pulses=(16, 64, 112, 160, 208),
    )
    boundary = split_tick if split_tick is not None else selected.ticks // 2
    if (isinstance(boundary, bool) or not isinstance(boundary, int)
            or not 1 <= boundary < selected.ticks):
        raise ValueError("split_tick must be within the configured run horizon")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    seeded = replace(selected, seed=seed)
    traces = {
        "enabled": build_genesis_harness(
            seeded, interoception_enabled=True, interoception_mode="enabled",
            reproduction_enabled=False, social_enabled=social_enabled,
            resource_profiles=resource_profiles,
        ).run(),
        "sham": build_genesis_harness(
            seeded, interoception_enabled=True, interoception_mode="sham",
            reproduction_enabled=False, social_enabled=social_enabled,
            resource_profiles=resource_profiles,
        ).run(),
        "absent": build_genesis_harness(
            seeded, interoception_enabled=False, interoception_mode="absent",
            reproduction_enabled=False, social_enabled=social_enabled,
            resource_profiles=resource_profiles,
        ).run(),
    }
    return LongitudinalInteroceptionResult(
        split_tick=boundary,
        with_interoception=_longitudinal_arm(
            traces["enabled"], enabled=True, split_tick=boundary
        ),
        sham_interoception=_longitudinal_arm(
            traces["sham"], enabled=True, split_tick=boundary
        ),
        without_interoception=_longitudinal_arm(
            traces["absent"], enabled=False, split_tick=boundary
        ),
    )


__all__ = [
    "InteroceptionArm", "InteroceptionAblationResult",
    "InteroceptionControlResult", "LongitudinalInteroceptionArm",
    "LongitudinalInteroceptionResult", "ExperienceInteroceptionArm",
    "ExperienceInteroceptionResult",
    "run_interoception_ablation", "run_interoception_ablation_replicates",
    "run_interoception_control", "run_interoception_control_replicates",
    "run_interoception_longitudinal", "run_interoception_experience_control",
]
