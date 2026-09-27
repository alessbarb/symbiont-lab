# Factorized Effect Representation v1 — Draft Specification

**Status:** APPROVED with the §11 proposals, **implementation on hold**: the §12 spike shows footprints do not form stably in the Physics3D body; back to the owner.
**Depends on:** Agency Acquisition & Executive Action v1 (frozen; audit §0,
§0.1), Executive Outcome Learning v1.1.
**Origin:** inspection of the owner's Physics3D organism, 2026-09-27
(audit §0.1).

---

## 1. Problem

Agency v1 identifies an effect as the **whole-state quantized change** of one
transition: every organism feature whose change reaches one bucket (1/14)
enters one signature, and the signature is the effect identity
(`EffectSpace.observe`). Effects are compared by identity (`EffectMatcher`
v1, §33).

On the 4-actuator synthetic body this works. On the owner's Physics3D
organism (62 effectors, 107 receptors, tick 5120) it does not:

- 1309 effectful attempts produced 832 distinct effects; the most frequent
  recurs 43 times;
- the EffectSpace is saturated at its 512-signature cap, 84% of signatures
  seen once;
- therefore every competence has `effect_id = None`, no competence is bound,
  and the organism has formed **no intent** — nothing in Agency v1 or EOL can
  engage.

Three mechanisms produce this:

1. **Combinatorial identity.** A transition that moves k features yields one
   of ~15^k signatures; with many receptors, a repeat of the exact set and
   buckets is rare even when the same outputs cause the same changes.
2. **Passive contamination.** Features that drift regardless of action
   (gravity, balance, other limbs) enter the same signature, so an otherwise
   repeatable consequence gets a new identity every time.
3. **Capacity pressure.** Passive windows and one-off signatures share the
   512 slots; eviction keeps the highest support, so newborn effects compete
   poorly before they can recur.

E4 showed the same limitation from the other side: a broken output changes
one feature, but whole-state identity cannot express "the same effect minus
one feature".

## 2. Goal

Effects that **recur whenever the same causal consequence recurs**, in any
body size, so that:

```text
exploration -> recurring effect -> dimension -> competence with effect
-> binding -> affordance -> intent -> reconciliation -> outcome learning
```

engages on the Physics3D organism as it does on the synthetic body, without
changing the frozen architecture of Agency v1.

## 3. Principles

1. **Organism-owned and semantic-free.** Effects are built only from opaque
   organism feature references; no body, part or world label.
2. **Consequence, not state.** An effect is what an intervention *changes*
   beyond what happens anyway; counterfactual evidence decides which feature
   changes belong to a source.
3. **Single factual source.** The CausalEvidenceLedger remains the only
   source for every causal view; imagination never writes effects.
4. **Bounded and deterministic.** Every registry is bounded; identities are
   pure functions of their content; same-seed runs stay identical.
5. **Graded equivalence through one door.** All effect comparison still goes
   through `EffectMatcher` (§33); v1 identity is replaced by a graded
   similarity without changing its callers' contract.
6. **No reward, no new decision system.** This changes what an effect *is*,
   not how action is chosen.

## 4. Representation

### 4.1 Atomic effects

Each transition's opaque changes decompose into **atomic effects**:

```text
EffectAtom(feature_ref, direction, magnitude_class)
  direction        in {+, -}
  magnitude_class  in {1, 2, 3}   # coarse; see §10
```

with the magnitude class a fixed function of the v4 bucket
`b = clamp(round(delta * 7), -7, 7)`:

```text
|b| in {1, 2} -> 1      |b| in {3, 4} -> 2      |b| in {5, 6, 7} -> 3
direction = sign(b)     b = 0 -> no atom
```

so every v4 signature entry maps to exactly one atom (the migration in §8 is
exact by construction). Identity
`effect.atom.<hash(feature_ref, direction, magnitude_class)>`.
The atom vocabulary is bounded by `features x 2 x 3` and recurs by
construction. A transition yields a **set** of atoms (possibly empty).

### 4.2 Causal footprints (composite effects)

A **footprint** is the set of atoms a causal source reliably produces beyond
the counterfactual rate:

```text
footprint(source) = { atom : agency(source, atom) >= footprint_agency
                             and controllability(source, atom) > 0 }
```

Identity `effect.footprint.<hash(sorted atom ids)>`.

**Membership hysteresis.** An atom enters a source's footprint when its
agency reaches `footprint_agency` and leaves only when it falls below
`footprint_agency - footprint_hysteresis` (proposed 0.05); a footprint's
identity changes only when its membership changes under that rule. This
prevents an atom near the threshold from flickering the identity that
competences, bindings, intents and EOL keys refer to.

