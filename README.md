# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence: local learning, curiosity, memory, collective trust, bounded reasoning and metacognition in changing synthetic worlds.

It deliberately has **no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data**. Every host, pathogen and reporter is a synthetic simulator object.

## v0.6 — changing worlds

v0.6 asks a harder question than “is this unusual?”: **can the population notice that normality itself changed without treating the new world forever as an attack?**

At a configurable point in the simulation, a subset of synthetic hosts receives a benign workload regime shift. Their normal CPU, network, file-change and process activity changes. Agents are not told that the shift occurred.

Agents now have a deliberately conservative drift adaptation mechanism: sustained novelty may update a host baseline only when risk remains low and collective threat belief is not strong. This mechanism has no access to simulator truth and can therefore make mistakes — an important experimental property.

The external evaluator tracks false positives specifically on drifted benign hosts, including a recent rolling rate, while the internal population sees only novelty, uncertainty, collective beliefs and its own adaptation state.

## Live visualization

```bash
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --hosts 100 --steps 300 --seed 7 --poison-fraction 0.08 --drift-fraction 0.35 --drift-magnitude 0.22 --delay 0.08
```

Open `http://127.0.0.1:8765`. Around the drift step, watch mean novelty and epistemic pressure rise. A healthy adaptation should eventually reduce novelty and the recent drift false-positive rate rather than simply learning that every changed state is malicious.

## Experimental integrity

- Agents receive observations, never benign/pathogen labels.
- Agents are not told which hosts underwent concept drift.
- Source reputation uses peer agreement, not an oracle.
- Bounded reasoning cannot act on the world.
- Metacognition sees internal uncertainty only.
- Drift truth and drift-specific false-positive metrics belong to the external evaluator only.

## Roadmap

- **v0.1 — organism:** baseline, novelty, curiosity, collective memory.
- **v0.2 — memory and ambiguity:** label separation, overlap, forgetting, consolidation, live experiments.
- **v0.3 — species resilience:** heterogeneity, reputation and synthetic poisoned reports.
- **v0.4 — bounded reasoning:** hypotheses, uncertainty and information-seeking questions.
- **v0.5 — metacognition:** self-confidence, calibration, overconfidence and blind spots.
- **v0.6 — changing worlds:** **current** — benign regime drift and cautious adaptation.
- **v0.7 — experimental curiosity:** choose among safe synthetic probes by expected information gain.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
