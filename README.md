# Symbiont Lab

A **safe, simulation-only** research prototype for exploring distributed defensive intelligence: local baselines, anomaly detection, curiosity, bounded memory, collective beliefs, and open questions.

It deliberately has **no propagation code, no persistence, no network scanning, no OS modification, no stealth/evasion, and no access to real user data**. Hosts and “pathogens” are synthetic objects inside the simulator.

## Research hypothesis

Can many small agents collectively learn useful defensive patterns without each agent containing a large AI model — and can they recognize when they do **not** understand what they are seeing?

## v0.2 — memory and ambiguity

v0.2 removes a major experimental shortcut from v0.1: agents no longer receive simulator ground truth. `Observation` contains perception only; truth lives in a separate `SimulatedEvent` envelope used exclusively by the evaluator.

This version adds:

1. **No label leakage** — agents cannot inspect whether an event is benign or pathogenic.
2. **Ambiguous ecology** — benign backups/builds can resemble attacks; a stealth pathogen stays close to normal behavior.
3. **Adaptive host models** — online statistics slowly forget old normality and adapt to drift.
4. **Bounded episodic memory** — agents retain interesting investigations instead of every observation.
5. **Forgetting and consolidation** — low-salience episodes disappear; useful old episodes compress into semantic concepts.
6. **Collective belief vs certainty** — the species separately tracks *what* it believes and *how sure* it is.
7. **Open questions** — repeated patterns with insufficient certainty remain unresolved.
8. **External evaluation** — precision/recall metrics are computed outside the agent.
9. **Live experiment dashboard** — stream snapshots to a local browser while the synthetic world runs.

## Architecture

```text
Synthetic world
  │
  ├── SimulatedEvent ───────────────→ Evaluator (ground truth)
  │        │                              │
  │        └── Observation only           └── live snapshots ──→ Dashboard
  │                 ↓
  │              Agent
  │        ┌────────┼────────┐
  │        ↓        ↓        ↓
  │    Host model  Memory  Curiosity
  │        └────────┼────────┘
  │                 ↓
  └────────── Collective memory
                 │
                 └── Open questions
```

The separation matters: the organism must be able to be wrong.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-sim --hosts 100 --steps 300 --seed 7
pytest
```

### Live dashboard

```bash
symbiont-dashboard --hosts 100 --steps 300 --seed 7
```

Then open `http://127.0.0.1:8765` in a browser. The dashboard is intentionally bound to localhost and has no external dependencies. It shows, while the simulation advances:

- detection rate, precision and false-positive rate;
- investigations and progress;
- collective patterns and open questions;
- memory consolidation/forgetting;
- time-series learning curves and a compact population-state view.

Use `--delay 0.1` to slow the experiment for observation, `--port 9000` to choose another local port, or `--threat-rate` to change the synthetic ecology.

## Deterministic v0.2 reference run

With `100` hosts, `300` steps, seed `7`:

```text
pathogen events:     421
benign events:       29579
investigations:      298
true positives:      212
false positives:      86
false negatives:     209
detection rate:      50.4%
precision:           71.1%
false-positive rate:  0.3%
known patterns:       57
open questions:       11
consolidated:        207
```

This is **not a security benchmark**. The lower headline scores are intentional: v0.1 was too separable and leaked labels into learning. v0.2 creates overlap and uncertainty so curiosity and collective knowledge can actually matter.

## Safety boundaries

Symbiont Lab remains a laboratory ecology, not endpoint software.

- no real endpoint monitoring;
- no self-replication or propagation;
- no stealth/evasion;
- no autonomous remediation;
- no network scanning;
- no modification of the host OS;
- no collection of real user data;
- no offensive exploitation;
- no LLM-generated system actions.

## Research roadmap

### v0.1 — organism
Baseline learning, novelty, risk, curiosity and collective memory.

### v0.2 — memory and ambiguity
**Current version.** Separate ground truth, overlapping benign/threat behavior, forgetting, consolidation, explicit uncertainty and live observability.

### v0.3 — species
Add heterogeneous agents, source trust/reputation, adversarially wrong reports, poisoning resistance and population health metrics.

### v0.4 — reasoning
Add a constrained reasoning layer over **synthetic abstractions only**. It proposes hypotheses and information-seeking questions; it does not execute system actions.

### v0.5 — metacognition
Track calibration, model drift, collective blind spots, self-impact and whether the population knows when its own model is failing.

The central question is no longer “can it flag simulated malware?” It is:

> **Can a population discover what it does not understand, learn from disagreement, and improve without being given the answer?**
