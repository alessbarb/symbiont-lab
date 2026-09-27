"""Executive Outcome Learning v1 evidence, policy and bounds (EOL §4-§9)."""

from __future__ import annotations

import pytest

from symbiont.agency.executive_outcome import (
    NO_HISTORY,
    CausalRevisionState,
    ExecutiveAdmissionModulator,
    ExecutiveOutcomeEvidence,
    ExecutiveOutcomeLedger,
    ExecutiveOutcomeSample,
    OutcomeClass,
    classify_outcome,
)

KEY = ("competence.c", "effect.e", "context.x")
OTHER = ("competence.d", "effect.f", "context.x")
STATE = CausalRevisionState(
    binding_fingerprint="surface|effect.e|10",
    executable=False,
    controllability_revision=10,
    agency_revision=10,
)


def _sample(
    outcome_class: OutcomeClass, *, tick: int = 1, reason: str = "r"
) -> ExecutiveOutcomeSample:
    return ExecutiveOutcomeSample(
        tick=tick,
        outcome_class=outcome_class,
        reason=reason,
        effect_similarity=None,
        prediction_mismatch=None,
        progress_before_failure=None,
    )


@pytest.mark.parametrize(
    ("status", "reason", "binding", "expected"),
    [
        ("satisfied", "anticipated_effect_observed", False, OutcomeClass.POSITIVE),
        ("failed", "repeated_high_mismatch", False, OutcomeClass.CONTRADICTING),
        (
            "failed",
            "competence_exhausted_without_anticipated_consequence",
            False,
            OutcomeClass.CONTRADICTING,
        ),
        ("failed", "stagnation", False, OutcomeClass.CONTRADICTING),
        ("failed", "controller_terminal_failure", True, OutcomeClass.TERMINAL),
        ("failed", "commitment_terminal_failure", True, OutcomeClass.TERMINAL),
        ("failed", "controller_terminal_failure", False, OutcomeClass.NEUTRAL),
        ("invalidated", "surface_incompatible", True, OutcomeClass.SUPPRESS),
        ("invalidated", "competence_no_longer_executable", True, OutcomeClass.SUPPRESS),
        ("invalidated", "required_causal_binding_invalidated", True, OutcomeClass.SUPPRESS),
        ("invalidated", "embodiment_changed", True, OutcomeClass.SUPPRESS),
        ("interrupted", "protection_takes_priority", True, OutcomeClass.NEUTRAL),
        ("interrupted", "new_motor_authority_supersedes_commitment", True, OutcomeClass.NEUTRAL),
        ("rejected", "proposal_not_selected", True, OutcomeClass.NEUTRAL),
        ("satisfied", "commitment_completed_unverified", True, OutcomeClass.NEUTRAL),
    ],
)
def test_outcome_classes_follow_the_failure_reason(status, reason, binding, expected):
    assert (
        classify_outcome(status=status, reason=reason, binding_valid_at_start=binding) is expected
    )


def test_confidence_formula_and_bounded_factor():
    modulator = ExecutiveAdmissionModulator()
    evidence = ExecutiveOutcomeEvidence()
    assert modulator.confidence(evidence) == 0.5 and modulator.factor(evidence) == 1.0
    evidence.samples.append(_sample(OutcomeClass.CONTRADICTING))
    evidence.samples.append(_sample(OutcomeClass.TERMINAL))
    # (1 + 0) / (2 + 0 + 1 + 2 * 1) = 0.2 -> 0.4, clamped to 0.5
    assert modulator.confidence(evidence) == pytest.approx(0.2)
    assert modulator.factor(evidence) == 0.5
    positive = ExecutiveOutcomeEvidence()
    for tick in range(16):
        positive.samples.append(_sample(OutcomeClass.POSITIVE, tick=tick))
    assert modulator.confidence(positive) == pytest.approx(17 / 18)
    assert modulator.factor(positive) == 1.5  # clamped: history never dominates relevance


def test_window_keeps_the_last_sixteen_real_outcomes():
    ledger = ExecutiveOutcomeLedger()
    for tick in range(20):
        ledger.record(KEY, _sample(OutcomeClass.CONTRADICTING, tick=tick))
    evidence = ledger.get(KEY)
    assert evidence is not None and len(evidence.samples) == 16
    assert evidence.samples[0].tick == 4


def test_neutral_outcomes_are_never_evidence():
    with pytest.raises(ValueError):
        ExecutiveOutcomeLedger().record(KEY, _sample(OutcomeClass.NEUTRAL))


def test_modulation_is_per_key():
    ledger = ExecutiveOutcomeLedger()
    ledger.record(KEY, _sample(OutcomeClass.POSITIVE))
    assert ledger.modulation(KEY, revision=None).factor > 1.0
    assert ledger.modulation(OTHER, revision=None) == NO_HISTORY


def test_suppression_lifts_only_on_relevant_revision():
    ledger = ExecutiveOutcomeLedger()
    ledger.record(
        KEY, _sample(OutcomeClass.SUPPRESS, reason="surface_incompatible"), revision=STATE
    )
    assert ledger.modulation(KEY, revision=STATE).suppressed
    # Time passing alone never lifts it.
    assert ledger.modulation(KEY, revision=STATE).suppressed
    revised = CausalRevisionState(
        binding_fingerprint=STATE.binding_fingerprint,
        executable=STATE.executable,
        controllability_revision=11,
        agency_revision=STATE.agency_revision,
    )
    modulation = ledger.modulation(KEY, revision=revised)
    assert not modulation.suppressed and modulation.had_history


def test_suppression_requires_the_state_it_is_judged_against():
    with pytest.raises(ValueError):
        ExecutiveOutcomeLedger().record(KEY, _sample(OutcomeClass.SUPPRESS))


def test_ledger_is_bounded_and_reports_saturation():
    ledger = ExecutiveOutcomeLedger(max_keys=2)
    for index in range(3):
        ledger.record((f"competence.{index}", "effect.e", None), _sample(OutcomeClass.POSITIVE))
    ledger.record(("competence.2", "effect.e", None), _sample(OutcomeClass.POSITIVE))
    ledger.modulation(("competence.0", "effect.e", None), revision=None)  # evicted
    ledger.modulation(("competence.2", "effect.e", None), revision=None)
    metrics = ledger.metrics()
    assert len(ledger) == 2
    assert metrics["keys_created"] == 3 and metrics["keys_evicted"] == 1
    assert metrics["single_sample_key_fraction"] == 0.5
    assert metrics["mean_samples_per_key"] == 1.5
    assert metrics["history_hit_rate"] == 0.5


def test_ledger_checkpoint_round_trip_is_exact():
    ledger = ExecutiveOutcomeLedger()
    ledger.record(KEY, _sample(OutcomeClass.TERMINAL, reason="controller_terminal_failure"))
    ledger.record(
        OTHER, _sample(OutcomeClass.SUPPRESS, reason="embodiment_changed"), revision=STATE
    )
    ledger.modulation(KEY, revision=None)
    restored = ExecutiveOutcomeLedger.restore(ledger.checkpoint())
    assert restored.checkpoint() == ledger.checkpoint()
    assert restored.modulation(OTHER, revision=STATE).suppressed
    assert ExecutiveOutcomeLedger.restore(None).checkpoint()["entries"] == []
