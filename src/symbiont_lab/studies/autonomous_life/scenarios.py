"""Evaluator-side scenario catalogue for biological-closure runs.

Scenario names and expected outcomes stay on the apparatus side.  A scenario
runner may use the catalogue to select a fixture, but it must only alter the
authorized observation surfaces or finite habitats supplied to an organism.
No scenario label is part of an organism checkpoint or tick input.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AdversarialScenario(StrEnum):
    FALSE_CORRELATIONS = "false_correlations"
    STALE_RESOURCES = "stale_resources"
    SENSOR_DISAPPEARANCE = "sensor_disappearance"
    SENSOR_REAPPEARANCE = "sensor_reappearance"
    RESOURCE_INVERSION = "resource_inversion"
    POPULATION_PRESSURE = "population_pressure"
    FAILED_REPAIR = "failed_repair"
    BIRTH_DENIAL = "birth_denial"
    PARENT_DEATH = "parent_death"
    OFFSPRING_SURVIVAL = "offspring_survival"
    SOCIAL_PARTNER_LOSS = "social_partner_loss"
    CHECKPOINT_STRESS = "checkpoint_stress"
    CHECKPOINT_DORMANCY = "checkpoint_dormancy"
    CHECKPOINT_BEFORE_DEATH = "checkpoint_before_death"
    RESTORE = "restore"


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    scenario: AdversarialScenario
    apparatus_surface: str
    invariant: str


SCENARIO_MATRIX: tuple[ScenarioSpec, ...] = (
    ScenarioSpec(AdversarialScenario.FALSE_CORRELATIONS, "opaque resource quantities", "no evaluator label reaches the tick"),
    ScenarioSpec(AdversarialScenario.STALE_RESOURCES, "finite habitat supply", "existing allocations are preserved"),
    ScenarioSpec(AdversarialScenario.SENSOR_DISAPPEARANCE, "authorized reading provider", "missing capability is observed as unavailable"),
    ScenarioSpec(AdversarialScenario.SENSOR_REAPPEARANCE, "authorized reading provider", "reappearance requires fresh observation"),
    ScenarioSpec(AdversarialScenario.RESOURCE_INVERSION, "opaque resource quantities", "local resource evidence remains revisable"),
    ScenarioSpec(AdversarialScenario.POPULATION_PRESSURE, "bounded birth authority", "capacity is not an evaluator fitness signal"),
    ScenarioSpec(AdversarialScenario.FAILED_REPAIR, "metabolism and homeostasis", "failed repair remains an observable outcome"),
    ScenarioSpec(AdversarialScenario.BIRTH_DENIAL, "bounded birth authority", "denial does not create a child or hidden reward"),
    ScenarioSpec(AdversarialScenario.PARENT_DEATH, "lineage and habitat release", "death is irreversible and releases only the parent"),
    ScenarioSpec(AdversarialScenario.OFFSPRING_SURVIVAL, "independent child runtime", "child viability is measured separately"),
    ScenarioSpec(AdversarialScenario.SOCIAL_PARTNER_LOSS, "social habitat membership", "presence changes without peer semantics"),
    ScenarioSpec(AdversarialScenario.CHECKPOINT_STRESS, "organism checkpoint", "stress evidence survives export"),
    ScenarioSpec(AdversarialScenario.CHECKPOINT_DORMANCY, "organism checkpoint", "dormancy evidence survives export"),
    ScenarioSpec(AdversarialScenario.CHECKPOINT_BEFORE_DEATH, "organism checkpoint", "pre-death state can be resumed only before death"),
    ScenarioSpec(AdversarialScenario.RESTORE, "organism plus apparatus checkpoints", "continuation uses restored state, not reconstructed microstate"),
)


def validate_scenario_matrix(matrix: tuple[ScenarioSpec, ...] = SCENARIO_MATRIX) -> None:
    """Reject an incomplete or duplicated evaluator protocol."""
    expected = set(AdversarialScenario)
    actual = [item.scenario for item in matrix]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("adversarial scenario matrix must cover each scenario exactly once")
    if any(not item.apparatus_surface or not item.invariant for item in matrix):
        raise ValueError("scenario specifications require apparatus surface and invariant")


validate_scenario_matrix()

__all__ = ["AdversarialScenario", "ScenarioSpec", "SCENARIO_MATRIX", "validate_scenario_matrix"]
