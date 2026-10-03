"""Competence availability: one derived answer to "what can be done with it now".

Cross-Domain Revision Coherence v1 §3.1. A projection, never an authority:
derived from competence knowledge, the execution binding, controller
availability and executive suppression, recomputed on demand, never persisted.
Four orthogonal questions — known, predictable, executable, admissible — plus
the epistemic ones (testable, actionable test) and the scope of a prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..actuation.binding import BindingStatus, CompetenceExecutionBinding, StalenessReason
from ..actuation.competence import CompetenceMaturity, MotorCompetence

_MATURE = frozenset({CompetenceMaturity.ESTABLISHED, CompetenceMaturity.ROBUST})
_HISTORICAL = frozenset(
    {StalenessReason.SURFACE_NOT_CURRENT, StalenessReason.EMBODIMENT_NOT_CURRENT}
)
# Staleness that records a live condition (reconciled every tick): executability
# reads the condition itself, so a status never lags it within a tick.
_LIVE = frozenset({StalenessReason.SURFACE_NOT_CURRENT, StalenessReason.CONTROLLER_UNAVAILABLE})


class PredictionScope(StrEnum):
    CURRENT = "current"  # about this body, on valid evidence
    HISTORICAL = "historical"  # about a previous surface/embodiment
    UNCERTAIN_CURRENT = "uncertain_current"  # about this body, evidence in doubt


class AvailabilityReason(StrEnum):
    NOT_MATURE = "not_mature"
    UNBOUND = "unbound"
    SURFACE_MISMATCH = "surface_mismatch"
    BINDING_STALE = "binding_stale"
    BINDING_INVALIDATED = "binding_invalidated"
    CONTROLLER_UNAVAILABLE = "controller_unavailable"
    EXECUTIVELY_SUPPRESSED = "executively_suppressed"
    OK = "ok"


@dataclass(frozen=True, slots=True)
class CompetenceAvailability:
    competence_id: str
    maturity: CompetenceMaturity
    binding_status: BindingStatus | None
    surface_match: bool
    controller_available: bool
    suppressed: bool
    predictable_now: bool
    prediction_scope: PredictionScope | None
    executable_now: bool
    admissible_now: bool
    testable_now: bool
    actionable_test_now: bool
    reason: AvailabilityReason


def derive_availability(
    competence: MotorCompetence,
    *,
    binding: CompetenceExecutionBinding | None,
    effect_known: bool,
    surface_fingerprint: str | None,
    controller_available: bool,
    suppressed: bool,
) -> CompetenceAvailability:
    status = binding.status if binding is not None else None
    surface_match = (
        binding is not None
        and surface_fingerprint is not None
        and binding.surface_fingerprint == surface_fingerprint
    )
    mature = competence.maturity in _MATURE
    predictable = (
        effect_known
        and competence.effect_id is not None
        and status in (BindingStatus.VALID, BindingStatus.STALE)
    )
    if not predictable:
        scope = None
    elif status is BindingStatus.VALID:
        scope = PredictionScope.CURRENT
    elif binding is not None and binding.status_reason in _HISTORICAL:
        scope = PredictionScope.HISTORICAL
    else:
        scope = PredictionScope.UNCERTAIN_CURRENT
    usable = status is BindingStatus.VALID or (
        status is BindingStatus.STALE and binding is not None and binding.status_reason in _LIVE
    )
    executable = usable and surface_match and mature and controller_available
    admissible = executable and not suppressed
    testable = predictable and executable
    if not mature:
        reason = AvailabilityReason.NOT_MATURE
    elif binding is None:
        reason = AvailabilityReason.UNBOUND
    elif status is BindingStatus.INVALIDATED:
        reason = AvailabilityReason.BINDING_INVALIDATED
    elif not usable:
        reason = AvailabilityReason.BINDING_STALE
    elif not surface_match:
        reason = AvailabilityReason.SURFACE_MISMATCH
    elif not controller_available:
        reason = AvailabilityReason.CONTROLLER_UNAVAILABLE
    elif suppressed:
        reason = AvailabilityReason.EXECUTIVELY_SUPPRESSED
    else:
        reason = AvailabilityReason.OK
    return CompetenceAvailability(
        competence_id=competence.competence_id,
        maturity=competence.maturity,
        binding_status=status,
        surface_match=surface_match,
        controller_available=controller_available,
        suppressed=suppressed,
        predictable_now=predictable,
        prediction_scope=scope,
        executable_now=executable,
        admissible_now=admissible,
        testable_now=testable,
        actionable_test_now=testable and admissible,
        reason=reason,
    )


__all__ = [
    "AvailabilityReason",
    "CompetenceAvailability",
    "PredictionScope",
    "derive_availability",
]
