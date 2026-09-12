# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence: local learning, curiosity, memory, collective trust, bounded reasoning, metacognition and adaptation in changing synthetic worlds.

It deliberately has **no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data**. Every host, pathogen, reporter and counterfactual is a synthetic simulator object.

## v0.7 — experimental curiosity

v0.7 turns “I do not know” into a bounded research agenda. The system now ranks **shadow-only counterfactual probes** for unresolved hypotheses.

A probe is a question such as:

> In a shadow-only counterfactual, does lowering synthetic network intensity from H to M materially change collective belief?

The planner scores candidates by expected information gain and a small synthetic cost. It can inspect only coarse fingerprints, collective beliefs and bounded hypotheses. It cannot run commands, inspect real machines or modify even the simulated hosts.

This gives Symbiont Lab a measurable form of curiosity: not merely surprise, but choosing what would be most informative to understand next.

## Live visualization

```bash
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --hosts 100 --steps 300 --seed 7 --poison-fraction 0.08 --drift-fraction 0.35 --drift-magnitude 0.22 --delay 0.08
```

Open `http://127.0.0.1:8765`. The dashboard now includes a live **Curiosity agenda** with the highest-value counterfactual questions, expected information gain and utility.

## Experimental integrity

- Ground truth remains evaluator-only.
- Curiosity plans only over synthetic aggregate representations.
- Counterfactual probes are descriptive shadow questions, not host actions.
- Reasoning and curiosity cannot execute tools or alter the world.
- Drift membership is hidden from the species.

## Roadmap

- **v0.1 — organism:** baseline, novelty, curiosity, collective memory.
- **v0.2 — memory and ambiguity:** label separation, overlap, forgetting, consolidation, live experiments.
- **v0.3 — species resilience:** heterogeneity, reputation and synthetic poisoned reports.
- **v0.4 — bounded reasoning:** hypotheses, uncertainty and information-seeking questions.
- **v0.5 — metacognition:** self-confidence, calibration, overconfidence and blind spots.
- **v0.6 — changing worlds:** benign regime drift and cautious adaptation.
- **v0.7 — experimental curiosity:** **current** — rank safe shadow counterfactuals by expected information gain.
- **v0.8 — research memory:** track which questions persist, recur or become resolved across experiments.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
