"""P6: private-model learnability under the training budget.

Private Model Learnability v1 §8 (preregistered at 6d35a6c2). Offline: the
corpus is rebuilt from checkpoint state with the organism's own selection;
only the training budget varies. The long arm evaluates the current weights at
each grid step of one fixed-budget training; the reference arm is the resident
regime on identical inputs.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import statistics
import time
import zipfile
from pathlib import Path
from typing import Any, Sequence

from symbiont.modeling import ArchitectureId, NativeTokenizer, TrainingRequest
from symbiont.modeling.authority import ModelObjective, ModelTrainingAuthority
from symbiont.modeling.corpus import build_training_corpus
from symbiont.modeling.ledger import ExperienceLedger, HistoricalExperienceArchive
from symbiont.modeling.runtime import private_causal_records
from symbiont_lab.modeling.baselines import (
    evaluate_frequency_baseline,
    evaluate_persistence_baseline,
    evaluate_uniform_baseline,
)
from symbiont_lab.modeling.dataset import EncodedCorpus, encode_corpus
from symbiont_lab.modeling.gateway import load_artifact_model
from symbiont_lab.modeling.outcome_metrics import evaluate_outcome_model
from symbiont_lab.modeling.trainer import TrainingProbe, evaluate_model, train_private_model

GRID = (48, 96, 192, 384, 768, 1536)
SEEDS_PER_CORPUS = 3
CONTEXT_WINDOW = 96
REQUESTED_PARAMETERS = 1_000_000
LONG_EPOCH_CEILING = 128
OVERFIT_WORSENING = 0.05


def load_runtime_payload(path: str | Path) -> dict[str, Any]:
    """runtime.json of a portable bundle, a gzipped runtime.json, or plain JSON."""
    source = Path(path).expanduser()
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            raw = json.loads(archive.read("runtime.json"))
    elif source.suffix == ".gz":
        with gzip.open(source, "rb") as handle:
            raw = json.loads(handle.read())
    else:
        raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("runtime payload root must be an object")
    return raw


def corpus_from_payload(payload: dict[str, Any]):
    """(organism_id, corpus, tokenizer) exactly as the organism would train."""
    organism_id = str(payload["organism_id"])
    ledger = ExperienceLedger.restore(payload.get("experience_ledger"), organism_id=organism_id)
    archive = HistoricalExperienceArchive.restore(
        payload.get("experience_archive"), organism_id=organism_id
    )
    corpus = build_training_corpus(private_causal_records(ledger, archive))
    return organism_id, corpus, NativeTokenizer.from_records(corpus.train)


def p6_seed(corpus_hash: str, index: int) -> int:
    digest = hashlib.sha256(f"p6:{corpus_hash}:{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFF


def _request(organism_id, corpus, tokenizer, seed, *, created_tick, long_arm: bool):
    return TrainingRequest(
        organism_id=organism_id,
        corpus_hash=corpus.manifest.corpus_hash,
        tokenizer_hash=tokenizer.tokenizer_hash,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=seed,
        context_window=CONTEXT_WINDOW,
        requested_parameters=REQUESTED_PARAMETERS,
        requested_epochs=LONG_EPOCH_CEILING if long_arm else 8,
        requested_steps=max(GRID) if long_arm else 48,
        created_tick_class=created_tick,
        autonomous_stopping=not long_arm,
        requested_patience=2 if not long_arm else 4,
        requested_min_validation_gain=0.005 if not long_arm else 1e-9,
    )


def _baselines(encoded: EncodedCorpus) -> dict[str, float]:
    test = encoded.test
    values = {
        "uniform": evaluate_uniform_baseline(test, vocab_size=encoded.vocab_size),
        "frequency": evaluate_frequency_baseline(
            encoded.train, test, vocab_size=encoded.vocab_size
        ),
        "persistence": evaluate_persistence_baseline(test, vocab_size=encoded.vocab_size),
    }
    return {name: metrics.mean_log_loss for name, metrics in values.items()}


def _metrics(model, encoded: EncodedCorpus, best_baseline: float) -> dict[str, Any]:
    kwargs = {"pad_id": encoded.pad_id, "context_window": CONTEXT_WINDOW}
    train = evaluate_model(model, encoded.train, **kwargs)
    validation = evaluate_model(model, encoded.validation, **kwargs)
    held_out = evaluate_outcome_model(model, encoded.test, **kwargs)
    return {
        "train_loss": train.mean_log_loss,
        "validation_loss": validation.mean_log_loss,
        "held_out_loss": held_out.mean_log_loss,
        "held_out_accuracy": held_out.accuracy,
        "gap": held_out.mean_log_loss - best_baseline,
        "outcome_tokens": {
            "train": train.predictions,
            "validation": validation.predictions,
            "held_out": held_out.predictions,
        },
    }


def run_long_arm(organism_id, corpus, tokenizer, encoded, seed, best_baseline, created_tick):
    request = _request(
        organism_id, corpus, tokenizer, seed, created_tick=created_tick, long_arm=True
    )
    rows: dict[str, Any] = {}

    def record(step: int, model) -> None:
        rows[str(step)] = _metrics(model, encoded, best_baseline)

    started = time.monotonic()
    result = train_private_model(
        request=request,
        corpus=encoded,
        authority=ModelTrainingAuthority(),
        probe=TrainingProbe(steps=GRID, callback=record),
    )
    return {
        "seed": seed,
        "steps_completed": result.steps_completed,
        "epochs_completed": result.epochs_completed,
        "checkpoints": rows,
        "wall_clock_s": time.monotonic() - started,
    }


def run_reference_arm(organism_id, corpus, tokenizer, encoded, seed, best_baseline, created_tick):
    request = _request(
        organism_id, corpus, tokenizer, seed, created_tick=created_tick, long_arm=False
    )
    started = time.monotonic()
    result = train_private_model(
        request=request, corpus=encoded, authority=ModelTrainingAuthority()
    )
    model = load_artifact_model(
        result.artifact, vocab_size=encoded.vocab_size, pad_id=encoded.pad_id, device="cpu"
    )
    return {
        "seed": seed,
        "steps_completed": result.steps_completed,
        "epochs_completed": result.epochs_completed,
        "metrics": _metrics(model, encoded, best_baseline),
        "wall_clock_s": time.monotonic() - started,
    }


def classify(long_runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """§8 criteria on the median over seeds of one corpus."""
    median = {
        step: statistics.median(run["checkpoints"][str(step)]["gap"] for run in long_runs)
        for step in GRID
    }
    train = {
        step: statistics.median(run["checkpoints"][str(step)]["train_loss"] for run in long_runs)
        for step in GRID
    }
    g48 = median[GRID[0]]
    later = [median[step] for step in GRID[1:]]
    reduction = (g48 - min(later)) / g48 if g48 > 0 else None
    crossed = any(value <= 0 for value in median.values())
    minimum_step = min(GRID, key=lambda step: (median[step], step))
    after_min = [median[step] for step in GRID if step > minimum_step]
    worsened = bool(after_min) and max(after_min) - median[minimum_step] > OVERFIT_WORSENING
    train_after_min = [train[step] for step in GRID if step >= minimum_step]
    train_decreasing = all(b < a for a, b in zip(train_after_min, train_after_min[1:]))
    train_drop = train[GRID[0]] - train[GRID[-1]]
    if crossed or (reduction is not None and reduction >= 0.50):
        outcome = "budget-limited"
    elif worsened and train_decreasing:
        outcome = "overfitting"
    elif reduction is not None and reduction < 0.25 and train_drop < OVERFIT_WORSENING:
        outcome = "structural"
    else:
        outcome = "mixed"
    return {
        "outcome": outcome,
        "median_gap": {str(step): value for step, value in median.items()},
        "median_train_loss": {str(step): value for step, value in train.items()},
        "R": reduction,
        "crossed": crossed,
        "min_gap_step": minimum_step,
        "worsened_after_min": worsened,
        "train_decreasing_after_min": train_decreasing,
        "train_loss_drop": train_drop,
    }


def run_private_model_learnability_study(
    *, corpora: dict[str, str], arms: Sequence[str] = ("long", "reference")
) -> dict[str, Any]:
    results: dict[str, Any] = {
        "protocol": "learning.private-model-learnability",
        "grid": list(GRID),
    }
    per_corpus = {}
    for label, path in sorted(corpora.items()):
        payload = load_runtime_payload(path)
        organism_id, corpus, tokenizer = corpus_from_payload(payload)
        encoded = encode_corpus(corpus, tokenizer, context_window=CONTEXT_WINDOW)
        baselines = _baselines(encoded)
        best = min(baselines.values())
        created_tick = int(payload.get("saved_at_tick") or 0)
        seeds = [p6_seed(corpus.manifest.corpus_hash, i) for i in range(SEEDS_PER_CORPUS)]
        entry: dict[str, Any] = {
            "source_tick": created_tick,
            "organism_id": organism_id,
            "corpus_hash": corpus.manifest.corpus_hash,
            "tokenizer_hash": tokenizer.tokenizer_hash,
            "vocab_size": encoded.vocab_size,
            "sequences": {
                "train": len(encoded.train.sequences),
                "validation": len(encoded.validation.sequences),
                "held_out": len(encoded.test.sequences),
            },
            "baselines": baselines,
            "best_baseline": min(baselines, key=baselines.__getitem__),
            "seeds": seeds,
        }
        args = (organism_id, corpus, tokenizer, encoded)
        if "reference" in arms:
            entry["reference"] = [
                run_reference_arm(*args, seed, best, created_tick) for seed in seeds
            ]
        if "long" in arms:
            entry["long"] = [run_long_arm(*args, seed, best, created_tick) for seed in seeds]
            entry["classification"] = classify(entry["long"])
        per_corpus[label] = entry
    results["corpora"] = per_corpus
    return results
