from __future__ import annotations

from symbiont.core.individual import create_individual


def test_reduced_symbiont_physical_output_has_canonical_action_trace() -> None:
    individual = create_individual(
        "symbiont.action-authority",
        "body.action-authority",
        num_receptors=2,
        num_effectors=2,
    )
    individual.symbiont.exploration_rate = 1.0
    individual.step({"stimulus.a": 0.2})
    command = individual.symbiont.action_domain.last_motor_command
    assert command is not None
    assert command.embodiment_id == individual.embodiment_id
    trace = individual.symbiont.action_domain.trace_action(command.command_id)
    assert trace is not None
    assert trace.commitment_id == command.commitment_id


def test_passive_change_without_command_is_not_motor_causal_evidence() -> None:
    individual = create_individual(
        "symbiont.passive-authority",
        "body.passive-authority",
        num_receptors=2,
        num_effectors=0,
    )
    individual.step({"stimulus.a": 0.2})
    individual.step({"stimulus.a": 0.8})
    assert individual.symbiont.causal_evidence.evidence == ()
