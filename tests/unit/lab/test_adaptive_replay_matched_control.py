from __future__ import annotations

from types import SimpleNamespace

from symbiont.modeling import ModeledOrganismRuntime
from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning import adaptive_replay_matched_control as study


def test_adaptive_replay_protocol_registered():
    assert (
        get_protocol("learning.adaptive-replay-matched-control").__name__
        == "run_adaptive_replay_matched_control_study"
    )


def test_matched_control_request_changes_only_replay_budget():
    runtime = ModeledOrganismRuntime(
        organism_id="matched-request",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    for record in study._transition_history(
        organism_id=runtime.organism_id,
        seed=101,
        ticks=128,
    ):
        runtime.record_experience(record)

    plan = runtime.autonomous_private_learning_plan()
    assert plan is not None
    control = study._matched_control_request(plan)
    treatment = plan.request

    assert control.organism_id == treatment.organism_id
    assert control.corpus_hash == treatment.corpus_hash
    assert control.tokenizer_hash == treatment.tokenizer_hash
    assert control.architecture_id is treatment.architecture_id
    assert control.objective is treatment.objective
    assert control.seed == treatment.seed
    assert control.context_window == treatment.context_window
    assert control.requested_parameters == treatment.requested_parameters
    assert control.created_tick_class == treatment.created_tick_class
    assert control.requested_epochs == 2
    assert control.requested_steps == 12
    assert treatment.requested_epochs >= control.requested_epochs
    assert treatment.requested_steps >= control.requested_steps


def test_matched_control_study_uses_identical_corpus_for_both_arms(monkeypatch):
    seen: list[tuple[str, str, int, int]] = []

    def fake_train_and_score(*, request, corpus, tokenizer):
        seen.append(
            (
                request.corpus_hash,
                tokenizer.tokenizer_hash,
                request.requested_epochs,
                request.requested_steps,
            )
        )
        loss = 1.0 - request.requested_steps / 1000.0
        accuracy = request.requested_steps / 100.0
        return SimpleNamespace(mean_log_loss=loss, accuracy=accuracy)

    monkeypatch.setattr(study, "_train_and_score", fake_train_and_score)

    result = study.run_adaptive_replay_matched_control_study(
        seeds=(101,),
        ticks=128,
    )

    assert len(seen) == 2
    assert seen[0][0] == seen[1][0]
    assert seen[0][1] == seen[1][1]
    assert seen[0][2:] != seen[1][2:]
    assert result.per_seed[0].loss_gain > 0.0
    assert result.per_seed[0].accuracy_gain > 0.0


def test_transition_history_is_deterministic_and_opaque():
    left = study._transition_history(
        organism_id="same-organism",
        seed=127,
        ticks=128,
    )
    right = study._transition_history(
        organism_id="same-organism",
        seed=127,
        ticks=128,
    )
    assert left == right
    model_tokens = {
        token
        for record in left
        for token in (*record.context_tokens, record.action_token or "", *record.outcome_tokens)
    }
    assert all("adaptive-replay" not in token for token in model_tokens)
