# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.19 — fixed-world heritage stress

Symbiont Lab can now test whether inherited collective knowledge helps, harms or gets corrected when the prior itself is wrong.

`symbiont-heritage-stress` first learns bounded heritage in one synthetic source world and then evaluates four conditions on **exactly the same target-world event stream**:

- `naive` — no inherited patterns;
- `learned` — the source heritage as learned;
- `inverted` — the same fingerprints with threat probabilities reversed;
- `misaligned` — learned beliefs deterministically rotated across fingerprints.

The target-world digest must be identical for all conditions. The only intervention is the inherited prior.

For each condition the observer records attention/classification metrics, Brier/calibration behavior and the fate of the inherited beliefs. For fingerprints actually observed in the target world it compares prior probability against empirical synthetic threat frequency, then measures live-evidence error, combined-belief error and correction gain. It also records whether old fingerprints are re-exported and whether re-exported beliefs switch direction.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-heritage-stress \
  --source-seed 7 \
  --target-seed 1016 \
  --hosts 100 \
  --steps 300 \
  --heritage-limit 24
```

A positive `correction_gain` means the final combined belief moved closer to the target world's empirical synthetic event rate than the inherited prior. It does **not** prove the fingerprint is a universally correct threat concept; fingerprints may contain mixed benign/threat events.

## Evidence and attention experiments

The shadow-only bounded-evidence study remains available across paired seeds:

```bash
symbiont-evidence-study --seeds 3,7,11,17,23 --hosts 100 --steps 300
```

Single-seed second look and equal-attention analysis remain available as `symbiont-evidence` and `symbiont-budget`.

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and the reasoning engine may use only synthetic observations, local memory, collective reports, coarse fingerprints and derived trust.

Current safeguards include:

- attention and classification are separate metrics;
- zero-denominator rates are `N/A`, not zero;
- evaluator breakdowns are available by family, phase and drift state;
- calibration uses the explicit threat score with binned ECE and Brier score;
- same-seed agent-side comparisons preserve the same synthetic world;
- attention/evidence selectors are observer-side only;
- paired studies preserve per-world comparisons;
- heritage stress conditions assert an identical target-world digest;
- inherited priors do not create reporters, trust or host memory;
- inherited-only beliefs cannot be re-exported without fresh live reports;
- research archives and evaluator truth never feed back into the species.

Historical frozen audits and protocols live under `research/2026-09-12/`.

## Roadmap

- **v0.1–0.14:** organism → ambiguity → resilience → reasoning → metacognition → curiosity → research memory → studies/campaigns → bounded longitudinal heritage.
- **v0.15:** experimental integrity — explicit evaluation contract and reproducible worlds.
- **v0.16:** equal-attention research.
- **v0.17:** bounded synthetic second look, shadow-only.
- **v0.18:** replicated paired second-look studies.
- **v0.19 — heritage stress:** **current** — learned, inverted and misaligned priors on one fixed target world.
- **next:** true ecological change between generations, replicated heritage-stress studies, and dashboard integration of the new experimental layers before considering any bounded agent-side evidence interface.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
