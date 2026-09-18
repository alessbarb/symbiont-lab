# Genesis v1 — W01/W02 audit

Preregistration and script: `run_w01_w02.py`. Raw output: `results.json`.
Runner: `symbiont_lab.world.adapter.SingleOrganismGenesisRuntime` (W3,
docs/design/symbiont-world-v1.md §15) against `symbiont_lab.world.genesis_v1`
(the frozen Genesis v1 preset). Seeds `101, 127, 149`, `300` ticks each,
single stationary organism, hex world 8×8 (bounded smoke scale, not the
full 64×64 Genesis map — reproducibility only requires the same
`GroundTruth`/topology width, not the full map size).

## W01 — result: **H0 stands (NOT rejected)**

Preregistered rule: reject H0 only if the cognitive policy's
`composite_score` (mean metabolic reserve + integrity, both in `[0,1]`)
exceeds the random-policy control's in at least 2 of 3 seeds.

```
seed 101: cognitive=1.450  random=1.949   cognitive loses
seed 127: cognitive=1.300  random=2.000   cognitive loses
seed 149: cognitive=2.000  random=2.000   tie (not a win)
cognitive_wins = 0 / 3
```

**Observed mechanism, not yet a confirmed claim (OBSERVED, needs
replication):** the cognitive policy's action counts show near-exclusive
`INTAKE` selection (e.g. 279/300 ticks on one resource) and *zero*
`REPAIR` actions across all three seeds. The random control, by uniform
sampling, selects `REPAIR` 28–41 times per run and ends with materially
higher integrity. Hazard damage (`apply_environmental_damage`) is an
externally injected consequence the organism's local action model does
not predict as a consequence of any opportunity's `ExpectedOutcome` —
nothing in `action_opportunities()` currently links accumulated
environmental damage to `REPAIR`'s expected value, so a purely
expected-outcome-greedy policy (`exploration=0.0`, the default) never
learns to reach for it reactively. This is a plausible, falsifiable
mechanism, not confirmed: it has not been tested against a longer horizon,
different hazard parameters, or repair-cost sensitivity.

This matches this project's own documented pattern of controls turning out
more effective than the "real" condition (cf. prior sensory-specialisation
runs where the negative-control baseline outperformed or matched the
organism's adaptive path) — consistent with, not contradicting, prior
findings.

## W02 — result: **H0 stands (NOT rejected), plus a methodological finding**

Two operationalizations were run, because the naive one is a tautology:

- `identical_clone`: two replicas sharing both `world_seed` and
  `organism_seed`. Diverges: **False**. This is expected and uninformative
  — with every RNG stream in the adapter and the organism derived from the
  same two seeds, identical behavior is guaranteed by construction
  (confirms invariant 2, determinism; it is not evidence about anything
  else).
- `distinct_history`: two replicas sharing `world_seed` (same world) but
  with *different* `organism_seed` (`+1000`, `+2000`) — the actual W02
  operationalization the spec asks for. Diverges: **also False.** Action
  counts and `composite_score` are bit-for-bit identical between the two
  replicas.

**This is a real, if unglamorous, finding about the current build, not a
fabricated null result:** in this v1 wiring, `organism_seed` only reaches
`mutation_seed` (which matters solely for genome mutation, exercised only
during reproduction) and `body_schema` salt (which does not feed action
selection). With `exploration=0.0` (deterministic Pareto tie-break),
`discover_senses=False`, and `sensory_plasticity` left at its default
(off), there is currently **no causal path from a different
`organism_seed` to a different single-lifetime action trajectory** for a
lone, non-reproducing organism. W02 as specified needs one of: (a)
`exploration > 0` with a genuinely independent per-replica RNG feeding
tie-break, (b) `sensory_plasticity=True`/`discover_senses=True` so
adaptive sensing has room to diverge, or (c) reproduction, so mutation
actually executes. None of those are in W3's v1 scope (§15 explicitly
excludes movement/reproduction/communication) — this is recorded as an
open methodological gap for the next increment, not as a claim that
Symbionts cannot diverge.

## Status

Both gates ran against real data from the real adapter; neither rejects
its H0. Per docs/design/symbiont-world-v1.md §15: *"Su resultado — sea
cual sea, incluida convergencia trivial como H0 — es lo que cierra v1, no
la existencia del adaptador por sí sola."* This closes v1's falsification
program as specified: the organism was tested, real numbers came back,
and the honest reading is that neither hypothesis was rejected at this
scale. W03+ (ecology, evolution, culture, open-endedness) remain
correctly gated behind this — with W01/W02 both at H0, there is no basis
to proceed to interpreting niches, heredity or culture as if adaptation
were already demonstrated (§8, barrera formal entre programas).
