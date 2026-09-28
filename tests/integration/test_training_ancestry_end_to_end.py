"""Revision Coherence §8.4: a SHADOW ancestor trains a child through ``adapt``.

End-to-end mechanics with real (tiny) training in-process: the child request
names the parent, its tokenizer extends the parent's append-only, the trainer
inherits the parent's rows, and the adopted child is generation 1 and never
ACTIVE by ancestry. The parent's losses are set explicitly to make it eligible:
this checks the path, not model quality (that is P5's question).
"""

from __future__ import annotations

import pytest

pytest.importorskip("torch")

from symbiont.modeling import ModeledOrganismRuntime, ModelState
from symbiont_lab.modeling.artifacts import FileArtifactStore
from symbiont_lab.physics3d.slm import _train_job
from tests.unit.test_modeled_organism_runtime import _transition


@pytest.mark.slow
def test_shadow_ancestor_trains_a_child_with_an_inherited_vocabulary(tmp_path):
    runtime = ModeledOrganismRuntime(organism_id="ancestry-e2e")
    runtime.ancestry_training = True
    runtime.trace_training_requests = True
    store_dir = tmp_path / "models"
    store_dir.mkdir()
    for tick in range(64):
        runtime.record_experience(_transition(runtime, tick))
    root_plan = runtime.autonomous_private_learning_plan()
    assert root_plan is not None and root_plan.request.parent_model_id is None
    root = _train_job(
        str(store_dir), root_plan.request, root_plan.corpus, root_plan.tokenizer.vocabulary, "cpu"
    )
    manifest = FileArtifactStore(store_dir).get(root["model_id"]).manifest
    parent = runtime.adopt_private_model(
        manifest,
        evaluation_summary=(0,),
        validation_loss=1.0,
        baseline_loss=2.0,
        vocabulary=tuple(root["vocabulary"]),
    )
    assert parent.state is ModelState.SHADOW

    for tick in range(64, 400):  # new ticks bring new tokens
        runtime.record_experience(_transition(runtime, tick * 7))
    child_plan = runtime.autonomous_private_learning_plan()
    assert child_plan is not None and child_plan.request.parent_model_id == parent.model_id
    parent_vocabulary = tuple(root["vocabulary"])
    assert child_plan.tokenizer.vocabulary[: len(parent_vocabulary)] == parent_vocabulary
    child = _train_job(
        str(store_dir),
        child_plan.request,
        child_plan.corpus,
        child_plan.tokenizer.vocabulary,
        "cpu",
        child_plan.parent_vocabulary,
    )
    child_manifest = FileArtifactStore(store_dir).get(child["model_id"]).manifest
    record = runtime.adopt_private_model(
        child_manifest,
        evaluation_summary=(0,),
        validation_loss=child["candidate_loss"],
        baseline_loss=child["best_baseline_loss"],
        vocabulary=tuple(child["vocabulary"]),
    )
    assert record.parent_model_id == parent.model_id and record.generation == 1
    assert record.state is ModelState.SHADOW
    assert tuple(child["vocabulary"])[: len(parent_vocabulary)] == parent_vocabulary
