---
name: performance-investigation
description: Measure, profile, and causally attribute computational cost, latency, throughput, memory pressure, scaling behavior, and observability overhead across Symbiont runtime domains under controlled and reproducible conditions.
---

# Symbiont Performance Investigation Skill

## Purpose

Systematically measure, profile and causally attribute computational performance across the Symbiont ecosystem.

The objective is to determine:

- where computational cost originates;
- whether runtime performance has materially changed;
- how cost scales with organism development and system size;
- whether infrastructure or observability affects the organism's execution;
- whether an optimization improves performance without changing scientifically relevant behavior.

Performance investigation is an empirical discipline.

Do not optimize because code looks expensive.

Measure first.

Attribute second.

Intervene third.

Re-measure afterwards.

The objective is not maximum speed at any cost.

The objective is **efficient execution while preserving organism behavior, scientific validity, architectural boundaries and runtime contracts**.

---

# Operating Contract

When this skill is active, the agent MUST:

1. **Define the performance question and metric before profiling.**

   Examples include:

   - tick latency;
   - ticks per second;
   - p95 or p99 tick latency;
   - memory residency;
   - allocation rate;
   - checkpoint serialization latency;
   - IPC overhead;
   - observability tax;
   - scaling with concept count;
   - scaling with history length;
   - rendering or transport backpressure.

2. **Establish a controlled baseline before intervention.**

   Record enough execution and environment information for the comparison to be reproducible or meaningfully interpretable.

3. **Distinguish runtime domains when attributing cost.**

   Investigate separately where relevant:

   - organism computation;
   - embodiment;
   - body / physics;
   - world;
   - laboratory orchestration;
   - persistence;
   - telemetry;
   - transport;
   - observatory rendering;
   - operating-system or runtime overhead.

4. **Attribute the hotspot to the narrowest defensible causal source before modifying code.**

   The source may be:

   - a function;
   - call path;
   - algorithm;
   - data structure;
   - allocation pattern;
   - synchronization point;
   - I/O boundary;
   - process interaction;
   - scheduler effect;
   - emergent subsystem interaction.

   Do not require a single source line when the evidence supports a broader causal mechanism.

5. **Account for profiler and instrumentation overhead.**

   Profiling itself may perturb:

   - latency;
   - scheduling;
   - allocation;
   - thread behavior;
   - cache behavior;
   - I/O;
   - synchronization.

6. **Use repeated measurements when noise can materially affect the conclusion.**

7. **Re-measure after intervention under equivalent conditions.**

8. **Verify the strongest behavioral equivalence required by the system contract.**

9. **Keep infrastructure and observability cost separate from intrinsic organism computation.**

10. **Report uncertainty when the measured effect cannot be distinguished reliably from measurement variability.**

The agent MUST NOT:

- optimize based solely on intuition or source inspection;
- report a single noisy execution as a confirmed regression or improvement;
- attribute laboratory, world or observability overhead to intrinsic organism cognition;
- hide infrastructure cost merely because it is not intrinsic organism cost;
- sacrifice constitutional invariants or epistemic boundaries for speed;
- reduce sensory frequency, cognitive horizons, world fidelity or organism capabilities merely to make a benchmark pass;
- require bit-identical trajectories when the relevant runtime contract does not guarantee them;
- accept weaker behavioral equivalence merely because exact comparison is inconvenient;
- compare measurements from materially different environments without declaring the limitation;
- assume that average latency alone adequately describes runtime behavior;
- treat profiler output as causal proof without further attribution.

---

# Normative Language

## MUST / MUST NOT

Mandatory performance-investigation invariant.

## SHOULD / SHOULD NOT

Default measurement or profiling practice.

Deviation requires a concrete reason.

## MAY

Optional technique or tool when appropriate.

---

# Use This Skill When

Use this skill when:

