# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence: local learning, curiosity, memory, collective trust and bounded reasoning.

It deliberately has **no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data**. Every host, pathogen and reporter is a synthetic simulator object.

## v0.4 — bounded reasoning

v0.4 gives the population a small reasoning layer without giving it operational control. The reasoner receives only coarse fingerprints and aggregate collective beliefs. It can produce:

- a named hypothesis for an unresolved pattern;
- bounded confidence and investigation priority;
- a short rationale;
- information-seeking questions that could distinguish competing explanations.

It **cannot execute commands, call tools, inspect a real computer, generate remediation steps or modify the simulated world**. This deliberately separates thinking from acting.

## Live visualization

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --hosts 100 --steps 300 --seed 7 --delay 0.08
```

Open `http://127.0.0.1:8765`. The dashboard now shows live hypotheses beneath the population metrics. As collective certainty changes, hypotheses can appear, change priority or disappear when the population considers a pattern sufficiently understood.

The useful thing to watch is not merely detection rate. Watch whether the system develops questions such as:

> Does disagreement fall when one synthetic feature is reduced while comparable features stay stable?

That is the first explicit implementation of the “I do not know, but I know what I need to learn next” behavior.

## Experimental integrity

Ground truth remains isolated inside the evaluator. Neither source reputation nor the reasoning layer can read benign/pathogen labels. The external dashboard may show evaluator metrics, but those metrics do not feed back into agent reasoning.

## Roadmap

- **v0.1 — organism:** baseline, novelty, curiosity, collective memory.
- **v0.2 — memory and ambiguity:** label separation, overlap, forgetting, consolidation, live experiments.
- **v0.3 — species resilience:** heterogeneity, reputation and synthetic poisoned reports.
- **v0.4 — bounded reasoning:** **current** — hypotheses, uncertainty and information-seeking questions.
- **v0.5 — metacognition:** calibration, drift, blind spots and self-impact.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
