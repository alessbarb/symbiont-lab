# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.7 — experimental curiosity + experiment launcher

The laboratory can now be operated from **either CLI or the local dashboard**. Both surfaces describe an experiment with the same research metadata:

- title;
- hypothesis;
- success criteria;
- notes;
- synthetic world parameters.

### Dashboard

```bash
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --hosts 100 --steps 300 --seed 7 --poison-fraction 0.08
```

Open `http://127.0.0.1:8765`. The initial experiment starts automatically for backwards compatibility. After it finishes, edit the form and launch another experiment. Use `--no-autorun` if you want the dashboard to open idle and define the first experiment entirely in the browser.

The browser form includes hypothesis, success criteria and notes alongside hosts, steps, seed, threat rate, poisoning, heterogeneity and concept-drift settings. A second experiment cannot start while one is running.

### CLI

```bash
symbiont-sim \
  --title "Curiosity under benign drift" \
  --hypothesis "Epistemic pressure rises after drift, then settles" \
  --success-criteria "Recent drift false positives decline after adaptation" \
  --hosts 100 --steps 300 --seed 7 \
  --poison-fraction 0.08 --drift-fraction 0.35
```

The CLI prints the experiment annotation before its metrics, so a copied run remains interpretable.

## Experimental curiosity

For unresolved collective hypotheses, `CuriosityPlanner` ranks **shadow-only counterfactual probes** by expected information gain and synthetic cost. These probes are research questions over coarse simulated fingerprints. They never run commands, inspect hosts or alter the world.

## Experimental integrity

- Ground truth remains evaluator-only.
- Agents never receive benign/pathogen labels or drift membership.
- Dashboard and CLI are observer/launcher surfaces, not members of the simulated species.
- Curiosity plans only descriptive counterfactuals over aggregate synthetic state.
- Reasoning and curiosity cannot execute tools or alter hosts.

## Roadmap

- **v0.1 — organism:** baseline, novelty, curiosity, collective memory.
- **v0.2 — memory and ambiguity:** label separation, overlap, forgetting, consolidation, live experiments.
- **v0.3 — species resilience:** heterogeneity, reputation and synthetic poisoned reports.
- **v0.4 — bounded reasoning:** hypotheses, uncertainty and information-seeking questions.
- **v0.5 — metacognition:** self-confidence, calibration, overconfidence and blind spots.
- **v0.6 — changing worlds:** benign regime drift and cautious adaptation.
- **v0.7 — experimental curiosity:** **current** — ranked shadow counterfactuals plus dashboard/CLI experiment launcher.
- **v0.8 — research memory:** persist experiment specifications and compare recurring questions across runs.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