**Pinning.** A footprint referenced by a live intent, an execution binding, a
competence or an EOL key is pinned: it cannot be evicted, and it keeps
resolving to its atom set while referenced. A live intent additionally
stores its expected atom set, so reconciliation never depends on registry
state. Footprints are what
dimensions, competences, affordances and intents refer to as "the effect".
Passive-drift atoms have a high counterfactual rate and therefore never enter
a footprint (principle 2), which removes mechanism 2.

### 4.3 EffectMatcher v2

```text
similarity(expected_footprint, observed_atoms)
  = |expected ∩ observed| / |expected|        # recall of the intended change
```

Identity footprints still give 1.0. Observed extra atoms do not reduce
similarity (other things may also happen); missing intended atoms do.
Satisfaction, mismatch and prediction error use this similarity unchanged in
form (`IntentionPolicy.satisfaction_similarity` gets a v2 default, §10).

## 5. Evidence and estimates

- `SensorimotorTransition` and passive windows carry the **atom set** of the
  transition (bounded: at most `max_atoms_per_transition`, largest magnitudes
  first, deterministic tie-break).
- The ledger counts opportunities per `(source, atom)` incrementally, exactly
  as it counts `(source, effect)` today; passive windows count per atom too.
- Controllability and agency are estimated per `(source, atom)` with the v1
  formulas; the v1 guarantees (prediction match alone never yields agency;
  counterfactual support required) are unchanged.
- Footprints are **derived** from those estimates (never stored as facts),
  recomputed when a source's estimates are refreshed, and registered with a
  stable identity once they hold for `footprint_stability` refreshes.

## 6. Consumers (unchanged contracts, new effect meaning)

| Consumer | v1 | v2 |
| --- | --- | --- |
| `assess_family` (dimension discovery) | dominant single effect id | dominant footprint (most supported atoms jointly), qualifies on atom-level repeatability and counterfactual advantage |
| `ground_competence` | competence effect = dimension's dominant effect | competence effect = dimension footprint |
| `AffordanceResolver` | predicted effect id | predicted footprint |
| Intent reconciliation (§64-§70) | identity match | `EffectMatcher` v2 similarity |
| EOL key | (competence, effect id) | (competence, footprint id) |
| BodySchema agentic evidence | effect feature refs | footprint atom features (directly the caused features) |
| Generative Cognition anticipation | effect ids | footprint ids (still never factual) |
| Observatory / Atlas | effect nodes | footprint nodes; atoms as detail |

## 7. EffectSpace bounds

- Atom registry: bounded by the feature vocabulary (already bounded by sensory
  development); evicted only with its feature.
- Footprint registry: `max_footprints` (default 512) with eviction by
  `(last_supported_tick, support)` and a newborn residence window
  (`footprint_residence_ticks`) so a new footprint can recur before it
  competes.
- Passive windows never create footprints (mechanism 3).

## 8. Persistence and migration

- New sensorimotor checkpoint schema (5). Whole-state signatures of schema 4
  decompose **exactly** into atoms (a signature is already a tuple of
  `(feature_ref, bucket)`), so v4 effect support migrates to atom support.
- Ledger entries that reference a v4 effect id whose signature is still in the
  EffectSpace are rewritten to its atom set; entries whose effect was evicted
  lose their effect (bounded, recorded as a migration count).
- Estimates, dimensions' dominant effects and competence effects are rebuilt
  from the migrated ledger; EOL keys referencing v4 effect ids are dropped
  (their meaning changed), with a count.
- Raw telemetry is never persisted; checkpoints stay bounded.

## 9. Tests (release gate, mechanical)

1. The same caused change with different passive drift yields the same
   footprint.
2. A passive-only drifting feature never enters any footprint.
3. Breaking one output removes exactly its atoms from the observed set and
   lowers similarity proportionally (E4 at atom level).
4. Atom and footprint identities are pure and deterministic; same-seed runs
   identical; restored continuations identical.
5. Schema-4 checkpoint migrates: atom support equals decomposed signature
   support; migration counts reported.
6. Registries stay within bounds under adversarial feature counts.
7. Imagination never creates atoms or footprints.
8. All §92-§111 Agency v1 tests and EOL §10 tests still pass (effect meaning
   changes, contracts do not).

## 10. Studies

- **E1-E6 regression** on the synthetic body (same seeds): E6 must still
  pass; E1 ablations must still acquire nothing; E2/E3/E5 reported against
  their v4 numbers.
