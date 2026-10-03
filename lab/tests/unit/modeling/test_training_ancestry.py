"""Revision Coherence §8.4 (Wave 5): training ancestry of non-authoritative models.

Gates exercised here: ancestry-eligible implies tokenizer available (retirement
removes both), the best eligible SHADOW is protected from recency retirement,
lineages stagnate after 3 non-improving children, the plan inherits the
parent's vocabulary append-only, restore keeps the exact ancestry-capable
tokenizers, and ancestry never grants control.
"""

from __future__ import annotations

import pytest

from symbiont.modeling import (
    ArchitectureId,
    ModelArtifactManifest,
    ModeledOrganismRuntime,
    ModelObjective,
    ModelState,
    TrainingRequest,
)

from .test_modeled_organism_runtime import _transition

VOCAB = ("<PAD>", "<UNK>", "<BOS>", "<EOS>", "<SEP>", "sense.test.0", "action.test.0")


def _manifest(runtime, *, seed, parent=None, weights="c"):
    request = TrainingRequest(
        organism_id=runtime.organism_id,
        corpus_hash="a" * 64,
        tokenizer_hash="b" * 64,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=seed,
        context_window=32,
        requested_parameters=1_000_000,
        requested_epochs=4,
        requested_steps=100,
        created_tick_class=seed,
        parent_model_id=parent.model_id if parent is not None else None,
        adaptation_reason="ancestry" if parent is not None else None,
    )
    return ModelArtifactManifest.build(
        request=request,
        parameter_count=100_000,
        weights_hash=(weights * 64)[:64],
        artifact_bytes=1024,
        parent=parent,
    )


def _adopt(runtime, *, seed, loss, baseline=2.0, parent=None, vocabulary=VOCAB, weights="c"):
    manifest = _manifest(runtime, seed=seed, parent=parent, weights=weights)
    record = runtime.adopt_private_model(
        manifest,
        evaluation_summary=(0,),
        validation_loss=loss,
        baseline_loss=baseline,
        vocabulary=vocabulary,
    )
    return manifest, record


def _runtime():
    runtime = ModeledOrganismRuntime(organism_id="ancestry")
    runtime.ancestry_training = True
    runtime.trace_training_requests = True
    return runtime


def test_eligibility_requires_losses_that_beat_the_baseline_and_a_held_tokenizer():
    runtime = _runtime()
    _, good = _adopt(runtime, seed=1, loss=1.0)
    _, poor = _adopt(runtime, seed=2, loss=3.0, weights="d")
    _, blind = _adopt(runtime, seed=3, loss=1.0, vocabulary=None, weights="e")
    assert runtime.training_ancestry_eligible(good.model_id)
    assert not runtime.training_ancestry_eligible(poor.model_id)  # worse than baseline
    assert not runtime.training_ancestry_eligible(blind.model_id)  # no tokenizer held

    runtime.retire_private_model(good.model_id)
    assert not runtime.training_ancestry_eligible(good.model_id)
    assert good.model_id not in runtime.checkpoint()["training_ancestry"]["vocabularies"]


def test_best_eligible_shadow_is_protected_and_deferrals_are_counted():
    runtime = _runtime()
    _adopt(runtime, seed=1, loss=1.5)
    _, best = _adopt(runtime, seed=2, loss=1.0, weights="d")
    assert runtime.protected_training_ancestor() == best.model_id
    runtime.note_retirement_deferred(best.model_id)
    runtime.note_retirement_deferred("model.other")  # not protected: not counted
    snapshot = runtime.measurement_snapshot()["private_models"]
    assert snapshot["retirement_deferrals"] == 1 and snapshot["eligible_ancestors"] == 2


def test_lineage_stagnates_after_three_non_improving_children():
    runtime = _runtime()
    parent_manifest, parent = _adopt(runtime, seed=1, loss=1.0)
    for index, weights in enumerate("def"):
        _adopt(
            runtime, seed=10 + index, loss=1.5, parent=parent_manifest, weights=weights
        )  # worse than its parent: not eligible
    chosen, reason = runtime._training_parent()
    assert chosen is None and reason == "lineage-stagnation"


def test_plan_inherits_the_parent_vocabulary_append_only_and_is_traced():
    runtime = _runtime()
    _, parent = _adopt(runtime, seed=1, loss=1.0)
    events = []
    runtime.provenance.subscribe(events.append)
    for tick in range(64):
        runtime.record_experience(_transition(runtime, tick))
    plan = runtime.autonomous_private_learning_plan()
    assert plan is not None and plan.request.parent_model_id == parent.model_id
    assert plan.parent_vocabulary == VOCAB
    assert plan.tokenizer.vocabulary[: len(VOCAB)] == VOCAB  # same ids, nothing lost
    assert len(plan.tokenizer.vocabulary) > len(VOCAB)
    (event,) = [e for e in events if e.domain == "private_model"]
    assert event.parameters["parent_model_id"] == parent.model_id
    assert event.parameters["corpus_hash"] == plan.corpus.manifest.corpus_hash


def test_restore_keeps_the_exact_ancestry_capable_tokenizers():
    runtime = _runtime()
    _, parent = _adopt(runtime, seed=1, loss=1.0)
    restored = ModeledOrganismRuntime.from_checkpoint(runtime.checkpoint())
    assert restored.ancestry_training and restored.training_ancestry_eligible(parent.model_id)
    assert restored.checkpoint()["training_ancestry"] == runtime.checkpoint()["training_ancestry"]


def test_ancestry_never_grants_action_authority():
    runtime = _runtime()
    parent_manifest, _ = _adopt(runtime, seed=1, loss=1.0)
    _, child = _adopt(runtime, seed=2, loss=0.5, parent=parent_manifest, weights="d")
    assert child.state is ModelState.SHADOW and child.generation == 1
    assert runtime.model_registry.active is None
    with pytest.raises(ValueError):
        runtime.activate_private_model(
            child.model_id, promotion_authorized=False, evaluation_summary=(0,)
        )


def test_defaults_leave_checkpoints_without_ancestry_state():
    runtime = ModeledOrganismRuntime(organism_id="plain")
    runtime.adopt_private_model(_manifest(runtime, seed=1), evaluation_summary=(0,))
    assert "training_ancestry" not in runtime.checkpoint()
