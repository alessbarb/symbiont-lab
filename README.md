# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.24.2 — exact online causal quantiles

The frozen v0.24 audit also identified a scaling limit in the causal selector: after semantic correctness, every event rebuilt `sorted(history)` to obtain a historical quantile. That is exact but superlinear enough to make the full corrected revalidation unnecessarily expensive.

v0.24.2 replaces repeated sorting with a deterministic order-statistics treap. It stores the same observed scores, preserves duplicates, and returns the **same quantile value** as the historical sorted-prefix implementation. The tree shape is determined only by insertion order and does not affect score ordering or policy decisions.

A regression compares online quantiles against the old reference implementation across continuous values, zeros, repeated ties and several target rates. This release is therefore intended as a performance-equivalent infrastructure change, not a new attention policy.

## v0.24.1 — audit-integrity corrections

The frozen v0.24 audit is archived under `research/v024-audit/`. It verified the v0.21 integrity corrections but found three methodological gaps that must be fixed before the causal-attention line is interpreted further.

### Causal attention startup

v0.22/v0.23 were genuinely causal — selectors did not inspect future scores — but the novelty selector could spend most or all of a small budget on zero-valued startup novelty. After 32 historical zeros its learned threshold became zero and `score >= threshold` accepted every tie.

v0.24.1 therefore:

- defines one common startup eligibility interval for **all** compared causal selectors: the first six observations per host are not spendable because host-relative novelty is not yet defined;
- resolves score ties causally with the current event's deterministic tiebreak instead of accepting the full tie block;
- records `eligible_events`, zero-score selections and spend by `warmup`, `pre_drift` and `post_drift`;
- keeps the ex-ante budget equal across strategies and preserves prefix causality.

The historical v0.22/v0.23 results remain reproducible records, but their novelty comparisons should not be treated as evidence until rerun under the corrected contract.

### Evidence-revision identity

v0.21 made trust recalibration idempotent when no fresh reports arrived, but an identical vote could still be replayed as a new report and cause every historical source in the pattern to be evaluated again.

v0.24.1 gives live reports evidence identities. The simulator identifies reports by event step. Replaying the same identity is ignored; compatibility-mode identical latest votes are also treated as replay. A fresh revision evaluates only the source that supplied that revision against its current peers instead of re-scoring every old voter.

Peer consensus is still not ground truth. Collusion and poisoning remain measurable failure modes; this change only prevents duplicated evidence from manufacturing confidence.

### Strong noise-sweep pairing

Second-look studies now expose:

- a digest of the complete synthetic world;
- a digest of the exact selected `(step, host_index)` identities for every strategy.

`symbiont-evidence-noise-sweep` refuses to continue if changing sensor noise changes either digest. Count and pre-Brier checks remain as additional invariants.

The auxiliary sensor is still **shadow-only** and does not influence the live agent.

## v0.24 — paired second-look sensor-noise sweep

`symbiont-evidence-noise-sweep` runs the same first-look selections across several sensor-noise levels and validation seeds. By default:

- validation seeds: `211,223,239,251,269`;
- sensor noise: `0.08,0.18,0.30,0.45`;
- evidence capacity: `12` second looks per 1,000 events.

The sensor RNG is deterministic per event. Re-running the same event at different noise levels reuses the same underlying random draw and changes only its amplitude, giving the sweep a paired interpretation.

Reported metrics include Brier gain, net classification-correction rate, entropy reduction, `stealth_sim` correction rate when defined and paired degradation relative to the lowest tested noise level. Direction agreement remains descriptive, not statistical significance.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-causal-budget \
  --hosts 100 \
  --steps 300 \
  --seed 7 \
  --budget-per-1000 12

symbiont-causal-budget-study \
  --seeds 101,127,149,173,199 \
  --budgets-per-1000 5,12,20 \
  --hosts 100 --steps 300

symbiont-evidence-noise-sweep \
  --seeds 211,223,239,251,269 \
  --noise-levels 0.08,0.18,0.30,0.45 \
  --hosts 100 \
  --steps 300 \
  --budget-per-1000 12
