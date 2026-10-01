"""Promotion Stability v1 D1: paired candidate-vs-ACTIVE evaluation.

Observational instrument: the current ACTIVE is evaluated on the candidate's
held-out split with its own tokenizer; the training result is unchanged.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

pytest.importorskip("torch")

from symbiont.modeling import ModeledOrganismRuntime
from symbiont_lab.physics3d.private_model_training import _train_job
from tests.unit.modeling.test_modeled_organism_runtime import _transition


@pytest.mark.slow
def test_paired_reference_is_observational(tmp_path):
    runtime = ModeledOrganismRuntime(organism_id="paired-promotion")
    for tick in range(64):
        runtime.record_experience(_transition(runtime, tick))
    root_plan = runtime.autonomous_private_learning_plan()
    root = _train_job(
        str(tmp_path), root_plan.request, root_plan.corpus, root_plan.tokenizer.vocabulary, "cpu"
    )
    assert root["paired_reference"] is None
    for tick in range(64, 200):  # a corpus with tokens the reference never saw
        record = _transition(runtime, tick)
        runtime.record_experience(replace(record, outcome_tokens=(f"outcome.novel.{tick % 7}",)))
    plan = runtime.autonomous_private_learning_plan()
    args = (str(tmp_path), plan.request, plan.corpus, plan.tokenizer.vocabulary, "cpu", None)
    plain = _train_job(*args)
    paired = _train_job(*args, root["model_id"])

    reference = paired.pop("paired_reference")
    plain.pop("paired_reference")
    assert paired == plain  # the instrument changes nothing about the candidate
    assert "error" not in reference
    assert reference["reference_model_id"] == root["model_id"]
    assert reference["reference_loss"] > 0
    assert reference["reference_predictions"] == reference["candidate_predictions"]
    assert 0 < reference["reference_unknown_target_fraction"] <= 1


@pytest.mark.slow
def test_common_vocabulary_loss_is_fair(tmp_path):
    from symbiont_lab.physics3d.private_model_training import _paired_reference_evaluation

    runtime = ModeledOrganismRuntime(organism_id="paired-common")
    for tick in range(64):
        runtime.record_experience(_transition(runtime, tick))
    root_plan = runtime.autonomous_private_learning_plan()
    root = _train_job(
        str(tmp_path), root_plan.request, root_plan.corpus, root_plan.tokenizer.vocabulary, "cpu"
    )
    for tick in range(64, 200):
        record = _transition(runtime, tick)
        if tick % 2:  # half the outcomes stay in the reference vocabulary
            record = replace(record, outcome_tokens=(f"outcome.novel.{tick % 7}",))
        runtime.record_experience(record)
    plan = runtime.autonomous_private_learning_plan()
    candidate = _train_job(
        str(tmp_path),
        plan.request,
        plan.corpus,
        plan.tokenizer.vocabulary,
        "cpu",
        None,
        root["model_id"],
    )["paired_reference"]
    assert 0 < candidate["common_targets"] < candidate["reference_predictions"]
    assert candidate["candidate_common_loss"] > 0 and candidate["reference_common_loss"] > 0

    # A model paired with itself scores identically on the common targets.
    itself = _paired_reference_evaluation(
        str(tmp_path),
        root["model_id"],
        plan.corpus,
        plan.request.context_window,
        root["model_id"],
        tuple(root["vocabulary"]),
    )
    assert itself["candidate_common_loss"] == pytest.approx(itself["reference_common_loss"])
