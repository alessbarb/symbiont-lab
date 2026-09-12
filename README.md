# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.14 — longitudinal species and bounded heritage

Symbiont Lab can now study synthetic generations without introducing software reproduction or propagation.

A generation may receive a compact **heritage** consisting only of coarse collective fingerprint priors from the previous generation. It never inherits:

- executable code changes;
- host baselines or personal memory;
- source identities or source trust;
- raw observations;
- evaluator ground truth;
- researcher study history.

Inherited priors are deliberately weak. They do not count as live reporters and fresh evidence can override them.

A pattern can survive into the next generation only if the current population independently rebuilds enough live support and source diversity. An inherited pattern that is never observed again disappears instead of becoming permanent dogma.

### Paired longitudinal experiment

Each synthetic generation is run twice against the same deterministic world seed:

```text
same world
   ├── inherited population
   └── naive control population
```

This lets the observer measure whether heritage improves or harms:

- detection;
- precision;
- false-positive rate;
- calibration;
- blind spots.

It also measures how many abstract patterns are inherited, re-earned and exported to the next generation.

### CLI

```bash
source .venv/bin/activate
pip install -e '.[dev]'

symbiont-generations \
  --generations 5 \
  --hosts 100 \
  --steps 300 \
  --seed 7 \
  --heritage-limit 24
```

Generation 1 contains no inherited knowledge and therefore acts as an internal parity check against the naive control. Later generations may diverge only through the bounded priors they received.

## Research questions

The new longitudinal experiment lets us ask questions that a single run cannot answer:

- Does collective knowledge transfer accelerate useful recognition?
- Does an old belief become harmful when the synthetic world changes?
- Which patterns survive because the next generation independently confirms them?
- How much inherited knowledge is too much?
- Does heritage improve detection while worsening calibration or false positives?
- Is forgetting stale knowledge as important as inheriting useful knowledge?

## Research integrity

- Heritage is derived from **live current-generation collective evidence**, not evaluator truth.
- Inherited priors do not create reporters or source reputation.
- Prior certainty is capped so live evidence can contradict it.
- An inherited-only pattern cannot be re-exported without fresh support.
- Every inherited generation is compared with a naive control on the same seed.
- No executable behavior evolves between generations.

## Roadmap

- **v0.1–0.8:** organism → ambiguity → species resilience → reasoning → metacognition → changing worlds → experimental curiosity → research memory.
- **v0.9–0.13:** reproducible studies → dashboard studies → interpretation → study lineage → research campaigns.
- **v0.14 — longitudinal species:** **current** — bounded abstract heritage and paired generational controls.
- **v0.15 — longitudinal dashboard:** launch and visualize generational experiments in the browser.
- **v0.16 — heritage stress tests:** world shifts, stale heritage and controlled forgetting between generations.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
