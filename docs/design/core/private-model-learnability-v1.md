# Private Model Learnability v1

Status: **P6 preregistered** (owner approval 2026-09-28, §8; supersedes the
draft §4-§5 where they differ).
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

Closed by §8.

## 8. P6 preregistration (owner, 2026-09-28; fixed before any code or run)

Approved: grid 48, 96, 192, 384, 768, 1 536 steps (maximum 1 536);
corpora C1 and C2 with 3 seeds each; architecture, corpus construction,
parameter ceiling, baselines and promotion gate frozen. No P6 result
changes the production budget automatically.

**Seeds.** For corpus hash *h*, training seed *i* ∈ {0, 1, 2} is the first
8 bytes (big-endian) of `sha256("p6:<h>:<i>")` masked to 31 bits. The same
seeds serve the long and reference arms.

**Long arm.** Fixed budget: no early stopping of any kind (autonomous
stopping off and the per-epoch patience stop disabled), `step_ceiling`
1 536 and `epoch_ceiling` 128 so that steps bind. At each grid step the
current weights (not a best-validation state) are evaluated.

**Prefix equivalence is tested, not assumed.** Automated tests before the
run: (a) the weights at step *b* inside a longer fixed-budget run equal,
exactly, the weights of a fixed-budget run with `step_ceiling` *b*; (b)
evaluating at intermediate steps does not change training (final weights
identical with and without intermediate evaluations). Batch order uses its
own seeded generator; model initialisation uses the seeded global RNG;
`gru-v1` has one layer, so no dropout is active; evaluation runs in
`no_grad`/eval mode, consumes no randomness and restores train mode.

**Reference arm.** The current regime (48 steps, 8 epochs, autonomous
stopping on, patience 2, minimum gain 0.005, best-validation state), on the
same C1/C2, corpus, split, preprocessing and seeds as the long arm. It
checks that P6 reproduces P5's loss level.

**Measured at each grid step and seed:** training-split loss, internal
validation loss, held-out (test-split) candidate loss, the three baseline
losses and the best one (held-out split), *G* = held-out loss − best
baseline, and the **number of outcome tokens evaluated** in each split.
Also wall-clock per run.

**Criteria.** Per corpus, with *G_b* the median over seeds at step *b* of
the long arm, and *R* defined only when *G_48* > 0:

    R = (G_48 − min(G_96 … G_1536)) / G_48

1. **budget-limited:** some checkpoint has *G* ≤ 0, or *R* ≥ 0.50;
2. **overfitting:** held-out *G* reaches a minimum, then worsens by more
   than 0.05, **and** training-split loss keeps decreasing;
3. **structural:** *R* < 0.25 **and** training-split loss also fails to
   fall materially (the optimisation does not fit the training objective);
4. **mixed:** anything else, or patterns not classifiable above.

If at 1 536 steps the curve is still clearly improving but has not crossed
the baseline, the result is **mixed / unresolved**, not licence to keep
raising the budget; a further range needs its own preregistered decision.
The overfitting threshold 0.05 is fixed and does not move afterwards.

**Reporting.** Global classification uses the preregistered median;
the report also shows every seed's curve and the dispersion, so a median
cannot hide that for example 1 of 3 seeds learns and 2 do not. No
further corpora are added after seeing C1/C2.

**Inputs.** C1 = `org-ea3e7bbbc628` checkpoint at tick 9 246 (the owner's
state directory); C2 = the archived final P5 runtime state at tick 11 891
(`.symbiont/archive/p5/a/organism/runtime.json.gz`). Both corpora are
built from the checkpoint's experience ledger and archive with the same
selection the organism uses (`private causal records` →
`build_training_corpus` → `NativeTokenizer.from_records`). Each result
records the corpus and tokenizer hashes.

**Separate item (not part of P6).** A mechanics-only lineage test forces an
eligible SHADOW parent and checks: child selected from it; generation =
parent + 1; parent token ids and embeddings preserved; new tokens appended
deterministically; checkpoint → restore preserves ancestry, tokenizer and
parameters; training ancestry never grants ACTIVE/control authority; a
retired or non-eligible parent is never selected. It is never reported as
evidence for ancestry.
