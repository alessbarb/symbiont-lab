# Factorized Effect Representation v1 — Draft Specification

**Status:** DRAFT for owner review. Not implemented.
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

Identity `effect.atom.<hash(feature_ref, direction, magnitude_class)>`.
The atom vocabulary is bounded by `features x 2 x 3` and recurs by
construction. A transition yields a **set** of atoms (possibly empty).

### 4.2 Causal footprints (composite effects)

A **footprint** is the set of atoms a causal source reliably produces beyond
the counterfactual rate:

```text
footprint(source) = { atom : agency(source, atom) >= footprint_agency
                             and controllability(source, atom) > 0 }
```

Identity `effect.footprint.<hash(sorted atom ids)>`. Footprints are what
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

## 11. Open decisions for the owner

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