- investigating tick latency degradation;
- investigating throughput reduction;
- measuring organism hot-path cost;
- measuring observability overhead;
- profiling physics or world-step cost;
- investigating memory growth or leaks;
- investigating allocation or garbage-collection pressure;
- measuring checkpoint save or restore overhead;
- investigating serialization cost;
- investigating IPC or multiprocessing overhead;
- evaluating scaling as concepts, memories, models, relationships or histories grow;
- comparing performance before and after a refactor;
- establishing or updating benchmark baselines;
- investigating performance regressions in CI or development;
- determining whether instrumentation or observability affects the vital execution loop.

---

# Do Not Use This Skill When

Do not use this skill as the primary workflow for:

- investigating scientific state anomalies — use `scientific-investigation`;
- designing formal scientific experiments — use `scientific-experiment`;
- maintaining canonical scientific documentation — use `scientific-documentation`;
- routine implementation where no performance claim exists;
- arbitrary micro-optimization without an identified bottleneck;
- governance, validation selection or publishing — handled by repository governance and `agentctl`.

Performance investigation MAY discover a scientific anomaly.

Do not silently switch disciplines.

Record the finding and use the appropriate workflow.

---

# Performance Domains

Performance investigation must preserve domain attribution.

A useful current decomposition is:

```text
┌───────────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE RUNTIME DOMAINS                       │
├───────────────────────┬───────────────────────┬──────────────────────┤
│ ORGANISM              │ WORLD / EMBODIMENT    │ INFRASTRUCTURE       │
├───────────────────────┼───────────────────────┼──────────────────────┤
│ cognition             │ physics               │ persistence          │
│ prediction            │ body dynamics         │ serialization        │
│ learning              │ sensor generation     │ journal              │
│ concept lookup        │ actuator application  │ IPC                  │
│ memory access         │ collisions            │ telemetry            │
│ internal transforms   │ spatial queries       │ transport            │
│                       │ world stepping         │ observatory          │
└───────────────────────┴───────────────────────┴──────────────────────┘
```

This table is illustrative, not exhaustive.

If new runtime domains appear, measure and attribute them according to their actual ownership.

Do not force every cost into an existing category.

---

# Performance Dimensions

Do not reduce performance to one metric.

Different questions require different measurements.

## Latency

Examples:

- time per organism tick;
- world-step latency;
- checkpoint save latency;
- telemetry publication latency.

Useful statistics may include:

- median;
- p95;
- p99;
- maximum;
- jitter.

## Throughput

Examples:

- ticks per second;
- events per second;
- serialized checkpoints per unit time;
- observations processed per second.

## Memory

Examples:

- RSS;
- heap growth;
- retained allocations;
- tensor memory;
- process memory;
- peak memory.

## Allocation pressure

Examples:

- allocations per tick;
- temporary arrays;
- object churn;
- garbage-collection frequency.

## Scaling

Measure how cost changes with relevant system dimensions.

Examples:

```text
concept count
history size
model size
body complexity
sensor count
population size
runtime age
telemetry volume
```

## Infrastructure overhead

Examples:

- logging;
- journaling;
- persistence;
- IPC;
- telemetry encoding;
- transport.

## Observability overhead

Measure the cost introduced by observing and presenting execution.

This must remain separate from intrinsic organism computation.

---

# Performance Investigation Workflow

```text
                 DEFINE QUESTION
                       │
                       ▼
             DEFINE METRIC & BUDGET
                       │
                       ▼
           ESTABLISH CONTROLLED BASELINE
                       │
                       ▼
              CHARACTERIZE VARIANCE
                       │
                       ▼
                 PROFILE RUNTIME
                       │
                       ▼
              ISOLATE PERFORMANCE DOMAIN
                       │
                       ▼
               CAUSAL ATTRIBUTION
                       │
              ┌────────┴─────────┐
              │                  │
              ▼                  ▼
       IMPLEMENT CHANGE      REPORT FINDING
              │
              ▼
          RE-MEASURE
              │
              ▼
      BEHAVIORAL EQUIVALENCE
              │
              ▼
          DETERMINATION
```

---

# Phase 1: Define the Performance Question

