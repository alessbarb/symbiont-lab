"""P6 instrumentation (Private Model Learnability v1 §8).

The learning curve reads every budget from one fixed-budget training, which is
valid only if a prefix of the long run is exactly the shorter run and if the
intermediate evaluations leave training untouched. Both are asserted here.
"""

from __future__ import annotations

import pytest

pytest.importorskip("torch")

import torch

from symbiont.modeling import (
    ArchitectureId,
    EpistemicStatus,
    ExperienceRecord,
    ModelObjective,
    ModelTrainingAuthority,
    NativeTokenizer,
    SourceKind,
    TrainingBudget,
    TrainingRequest,
    build_training_corpus,
)
from symbiont.modeling.ledger import ExperienceLedger, HistoricalExperienceArchive
from symbiont.modeling.runtime import private_causal_records
from symbiont_lab.modeling import TrainingConfig, encode_corpus, train_private_model
from symbiont_lab.modeling.outcome_metrics import evaluate_outcome_model
from symbiont_lab.modeling.trainer import TrainingProbe
from symbiont_lab.studies.learning.private_model_learnability import (
    GRID,
    classify,
    corpus_from_payload,
)

ORGANISM = "organism-learnability"


def _records(count: int = 320) -> tuple[ExperienceRecord, ...]:
    return tuple(
        ExperienceRecord(
            record_id=f"transition.{tick}",
            organism_id=ORGANISM,
            tick_class=tick,
            context_tokens=(f"sense.{tick % 5}", f"state.{tick % 3}"),
            action_token="action.observe",
            outcome_tokens=(f"outcome.{(tick * 7) % 11}",),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=(f"evidence.{tick}",),
            confidence_class=6,
            source_kind=SourceKind.DIRECT,
        )
        for tick in range(count)
    )


def _setup():
    corpus = build_training_corpus(_records())
    tokenizer = NativeTokenizer.from_records(corpus.train)
    return corpus, tokenizer, encode_corpus(corpus, tokenizer, context_window=16)


def _train(ceiling: int, probe_steps: tuple[int, ...], *, evaluate: bool = False):
    corpus, tokenizer, encoded = _setup()
    request = TrainingRequest(
        organism_id=ORGANISM,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=11,
        context_window=16,
        requested_parameters=200_000,
        requested_epochs=64,
        requested_steps=ceiling,
        created_tick_class=0,
    )
    states: dict[int, dict[str, torch.Tensor]] = {}

    def callback(step: int, model) -> None:
        if evaluate:
            evaluate_outcome_model(model, encoded.test, pad_id=encoded.pad_id, context_window=16)
        states[step] = {k: v.detach().clone() for k, v in model.state_dict().items()}

    result = train_private_model(
        request=request,
        corpus=encoded,
        authority=ModelTrainingAuthority(TrainingBudget(max_epochs=64, max_steps=ceiling)),
        # patience=1 would stop a non-fixed run early; the probe must override it.
        config=TrainingConfig(batch_size=16, patience=1),
        probe=TrainingProbe(steps=probe_steps, callback=callback),
    )
    return result, states


def _same(a: dict[str, torch.Tensor], b: dict[str, torch.Tensor]) -> bool:
    return a.keys() == b.keys() and all(torch.equal(a[k], b[k]) for k in a)


def test_prefix_of_long_run_equals_shorter_fixed_budget_run():
    # 40 steps span several epochs of the ~14-batch training split.
    _, long_states = _train(40, (20, 40))
    _, short_states = _train(20, (20,))
    assert _same(long_states[20], short_states[20])


def test_intermediate_evaluation_does_not_change_training():
    _, probed = _train(40, (5, 10, 20, 30, 40), evaluate=True)
    _, quiet = _train(40, (40,))
    assert _same(probed[40], quiet[40])


def test_fixed_budget_disables_every_early_stop():
    result, _ = _train(40, (40,))
    assert result.steps_completed == 40


def test_offline_corpus_uses_the_organism_selection():
    records = _records(64)
    ledger = ExperienceLedger(ORGANISM)
    ledger.extend(records[32:])
    archive = HistoricalExperienceArchive(ORGANISM)
    for record in records[:32]:
        archive.consider(record)
    payload = {
        "organism_id": ORGANISM,
        "experience_ledger": ledger.checkpoint(),
        "experience_archive": archive.checkpoint(),
    }
    _, corpus, tokenizer = corpus_from_payload(payload)
    expected = build_training_corpus(private_causal_records(ledger, archive))
    assert corpus.manifest.corpus_hash == expected.manifest.corpus_hash
    assert tokenizer.tokenizer_hash == NativeTokenizer.from_records(expected.train).tokenizer_hash


def _runs(gaps_by_seed, train_by_seed):
    return [
        {
            "checkpoints": {
                str(step): {"gap": gap, "train_loss": train}
                for step, gap, train in zip(GRID, gaps, trains)
            }
        }
        for gaps, trains in zip(gaps_by_seed, train_by_seed)
    ]


FALLING_TRAIN = [(3.0, 2.8, 2.6, 2.4, 2.2, 2.0)] * 3
FLAT_TRAIN = [(3.0, 3.0, 2.99, 2.99, 2.98, 2.98)] * 3


@pytest.mark.parametrize(
    ("gaps", "train", "outcome"),
    [
        ([(0.8, 0.6, 0.3, 0.1, -0.1, -0.2)] * 3, FALLING_TRAIN, "budget-limited"),
        ([(0.8, 0.6, 0.5, 0.4, 0.38, 0.39)] * 3, FALLING_TRAIN, "budget-limited"),
        ([(0.8, 0.7, 0.6, 0.75, 0.8, 0.9)] * 3, FALLING_TRAIN, "overfitting"),
        ([(0.8, 0.79, 0.78, 0.77, 0.76, 0.75)] * 3, FLAT_TRAIN, "structural"),
        ([(0.8, 0.75, 0.7, 0.62, 0.55, 0.5)] * 3, FALLING_TRAIN, "mixed"),
    ],
)
def test_classification_follows_the_preregistered_rules(gaps, train, outcome):
    assert classify(_runs(gaps, train))["outcome"] == outcome


def test_classification_uses_the_median_over_seeds():
    gaps = [
        (0.8, 0.6, 0.3, 0.1, -0.1, -0.2),
        (0.8, 0.79, 0.78, 0.77, 0.76, 0.75),
        (0.8, 0.79, 0.78, 0.77, 0.76, 0.75),
    ]
    result = classify(_runs(gaps, FLAT_TRAIN))
    assert result["outcome"] == "structural"
    assert result["median_gap"]["1536"] == pytest.approx(0.75)
