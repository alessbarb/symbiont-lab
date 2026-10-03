"""Small deterministic helpers driving AgencyAcquisition without a runtime."""

from __future__ import annotations

from symbiont.actuation.acquisition import AgencyAcquisition
from symbiont.actuation.action import MotorCommand
from symbiont.actuation.commitment import ActionCommitment
from symbiont.actuation.surface import derive_actuator_constitution

SURFACE = derive_actuator_constitution(3, physical_contract="dimension-unit")
A, B, C = SURFACE.actuator_ids


def commitment(index: int, *, competence_id: str | None = None) -> ActionCommitment:
    return ActionCommitment(
        commitment_id=f"commitment.{index}",
        proposal_id=f"proposal.{index}",
        effect_target_id=None,
        competence_id=competence_id,
        started_tick=index,
        controller_id="controller.sensorimotor-exploration",
        surface_fingerprint=SURFACE.contract_fingerprint,
    )


def act(
    acquisition: AgencyAcquisition,
    tick: int,
    channels: dict[str, float],
    changes: dict[str, float],
    *,
    competence_id: str | None = None,
    body_schema=None,
):
    commitment_ = commitment(tick, competence_id=competence_id)
    command = MotorCommand.from_mapping(
        command_id=f"command.{tick}",
        commitment_id=commitment_.commitment_id,
        controller_id=commitment_.controller_id,
        competence_id=competence_id,
        surface_fingerprint=SURFACE.contract_fingerprint,
        channels=channels,
        issued_at_tick=tick,
    )
    acquisition.open_attempt(
        command=command,
        commitment=commitment_,
        context_ref="context.unit",
        actuation_ref=f"actuation.{tick}",
        tick=tick,
    )
    effect = acquisition.effect_space.observe(changes)
    transition = acquisition.close_attempt(
        tick=tick + 1,
        state_before_ref=f"state.{tick}",
        state_after_ref=f"state.{tick + 1}",
        prediction_ref=None,
        observed_effect_id=effect.effect_id if effect is not None else None,
        prediction_error=None,
        observed_changes=changes,
    )
    return acquisition.learn(transition, body_schema=body_schema)


def rest(acquisition: AgencyAcquisition, tick: int, changes: dict[str, float]) -> None:
    acquisition.observe_passive_window(
        tick_start=tick,
        tick_end=tick + 1,
        context_ref="context.unit",
        prior_state_ref=f"state.{tick}",
        resulting_state_ref=f"state.{tick + 1}",
        changes=changes,
    )


def fresh_acquisition() -> AgencyAcquisition:
    acquisition = AgencyAcquisition()
    acquisition.bind_surface(SURFACE.actuator_ids, surface_fingerprint=SURFACE.contract_fingerprint)
    return acquisition


def acquire_agentic_dimension(
    acquisition: AgencyAcquisition,
    *,
    channels: dict[str, float],
    changes: dict[str, float],
    start_tick: int = 0,
    repetitions: int = 8,
    body_schema=None,
) -> int:
    """Quiet windows, then a repeated specific intervention; returns next free tick."""
    tick = start_tick
    for _ in range(8):
        rest(acquisition, tick, {})
        tick += 2
    for _ in range(repetitions):
        act(acquisition, tick, channels, changes, body_schema=body_schema)
        tick += 2
    return tick