```

The retrospective `symbiont-budget` tool remains available as a descriptive upper-bound comparison, but it is not treated as an online policy experiment.

## Integrity foundation

The current research line now enforces:

- reporter poisoning and agent personality consume independent deterministic RNG streams;
- trust consumes each identified live evidence revision at most once;
- identical replay does not create report or trust evidence;
- undefined longitudinal rates remain `N/A`;
- generation 1 is a parity control and is excluded from mean heritage-effect estimates;
- threshold-direction changes are separated from evaluator-measured re-export improvement;
- replicated studies reject duplicate seed lists;
- causal attention uses common startup eligibility, explicit tiebreaks and phase diagnostics;
- causal historical quantiles are maintained online with exact order statistics;
- sensor-noise sweeps verify exact world and selected-event digests;
- evaluator truth never feeds the organism.

## Experimental tools

```bash
# Baseline synthetic population
symbiont-sim --hosts 100 --steps 300 --seed 7

# Longitudinal inheritance
symbiont-generations --generations 5 --hosts 100 --steps 300 --seed 7

# Retrospective equal-attention score analysis
symbiont-budget --hosts 100 --steps 300 --seed 7

# Causal online attention: replicated paired study
symbiont-causal-budget-study \
  --seeds 101,127,149,173,199 \
  --budgets-per-1000 5,12,20 \
  --hosts 100 --steps 300

# Paired second-look noise sweep
symbiont-evidence-noise-sweep \
  --seeds 211,223,239,251,269 \
  --noise-levels 0.08,0.18,0.30,0.45 \
  --hosts 100 --steps 300 --budget-per-1000 12

# Replicated fixed-world heritage stress
symbiont-heritage-stress-study \
  --source-seeds 3,7,11,17,23 \
  --target-offset 1009 \
  --hosts 100 \
  --steps 300
```

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and the reasoning engine may use only synthetic observations, local memory, collective reports, coarse fingerprints and derived trust.

Current safeguards include:

- attention and classification are separate metrics;
- evaluator breakdowns are available by family, phase and drift state;
- calibration uses the explicit threat score with binned ECE and Brier score;
- host profiles, agent traits, reporter selection, event scheduling, observations and drift use separated deterministic random streams;
- same-seed comparisons preserve the same synthetic world;
- repeated trust recalibration without fresh evidence is idempotent;
- replayed evidence identities are rejected;
- longitudinal optional rates remain `N/A` rather than becoming zero;
- attention/evidence experiments are observer-side and do not change agent decisions;
- causal attention selectors cannot inspect future scores;
- causal selectors share startup eligibility and equal capacity;
- causal quantile optimization is regression-checked against the sorted-prefix reference;
- replicated causal studies preserve `seed × budget` pairing;
- second-look noise sweeps assert exact world and selected-event identity parity;
- replicated studies require unique seeds and preserve per-world pairing;
- heritage stress conditions assert an identical target-world digest;
- inherited priors do not create reporters, trust or host memory;
- research archives and evaluator truth never feed back into the species.

Historical frozen audits and protocols live under `research/`.

## Roadmap

- **v0.1–0.14:** organism → ambiguity → resilience → reasoning → metacognition → curiosity → research memory → studies/campaigns → bounded longitudinal heritage.
- **v0.15:** explicit evaluation contract and reproducible worlds.
- **v0.16:** retrospective equal-attention observer research.
- **v0.17:** bounded synthetic second look, shadow-only.
- **v0.18:** replicated paired second-look studies.
- **v0.19:** fixed-world heritage stress.
- **v0.20:** replicated source→target heritage stress.
- **v0.21:** engine-integrity corrections from the frozen audit.
- **v0.22:** causal online attention under a fixed ex-ante capacity.
- **v0.23:** replicated causal attention across validation seeds and capacities.
- **v0.24:** paired second-look sensor-noise sweep, still shadow-only.
- **v0.24.1:** audit-integrity corrections: startup/ties, evidence replay identity and exact sweep pairing.
- **v0.24.2 — causal scaling:** **current** — exact online order-statistics quantiles with regression equivalence.
- **next:** rerun the causal attention comparison under the corrected/scalable contract; then resume ecological heritage shift. Do not connect second-look evidence to the live agent before observer-side evidence is robust.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
