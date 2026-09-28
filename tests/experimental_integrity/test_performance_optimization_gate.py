"""P0 — multi-dimensional performance optimization gate.

This file is deliberately about *equivalence*, not speed.  Wall-clock timing is
measured by scripts/bench_observability_tax.py because timing assertions are too
noisy for deterministic CI.

The gate establishes the contract every later performance change must preserve:
observer-side reads may inspect the organism, but may not change its causal
future for the same seed, body and tick schedule.
"""

from __future__ import annotations

from dataclasses import dataclass

from symbiont.core.orchestration.runtime import OrganismRuntime, RuntimeTickResult
from symbiont_lab.studies.learning.agency_acquisition_body import (
    CausalBody,
    build_subject,
)


@dataclass(frozen=True)
class GateTrace:
    """A diagnostic projection of one organism tick.

    state_hash remains the strongest whole-state equality check.  The additional
    fields make failures local: a future optimization should report whether it
    changed motor authority, causal provenance, competence development or
    representation maturity rather than only saying that a hash diverged.
    """

    tick: int
    state_hash: str
    motor_intents: tuple[object, ...]
    actuations: tuple[object, ...]
    provenance_events: tuple[object, ...]
    competence_candidates: tuple[dict[str, object], ...]
    available_competences: tuple[str, ...]
    representation_maturity: tuple[tuple[str, int], ...]


def _subject(seed: int = 127) -> tuple[OrganismRuntime, CausalBody]:
    body = CausalBody(actuator_count=4, seed=seed)
    runtime = build_subject(
        body,
        organism_id=f"performance-gate-{seed}",
        factorized_effects=True,
    )
    return runtime, body


def _maturity(runtime: OrganismRuntime) -> tuple[tuple[str, int], ...]:
    bridge = runtime.cognitive_bridge
    if bridge is None:
        return ()
    values = bridge.representation_maturity_counts()
    return tuple(sorted((str(key), int(value)) for key, value in values.items()))


def _trace(runtime: OrganismRuntime, result: RuntimeTickResult) -> GateTrace:
    provenance = runtime._action_domain.acquisition.provenance
    return GateTrace(
        tick=result.tick,
        state_hash=runtime.state_hash(),
        motor_intents=tuple(runtime.last_motor_intents),
        actuations=tuple(runtime.last_actuations),
        provenance_events=tuple(provenance.events()),
        competence_candidates=tuple(runtime.sensorimotor_competence_candidates),
        available_competences=tuple(runtime.available_motor_competence_ids),
        representation_maturity=_maturity(runtime),
    )


def _passive_observer_read(runtime: OrganismRuntime) -> None:
    """Exercise the current passive observation surface.

    These reads intentionally mirror data consumed by the laboratory without
    asking the organism to take another step.  P1 may make them lazy or move
    derived work outside tick(), but their presence must never alter causal
    state.
    """

    before = runtime.state_hash()

    _ = runtime.sensorimotor_snapshot
    _ = runtime.sensorimotor_competence_candidates
    _ = runtime.sensorimotor_competence_episodes
    _ = runtime.available_motor_competence_ids
    _ = runtime.body_schema.export_representation(current_tick=runtime.tick_count)
    _ = tuple(runtime._action_domain.acquisition.provenance.events())

    assert runtime.state_hash() == before, "passive observation mutated organism state"


def test_performance_gate_observer_on_off_is_causally_equivalent() -> None:
    """Gate 1/2/3/5/6: observer presence cannot change the organism."""

    silent, silent_body = _subject()
    observed, observed_body = _subject()

    for _ in range(160):
        silent_result = silent.tick(include_observability=False)
        observed_result = observed.tick(include_observability=True)

        # Capture the actual decision before the external body advances.
        silent_trace = _trace(silent, silent_result)
        observed_trace = _trace(observed, observed_result)
        assert observed_trace == silent_trace

        # Observer ON: inspect after the decision, before the same physical
        # consequence is applied to both matched bodies.
        _passive_observer_read(observed)
        assert observed.state_hash() == silent.state_hash()

        silent_body.advance(silent.last_actuations)
        observed_body.advance(observed.last_actuations)


def test_performance_gate_repeated_matched_runs_emit_identical_causal_history() -> None:
    """Gate 1/2/3/5: the harness itself is deterministic for a fixed seed."""

    first, first_body = _subject(seed=149)
    second, second_body = _subject(seed=149)

    for _ in range(220):
        first_result = first.tick()
        second_result = second.tick()
        assert _trace(first, first_result) == _trace(second, second_result)
        first_body.advance(first.last_actuations)
        second_body.advance(second.last_actuations)

    assert first.state_hash() == second.state_hash()
    assert (
        first._action_domain.acquisition.provenance.events()
        == second._action_domain.acquisition.provenance.events()
    )


def test_headless_tick_omits_only_passive_projections() -> None:
    """P1: suppress observer projections without changing causal state."""

    silent, silent_body = _subject(seed=101)
    observed, observed_body = _subject(seed=101)

    silent_result = silent.tick(include_observability=False)
    observed_result = observed.tick(include_observability=True)

    assert silent_result.narrative == ()
    assert silent_result.sensory_phenotype is None
    assert silent_result.cognition is not None
    assert silent_result.cognition.representation_maturity is None

    # This fixture intentionally has no semantic host senses. On tick 1 it may
    # have no acclimated capabilities yet, so a correctly enabled observer can
    # still have an empty host narrative. Observer activation is instead proven
    # by projections whose source state always exists for this embodied subject.
    assert isinstance(observed_result.narrative, tuple)
    assert observed_result.sensory_phenotype is not None
    assert observed_result.cognition is not None
    assert observed_result.cognition.representation_maturity is not None

    # The bounded life journal, BodySchema, cognition and motor authority remain
    # identical even though one result omits human-facing projections.
    assert silent.state_hash() == observed.state_hash()
    assert silent.last_motor_intents == observed.last_motor_intents
    assert silent.last_actuations == observed.last_actuations
    assert _maturity(silent) == _maturity(observed)

    silent_body.advance(silent.last_actuations)
    observed_body.advance(observed.last_actuations)