Begin with a specific question.

Poor:

> Symbiont is slow.

Better:

> Tick throughput decreased after revision X.

Better still:

> Median organism tick latency increased from the established baseline after revision X under the same body, seed and cognitive state.

Determine:

- metric;
- measured boundary;
- expected comparison;
- relevant workload;
- relevant runtime phase;
- acceptable budget if one exists.

Do not begin profiling without knowing what performance property is being investigated.

---

# Phase 2: Establish Controlled Baseline

A baseline must describe both the workload and the measurement environment.

Record where relevant:

## Code

- revision;
- branch;
- dirty-tree state;
- Python/runtime version;
- relevant dependency versions.

## Workload

- organism state;
- checkpoint;
- genome;
- body;
- world;
- seed;
- horizon;
- cognition enabled/disabled;
- training enabled/disabled;
- telemetry configuration;
- observer configuration.

## Host

Record materially relevant conditions such as:

- CPU;
- memory;
- operating system;
- power mode;
- process/thread configuration;
- major concurrent workloads.

Perfect host quiescence is desirable but not always possible.

If the environment cannot be isolated:

- record the limitation;
- increase repetitions where useful;
- interpret small differences cautiously.

Do not falsely claim controlled conditions.

---

# Warmup and Stabilization

Do not prescribe a universal fixed warmup duration.

Warmup requirements depend on the workload and runtime.

Possible warmup effects include:

- module initialization;
- tensor allocation;
- memory pools;
- filesystem caches;
- Python specialization;
- process startup;
- body settling;
- cognitive model initialization;
- lazy loading.

Use a warmup period sufficient for the measured metric to stabilize where practical.

Record the warmup policy.

If cold-start performance is itself the metric, do not warm it away.

Distinguish:

```text
cold-start performance
```

from:

```text
steady-state performance
```

---

# Phase 3: Characterize Measurement Variance

Before claiming a small regression or improvement, determine normal measurement variation.

Where practical:

1. run the baseline multiple times;
2. record the distribution;
3. identify outliers;
4. determine whether variability is host-induced or workload-induced;
5. use robust statistics appropriate to the metric.

Do not assume performance measurements are deterministic merely because the organism state is deterministic.

Useful summary statistics may include:

- median;
- interquartile range;
- standard deviation;
- coefficient of variation;
- p95;
- p99.

The exact statistical treatment should match the question.

Do not add statistical machinery that does not improve interpretation.

---

# Phase 4: Profile Without Losing the Phenomenon

Use the least intrusive tool capable of answering the question.

Possible tools include:

- benchmark scripts;
- wall-clock instrumentation;
- sampling profilers;
- deterministic profilers;
- allocation profilers;
- memory tracers;
- operating-system metrics;
- process metrics.

Examples may include:

```text
py-spy
cProfile
yappi
tracemalloc
time.perf_counter
```

Tool availability does not make a tool appropriate.

---

# Profiler Observer Effect

Profilers alter execution.

The amount varies substantially.

Sampling profilers typically perturb execution differently from deterministic call tracing.

Memory profilers may dramatically alter allocation patterns.

Instrumentation inside a hot path may itself become the hotspot.

Therefore:

1. establish unprofiled benchmark measurements first;
2. use profiling primarily for attribution;
3. compare profiler-on versus profiler-off when profiler overhead may affect conclusions;
4. do not use profiler timing as the canonical performance baseline unless justified.

The profiler is an instrument.

It is not invisible.

---

# Phase 5: Isolate Runtime Cost

Break the measured path into meaningful domains.

A tick might conceptually include:

```text
observation
→ organism processing
→ action production
→ embodiment/body processing
→ world evolution
→ laboratory orchestration
→ persistence / telemetry
```

Do not assume these phases are always sequential or mutually exclusive.

Work may be:

- asynchronous;
- amortized;
- buffered;
- overlapped;
- deferred to another process;
- performed less frequently than every tick.

Therefore a formula such as:

```text
T_total =
    T_sensory
  + T_cognition
  + T_actuation
  + T_world
  + T_infrastructure
```

is an analytical model, not a universal architectural identity.

Verify the actual runtime structure.

---

# Phase 6: Causal Attribution

Profiling identifies correlation between execution regions and cost.

Performance investigation must go further and establish the strongest defensible causal attribution.

Possible causes include:

## Algorithmic complexity

Examples:

- quadratic comparisons;
- repeated scans;
- unbounded history traversal;
- unnecessary recomputation.

## Allocation and garbage collection

Examples:

- temporary arrays;
- repeated object creation;
- tensor copies;
- dictionary churn;
- serialization buffers.

## Data movement

Examples:

- copying;
- marshaling;
- tensor conversion;
- process-boundary transfer.

## I/O

Examples:

- synchronous disk writes;
- log flushing;
- filesystem metadata;
- socket writes.

## Serialization

Examples:

- JSON encoding;
- checkpoint encoding;
- compression;
- schema conversion.

## Synchronization

Examples:

- locks;
- queues;
- barriers;
- process joins;
- contention.

## Scheduling

Examples:

- thread oversubscription;
- process contention;
- scheduler latency;
- CPU affinity interactions.

## Numerical kernels

Examples:

- tensor operations;
- matrix operations;
- model inference;
- training.

## Cache and locality

Examples:

- poor data locality;
- oversized working sets;
- repeated cache misses.

## Transport and backpressure

Examples:

- telemetry consumers;
- socket buffers;
- SSE/WebSocket transport;
- event queues.

## Frequency mismatch

Examples:

- UI consuming faster than data production;
- telemetry production faster than transport;
- physics stepping at a different rate from organism execution.

Do not conclude that the largest profiler entry is necessarily the root cause.

Ask why that cost exists.

---

# Narrowest Defensible Attribution

Performance attribution should reach the narrowest level supported by evidence.

Possible outcomes include:

```text
specific line
specific function
specific call path
specific data structure
algorithmic pattern
allocation behavior
subsystem interaction
runtime scheduling behavior
```

Do not invent artificial precision.

For example:

> `foo.py:124` is slow.

may be weaker than:

> repeated construction of the full concept-distance matrix creates quadratic work as the concept set grows.

Prefer causal explanations over location labels.

---

# Observability Invariant

Observation must not control the organism's vital execution merely because an observer is slow.

Where architecture requires passive observation:

- rendering MAY drop frames;
- telemetry MAY be sampled;
- consumers MAY lag;
- UI MAY refresh at a lower frequency;

but observer backpressure MUST NOT silently become a dependency of organism progress.

Measure this explicitly.

---

# Observability Tax

Observability tax is the incremental system cost introduced by observation.

A simple comparison may be:

```text
Observability Tax =
    (Observer ON - Observer OFF)
    / Observer OFF
```

This ratio MAY be useful.

Do not rely exclusively on a mean ratio.

Where relevant compare:

- median latency;
- p95;
- p99;
- throughput;
- jitter;
- memory;
- queue growth;
- dropped telemetry;
- backpressure.

Always specify the measured boundary.

For example:

```text
organism-only cost
system tick cost
wall-clock simulation cost
telemetry process cost
UI render cost
```

Do not call all of these “observability tax” without distinguishing them.

---

# Intrinsic Cost vs. Infrastructure Cost

Do not attribute infrastructure overhead to intrinsic organism computation.

For example:

```text
telemetry encoding
logging
checkpoint writes
SSE transport
dashboard rendering
```

may affect total runtime performance while remaining external to organism cognition.

Report both where relevant:

```text
intrinsic organism cost
```

and:

```text
system / apparatus / observability overhead
```

External cost is still real cost.

Classification must not hide it.

---

# Phase 7: Intervention

Do not optimize until the hotspot is sufficiently attributed.

Prefer changes that reduce the identified cause rather than obscure the metric.

Examples may include:

