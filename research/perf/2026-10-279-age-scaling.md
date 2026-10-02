# #279 — Cognitive cost scaling with organism age

Status: measured and attributed; no optimization applied  
Issue: [#279](https://github.com/alessbarb/symbiont-lab/issues/279)  
Apparatus: `scripts/bench_age_scaling.py` at base `a91b93d7`

## Question

How does the cost of one developing organism change with its age, in which
runtime domain, and through which mechanism?

## Method

One private-model organism (seed 127, four-actuator `CausalBody`, no physics,
World or telemetry writer) was developed once; its checkpoint was saved on
reaching ages 500, 1000, 2000, 5000 and 10000 ticks. Each age was then restored
into a fresh Body and measured three times, in a randomized order, so every age
is the same individual and age is not confounded with when it was measured. Per
measurement: 32 warm-up ticks, then a 100-tick window with the observer off and
another with the observer on; the Body step is timed apart from the organism
tick.

The subject is the organism as constructed before the canonical organism
profile (ADR-0062): no sensory plasticity, no predictor auto-promotion. The
mechanisms attributed here do not depend on those options.

## Results

Medians of the three repeats (range of the tick median in brackets).

| Age | Tick median ms | p95 | p99 | Observer read ms | RSS MB | Checkpoint MB | Restore ms | Training plan ms (vocabulary) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 500 | 50 (49–57) | 63 | 70 | 62 | 222 | 4.3 | 264 | 33 (579) |
| 1000 | 129 (112–145) | 164 | 175 | 82 | 217 | 6.3 | 457 | 59 (879) |
| 2000 | 251 (209–292) | 323 | 343 | 131 | 241 | 9.4 | 517 | 174 (1409) |
| 5000 | 498 (372–564) | 578 | 607 | 262 | 241 | 18.5 | 1028 | 330 (3003) |
| 10000 | 440 (412–587) | 501 | 535 | 274 | 268 | 21.0 | 996 | 387 (3760) |

- **Body step:** 0.02 ms at every age. Body cost is negligible and does not grow.
- **In-tick observability tax** (observer-on minus observer-off tick): within
  measurement noise beyond age 1000.
- **External observer read** (state hash and passive projections, outside the
  tick): grows from 62 to 274 ms.
- **Checkpoint at 10000:** the largest fields are the experience archive
  (8.4 MB), the experience ledger (5.0 MB), actuation (4.7 MB) and episodic
  memory (1.9 MB).

## Attribution

### Organism tick: retrospective episodic reinterpretation

Organism tick latency grows about tenfold from age 500 to 5000, then flattens.
The growth follows one mechanism, counted deterministically (independent of host
load):

`ModeledOrganismRuntime._refresh_episodic_interpretations`
(`src/symbiont/modeling/runtime.py:762`) runs every tick. For every concept
lineage, `EpisodicExperienceMemory.reinterpret`
(`src/symbiont/modeling/episodic.py:1142`) scans every stored episode and
rebuilds its projection, which is rebuilt and validated on every access.

| Age | Concept lineages | Episodes | Projection builds per tick |
| --- | --- | --- | --- |
| 500 | 7 | 452 | 3,808 |
| 1000 | 16 | 777 | 13,691 |
| 2000 | 32 | 781 | 26,239 |
| 5000 | 55 | 777 | 44,290 |

The cost is proportional to lineages × episodes:

- Episodes saturate near 780, at the episodic memory's byte cap.
- In this run, lineages stopped at 55 by age 5000. That is why latency flattens
  between 5000 and 10000.
- Lineages are bounded only by `KernelLimits.max_concepts = 192`. An organism
  that reaches that bound would pay roughly 3.5 times the age-5000 cost. This is
  an extrapolation, not measured.

**No interpretation was ever recorded** (`episodic_interpretations = 0` at every
age). The per-episode cheap exit therefore never fires, and all the work
produces nothing. Either the support tokens (`parent`, `sense.parent`,
`concept.parent`) never match the tokens episodes are indexed by, or concept
parents never overlap episode context at the 0.5 threshold. This is recorded as
an **unresolved functional finding**: retrospective reinterpretation, as
configured, does not occur. Whether it should is a scientific question.

### Other growing costs

- **Private-model training plan:** grows with tokenizer vocabulary (579 → 3760
  tokens, 33 → 387 ms per plan). Linear in vocabulary; paid per training plan,
  not per tick.
- **Checkpoint size and restore time:** grow with the experience archive,
  ledger and actuation evidence. All are bounded; restore reaches about 1 s at
  age 10000.
- **External observer read:** grows with the same structures it hashes.

## Proposed changes

| Change | Kind | Expected effect |
| --- | --- | --- |
| Cache each episode's projection: the factual core is immutable, so the projection is a pure function of it | Semantically neutral; must be proven by state-hash equivalence over a developed organism | Removes most of the per-tick rebuild cost |
| Reinterpret only lineages or episodes that changed since the last pass | Semantically neutral if `reinterpret` is idempotent for unchanged inputs; same equivalence proof | Makes the per-tick cost proportional to change instead of age |
| Decide whether retrospective reinterpretation should ever fire, and repair it if so | **Scientific**: changes what the organism remembers | Owner decision; needs its own protocol |

No change was applied. The two neutral changes are candidates for an ORDINARY
change with equivalence evidence. The third is for the owner.

## Limits

- **Uncontrolled host:** load average 1.7–2.4. Part of the run overlapped test
  executions, and repeats of the same age differ by up to about 35 %. The
  tenfold growth and the deterministic counts are far outside that spread; small
  differences between neighbouring ages are not interpretable.
- **One seed, one Body.** Age 25000 was not reached within the development time
  limit.
- **Pre-profile subject:** measured before the canonical organism profile `v1`.
  Re-measure after that profile lands to confirm it adds no new growing term,
  for example receptor-driven drift baselines, which are now bounded.
