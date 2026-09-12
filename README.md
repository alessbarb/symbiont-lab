# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.11 — observer-side study interpretation

Symbiont Lab now goes beyond aggregate baseline/variant means. Comparative studies retain the **paired delta for every metric on every shared seed**, allowing the observer to ask whether a change was merely positive on average or moved consistently across simulated worlds.

```bash
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --no-autorun
```

Open `http://127.0.0.1:8765`.

### Comparative evidence

For each metric, studies now expose:

- baseline and variant means;
- mean paired delta;
- standard deviation of paired deltas;
- the fraction of paired seeds that moved in the same direction.

The observer-side interpreter classifies effects as **strong**, **moderate** or **weak** and distinguishes beneficial, harmful and neutral cognitive-state shifts. It never feeds its conclusions back into agents, collective trust, curiosity, reasoning or metacognition.

The dashboard shows the interpretation below the study table and proposes a bounded follow-up. A button can load that proposal into the study form without launching it automatically.

Typical logic:

- a strong consistent effect → test a midpoint next to locate the onset of the effect;
- a moderate effect → repeat the same comparison with more paired seeds;
- no robust effect → increase synthetic stress modestly and increase sample size.

The CLI prints the same observer interpretation:

```bash
symbiont-study \
  --parameter poison_fraction \
  --baseline 0 \
  --variant 0.12 \
  --seeds 3,7,11,17,23
```

## Research integrity

- All hosts, threats, drift and counterfactuals are synthetic.
- Ground truth remains evaluator-only.
- Study interpretation is observer-side and never becomes species knowledge.
- Follow-up proposals only vary whitelisted simulator parameters.
- Dashboard proposals require an explicit launch; they do not start experiments autonomously.
- Curiosity remains shadow-only and cannot execute probes.

## Roadmap

- **v0.1–0.8:** organism → ambiguity → species resilience → reasoning → metacognition → changing worlds → experimental curiosity → research memory.
- **v0.9:** reproducible paired studies from CLI.
- **v0.10:** unified browser launcher for single experiments and comparative studies.
- **v0.11 — study interpretation:** **current** — paired consistency, effect interpretation and bounded follow-up proposals.
- **v0.12 — study memory:** persist aggregate studies, interpretations and follow-up lineage.
- **v0.13 — research campaigns:** connect related studies into explicit, researcher-approved experiment sequences.
- **v0.14 — longitudinal species:** simulated generations and inheritance of bounded abstract knowledge.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