- better algorithmic structure;
- avoiding repeated work;
- bounded caching;
- reducing allocations;
- eliminating unnecessary copies;
- batching I/O;
- decoupling observers;
- improving queue handling;
- changing data layout;
- reducing synchronization.

Do not:

- remove scientifically required work;
- alter organism semantics;
- weaken evidence collection without explicit justification;
- bypass architectural boundaries;
- change lifecycle behavior merely to improve benchmark numbers.

---

# Phase 8: Re-measure

After intervention:

1. run the same workload;
2. use equivalent measurement conditions;
3. repeat sufficiently to characterize variation;
4. compare the same metrics;
5. report absolute and relative change.

Examples:

```text
median latency
before: 6.8 ms
after: 5.4 ms

delta: -1.4 ms
relative: -20.6%
```

Where tail latency matters, also report it.

Example:

```text
p95
before: ...
after: ...
```

Do not report percentage improvement without the underlying measurements.

---

# Behavioral Equivalence

A performance change is valid only if required behavior remains equivalent.

Use the strongest applicable equivalence level.

## Level 1 — Exact state identity

Use when the relevant runtime contract is deterministic.

Possible checks include:

- identical state hashes;
- identical checkpoint state;
- identical outputs;
- identical deterministic trajectories.

## Level 2 — Contract-level equivalence

Use when exact state identity is not required but externally or scientifically relevant behavior must remain unchanged.

Verify the relevant invariants.

## Level 3 — Statistical equivalence

Use when behavior is intentionally stochastic.

Compare the behavior at the level defined by the scientific or runtime contract.

Never require stronger equivalence than the system actually guarantees.

Never accept weaker equivalence merely because stronger checking is inconvenient.

---

# Performance Comparison Across Machines

Absolute performance is hardware-dependent.

Do not compare raw latency numbers across materially different machines as if they represented a controlled regression.

When hardware differs, possible valid approaches include:

- same-host before/after comparison;
- normalized ratios;
- controlled reference workloads;
- machine-specific baselines.

Always state when absolute measurements are not directly comparable.

---

# Regression Thresholds

A threshold must have a documented basis.

Possible sources include:

- established historical baseline;
- explicit runtime budget;
- CI budget;
- scaling requirement;
- user-facing latency requirement;
- scientific apparatus constraint.

Do not invent a threshold merely because a benchmark needs one.

Distinguish:

```text
target
warning threshold
regression threshold
hard limit
```

If no formal budget exists, report the measured baseline and observed change rather than pretending one does.

---

# Performance Determinations

Use one or more of the following outcomes.

## REGRESSION CONFIRMED

Use when performance degradation exceeds expected measurement variation and the comparison is valid.

## IMPROVEMENT CONFIRMED

Use when performance improvement exceeds expected measurement variation and required behavioral equivalence is preserved.

## NO MATERIAL CHANGE

Use when the observed difference is within normal measurement variation or below the relevant significance/budget threshold.

## ATTRIBUTED

Use when the dominant performance cause has been identified to the required causal level.

This may coexist with a regression or improvement determination.

## INCONCLUSIVE

Use when:

- measurement noise is too high;
- environments are not comparable;
- profiling perturbation is too large;
- workload identity is uncertain;
- evidence cannot distinguish competing performance causes.

Do not force a regression or improvement conclusion when the evidence does not support it.

---

# Memory Investigation

Memory performance requires separate treatment from latency.

Investigate where relevant:

- RSS;
- heap growth;
- peak memory;
- retained objects;
- tensor memory;
- allocation rate;
- GC frequency;
- per-tick growth;
- lifecycle-bound memory release.

Distinguish:

```text
temporary allocation pressure
```

from:

```text
retained growth
```

from:

```text
intentional state accumulation
```

Growth is not automatically a leak.

A leak requires evidence that memory remains retained beyond its intended lifecycle.

---

# Scaling Investigation

Do not assume a hotspot remains constant as the organism develops.

Measure cost against relevant dimensions.

Examples:

```text
ticks
concept count
memory entries
model count
history length
body complexity
sensor count
population count
```

