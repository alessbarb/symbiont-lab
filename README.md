# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.8 — research memory

Symbiont Lab now treats each run as an experiment rather than a disposable simulation. Completed experiments can be recorded with:

- title, hypothesis, success criteria and notes;
- full synthetic-world configuration;
- detection, precision and false-positive metrics;
- calibration, blind spots and metacognitive state;
- concept-drift adaptation metrics;
- unresolved-question and curiosity metrics.

By default records are appended locally to:

```text
.symbiont/experiments.jsonl
```

`.symbiont/` is ignored by Git. The archive belongs to the **external researcher**, not to the simulated species. Agents, collective trust, reasoning, curiosity and metacognition cannot read it.

## Dashboard workflow

```bash
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --hosts 100 --steps 300 --seed 7 --poison-fraction 0.08
```

Open `http://127.0.0.1:8765`.

The dashboard can now:

1. define title, hypothesis, success criteria and notes;
2. configure all synthetic experiment parameters;
3. launch and observe the experiment live;
4. record the final result;
5. compare recent runs in the **Research memory** table;
6. load any prior configuration back into the launcher for a controlled follow-up.

Use `--no-autorun` to open the dashboard idle. Use `--no-record` for an ephemeral session, or `--archive path/to/file.jsonl` to choose another archive.

## CLI workflow

```bash
symbiont-sim \
  --title "Curiosity under benign drift" \
  --hypothesis "Epistemic pressure rises after drift, then settles" \
  --success-criteria "Recent drift false positives decline after adaptation" \
  --hosts 100 --steps 300 --seed 7 \
  --poison-fraction 0.08 --drift-fraction 0.35
```

CLI runs are recorded in the same archive by default and print their record ID. Use `--no-record` to disable that behavior or `--archive` to point at a different JSONL file.

## Experimental curiosity

For unresolved collective hypotheses, `CuriosityPlanner` ranks **shadow-only counterfactual probes** by expected information gain and synthetic cost. These probes are research questions over coarse simulated fingerprints. They never run commands, inspect hosts or alter the world.

## Experimental integrity

- Ground truth remains evaluator-only.
- Agents never receive benign/pathogen labels or drift membership.
- Dashboard, CLI and research archive are observer-side facilities.
- Research history never feeds back into an agent or collective belief.
- Curiosity plans only descriptive counterfactuals over aggregate synthetic state.
- Reasoning and curiosity cannot execute tools or alter hosts.

## Roadmap

- **v0.1 — organism:** baseline, novelty, curiosity, collective memory.
- **v0.2 — memory and ambiguity:** label separation, overlap, forgetting, consolidation, live experiments.
- **v0.3 — species resilience:** heterogeneity, reputation and synthetic poisoned reports.
- **v0.4 — bounded reasoning:** hypotheses, uncertainty and information-seeking questions.
- **v0.5 — metacognition:** self-confidence, calibration, overconfidence and blind spots.
- **v0.6 — changing worlds:** benign regime drift and cautious adaptation.
- **v0.7 — experimental curiosity:** ranked shadow counterfactuals plus dashboard/CLI launcher.
- **v0.8 — research memory:** **current** — persistent experiment records and comparison.
- **v0.9 — reproducible studies:** experiment batches, parameter sweeps and explicit baselines.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
