"""Longitudinal, evaluator-only harnesses for autonomous life studies."""

from .harness import (
    AutonomousLifeHarness,
    HarnessConfig,
    LifeEvent,
    LifeMetrics,
    LifeTrace,
    SubjectObservation,
    OpaqueEnvironment,
    run_autonomous_life,
)
from .scenarios import AdversarialScenario, SCENARIO_MATRIX, ScenarioSpec
from .evolution import EvolutionarySnapshot, measure_lineages
from .evolution_study import (
    EvolutionObservation,
    LocusAssociation,
    run_genesis_evolution_replicates,
    summarize_locus_associations,
)
from .genesis import build_genesis_harness
from .ecology import (
    DEFAULT_RESOURCE_PROFILES,
    EcologyObservation,
    run_genesis_ecology_factorial,
)
from .ablation import (
    InteroceptionArm,
    InteroceptionAblationResult,
    InteroceptionControlResult,
    LongitudinalInteroceptionArm,
    LongitudinalInteroceptionResult,
    ExperienceInteroceptionArm,
    ExperienceInteroceptionResult,
    run_interoception_ablation,
    run_interoception_ablation_replicates,
    run_interoception_control,
    run_interoception_control_replicates,
    run_interoception_longitudinal,
    run_interoception_experience_control,
)

__all__ = [
    "AutonomousLifeHarness",
    "HarnessConfig",
    "LifeEvent",
    "LifeMetrics",
    "LifeTrace",
    "SubjectObservation",
    "OpaqueEnvironment",
    "run_autonomous_life",
    "AdversarialScenario", "SCENARIO_MATRIX", "ScenarioSpec",
    "EvolutionarySnapshot", "measure_lineages",
    "EvolutionObservation", "LocusAssociation", "run_genesis_evolution_replicates",
    "summarize_locus_associations",
    "build_genesis_harness",
    "DEFAULT_RESOURCE_PROFILES", "EcologyObservation", "run_genesis_ecology_factorial",
    "InteroceptionArm", "InteroceptionAblationResult", "InteroceptionControlResult",
    "LongitudinalInteroceptionArm", "LongitudinalInteroceptionResult",
    "ExperienceInteroceptionArm", "ExperienceInteroceptionResult",
    "run_interoception_ablation", "run_interoception_ablation_replicates",
    "run_interoception_control", "run_interoception_control_replicates",
    "run_interoception_longitudinal", "run_interoception_experience_control",
]
