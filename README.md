# Symbiont Lab

A **safe, simulation-only** research prototype for distributed defensive intelligence. Every host, pathogen, reporter and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## v0.12 — persistent study memory and lineage

Symbiont Lab now preserves comparative studies as observer-side research records instead of treating each study as disposable output.

Two append-only local archives are kept outside the simulated species:

```text
.symbiont/experiments.jsonl   # individual runs
.symbiont/studies.jsonl       # paired comparative studies
```

A study record contains:

- the base synthetic-world configuration;
- baseline/variant parameter values and paired seeds;
- aggregate metrics and paired deltas;
- observer interpretation;
- an optional `parent_record_id` linking it to the study it follows.

This creates an explicit research lineage such as:

```text
initial poisoning study
        ↓
midpoint follow-up
        ↓
threshold refinement
```

The lineage is **research metadata**, never species memory.

### Dashboard

```bash
source .venv/bin/activate
pip install -e '.[dev]'
symbiont-dashboard --no-autorun
```

Open `http://127.0.0.1:8765`.

The dashboard now shows a **Study memory** table. A previous study can be loaded as-is, or selected as the parent of a follow-up. The observer-generated follow-up button also carries the completed study ID forward automatically. Nothing launches until the researcher explicitly presses **Launch comparative study**.

Use **Start new lineage** to clear the parent and begin an independent research thread.

### CLI

`study` runs are recorded by default:

```bash
symbiont-study \
  --parameter poison_fraction \
  --baseline 0 \
  --variant 0.12 \
  --seeds 3,7,11,17,23
```

The output prints the generated study ID. A later study can explicitly continue that line:

```bash
symbiont-study \
  --parameter poison_fraction \
  --baseline 0 \
  --variant 0.06 \
  --parent-study-id <study-id> \
  --seeds 3,7,11,17,23,27,31
```

Use `--no-record` when a study should remain ephemeral, or `--archive` to choose another observer-side study archive.

## Research integrity

- All hosts, threats, drift and counterfactuals are synthetic.
- Ground truth remains evaluator-only.
- Experiment and study archives are external observer facilities.
- Agents, collective trust, bounded reasoning, curiosity and metacognition cannot read research archives.
- Parent/child relationships do not alter simulation behavior.
- Loading a study or proposed follow-up never starts an experiment automatically.

## Roadmap

- **v0.1–0.8:** organism → ambiguity → species resilience → reasoning → metacognition → changing worlds → experimental curiosity → research memory.
- **v0.9:** reproducible paired studies from CLI.
- **v0.10:** unified browser launcher for single experiments and comparative studies.
- **v0.11:** paired consistency, observer interpretation and bounded follow-up proposals.
- **v0.12 — study memory:** **current** — persistent study records and explicit parent/child research lineage.
- **v0.13 — research campaigns:** group related lineages, detect convergence/repetition and recommend the next bounded comparison for researcher approval.
- **v0.14 — longitudinal species:** simulated generations and inheritance of bounded abstract knowledge.

## Safety boundary

Symbiont Lab remains a laboratory ecology. Do not add real endpoint monitoring, propagation, persistence, scanning, stealth/evasion, OS modification, exploitation, credential access, autonomous remediation or real user data.
