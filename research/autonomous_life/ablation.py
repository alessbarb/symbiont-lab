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
from .harness import HarnessConfig, LifeMetrics, LifeTrace


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
        ).run(),
        "sham": build_genesis_harness(
            selected, interoception_mode="sham",
            reproduction_enabled=reproduction_enabled, social_enabled=social_enabled,
        ).run(),
        "absent": build_genesis_harness(
            selected, interoception_mode="absent",
            reproduction_enabled=reproduction_enabled, social_enabled=social_enabled,
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
        )
        for seed in seeds
    )


__all__ = [
    "InteroceptionArm", "InteroceptionAblationResult",
    "InteroceptionControlResult",
    "run_interoception_ablation", "run_interoception_ablation_replicates",
    "run_interoception_control", "run_interoception_control_replicates",
]
