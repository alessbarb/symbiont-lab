# P8 — Full Performance Reprofile

Status: implementation candidate  
Base: P7 browser rendering optimization on `main`

## Purpose

P8 resets the performance baseline after P0-P7.

The percentages measured before the optimization program are historical evidence,
not the current cost distribution. P8 therefore does not carry them forward or
sum estimated savings.

The canonical measurement is local:

```bash
python scripts/reprofile_performance.py
```

A shorter smoke-sized run is available with:

```bash
python scripts/reprofile_performance.py --quick
```

Reports are written to:

```text
.artifacts/p8/report.json
.artifacts/p8/report.md
.artifacts/p8/observer_off.prof
.artifacts/p8/observer_on.prof
```

Use a custom location with `--output-dir`.

## What the runner measures

### 1. Organism throughput

Matched Observer OFF and Observer ON subjects are timed independently across
multiple fresh runs. The report uses median ms/tick and ticks/s.

The difference is reported as the current observability tax.

No timing number is treated as a deterministic assertion.

### 2. Current cProfile distribution

Headless and observed organisms are profiled separately.

P8 groups **self time** (`tottime`) into coarse runtime categories so the
distribution can be compared without double-counting nested calls.

The report also records the top functions by cumulative time, but cumulative
percentages must never be added together.

Current categories include:

- sensorimotor/action;
- cognition;
- perception;
- physiology;
- observability;
- serialization;
- genetics;
- Python standard library;
- other runtime.

The raw `.prof` files remain available for deeper inspection.

### 3. Causal equivalence

The local runner executes the P0 performance-equivalence test before reporting
focused subsystem results.

Performance evidence is invalid if the causal gate fails.

### 4. Focused subsystem benchmarks

P8 invokes the post-P0 benchmark set from the same report:

- canonical organism scaling;
- deterministic sensorimotor matching;
- World journal age scaling;
- SSE transport;
- browser cognition layout when Node.js is installed.

The existing focused scripts remain useful individually; P8 simply gives them a
single orchestration and output location.

## Local execution is canonical

GitHub-hosted runners are not considered authoritative performance hosts.

CPU model, virtualization, shared tenancy, frequency scaling and concurrent load
can alter wall-clock numbers substantially.

The CI job therefore runs only:

```bash
python scripts/reprofile_performance.py --quick
```

and is explicitly:

```yaml
continue-on-error: true
```

It uploads the report when GitHub Actions is available, but it cannot block a
merge and is not the baseline used to choose the next optimization target.

## Interpretation rule

Choose the next performance target from the new P8 evidence, primarily:

1. headless self-time distribution;
2. top current cumulative call paths;
3. focused benchmark scaling;
4. observed-minus-headless tax.

Do not choose the next target merely because it was expensive in the
pre-optimization baseline.

Do not optimize by reducing learning frequency, evidence acquisition,
plasticity, cognition, physics fidelity or any other genuine organism
mechanism.

## Closing P8

P8 is structurally complete when the runner and report contract are merged.

The empirical audit is complete only after a full local run is executed on a
documented host and its `report.json` / `report.md` are reviewed. The report
itself is generated evidence and should not be committed as a universal
baseline unless the host/environment is explicitly recorded.
