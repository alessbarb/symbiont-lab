# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.13 — observer-side research campaigns

Individual studies can now be interpreted as a **research campaign** by following their explicit parent/child lineage in `.symbiont/studies.jsonl`.

Campaign analysis remains entirely outside the simulated species. It asks a different question from the agents themselves:

> Are our experiments still learning something, or are we merely repeating the same comparison?

The observer recognizes several campaign states:

- **continue** — the line has useful evidence but still benefits from the latest bounded follow-up;
- **increase_evidence** — the same comparison was repeated with insufficient confidence, so add paired seeds instead of changing the condition;
- **stalled** — an already well-supported comparison is being repeated unnecessarily;
- **converged** — repeated refinements have narrowed the tested interval enough, with high confidence, to close the line unless a new hypothesis appears;
- **no_robust_effect** — three consecutive studies have failed to produce useful discrimination, so the observer recommends closing the line rather than escalating synthetic stress indefinitely.

### Dashboard

```bash
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --no-autorun
```

The **Study memory** table now includes the campaign status of each recorded study. Selecting a study shows the campaign assessment, interval narrowing, confidence and any proposed next comparison.

**Load campaign proposal** only fills the comparative-study form and keeps the current study as its parent. It never launches the proposal automatically.

### CLI

Inspect any recorded lineage directly:

```bash
symbiont-campaign --study-id <study-id>
```

The CLI prints the chain from the root study to the selected study, campaign state, interval evolution and the next researcher-approved comparison when one is appropriate.

Study creation remains unchanged:

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
- Study and campaign analysis are external observer facilities.
- Campaign state never changes agent behavior or collective knowledge.
- A campaign proposal can only vary bounded, whitelisted simulator parameters.
- No campaign proposal is executed automatically.
- A converged or non-discriminating line may deliberately produce **no next proposal**.

## Roadmap

- **v0.1–0.8:** organism → ambiguity → species resilience → reasoning → metacognition → changing worlds → experimental curiosity → research memory.
- **v0.9:** reproducible paired studies from CLI.
- **v0.10:** unified browser launcher for single experiments and comparative studies.
- **v0.11:** paired consistency, observer interpretation and bounded follow-up proposals.
- **v0.12:** persistent study memory and explicit research lineage.
- **v0.13 — research campaigns:** **current** — convergence, stalls, non-effects and bounded campaign proposals.
- **v0.14 — longitudinal species:** simulated generations and inheritance of bounded abstract knowledge.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