- **E8 — high-dimensional acquisition (new, preregistered):** a synthetic
  body with many receptors (e.g. 16 actuators, 96 receptors), outputs that
  drive several correlated receptors, and passively drifting receptors.
  Report effect recurrence, footprints, competences with an effect,
  bindings, intents formed and satisfied, under v1 (identity) and v2 arms.
- **Physics3D acceptance (on a copy of the owner's organism):** after a fixed
  budget the organism has at least one bound competence, forms intents and
  satisfies at least one; EOL history hit rate reported.
- **Overhead:** per-tick cost on the 5k-tick synthetic run and Physics3D
  62-effector run within +15% of current.
- **E4 re-analysis** at atom level (whether the broken output's atoms leave
  the footprint) as a secondary report.

**Comparability.** Removing whole-state effects (decision 4) means the v1
identity arm of E8 and the E1-E6 regression baselines run on the last
pre-change commit (`dad68394`) in a pinned worktree, recorded in the
preregistration. The study recorder counts a commitment as realized when
`EffectMatcher` similarity reaches `satisfaction_similarity` (0.75) instead of
identity; E2/E3/E5 therefore get new protocol versions and are reported as
new results, not as deltas against v4.

## 11. Decisions (owner-approved proposals)

1. Magnitude classes: 3 coarse classes (proposed) vs direction only.
2. `footprint_agency` threshold (proposed: the existing agentic threshold).
3. `satisfaction_similarity` default under v2 (proposed 0.75: most of the
   intended atoms observed).
4. Whether v1 whole-state effects are removed (proposed) or kept alongside
   for comparison arms only.
5. `max_atoms_per_transition`, `footprint_stability`,
   `footprint_residence_ticks` (proposed 16, 3 refreshes, 256 ticks).
6. Order of work: this before the E4 re-exploration spec (proposed, since the
   real organism cannot engage agency at all until effects recur).

## 12. Feasibility spike (before any contract change)

Record raw opaque change maps per attempt and passive window on a copy of the
owner's Physics3D organism and on the synthetic body, then compute offline —
with the model's own formulas — atoms per transition (does the 16 cap bind?),
per-atom counterfactual rates, per-source footprints at the agentic threshold,
their stability across halves of the run, and the resulting estimate count
against `MAX_ESTIMATES`. If footprints do not form or do not hold in the 3D
body, the design returns to the owner with that evidence before
implementation.

### 12.1 Spike results (2026-09-27)

Raw change maps recorded on a copy of `org-ea3e7bbbc628` (1500 Physics3D
ticks: 1494 attempts, 5 passive windows) and on the synthetic body (3000
ticks); footprints computed offline with the model's controllability and
agency formulas at the agentic threshold 0.35. Data and scripts:
`.symbiont/effect-spike/`.

| Question | Physics3D | Synthetic |
| --- | --- | --- |
| Atoms per transition (median / p90 / >16) | 2 / 5 / 0% | 1 / 1 / 0% |
| Atom vocabulary (seen >= 8 times) | 137 (67) | 11 (11) |
| Whole-state effects (distinct / attempts) | 612 / 1494 | 87 / 2999 |
| Sources with a non-empty footprint (per intervention family, n >= 8) | 11 / 71 | 6 / 39 |
| Footprint stability within a family (first vs second half of its attempts, n >= 16) | Jaccard 0.07, 0 / 22 identical | — |
| Footprints per output channel (all families pooled, n >= 16) | 0 / 62 | — |

Findings:

1. **Atoms recur** as designed; the 16-atom cap never binds.
2. **Footprints do not hold.** Intervention families are explored in bouts of
   about 24 attempts and abandoned (192 families in 1500 ticks); within a
   family the two halves' footprints barely overlap.
3. **Pooling by channel does not rescue it.** A typical attempt drives about
   4 channels at once, so a feature's change is spread over all of them and
   none reaches positive specificity against the others.
4. **Almost no counterfactual baseline.** 5 passive windows in 1500 ticks: the
   organism acts nearly every tick, so "what happens anyway" is estimated
   only from other interventions.

Conclusion: the effect representation is not the only bottleneck in a
high-dimensional body. Stable causal attribution also needs exploration that
(a) repeats an intervention enough times, (b) varies one or few channels at a
time, and (c) leaves quiet windows. Implementing factorized effects alone
would give recurring atoms but not stable footprints, so competences would
still not ground. Options for the owner:

- **A.** Extend this specification with an exploration component
  (per-channel probing bouts, quiet baseline windows) and re-run the spike
  with it before implementation.
- **B.** Implement factorized effects now as a necessary but insufficient
  step, measured on E8, and specify exploration separately.
- **C.** Revisit the design (e.g. regression-style attribution of feature
  changes to simultaneously driven channels instead of per-source
  frequencies).

## 13. Causal probing exploration (owner option A, 2026-09-27)

The spike showed that stable attribution in a high-dimensional body needs
exploration that repeats an intervention, varies few channels at a time and
leaves quiet windows. Current exploration (`CompetenceDevelopmentEngine`)
drives a log-uniform number of channels per 24-tick epoch with smoothed,
continuously emitted levels: every tick is an attempt, ramps overlap, and
passive windows almost never occur.

### 13.1 Probing bouts

Exploration epochs are of two kinds, chosen deterministically per epoch by an
organism-owned hash at a **probing share** (proposed 0.5; no developmental
mode). The existing exploration drive already decides how often exploration
wins arbitration; probing only changes what exploration emits when it does:

- **coordination epochs** — the current behaviour, unchanged, so recurrent
  multi-channel synergies still arise;
- **probing epochs** — one exploration unit (one opaque channel, or one
  channel of a mutually exclusive group) is driven in **pulses**: within a
  24-tick epoch, `rest 4 / pulse 6 / rest 4 / pulse 6 / rest 4`, with the pulse
  level set directly (no smoothing) at a hash-chosen intensity. Rest ticks
  emit no command, so they are genuine passive windows.

The probed unit is chosen by causal information gain (§24-§25 of Agency v1:
untried or unresolved channels first, ties by use count and hash) and kept for
`probe_repeats` consecutive probing epochs (proposed 4, i.e. 8 pulses) before
moving on.

### 13.2 Invariants

- No anatomical or semantic grouping: units are the existing opaque
  exploration units (exclusive groups are respected as today).
- Deterministic: every choice is a pure function of organism id, epoch and
  the organism's own evidence.
- Protection, regulation and intents keep priority exactly as today; probing
  is only what exploration emits when it wins arbitration.
- Bounded amplitude: pulse levels stay within the current exploration target
  range.

### 13.3 Spike before implementation

Implement probing in a throwaway spike branch only, record change maps on a
fresh copy of the owner's organism (1500 ticks) and recompute §12: per-channel
footprints, their stability across halves, passive-window count, and whether
any dimension and competence would ground. Implementation of §4-§9 and §13
proceeds only if footprints form and hold.

### 13.4 First probing spike (2026-09-27)

Probing implemented on the throwaway branch `spike/causal-probing`
(probing share 0.5, 4 repeats, `rest 4 / pulse 6 / rest 4 / pulse 6 /
rest 4`), recorded on a fresh copy of the owner's organism (run stopped at
1032 transitions).

