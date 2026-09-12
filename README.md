# Symbiont Lab

A **safe, simulation-only** research prototype for exploring distributed defensive intelligence: local baselines, anomaly detection, curiosity, bounded memory, collective beliefs, source trust and open questions.

It deliberately has **no propagation code, no persistence, no network scanning, no OS modification, no stealth/evasion, and no access to real user data**. Hosts and “pathogens” are synthetic objects inside the simulator.

## v0.3 — species resilience

v0.3 asks a harder question: what happens when the population itself is imperfect?

It adds:

- heterogeneous agents with slightly different risk/curiosity thresholds;
- a configurable minority of synthetic agents that invert their collective reports;
- source reputation learned from agreement with independent peers — without simulator ground truth;
- trust-weighted collective beliefs;
- explicit population-health metrics: mean source trust, low-trust sources and evaluator-side trust gap;
- live dashboard support for watching trust formation and poisoning resistance over time.

The poisoned agents are **only simulated reporters inside the synthetic ecology**. They do not compromise software, devices or networks.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
symbiont-sim --hosts 100 --steps 300 --seed 7
```

Experiment with population integrity:

```bash
symbiont-sim --poison-fraction 0.15 --heterogeneity 0.18
```

## Live dashboard

```bash
symbiont-dashboard --hosts 100 --steps 300 --seed 7 --poison-fraction 0.08
```

Open `http://127.0.0.1:8765`. In addition to detection/precision, the dashboard now shows mean source trust and the **trust gap** between honest and poisoned reporters. That trust gap is calculated by the external evaluator; the collective itself never receives the answer key.

## Experimental integrity

Ground truth stays outside the organism. `Observation` has no benign/pathogen label. Source trust is inferred from peer agreement, not from a trusted oracle, so collusion and bad consensus remain possible research outcomes rather than being designed away.

## Safety boundaries

Symbiont Lab remains a laboratory ecology, not endpoint software: no real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.

## Roadmap

- **v0.1 — organism:** local baseline, novelty, risk, curiosity, collective memory.
- **v0.2 — memory and ambiguity:** ground-truth separation, overlap, forgetting, consolidation, live experiments.
- **v0.3 — species resilience:** **current** — heterogeneity, reputation, poisoned reports, trust-weighted consensus.
- **v0.4 — reasoning:** constrained hypotheses and information-seeking over synthetic abstractions only.
- **v0.5 — metacognition:** calibration, drift, blind spots and self-impact.

The research question is now:

> **Can a population learn whom to trust without being given a trusted oracle?**
