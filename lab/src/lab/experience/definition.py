"""Lab run ontology: Experience acquires capability, World integrates it (ADR-0008).

Everything here is apparatus-side. Run kinds, definition ids, situations and
observer purposes are recorded in run manifests; none of them is passed to the
engine or becomes visible to Symbiont cognition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RunKind(StrEnum):
    ACQUISITION_EMBODIMENT = "acquisition.embodiment"
    ACQUISITION_VISION = "acquisition.vision"
    WORLD_CHALLENGE = "world.challenge"
    WORLD_OPEN = "world.open"

    @property
    def is_acquisition(self) -> bool:
        return self.value.startswith("acquisition.")


class TerminationReason(StrEnum):
    TIME_BUDGET_REACHED = "time_budget_reached"
    EVIDENCE_WINDOW_COMPLETE = "evidence_window_complete"
    OPERATOR_STOP = "operator_stop"
    EXPERIMENTAL_CONDITION_COMPLETE = "experimental_condition_complete"
    PROTECTED_RECOVERY = "protected_recovery"
    TECHNICAL_FAILURE = "technical_failure"
    BODY_NON_VIABLE = "body_non_viable"
    WORLD_DURATION_COMPLETE = "world_duration_complete"


# Raw exit causes reported by the Physics3D engine. The engine knows which loop
# exit fired; only the Lab knows what that means for the run kind.
EXIT_BUDGET = "budget_exhausted"
EXIT_STOP = "operator_stop"
EXIT_BODY_NON_VIABLE = "body_non_viable"
EXIT_DISCONNECTED = "physics_disconnected"
EXIT_ERROR = "error"
GUARD_PREFIX = "guard:"


def resolve_termination(
    kind: RunKind, exit_cause: str | None, *, failed: bool
) -> TerminationReason:
    """Map the engine's exit cause to the run-kind termination taxonomy."""
    if exit_cause and exit_cause.startswith(GUARD_PREFIX):
        return TerminationReason(exit_cause.removeprefix(GUARD_PREFIX))
    if exit_cause == EXIT_BODY_NON_VIABLE:
        return TerminationReason.BODY_NON_VIABLE
    if exit_cause == EXIT_BUDGET and not failed:
        return (
            TerminationReason.TIME_BUDGET_REACHED
            if kind.is_acquisition
            else TerminationReason.WORLD_DURATION_COMPLETE
        )
    if exit_cause == EXIT_STOP and not failed:
        return TerminationReason.OPERATOR_STOP
    if failed or exit_cause in {EXIT_DISCONNECTED, EXIT_ERROR}:
        return TerminationReason.TECHNICAL_FAILURE
    # A runner that reports nothing but ends cleanly was stopped by the operator.
    return TerminationReason.OPERATOR_STOP


@dataclass(frozen=True, slots=True)
class Situation:
    """Observer-only challenge region/condition. Never an organism task."""

    situation_id: str
    observer_purpose: tuple[str, ...]
    fixtures: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.situation_id,
            "observer_purpose": list(self.observer_purpose),
            "fixtures": list(self.fixtures),
        }


@dataclass(frozen=True, slots=True)
class RunDefinition:
    """Versioned, immutable Lab definition of an Experience or World run.

    ``environment`` of ``None`` means the operator chooses the recipe (open
    World only). Definitions never encode a route, goal, reward or win state.
    """

    definition_id: str
    version: int
    kind: RunKind
    title: str
    observer_purpose: tuple[str, ...]
    environment: str | None
    situations: tuple[Situation, ...] = ()
    unavailable_reason: str | None = None
    body_kind: str | None = None  # required apparatus, when the definition needs one

    @property
    def launchable(self) -> bool:
        return self.unavailable_reason is None

    def as_dict(self) -> dict[str, object]:
        return {
            "definition_id": self.definition_id,
            "version": self.version,
            "kind": self.kind.value,
            "title": self.title,
            "observer_purpose": list(self.observer_purpose),
            "environment": self.environment,
            "situations": [item.as_dict() for item in self.situations],
            "launchable": self.launchable,
            "body_kind": self.body_kind,
            "unavailable_reason": self.unavailable_reason,
        }


DEFINITIONS: tuple[RunDefinition, ...] = (
    RunDefinition(
        definition_id="embodiment-nursery-v1",
        version=1,
        kind=RunKind.ACQUISITION_EMBODIMENT,
        title="Embodiment nursery",
        observer_purpose=(
            "effector → consequence relations",
            "controllability and repeatability",
            "interoceptive regularities",
        ),
        environment="flat-v1",
    ),
    RunDefinition(
        definition_id="vision-nursery-v1",
        version=1,
        kind=RunKind.ACQUISITION_VISION,
        title="Vision nursery",
        observer_purpose=("temporal structure of a visual apparatus",),
        environment="vision-nursery-v1",
        body_kind="anthropomorphic-v6-vision",
    ),
    RunDefinition(
        definition_id="contact-garden-challenge-v1",
        version=1,
        kind=RunKind.WORLD_CHALLENGE,
        title="Contact garden challenge",
        observer_purpose=("integration of embodiment acquisitions under full consequence",),
        environment="contact-garden-v1",
        situations=(
            Situation(
                "support_variation",
                ("sensorimotor generalization across friction",),
                ("low-surface", "smooth-surface"),
            ),
            Situation("constrained_geometry", ("contact without known source",), ("barrier",)),
            Situation("contact_opportunity", ("multimodal contact",), ("block",)),
        ),
    ),
    RunDefinition(
        definition_id="open-world-v1",
        version=1,
        kind=RunKind.WORLD_OPEN,
        title="Open World",
        observer_purpose=("open-ended interaction",),
        environment=None,
    ),
)

DEFAULT_DEFINITION_ID = "open-world-v1"


def run_definition(definition_id: str | None = None) -> RunDefinition:
    wanted = definition_id or DEFAULT_DEFINITION_ID
    for item in DEFINITIONS:
        if item.definition_id == wanted:
            return item
    raise ValueError(f"unknown run definition: {wanted}")


def run_definition_catalog() -> list[dict[str, object]]:
    return [item.as_dict() for item in DEFINITIONS]


__all__ = [
    "DEFAULT_DEFINITION_ID",
    "DEFINITIONS",
    "EXIT_BODY_NON_VIABLE",
    "EXIT_BUDGET",
    "EXIT_DISCONNECTED",
    "EXIT_ERROR",
    "EXIT_STOP",
    "GUARD_PREFIX",
    "RunDefinition",
    "RunKind",
    "Situation",
    "TerminationReason",
    "resolve_termination",
    "run_definition",
    "run_definition_catalog",
]
