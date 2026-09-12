# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.20 — replicated fixed-world heritage stress

Symbiont Lab can now repeat the v0.19 heritage stress experiment across several paired source→target worlds instead of drawing conclusions from one lineage.

`symbiont-heritage-stress-study` runs the same four conditions for every source seed:

- `naive` — no inherited patterns;
- `learned` — bounded heritage learned in the source world;
- `inverted` — the same fingerprints with threat probabilities reversed;
- `misaligned` — learned beliefs deterministically rotated across fingerprints.

Within each source→target pair, all four conditions must receive **exactly the same target-world event stream**. The study refuses to aggregate a pair if that invariant is broken.

The replicated study keeps two questions separate:

1. **Performance versus the naive control** — paired deltas for attention, classification and calibration metrics.
2. **Heritage diagnostics** — prior/live/combined error, correction gain, override rate and re-export behavior.

Undefined rates remain `N/A` in this replicated study and are excluded only from the affected paired delta. Direction agreement is descriptive; it is not statistical significance or a probability that a result is true.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-heritage-stress-study \
  --source-seeds 3,7,11,17,23 \
  --target-offset 1009 \
  --hosts 100 \
  --steps 300 \
  --heritage-limit 24
```

The single-pair experiment remains available as `symbiont-heritage-stress`.

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and the reasoning engine may use only synthetic observations, local memory, collective reports, coarse fingerprints and derived trust.

Current safeguards include:

- attention and classification are separate metrics;
- evaluator breakdowns are available by family, phase and drift state;
- calibration uses the explicit threat score with binned ECE and Brier score;
- same-seed agent-side comparisons preserve the same synthetic world;
- attention/evidence selectors are observer-side only;
- paired evidence studies preserve per-world comparisons;
- heritage stress conditions assert an identical target-world digest;
- replicated heritage stress preserves source→target pairing rather than subtracting unrelated marginal means;
- inherited priors do not create reporters, trust or host memory;
- inherited-only beliefs cannot be re-exported without fresh live reports;
- research archives and evaluator truth never feed back into the species.

Two important legacy limitations remain intentionally **unfixed in v0.20** and are tracked for the next engine-integrity tranche: the longitudinal comparison still needs to preserve `N/A` instead of coercing it to zero, and the legacy `corrected_reexports` field means a threshold-direction flip, not a truth-validated correction.

Historical frozen audits and protocols live under `research/`.

## Evidence and attention experiments

The replicated shadow second-look study remains available:

```bash
symbiont-evidence-study --seeds 3,7,11,17,23 --hosts 100 --steps 300
```

Single-seed second look and equal-attention analysis remain available as `symbiont-evidence` and `symbiont-budget`.

## Roadmap

- **v0.1–0.14:** organism → ambiguity → resilience → reasoning → metacognition → curiosity → research memory → studies/campaigns → bounded longitudinal heritage.
- **v0.15:** experimental integrity — explicit evaluation contract and reproducible worlds.
- **v0.16:** equal-attention research.
- **v0.17:** bounded synthetic second look, shadow-only.
- **v0.18:** replicated paired second-look studies.
- **v0.19:** fixed-world learned/inverted/misaligned heritage stress.
- **v0.20 — replicated heritage stress:** **current** — several paired source→target worlds with separated performance and heritage diagnostics.
- **next:** repair the remaining causal/semantic integrity issues identified by the v0.19 audit before adding new cognitive mechanisms: independent reporter-selection RNG, longitudinal `N/A`, non-recycled trust evidence, and truth-aware re-export semantics; then move to causal online attention budgets and ecological-change heritage studies.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
