from __future__ import annotations

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning.temporal_private_model_controls import (
    _normalize_seeds,
    temporal_controls,
    temporal_history,
)


def test_temporal_controls_protocol_registered():
    assert (
        get_protocol("learning.temporal-private-model-controls").__name__
        == "run_temporal_private_model_controls_study"
    )


def test_temporal_history_has_embodied_causal_shape():
    records = temporal_history(seed=101, ticks=96)

    assert len(records) == 96
    assert all(record.record_id.startswith("transition.control.") for record in records)
    assert all(
        record.action_token and record.action_token.startswith("action.motor.")
        for record in records
    )
    assert all(record.outcome_tokens[0].startswith("outcome.sense.") for record in records)
    assert all(
        any(token.startswith("state.sense.") for token in record.context_tokens)
        for record in records
    )


def test_temporal_controls_break_only_the_declared_relation():
    records = temporal_history(seed=127, ticks=96)
    controls = temporal_controls(records, seed=127)

    causal = controls["causal"]
    action = controls["action_shuffled"]
    outcome = controls["next_state_shuffled"]
    no_action = controls["no_action"]

    assert tuple(r.context_tokens for r in action) == tuple(r.context_tokens for r in causal)
    assert tuple(r.outcome_tokens for r in action) == tuple(r.outcome_tokens for r in causal)
    assert any(a.action_token != b.action_token for a, b in zip(action, causal))

    assert tuple(r.context_tokens for r in outcome) == tuple(r.context_tokens for r in causal)
    assert tuple(r.action_token for r in outcome) == tuple(r.action_token for r in causal)
    assert any(a.outcome_tokens != b.outcome_tokens for a, b in zip(outcome, causal))

    assert tuple(r.context_tokens for r in no_action) == tuple(r.context_tokens for r in causal)
    assert tuple(r.outcome_tokens for r in no_action) == tuple(r.outcome_tokens for r in causal)
    assert all(r.action_token is None for r in no_action)


def test_temporal_control_seed_validation_matches_other_learning_protocols():
    assert _normalize_seeds([101, 127, 149]) == (101, 127, 149)
