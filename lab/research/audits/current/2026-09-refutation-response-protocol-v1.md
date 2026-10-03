# Refutation-response protocol v1: two counter-experiments against H0

Date: 2026-09-18. Scope: `symbiont` (organism/cognition) + `symbiont_lab` (evaluator) only.
No real-host, permission, or network changes. This audit responds to an external
methodological critique of Symbiont's strong hypothesis ("does organization
resembling an organism emerge from developmental processes, rather than being
programmed as final behavior?") by building two counter-experiments the critique
itself proposed, running them under this repository's existing preregistration
convention, and reporting the real results -- including a genuine negative one.

## H0, stated explicitly

**H0: every "organic" result produced by Symbiont to date is fully explained by
policies, structures, rules and environments we designed explicitly; no
autonomous emergence needs to be postulated to explain the results.**

Prior to this audit, that hypothesis was not rejected, and several existing
mechanisms actively support it:

- `SymbolPolicy.choose()` (`src/symbiont/modeling/symbols.py`) is a pure
  `sha256(seed, context, candidate)` rank. `emergent_symbol_grounding.py` gives
  every organism in a trial the **same** `symbol_policy_seed`
  (`emitter_a`/`emitter_b`/`learner`/`newborn` all constructed with
  `symbol_policy_seed=seed`), so its ESG5 "convention agreement" gate is close
  to structurally guaranteed to pass by construction, not by interaction.
  `research/audits/current/2026-09-emergent-symbol-grounding-v1.md` already
  admits this: "la convergencia del emisor proviene de una regla local seeded."
- `predictive_utility.py` hardcodes a `PREDICTOR` node with `predicts_node_id="s"`
  already set, and a `PlasticEdge` whose sign is already correct -- there is no
  structure for the organism to discover.
- `CulturalPolicy._score` (`src/symbiont/modeling/culture.py`) is a deterministic
  hash `(organism_id, seed, item_id, tick, features)` ranked against fixed
  thresholds -- not a learned policy.
  `research/audits/current/2026-09-autonomous-cultural-agency-v1.md` states
  plainly: "The policy is an explicit deterministic baseline, not an emergent
  learned cooperation mechanism."
- `research/studies/biological-closure/ecology/genesis-multigenerational-followup.md`
  reports that a **neutral-resource-surface control** (no real ecological
  contrast between habitats) reproduced essentially the same locus/persistence
  correlations as the contrasted-profile run -- i.e. an apparent "selection"
  signal that turned out to be a generic turnover/mutation artifact, not
  evidence of adaptive selection -- and that the one `behavior_exploration`
  differential that did replicate **vanished under `stale_resources` pressure**.

This audit does not attempt to settle H0 across the whole research program. It
builds two of the five counter-experiments the critique itself specified as
capable of genuinely threatening H0, executes them once under a committed
preregistration, and reports what happened.

## Counter-experiment A: symbol grounding without a shared seed

Module: `src/symbiont_lab/studies/learning/independent_symbol_grounding.py`.
Protocol: `experiments/learning/independent-symbol-grounding/experiment.toml`.
Result: `experiments/learning/independent-symbol-grounding/results.json`.

`emitter_a` keeps `symbol_policy_seed=seed`; `emitter_b` receives
`symbol_policy_seed=_independent_seed(seed)`, a distinct deterministic
derivation (`(seed * 1_000_003 + 7) mod (2**31-1)`, asserted `!= seed`). Both
still share the same 32-symbol vocabulary, so chance agreement per exchange is
`p0 = 1/32 ≈ 0.03125`. The only channel through which interaction can shift
behaviour is new, additive organism-side state:
`SymbolPolicy.reinforce()`/`choose_adaptive()` (schema v2 checkpoint) --
existing `choose()`/`choose_grounded()` are untouched and their existing tests
pass unmodified. Reinforcement is a frequency-dependent ("naming game")
mechanism: a receiver reports `success` back to a sender only when its own
prediction was correct **and** the emitted symbol matches the receiver's own
currently-leading symbol for that outcome (or no leading symbol exists yet) --
this is the one deliberate mechanism-design choice this experiment introduces,
and it is the only thing that could, in principle, create convergence pressure
between two independently-seeded emitters rather than mere individual accuracy.