- Probing does what it should: 100% of attempts drive a single channel and
  passive windows rise from 5 to 255.
- **Per-tick attribution still fails** (0 channel footprints): a sustained
  pulse changes the body mostly at its onset, so each of its 6 tick-level
  attempts hits a caused atom only ~15% of the time (e.g. 0.17 vs 0.00 at
  rest), below the agentic threshold.
- **Pulse-level attribution works**: taking the atoms accumulated over each
  pulse against rest windows of the same length, both channels with at least
  4 pulses form footprints, with atoms at 0.69 vs 0.04 and 0.57 vs 0.02.
- Coverage is the open question: in ~1000 ticks only 2 of 62 channels got
  4+ pulses.

Design consequence: the unit of attribution for probing is the **pulse**, i.e.
the exploration commitment — Agency v1 already keeps commitment-level evidence
and temporal commitment families (§77-§79). Footprints are estimated from
commitment-level atom sets against equal-length quiet windows. A longer spike
(6000 ticks) measures per-channel coverage and footprint stability before
implementation of §4-§9 and §13.

### 13.5 Probing in main (off by default)

`CompetenceDevelopmentEngine(probing_share=...)` implements §13.1 in `main`
with `probing_share = 0.0` by default, so organisms and studies are unchanged
until attribution (§4-§9) lands. Probe state (share, unit, remaining repeats)
is checkpointed; older checkpoints restore with probing off.

### 13.6 Pulse attribution against ground truth (synthetic E8 body)

Probing share 0.5 on the E8 body (16 outputs, 4 correlated receptors each,
32 drifting receptors; 6000 ticks; seeds 101 and 149), footprints from pulse
atom sets against equal-length rest windows, compared with the apparatus
ground truth:

| Seed | Channels pulsed | >= 4 pulses | With footprint | Precision | Recall | Stability (Jaccard, halves) |
| --- | --- | --- | --- | --- | --- | --- |
| 101 | 16 | 5 | 5 | 0.75 | 0.50 | 0.28 (n=4) |
| 149 | 15 | 10 | 10 | 0.62 | 0.47 | 0.18 (n=2) |

