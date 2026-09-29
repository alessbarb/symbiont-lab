# Simulation Throughput v1

Status: **proposed** (2026-09-29). Owner question: can Symbiont run hundreds
of ticks per second with the same impact on the organism? Baseline:
`main @ d3dac186`, Physics3D, `anthropomorphic-v6-vision` body.

## 1. Measurements

Snapshot of `org-2df92a9d8fda` (tick 768), headless, training off, one
laptop shared with a running study (so absolute numbers are pessimistic).

| Component (per tick) | Cost | Causal for the organism |
|---|---:|---|
| Rich telemetry every 2 ticks (`deepcopy`, structural diff, binary encoding, episodic snapshots) | ≈ 4.5 s amortised, ≈ 90 % of wall time | no (apparatus) |
| Episodic memory: `record_experience → reinterpret → projection/_prototype` (≈ 7 500 projections per tick) | ≈ 200 ms | yes |
| `deepcopy` inside the step, adaptive-sense eviction, hypotheses, signal claims, sensorimotor distances | ≈ 150 ms | yes |
| PyBullet (10 substeps at 240 Hz) | ≈ 36 ms | yes |

End to end: **0.19 ticks/s** with default observation; **2.0 ticks/s** with
`observation_hz=1`; organism step ≈ 440 ms.

**Ceiling.** Physics alone bounds one organism at ≈ 28 ticks/s on this
machine. "Hundreds of ticks per second with the same impact" is not
reachable for a single run without changing what the organism experiences;
it is reachable only in aggregate, with parallel runs on more cores.

## 2. Principle: same impact means identical causal history

An optimisation is admissible only if the organism's causal state is
identical: final `runtime.json` of the checkpoint, provenance journal and
body state byte-equal against the unoptimised code from the same snapshot
and seeds. This **equivalence harness** gates every level below; nothing
is merged on a speed number alone.

## 3. Levels

0. **Study mode — sparse or no rich telemetry (≈ ×10, no organism code).**
   *Verified 2026-09-29:* 30 ticks from the same snapshot with default
   observation and with `observation_hz=1` give byte-identical organism
   `runtime.json`, provenance journal and body. Studies whose gates do not
   read telemetry (P5, P5.1, P6) can use it.
1. **Algorithmic fixes in the organism, identical trajectories
   (estimated ×5-8 on cognition).** Incremental episodic reinterpretation
   instead of re-projecting every episode per record; removing the
   `deepcopy` inside the step; indexed structures for evictions (adaptive
   senses, signal claims). Target ≈ 50-60 ms per tick, 15-20 ticks/s.
   Each change ships with the equivalence harness over a long window.
2. **Throughput by parallelism.** Arms, seeds and organisms as separate
   processes (≈ ×3-4 aggregate on this machine; scales with cores).
3. **Different regime — not the same impact (owner decision).** Fewer
   physics substeps, cheaper vision, simplified world. Changes experience;
   would need its own study showing which effects are preserved.

## 4. Owner decisions (2026-09-29)

- **Level 0 approved:** sparse telemetry in studies, provided it is purely
  observational and changes no decision, causal order, RNG consumption or
  organism hash.
- **Level 1 approved under strict equivalence:** every organism
  optimisation must pass the equivalence harness (same behaviour and same
  observable causal history). A change that alters trajectory, RNG
  consumption, event order or provenance is not Level 1 and needs its own
  study.
- Level 3 remains out of scope.

## 5. Originally open for the owner

- Approve Level 0 as the default for studies that do not read telemetry.
- Approve Level 1 work (organism code, behaviour-identical by harness).
- Level 3 is out of scope unless explicitly requested.

Running P5.1 keeps its apparatus unchanged (full telemetry) so that arms A
and B are measured identically.
