# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence: local learning, curiosity, memory, collective trust, bounded reasoning and metacognition.

It deliberately has **no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data**. Every host, pathogen and reporter is a synthetic simulator object.

## v0.5 — metacognition

v0.5 adds an explicit distinction between what the simulated species can know about its own uncertainty and what the external experiment evaluator knows from ground truth.

The internal self-model can estimate, without labels:

- self-confidence;
- epistemic pressure;
- average uncertainty and novelty;
- collective disagreement;
- whether the current population state looks stable, watchful, novel, contested or uncertain.

The external evaluator separately measures:

- calibration error;
- Brier score;
- high-confidence error rate;
- blind spots — simulated threats missed while the population was relatively confident.

**Evaluator metrics never feed back into agents, trust, reasoning or metacognition.** This lets the experiment ask a meaningful question: does the population know when it does not know?

## Live visualization

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --hosts 100 --steps 300 --seed 7 --poison-fraction 0.08 --delay 0.08
```

Open `http://127.0.0.1:8765`.

The dashboard now separates **Internal self-model** from **External evaluator**. A useful experiment is to watch for periods where self-confidence rises while calibration or blind-spot metrics deteriorate. Those are candidate failures of metacognition rather than ordinary detection failures.

## Experimental integrity

Ground truth is isolated inside `Evaluator`. Source reputation, reasoning and `MetacognitionEngine` operate without benign/pathogen labels. The browser can display both sides because it is an observer of the experiment, not part of the simulated species.

## Roadmap

- **v0.1 — organism:** baseline, novelty, curiosity, collective memory.
- **v0.2 — memory and ambiguity:** label separation, overlap, forgetting, consolidation, live experiments.
- **v0.3 — species resilience:** heterogeneity, reputation and synthetic poisoned reports.
- **v0.4 — bounded reasoning:** hypotheses, uncertainty and information-seeking questions.
- **v0.5 — metacognition:** **current** — self-confidence, calibration, overconfidence and blind spots.
- **v0.6 — changing worlds:** regime drift, concept drift and adaptation under environmental change.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
