from __future__ import annotations

from symbiont.actuation.action import (
    ActionEvaluation,
    ActionJustification,
    ActionProposal,
    ActionSource,
)
from symbiont.core.regulation import (
    ActionArbitrator,
    InnateReactivity,
    ReactiveMemory,
)


def test_innate_reactivity_detects_worsening_without_anatomy() -> None:
    system = InnateReactivity(acute_velocity=0.02, smoothing=1.0)
    first = system.evaluate(
        percepts={"signal.a": 0.2, "signal.b": 0.4},
        homeostatic_deviation=0.10,
    )
    second = system.evaluate(
        percepts={"signal.a": 0.2, "signal.b": 0.4},
        homeostatic_deviation=0.20,
    )
    assert first.withdrawal == 0.0
    assert second.withdrawal == 1.0
    assert second.interrupt == 1.0


def test_innate_reactivity_orients_to_opaque_unexpected_change() -> None:
    system = InnateReactivity(surprise_threshold=0.10, smoothing=1.0)
    system.evaluate(percepts={"opaque.7": 0.1}, homeostatic_deviation=0.1)
    state = system.evaluate(
        percepts={"opaque.7": 0.9},
        homeostatic_deviation=0.1,
    )
    assert state.surprise > 0.7
    assert state.interrupt > 0.7
    assert state.withdrawal == 0.0


def test_reactive_memory_requires_repeated_real_relief() -> None:
    memory = ReactiveMemory()
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=0.2)
    assert (
        memory.best(
            signature="r3:s0:c0",
            candidates=("primitive.x",),
        )
        is None
    )
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=0.2)
    assert (
        memory.best(
            signature="r3:s0:c0",
            candidates=("primitive.x",),
        )
        == "primitive.x"
    )


def test_negative_experience_prevents_fast_response() -> None:
    memory = ReactiveMemory()
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=-0.2)
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=-0.1)
    assert (
        memory.best(
            signature="r3:s0:c0",
            candidates=("primitive.x",),
        )
        is None
    )


def test_arbitrator_never_invents_protective_motor_action() -> None:
    decision = ActionArbitrator().choose(
        proposals=(),
        current=None,
        tick=1,
    )
    assert decision.proposal is None
    assert decision.reason == "no_valid_proposal"

    proposal = ActionProposal(
        proposal_id="proposal.protection",
        source=ActionSource.PROTECTION,
        effect_target_id=None,
        competence_id="competence.safe",
        justification=ActionJustification(
            competence_id="competence.safe",
        ),
        evaluation=ActionEvaluation(
            protective_relevance=1.0,
            homeostatic_relevance=1.0,
            effect_confidence=0.8,
            controllability=0.8,
            uncertainty=0.2,
        ),
    )
    selected = ActionArbitrator().choose(
        proposals=(proposal,),
        current=None,
        tick=1,
    )
    assert selected.proposal is proposal
    assert selected.reason == "protective_dominance"


def test_reactive_checkpoint_roundtrip() -> None:
    system = InnateReactivity(smoothing=1.0)
    system.evaluate(percepts={"opaque.1": 0.2}, homeostatic_deviation=0.1)
    restored = InnateReactivity.restore(system.checkpoint())
    state = restored.evaluate(
        percepts={"opaque.1": 0.8},
        homeostatic_deviation=0.2,
    )
    assert state.interrupt > 0.0

    memory = ReactiveMemory()
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=0.2)
    memory.observe(signature="r3:s0:c0", primitive_id="primitive.x", relief=0.2)
    restored_memory = ReactiveMemory.restore(memory.checkpoint())
    assert (
        restored_memory.best(
            signature="r3:s0:c0",
            candidates=("primitive.x",),
        )
        == "primitive.x"
    )
