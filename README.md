# Symbiont Lab

A **safe simulation-only** prototype for exploring distributed defensive intelligence: local baselines, anomaly detection, curiosity, episodic memory, collective knowledge, and open questions.

It deliberately has **no propagation code, no persistence, no network scanning, no OS modification, and no access to real user data**. Hosts and “pathogens” are synthetic objects inside the simulator.

## MVP hypothesis

Can many small agents collectively learn useful defensive patterns without each agent containing a large AI model?

The first version models:

1. **Host learning** — every agent builds a baseline for its own synthetic host.
2. **Novelty** — observations are compared with that host-specific baseline.
3. **Risk** — disruptive signals are combined into a bounded risk score.
4. **Curiosity** — novelty × uncertainty × expected information gain × relevance.
5. **Episodic memory** — only interesting observations are retained.
6. **Collective memory** — agents share coarse behavior fingerprints, never raw host data.
7. **Open questions** — recurring patterns with insufficient confidence stay unresolved.

## Architecture

```text
Synthetic host A ── Agent A ──┐
Synthetic host B ── Agent B ──┼── Collective memory
Synthetic host C ── Agent C ──┘          │
                                         └── Open questions
```

Each agent has:

```text
observation
    ↓
host model
    ↓
novelty ─┐
          ├─ curiosity ── investigate?
risk ─────┤
          └─ memory / collective report
```

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-sim --hosts 100 --steps 300
pytest
```

Or without installing the CLI entry point:

```bash
PYTHONPATH=src python -m symbiont.cli --hosts 100 --steps 300
```

## What this version intentionally does not do

- No real endpoint monitoring.
- No self-replication.
- No stealth/evasion.
- No autonomous remediation.
- No LLM yet.
- No federated parameter training yet.

That separation is intentional: first test whether perception, curiosity and collective memory produce useful behavior. Language/reasoning should be added later only for cases that the statistical layer cannot explain.

## Suggested research sequence

### v0.1 — organism
Current version: baseline, anomaly, curiosity, collective memory.

### v0.2 — memory
Add forgetting, consolidation and concept formation from repeated episodes.

### v0.3 — species
Introduce agent diversity, trust/reputation and resistance to poisoned reports.

### v0.4 — reasoning
Add a constrained small-model reasoning layer that receives only abstract synthetic observations and proposes hypotheses/questions.

### v0.5 — metacognition
Track calibration, model drift and whether the defensive agent itself causes harm in the simulated world.

## Baseline result

With the deterministic default run (`100` hosts, `300` steps, seed `7`):

```text
pathogen events:   460
investigations:    463
true positives:    456
false positives:   7
detection rate:    99.1%
precision:         98.5%
```

This is **not a security benchmark**. The synthetic pathogens are intentionally easy to separate in v0.1. The result only verifies that the learning/attention pipeline is wired correctly. The next experiment should make benign and harmful behavior overlap so that uncertainty and curiosity become necessary rather than decorative.

## Next experiment: v0.2

The next useful milestone is not a real endpoint agent. It is a harder simulated ecology with:

- ambiguous benign events that resemble attacks;
- stealthy simulated pathogens that stay close to normal behavior;
- short-, episodic- and long-term memory;
- forgetting and consolidation;
- collective reports that can be wrong;
- trust/reputation between agents;
- explicit unresolved hypotheses;
- calibration: whether confidence matches reality;
- agent self-impact: detecting when its own intervention worsens the simulated host.

The key research question becomes: **does collective curiosity improve discovery without causing a false-positive explosion?**
