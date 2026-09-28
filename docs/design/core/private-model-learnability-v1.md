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

**Reporting rules (owner, 2026-09-28, during the run; criteria unchanged).**
The structural threshold (training loss falls < 0.05 nats from 48 to 1 536
steps) is approved and frozen. For every corpus and seed the report keeps
four readings separate: *optimisation* (does training loss fall?),
*generalisation* (does held-out loss fall?), *baseline competitiveness*
(how *G* evolves) and *shape* (still improving, flattening or reversing).
Vocabulary and baseline differences between C1 and C2 are corpus
properties and are not normalised; the main comparison stays *G* against
each corpus's own best baseline. If C1 and C2 fall into different
categories, no single diagnosis is forced: the result is reported per
corpus (for example "budget-limited on C1 / structural on C2"), the global
state is `mixed`, and the heterogeneity is part of the finding.

**Inputs.** C1 = `org-ea3e7bbbc628` checkpoint at tick 9 246 (the owner's
state directory); C2 = the archived final P5 runtime state at tick 11 891
(`.symbiont/archive/p5/a/organism/runtime.json.gz`). Both corpora are
built from the checkpoint's experience ledger and archive with the same
selection the organism uses (`private causal records` →
`build_training_corpus` → `NativeTokenizer.from_records`). Each result
records the corpus and tokenizer hashes.

**Operationalisation disclosed before the run (2026-09-28).** "Training
loss also fails to fall materially" (structural) is implemented as: the
median training-split loss falls by less than 0.05 nats between 48 and
1 536 steps (the same fixed 0.05). "Keeps decreasing" (overfitting) means
the median training-split loss decreases strictly at every grid step from
the held-out minimum onwards. Inputs are frozen copies in
`.symbiont/archive/p6/inputs/` (C1 sha256 `a482c285…`, taken read-only
from the owner's trashed `org-ea3e7bbbc628` at tick 9 246; C2 sha256
`41043cbd…`). Corpora: C1 `e057da8d…`, vocabulary 4 822, 2 288 / 490 /
491 train / validation / held-out sequences, best baseline frequency
6.037; C2 `526a47b2…`, vocabulary 4 495, 2 304 / 493 / 495, frequency
5.538.

**Separate item (not part of P6).** A mechanics-only lineage test forces an
eligible SHADOW parent and checks: child selected from it; generation =
parent + 1; parent token ids and embeddings preserved; new tokens appended
deterministically; checkpoint → restore preserves ancestry, tokenizer and
parameters; training ancestry never grants ACTIVE/control authority; a
retired or non-eligible parent is never selected. It is never reported as
evidence for ancestry.

*Result (2026-09-28):* the test found a defect P5 could not reach —
adoption rejected any child whose vocabulary had grown, because it required
the parent's exact tokenizer hash. Fixed in `c6ee7192` (an append-only
extension of the held parent vocabulary is accepted); the previous
end-to-end test never appended a token. All listed mechanics now pass.

## 9. P6 result (2026-09-28) — budget-limited on both corpora

Run `20260928T194311Z-learning-private-model-learnability-3c9a24e-eb71`
(`3c9a24ec`, clean). Artifacts: `.symbiont/archive/p6/run/`. Held-out
losses in nats; *G* = held-out − best baseline (frequency: C1 6.037, C2
5.538). Outcome tokens: C1 18 766 / 3 710 / 3 116 train / validation /
held-out; C2 15 860 / 1 420 / 1 536.

**Long arm, per seed (G at each budget):**