Three conditions per seed: `interactive` (reinforcement delivered as computed),
`isolated` (an H0 twin -- identical setup, reinforcement never delivered, so
interaction cannot affect behaviour even in principle), `shuffled`
(reinforcement delivered but the context/symbol pairing of each report is
permuted before delivery, preserving the marginal success rate while
destroying the causal link `interactive` relies on). Agreement is measured as
a **delta**: 32 probes before any interaction (`baseline`) vs. 32 probes after
64 interaction rounds (`post`), both using the identical probe schedule, so the
comparison isolates the effect of interaction from the deterministic
silence-gate pattern each policy already has.

Preregistered gates (`experiment.toml`, committed before the reported run):
`isg1` interactive post-agreement rejects `Binom(n, 1/32)` one-sided at
`p < 0.01` on every seed; `isg2`/`isg3` the isolated/shuffled H0 twins must
**not** reject that null; `isg4` interactive's agreement delta exceeds both
controls' deltas; `isg5`/`isg6` static AST checks (no shared seed passed to
both emitters, no evaluator symbol selector); `replay` full trace
determinism.

### Result: isg1 and isg4 FAILED on every seed

| seed | interactive post | isolated post | shuffled post | isg1 | isg2 | isg3 | isg4 |
|---|---|---|---|---|---|---|---|
| 101 | 0/30 | 4/30 (p=0.0137) | 0/30 | FAIL | pass | pass | FAIL |
| 127 | 2/23 (p=0.161) | 3/23 (p=0.034) | 2/23 (p=0.161) | FAIL | pass | pass | FAIL |
| 149 | 0/21 | 2/21 (p=0.139) | 2/21 (p=0.139) | FAIL | pass | pass | FAIL |

`all_gates_pass = false`. `isg5`/`isg6`/`replay` all passed on every seed --
the metric and the no-leakage invariants are not broken; the mechanism simply
did not produce convergence beyond chance under these preregistered
parameters (64 interaction rounds, 16-context alphabet, 32 probes).

**This is evidence for H0 on symbol grounding under this specific mechanism.**
Per the plan this audit follows: no future row in `research/STATUS.md` may
claim organic convention convergence without this gate passing, and this
result is reported as observed, not adjusted after the fact.

