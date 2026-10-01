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
from symbiont_lab.physics3d.private_model_training import _train_job
from tests.unit.modeling.test_modeled_organism_runtime import _transition


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

    for tick in range(64, 400):  # same token set as the root: no vocabulary expansion
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


@pytest.mark.slow
def test_lineage_mechanics_only(tmp_path):
    """Private Model Learnability v1 §8 separate item: mechanics P5 could not
    exercise, with a deliberately forced eligible parent. Never evidence that
    ancestry helps; only that the implementation works."""
    import io
    from collections import Counter
    from dataclasses import replace

    import torch

    from symbiont.modeling.tokenizer import _record_tokens
    from symbiont_lab.modeling.architectures import architecture_spec_from_manifest, build_model
    from symbiont_lab.modeling.dataset import encode_corpus
    from symbiont_lab.modeling.trainer import _extend_vocabulary_state

    runtime = ModeledOrganismRuntime(organism_id="ancestry-mechanics")
    runtime.ancestry_training = True
    store = FileArtifactStore(tmp_path)
    for tick in range(64):
        runtime.record_experience(_transition(runtime, tick))
    root_plan = runtime.autonomous_private_learning_plan()
    root = _train_job(
        str(tmp_path), root_plan.request, root_plan.corpus, root_plan.tokenizer.vocabulary, "cpu"
    )
    parent_artifact = store.get(root["model_id"])
    parent_vocabulary = tuple(root["vocabulary"])
    parent = runtime.adopt_private_model(
        parent_artifact.manifest,
        evaluation_summary=(0,),
        validation_loss=1.0,  # forced eligible
        baseline_loss=2.0,
        vocabulary=parent_vocabulary,
    )
    for tick in range(64, 400):  # tokens the parent never saw
        record = _transition(runtime, tick)
        runtime.record_experience(
            replace(
                record,
                context_tokens=(f"sense.novel.{tick % 6}",),
                outcome_tokens=(f"outcome.novel.{tick % 7}",),
            )
        )

    # A retired parent cannot be selected (checked on a restored copy).
    retired = ModeledOrganismRuntime.from_checkpoint(runtime.checkpoint())
    retired.retire_private_model(parent.model_id)
    retired_plan = retired.autonomous_private_learning_plan()
    assert retired_plan is not None and retired_plan.request.parent_model_id is None

    child_plan = runtime.autonomous_private_learning_plan()
    assert child_plan.request.parent_model_id == parent.model_id

    # New tokens appended deterministically: corpus frequency desc, then lexical.
    counts = Counter(
        token
        for record in child_plan.corpus.train
        for token in _record_tokens(record)
        if token not in set(parent_vocabulary)
    )
    expected = tuple(sorted(counts, key=lambda token: (-counts[token], token)))
    assert expected and child_plan.tokenizer.vocabulary == parent_vocabulary + expected

    # Parent rows are inherited at the same ids; appended rows keep the seeded init.
    encoded = encode_corpus(
        child_plan.corpus, child_plan.tokenizer, context_window=child_plan.request.context_window
    )
    torch.manual_seed(child_plan.request.seed)
    child_init = build_model(
        child_plan.request.architecture_id,
        vocab_size=encoded.vocab_size,
        context_window=child_plan.request.context_window,
        pad_id=encoded.pad_id,
        spec=architecture_spec_from_manifest(parent_artifact.manifest),
    ).state_dict()
    parent_state = torch.load(io.BytesIO(parent_artifact.weights), weights_only=True)
    merged = _extend_vocabulary_state(parent_state, child_init, len(parent_vocabulary), torch)
    widened = 0
    for key, tensor in merged.items():
        if tensor.shape == parent_state[key].shape:
            assert torch.equal(tensor, parent_state[key])
        else:
            widened += 1
            assert torch.equal(tensor[: len(parent_vocabulary)], parent_state[key])
            assert torch.equal(
                tensor[len(parent_vocabulary) :], child_init[key][len(parent_vocabulary) :]
            )
    assert widened >= 2  # input embedding and output projection

    child = _train_job(
        str(tmp_path),
        child_plan.request,
        child_plan.corpus,
        child_plan.tokenizer.vocabulary,
        "cpu",
        child_plan.parent_vocabulary,
    )
    record = runtime.adopt_private_model(
        store.get(child["model_id"]).manifest,
        evaluation_summary=(0,),
        validation_loss=child["candidate_loss"],
        baseline_loss=child["best_baseline_loss"],
        vocabulary=tuple(child["vocabulary"]),
    )
    assert record.generation == parent.generation + 1
    assert record.state is ModelState.SHADOW and runtime.model_registry.active is None

    # Checkpoint -> restore: same ancestry, tokenizers and (content-addressed) weights.
    restored = ModeledOrganismRuntime.from_checkpoint(runtime.checkpoint())
    restored_record = restored.model_registry.get(record.model_id)
    assert restored_record == record
    assert restored.checkpoint()["training_ancestry"] == runtime.checkpoint()["training_ancestry"]
    assert store.get(record.model_id).weights == store.get(child["model_id"]).weights