Precision is the fraction of footprint atoms on receptors the channel really
drives (chance ~4%); recall is the fraction of its 4 receptors found (the
weakest, gain x0.25, often stays below one bucket). Dropping the magnitude
class from atoms changes nothing. The complete 1500-tick Physics3D probing
run agrees: all 4 channels with >= 4 pulses form footprints (16 of 62
channels pulsed).

Reading: pulse attribution finds the true causal receptors; what is missing
is **sample size per channel** — with 4-6 pulses per half, footprints are not
yet stable. The 6000-tick Physics3D run measures how stability grows with
pulses; if it stays low, the remedy is more repeats per probed unit, not a
different attribution.

### 13.7 Footprint membership (ADOPTED by the owner, 2026-09-27; replaces decision 2)

Within-channel stability (a channel's footprint from the first vs second half
of its own pulses; the run-halves metric compares different channels because
probing visits each channel in bursts) on the E8 body, 8 repeats, 12000
ticks, seeds 101/149, against ground truth:

| Membership rule | Precision | Recall | Within-channel Jaccard |
| --- | --- | --- | --- |
| Decision 2: agency >= 0.35 (model formula), pulse vs quiet runs of different length | 0.62-0.69 | 0.43-0.46 | 0.19-0.23 |
| Proposed: length-matched baseline + Wilson lower bound, margin 0.05 | 0.77-0.80 | 0.61-0.67 | 0.53-0.55 |

Causes found:

1. True receptors never change at rest (rate 0.00) and appear in 17-66% of
   pulses, yet an atom at 30% gets agency 0.45·0.30 + 0.35·0.30 + 0.10 = 0.34,
   just under 0.35, so true atoms flicker in and out.
2. Pulses (~6 ticks) are compared with quiet runs of ~4 ticks, so drifting
   receptors appear more often during pulses (0.25 vs 0.14) and pass as
   caused.
3. Magnitude classes are not the cause (removing them changes nothing).

Proposed rule: an atom belongs to a source's footprint when the lower 95%
Wilson bound of its pulse hit rate exceeds the rate expected for a quiet
window of the same length, `1 - (1 - q)^L` (q = per-tick passive rate, L =
mean pulse length), by a margin of 0.05, with at least 4 pulses. Hysteresis
applies to the margin. Controllability and agency estimates keep the model
formulas for everything else (dimensions, competences, EOL).

**Adopted and implemented** (`symbiont/actuation/footprint.py`): enter margin
0.05, exit margin 0.0, at least 4 pulses. Validated through the module
itself against E8 ground truth (8 repeats, 12000 ticks): precision 0.77 /
0.80, recall 0.67 / 0.61, within-channel Jaccard 0.55 / 0.55 (seeds 101 /
149).

**Traceability (owner requirement: every causal claim must be traceable).**
Each footprint member keeps the estimate that justified it — pulses, hits,
mean pulse length, passive windows and hits, expected quiet rate, Wilson
lower bound, contrast, and the model's controllability and agency against
the same length-matched baseline. `FootprintRegistry.explain(source)` returns
it and the checkpoint stores it, so any effect a competence, binding, intent
or outcome-learning key refers to can be traced back to the pulses and quiet
windows that established it. Pulses keep their commitment id, which links
back to the ledger's commitment evidence.

**Causal provenance, not only causal state** (owner review, 2026-09-27).
Keeping the evidence of the *current* members preserves state; tracing
causality end to end also needs its history. `FootprintRegistry` (schema 3)
therefore records:

- per member: the tick it entered and its latest estimate; every estimate
  carries `estimated_tick` and `last_pulse_tick`;
- a bounded, checkpointed transition log — ENTER, EXIT, PIN, UNPIN, EVICT —
  each with tick, previous membership, the margin applied, the estimate that
  caused it, the content before/after and the entity version;
- two identities: the **entity** (`footprint_entity_id(source)`, stable across
  versions, so an entity's evolution can be followed) and the **content**
  (`footprint_id(atoms)`, a function of membership only, never of evidence
  values);
- pins as **frozen snapshots**: membership always reflects current evidence,
  while a pinned content keeps resolving (`resolve`) with the evidence it had
  when pinned (`explain_pin`, including whether it is still current), so
  stale pinned evidence is never mistaken for current evidence.

A restored registry continues the same causal history as the uninterrupted
one (same transitions, identities and checkpoint). The remaining link —
evidence → footprint → dimension/competence/affordance/intent/outcome
learning decision — is traced when footprints are wired into those consumers.
