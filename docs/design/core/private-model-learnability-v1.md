# Private Model Learnability v1

Status: **draft — P6 design proposed, pending owner approval** (2026-09-28).
Origin: Cross-Domain Revision Coherence v1 §8.5-§8.6 (P5 inconclusive:
0/41 candidates beat the non-neural baseline). Baseline: `main @ 376c0d4f`.

## 1. Problem

Under the authorized training budget, no private model trained on
`org-ea3e7bbbc628` beats the best non-neural baseline. In P5, 41
from-scratch candidates scored 0.50-0.92 nats worse than the best of the
uniform, frequency and persistence baselines on the held-out temporal
split; median loss of the last 10 candidates 6.362. Uniform over a vocabulary
of about 4 800 tokens is ln 4 800 ≈ 8.48, so the models learn something,
but less than a frequency count.

Question: **does the learning curve show the model converging towards and
past the baseline as the budget grows, or is the failure structural?**
The question is *not* how much training is needed to pass.

## 2. Facts from the code (`main @ 376c0d4f`)

- Budget per training: `step_ceiling` 48, `epoch_ceiling` 8, batch 16
  (≤ 768 sequences seen), AdamW at a constant learning rate of 3e-4, weight
  decay 0.01, gradient clip 1.0 (`modeling/trainer.py`).
- Autonomous stopping is on in the resident: validation every
  `min(12, step_ceiling // 4)` steps, patience 2, minimum gain 0.005, so a
  training can stop after 24-36 steps.
- The loss is computed only on outcome target positions.
- `gru-v1` at about 982 k parameters, embedding 64, hidden 112. With a
  vocabulary of about 4 800 tokens, the input embedding (about 307 k) and
  output projection (about 538 k) hold roughly 85% of the parameters; the
  recurrent core is small. Reported, not varied (§3).
- Registry `validation_loss` is the candidate loss on the held-out split
  (`candidate_loss`); `baseline_loss` is the best of the three baselines on
  the same split. Splits are contiguous in organism time
  (`build_training_corpus`).

## 3. Fixed

Architecture (`gru-v1`), parameter ceiling (1 M), promotion criterion,
baselines, corpus construction, tokenizer construction, learning rate,
batch size, weight decay and clip. Only the **training budget** varies.

## 4. P6 design (proposed)

**Corpora.** Frozen corpora built offline with `build_training_corpus`
from abstract checkpoint state, not from a live Physics3D run:

- C1: `org-ea3e7bbbc628` at tick 9 246 (the P5 starting state);
- C2: the final P5 state at tick 11 891 (`archive/p5/a/organism`).

**Runs.** For each corpus and each of 3 training seeds, one training with
autonomous stopping **off** and `step_ceiling` 1 536 (32 × the current
budget), with `epoch_ceiling` raised so steps bind. The learning rate is
constant and there is no schedule, so every prefix of the run is exactly the
run at that smaller budget. Evaluation at 48, 96, 192, 384, 768 and 1 536
steps gives the learning curve from a single training.

**Reference arm.** The current regime (48 steps, autonomous stopping on) on
each corpus and seed, to check that P6 reproduces P5's loss level.

**Measured at each checkpoint:** training loss, internal validation loss,
held-out candidate loss, gap to each baseline and to the best one,
overfit gap (held-out minus training), and gain per additional step
between checkpoints. Also recorded: wall-clock and training
nondeterminism.

## 5. Criteria (proposed, to be fixed on approval)

Let *G(b)* be the median over seeds of held-out loss minus best-baseline
loss at budget *b*, per corpus.

1. **Budget-limited learning:** *G* decreases from 48 to 1 536 steps and
   either crosses zero or shrinks by at least 50% → evidence for a larger
   budget. The smallest *b* with *G(b) < 0* on both corpora would be
   proposed as the new ceiling (owner decision).
2. **Overfitting:** training loss falls below the best baseline while *G*
   stops improving (its minimum is reached before 1 536 steps and rises by
   more than 0.05 after it) → the budget alone is not the fix.
3. **Structural:** *G* shrinks by less than 25% at 1 536 steps and
   training loss also stays above the baseline → the problem is in
   representation, objective, architecture or corpus, not budget.

Otherwise the result is reported as mixed with no proposal. Whatever the
outcome, no production budget changes without an owner decision.

## 6. Out of scope

Changing eligibility, the promotion gate or the architecture; any P5 re-run;
ancestry. A mechanics-only lineage test (seeding a child from a
baseline-beating model to check vocabulary, restore, embeddings and
inheritance) is a separate optional item, never scientific evidence.

## 7. Open for the owner

- Budget grid and the 1 536-step maximum.
- Thresholds in §5 (50%, 25%, 0.05).
- Corpora C1/C2 and the 3 seeds.