Look for:

- linear growth;
- superlinear growth;
- discontinuities;
- thresholds;
- periodic spikes;
- lifecycle-correlated growth.

When claiming complexity behavior such as `O(N²)`, distinguish:

```text
complexity demonstrated by code structure
```

from:

```text
complexity empirically observed over measured N
```

They are related but not identical claims.

---

# Stop Rule

Stop the investigation when one of the following is true:

1. the performance question has been answered at the requested level;
2. the dominant hotspot has been causally attributed sufficiently for action;
3. the regression or improvement has been reliably determined;
4. available measurements are exhausted and the result is inconclusive;
5. further progress requires unavailable hardware, instrumentation or workloads;
6. further investigation would only add measurement volume without changing the conclusion.

Do not profile indefinitely.

Performance investigation exists to resolve a concrete performance question.

---

# Performance Investigation Report

For substantial investigations, report:

```markdown
# Performance Investigation: [Title]

## 1. Question

What performance property is being investigated?

## 2. Metric and Scope

Measured metric:
- latency / throughput / memory / allocation / scaling / observability

Measured boundary:
- organism;
- world;
- lab;
- persistence;
- observatory;
- full runtime.

## 3. Environment

- revision;
- runtime version;
- hardware;
- workload;
- seed;
- checkpoint;
- body/world configuration;
- warmup policy.

## 4. Baseline

Report:
- repeated measurements;
- central tendency;
- variability;
- tail metrics where relevant.

## 5. Profiling Evidence

Identify:
- dominant paths;
- allocation sources;
- I/O;
- synchronization;
- process interactions;
- profiler limitations.

## 6. Causal Attribution

Describe the narrowest defensible cause.

Separate:
- intrinsic organism cost;
- world/body cost;
- apparatus cost;
- observability cost.

## 7. Intervention

If code changed:
- what changed;
- why it targets the attributed cause.

## 8. Re-measurement

Provide:
- before;
- after;
- absolute delta;
- relative delta;
- variability.

## 9. Behavioral Equivalence

State the applied equivalence level:

- exact;
- contract;
- statistical.

Report validation.

## 10. Determination

One or more:

- REGRESSION CONFIRMED;
- IMPROVEMENT CONFIRMED;
- NO MATERIAL CHANGE;
- ATTRIBUTED;
- INCONCLUSIVE.

## 11. Limitations

Record:
- host variability;
- profiler effects;
- missing workloads;
- unmeasured scaling dimensions;
- other relevant uncertainty.
```

Small investigations MAY use a shorter report but MUST preserve the same essential evidence.

---

# Quality Gate

Before closing a performance investigation, verify:

- Was the performance question defined before profiling?
- Is the metric appropriate to the question?
- Is the measured boundary explicit?
- Is the workload reproducible or sufficiently described?
- Is the hardware/environment recorded where relevant?
- Was baseline variability characterized?
- Was profiler overhead considered?
- Was cost attributed to the correct runtime domain?
- Was the hotspot causally investigated rather than merely ranked by profiler time?
- Were tail latency and jitter considered when relevant?
- Was infrastructure overhead kept separate from intrinsic organism cost?
- Was the same workload re-measured after intervention?
- Was the appropriate behavioral-equivalence level checked?
- Are before/after measurements directly comparable?
- Is any threshold actually documented rather than invented?
- Does the determination match the strength of the evidence?
- If inconclusive, is the reason explicit?

If important answers are missing, the performance claim is not sufficiently established.

---

# Final Principle

Performance numbers without context are not scientific evidence.

A profiler ranking without causal attribution is not a root cause.

A faster execution that changes organism behavior is not an optimization.

A slower execution is not necessarily a regression if the workload changed.

Observability overhead is not intrinsic organism computation, but it remains real system cost.

Measure the correct boundary.

Control what can be controlled.

Declare what cannot.

Attribute before optimizing.

Re-measure after intervention.

Preserve behavior.

Conclude only what the measurements support.