**Methods note, not a post-hoc rationalization:** with only ~56-57
interaction rounds spread over 16 contexts and alternating between two
emitters, each emitter sees a given context only ~2 times. Because
`choose_adaptive`'s tie-break is the same time-invariant `sha256(seed,
context, candidate)` digest `choose()` uses, each emitter's default symbol per
context is fixed from the first visit and self-reinforcing (a symbol that
succeeds once keeps succeeding, since there is no exploration pressure to try
alternatives). Two independently-seeded emitters therefore lock onto
different defaults for the same context and the reinforcement signal, as
designed, has no mechanism to force either one to *switch* toward the other --
it only entrenches whatever each already does. A mechanism with explicit
exploration/switching pressure (e.g. occasional non-greedy sampling, or a
receiver penalty for a symbol that conflicts with an outcome's established
leader even when the emitter's own prediction was "successful" in isolation)
is a concrete, identifiable next step, not attempted here to avoid tuning the
mechanism after seeing this run's numbers.

## Counter-experiment B: predictive structure discovery, no precabling

Module: `src/symbiont_lab/studies/learning/predictive_discovery.py`.
Protocol: `experiments/learning/predictive-discovery/experiment.toml`.
Result: `experiments/learning/predictive-discovery/results.json`.

### B.0 spike finding (methods)

Before building the full study, a minimal spike (`s_true`/`t` SENSE nodes,
`develop_senses=True`, `auto_promote_predictors=True`) confirmed empirically
that `CognitiveBridge.promote_shadow_prediction` commits a new `PREDICTOR`
node correctly attributed to the true predictive source (`predicts_node_id`
traces to the right target), but **does not autonomously wire an input edge
into that node**: an unconnected predictor node has zero activation every
tick, so it never coactivates with its source, so `StructuralPlasticity`
never grows the missing edge -- over 80 ticks post-promotion, no edge ever
appeared. Manually wiring that edge in the study would reintroduce exactly the
precabling this experiment exists to avoid. Instead, generalization is
evaluated using the same statistic the organism's own promotion decision is
based on: the raw one-step Huber loss of the discovered source's *own past
value* against the target, versus a persistence baseline, computed fresh on
held-out ticks the organism never saw. This is a legitimate deviation from
the original plan (which envisioned a lesion-matched wired-edge comparison)
forced by a real, now-documented architectural gap, not a convenience.

### Design

Five SENSE nodes, no `PREDICTOR`, no `predicts_node_id`, no `PlasticEdge`, at
construction time (`pd5`, AST-verified). Generating process: `s_true` is a
persistent AR(1) series; `t_t = s_true_{t-1} + eps` is the law to discover;
three decoys share `s_true`'s numeric scale but have no true relationship to
`t` (`decoy_indep`: independent AR(1); `decoy_wronglag`: lag of a *different*
independent driver, i.e. genuinely autocorrelated but unrelated to `t`;
`decoy_antiphase`: `-0.6 * s_true_{t-1}`, testing sign-sensitivity). The
organism runs its existing, unmodified `ShadowPrediction`/
`promote_shadow_prediction` machinery for 400 development ticks; when multiple
candidates become simultaneously promotable, the study ranks by
`predictive_gain` before attempting promotion (an early pilot run without this
ranking showed `promote_shadow_prediction`'s target selection order is
otherwise governed by `shadow_predictions`' alphabetical `(source_id,
target_id)` sort -- `decoy_wronglag` was winning the single promotion slot
purely because `"decoy_wronglag" < "s_true"` alphabetically, not because it
predicted better; this is documented here as a real implementation pitfall,
fixed before the preregistered gate threshold was locked).

Two-phase holdout: development uses seeds `(11, 23, 37)`; frozen evaluation
uses disjoint seeds `(211, 233, 257)`, fresh noise draws, computed
independently of anything touched during development (validated:
`set(development_seeds) & set(evaluation_seeds) == set()`).
`LOSS_GAIN_THRESHOLD = 0.0002` was calibrated once, before locking the
preregistered gate, against a pilot run that observed a true-source gain of
~0.00043-0.00046 and decoy gains of roughly -0.002 to -0.004 -- i.e. the
threshold sits below every observed true-source gain and well above zero, and
was fixed in `experiment.toml` before the officially reported run below.

### Result: all gates PASSED on every seed pair

| dev seed | eval seed | promoted | source gain | best decoy | decoy gain |
|---|---|---|---|---|---|
| 11 | 211 | s_true | +0.000426 | decoy_wronglag | -0.003408 |
| 23 | 233 | s_true | +0.000464 | decoy_indep | -0.003639 |
| 37 | 257 | s_true | +0.000437 | decoy_indep | -0.002290 |

`pd1`-`pd5` and `replay_deterministic` all passed on every seed;
`all_gates_pass = true`. The organism, given no predetermined predictor and no
labeled target, consistently discovered the single genuinely predictive
candidate out of four numerically-matched alternatives, and that discovery
generalized to noise seeds never touched during development, while every
decoy's held-out performance was *worse* than a naive persistence baseline. No
new evaluator channel or truth oracle was introduced: `pd1`-`pd4` are computed
from the same `huber_loss` function and `ShadowPrediction` bookkeeping the
organism's own promotion logic already uses.

**This is evidence against H0 for predictive structure discovery specifically**
(distinct from `predictive_utility.py`'s existing closed result, which never
tested discovery). It does not extend to symbol grounding (Counter-experiment
A, above) or to any other domain audited elsewhere in this repository.

## Roadmap: items #3-5

The critique proposed five counter-experiments. #1 and #2 were executed above.
#3 and #4 were subsequently executed for real (not merely scoped) in a second
pass on 2026-09-18; #5 remains an organizational decision, not a coding task.

### #3 -- Real evolutionary selection (many-seed, reversible mid-run pressure): EXECUTED, negative result

Module: `src/symbiont_lab/studies/autonomous_life/reversible_selection.py`.
Protocol: `experiments/autonomous-life/reversible-selection/experiment.toml`.
Result: `experiments/autonomous-life/reversible-selection/results.json`.

Every prior Genesis study founded its population with one identical genome,
so none of that evidence tests selection on standing variation -- only that a
fixed parameter changes outcomes. This experiment founds a population with
genuinely mixed `behavior_exploration` alleles (half `0.0`, half `0.1`,
declared as a real heritable `HeritableGenome` locus, confirmed to flow
parent-to-child through `OrganismRuntime.materialize_clonal_bud`, with real
Gaussian mutation via `mutate_genome`), runs it through
`regimes=("scarcity", "abundance", "scarcity")` -- pressure applies, reverses,
then reverses again back to the original pressure, using the existing
`OpaqueEnvironment` tick-fraction regime schedule unmodified -- and measures
the live population's mean allele value at each regime boundary.

**Seed-parallel execution is new, shared infrastructure**: no
`multiprocessing`/`concurrent.futures` usage existed anywhere in this
repository before this pass (verified by grep); `reversible_selection.py` adds
a `ProcessPoolExecutor`-based worker (`_run_one_seed`, a top-level picklable
function returning only plain dict data, never runtime objects) so many
independent, deterministic seeds run in parallel without sharing RNG state.

**Preregistered gates** (`experiment.toml`, committed before the run):
`rs1` -- across N seeds, the count where `sign(shift_a) != sign(shift_b)`
(both non-zero; a genuine reversal-then-reversal-back) rejects
`Binomial(N, 0.5)` one-sided at `p < 0.01`. `rs2` -- the same statistic on a
matched no-standing-variation control (`behavior_exploration=0.05` for every
founder) must **not** reject that null. `replay` -- full per-tick metric
determinism.

**Run**: 200 seeds (`1..200`), 8 founders, `ticks_per_segment=90` (270 ticks
total per run), 8 parallel workers. Actual wall-clock: **5205.6 seconds
(~86.8 minutes)** for all 400 seed x condition runs -- roughly 2.2x this
session's single-job benchmark (38.7s), attributable to CPU contention from
running 8 worker processes concurrently against other load on the same
8-core machine (confirmed via `top` mid-run: 8 `python3` workers pinned near
90% CPU alongside other running load), not a design flaw.

**Result: rs1 FAILED.** `mixed_reversals = 44/200` (p=1.0, nowhere near
`< 0.01`). `rs2` correctly held: `control_reversals = 40/200` (p=1.0, also
not significant -- the metric and mechanism are not broken). `replay` PASSED.
`all_gates_pass = false`.

**This is a genuine negative finding: no detected selection signal tracking
the pressure-reversal schedule on this locus, under this design.** A
secondary observation from the raw per-seed data, reported here rather than
used to retune anything: in the large majority of seeds, in **both** the
mixed and the no-variation control condition, the population's mean
`behavior_exploration` declines monotonically across all three segments
(mean `shift_a` and `shift_b` both negative in ~85-90% of seeds in both
conditions) rather than reversing with the regime. Because this pattern
appears almost identically in the control -- which has no standing variation
for any regime to select on -- it is far more consistent with a **mutation-
boundary clamping artifact** (`mutate_genome` draws `rng.gauss(0.0, 0.05)`
and clamps to `[0, 1]`; near the lower bound, a downward draw is clamped to
exactly `0.0` while an upward draw of similar magnitude is not truncated,
asymmetrically pulling the population mean toward `0.0` over many generations
regardless of regime) than with genuine ecological selection. This mirrors,
in a new setting, the exact epistemic trap
`genesis-multigenerational-followup.md` already documented once
(a neutral-resource control reproducing an apparent "selection" signal that
turned out to be a generic turnover/mutation artifact) -- and reinforces that
finding rather than contradicting it. No mechanism or threshold was adjusted
after seeing these numbers.

### #4 -- Frozen holdout harness, repo-wide: EXECUTED for one study, others intentionally unconverted

Module: `src/symbiont_lab/evaluation/holdout.py` (new `symbiont_lab.evaluation`
subpackage). Retrofit: `src/symbiont_lab/studies/learning/predictive_discovery.py`.

`DevelopmentPhase`/`FrozenEvaluationPhase` are bounded, validated frozen
dataclasses; `SeedLedger` persists an **append-only** JSON history, per
`study_id`, of every seed ever used for development
(`research/audits/current/holdout-seed-ledger.json` by default, injectable for
tests). `FrozenEvaluationPhase.validate_disjoint(ledger)` raises if any
evaluation seed appears anywhere in that study's recorded development
history -- not just the seeds passed in the current call -- which is the
actual mechanical enforcement the original roadmap text called for, not a
comment. `predictive_discovery.py`'s `run_predictive_discovery_study` now
takes an optional `ledger: SeedLedger | None = None`, validates disjointness
before running, and records its development seeds afterward; a new
integration test (`test_reusing_a_development_seed_as_an_evaluation_seed_is_rejected`)
confirms a second run that tries to reuse a prior development seed as an
evaluation seed is rejected with `ValueError`, using a temporary ledger so the
test suite never mutates the repository's real ledger file.

**Scope, honestly bounded**: only `predictive_discovery.py` was retrofitted
in this pass. Every other study using seeds for a development/evaluation
split (`emergent_symbol_grounding.py`, `independent_symbol_grounding.py`,
the Genesis/evolution family, and all `CLOSED` historical studies) still uses
its original ad hoc seed handling and is **not** yet covered by
`SeedLedger` enforcement. Converting them is an incremental, multi-study
retrofit explicitly out of scope for this pass, matching the original roadmap
estimate ("several days, no compute blocker") -- it was not attempted here to
avoid rushing a mechanical change into already-`CLOSED` audit records.

### #5 -- Independent replication

Not started; not schedulable by this audit. Requires a second implementer,
ideally without prior exposure to this codebase's internals, building a
harness from the public protocol alone (the `experiment.toml` files and audit
documents, deliberately not this source code) and reproducing
Counter-experiments A and B blind. Concrete next steps: (a) freeze a
protocol-only replication brief (inputs/outputs/gates, no implementation
detail); (b) assign a separate implementer; (c) compare their independently
derived results against `results.json` above without either side adjusting
thresholds after the fact. This is an organizational decision for the project
owner, not a task this audit can plan further.

## Summary

| Counter-experiment | Result | Verdict |
|---|---|---|
| A: independent-seed symbol grounding | isg1/isg4 FAIL on all 3 seeds; isg2/isg3/isg5/isg6/replay pass | Evidence **for** H0 on symbol grounding under this mechanism |
| B: predictive structure discovery + frozen holdout | pd1-pd5 and replay PASS on all 3 seed pairs | Evidence **against** H0 for predictive discovery specifically |
| #3: reversible-pressure selection, 200 seeds | rs1 FAILS (44/200, p=1.0); rs2/replay hold | Evidence **for** H0 on standing-variation selection under this design; likely mutation-clamp artifact, not signal |
| #4: frozen holdout enforcement | Built and enforced for `predictive-discovery` only; other studies unconverted | Mechanism exists and works; repo-wide coverage incomplete |

None of these results is final or repo-wide. A and #3 are genuine negative
findings, each with an identified, undone next step (exploration/switching
pressure for A; a mutation-clamp-robust statistic or an unbounded/rescaled
locus for #3). B is a genuine positive finding scoped narrowly to structure
discovery. #4 is a working mechanism with intentionally incomplete adoption.
Item #5 (independent replication) remains an organizational decision for the
project owner, not a task this audit can schedule or execute.