| corpus / seed | 48 | 96 | 192 | 384 | 768 | 1 536 |
|---|---:|---:|---:|---:|---:|---:|
| C1 / 1687003792 | +1.043 | +0.066 | −0.251 | −0.637 | −1.355 | −1.840 |
| C1 / 124483085 | +1.002 | +0.083 | −0.192 | −0.478 | −1.215 | −1.832 |
| C1 / 1076999112 | +1.088 | +0.076 | −0.264 | −0.673 | −1.380 | −1.882 |
| C2 / 1001803534 | +0.617 | −0.223 | −0.495 | −0.790 | −1.260 | −1.634 |
| C2 / 622678074 | +0.678 | −0.141 | −0.459 | −0.905 | −1.366 | −1.806 |
| C2 / 1899705726 | +0.864 | −0.087 | −0.479 | −0.801 | −1.268 | −1.687 |

**Classification (preregistered):** C1 **budget-limited** (median *G*
crosses zero; R = 2.76); C2 **budget-limited** (R = 3.49). No heterogeneity
between corpora; all six seeds agree.

**Four readings (every seed):**

- *Optimisation:* training loss falls from about 7.2 (C1) / 6.7 (C2) at
  48 steps to about 3.5 / 3.6 at 1 536 (drop 3.7 / 3.1 nats).
- *Generalisation:* held-out loss falls monotonically, 7.04-7.13 → 4.16-4.21
  (C1) and 6.16-6.40 → 3.73-3.90 (C2).
- *Baseline competitiveness:* *G* turns negative between 96 and 192 steps
  (C1: all seeds below zero at 192; C2: already at 96) and reaches about
  −1.7 to −1.9 at 1 536.
- *Shape:* still improving at 1 536 (held-out −0.37 to −0.62 nats between
  768 and 1 536), no flattening or reversal. The train/held-out gap opens
  late (held-out − train: −0.2 at 192, +0.1 to +0.2 (C1) / −0.3 (C2) at
  768, +0.7 (C1) / +0.1 to +0.3 (C2) at 1 536): an early sign of
  overfitting beyond the grid, not overfitting by the preregistered rule
  (held-out never worsens).

**Reference arm (current regime, same inputs and seeds):** 48 steps every
time; held-out 7.04-7.12 (C1, *G* +1.00 to +1.09) and 6.15-6.40 (C2, *G*
+0.61 to +0.86), matching the long arm at 48 steps. C2 lies inside P5's
range (+0.50 to +0.92); C1 is slightly worse (+1.00 to +1.09), consistent
with C1 being the earliest corpus. P6 reproduces P5's failure: the current
regime stops at 48 steps, just before the curve crosses the baseline.

**Proposal (owner decision; nothing changes automatically).** By §5 the
smallest budget with median *G* < 0 on both corpora is **192 steps** (every
seed below zero). Larger budgets keep improving up to 1 536, with a
widening train/held-out gap. Limits: one organism lineage, offline corpora,
fixed architecture and learning rate. If a budget is raised, P5 becomes
re-runnable with ancestry actually exercisable (Revision Coherence §8.6).

## 10. Owner decision after P6 (2026-09-28): step ceiling 48 → 192

The organism's autonomous training plan keeps its replay-pressure scaling,
multiplied by 4: `requested_steps = 48 + round(144 × pressure)` (was
`12 + round(36 × pressure)`), so full pressure — every P5 request — asks
for 192 steps. Epochs (`2 + round(6 × pressure)`), autonomous stopping
(patience 2, minimum gain 0.005), architecture, parameter ceiling,
baselines and the promotion gate are unchanged. Metabolic compute charge
is `steps / 100 000` (0.0019 instead of 0.0005 per training).

**Check under the resident regime (with autonomous stopping, which P6's
long arm disabled):** on C1/C2 with P6's seeds, all six trainings ran the
full 192 steps (2 epochs) and beat the baseline — held-out *G* −0.20 to
−0.27 (C1) and −0.47 to −0.50 (C2), matching P6's 192-step values.
Historical studies that fix their own budgets (e.g. the replay-pressure
curve) are unchanged.

Consequence: models can now become ancestry-eligible, so P5 can be re-run
with ancestry actually exercisable (Revision Coherence §8.6); that re-run
needs its own owner go-ahead.
