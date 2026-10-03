# P4 — Decoupled Physics, Cognition, Observation and Render Rates

Status: implementation candidate  
Base: P3 age-independent World journal on `main`

## Principle

A causal organism tick, a scientific observation sample and a presentation
frame are different operations and must not be aliases for one another.

P4 formalizes four clocks:

```text
physics_hz       physical integration
cognition_hz     organism perception / decision / learning
observation_hz   rich passive scientific projection / telemetry
render_hz        lightweight physical pose presentation
```

The observer and renderer never feed information back into the organism.

## Deterministic cadence

Physics remains an integer multiple of cognition because one organism motor
command is deliberately held for a fixed number of physics substeps.

Observation and render rates do not need to divide their source clocks.
Deterministic integer phase accumulation schedules them at the requested
long-run rate without wall-clock jitter or floating-point timers.

Default Physics3D rates are:

```text
physics       240 Hz
cognition      24 Hz
observation    12 Hz
render         60 Hz
```

An explicit configuration such as 24 Hz cognition / 10 Hz observation or
240 Hz physics / 50 Hz render is valid.

## Observer boundary

On cognition ticks where no observation sample is due:

- `OrganismRuntime.tick(include_observability=False)` is used;
- full human narrative / sensory phenotype / maturity projection remain absent;
- Physics3D does not materialize the rich observer state;
- telemetry does not append a sample;
- the rich monitor snapshot is not published.

Causal organism and physical state continue to advance normally.

Experience records are not discarded between samples. The observer cursor is
advanced only on observation ticks, so the next sample contains all newly
created observer-facing experience records since the prior sample.

## Presentation

Physical pose frames are captured inside the physics loop using a passive
rational phase accumulator. They are lightweight and independent of cognition
and rich telemetry.

The pose event reports its actual `sampling_hz`; the old hard-coded 60 Hz
metadata has been removed.

## Resident / Observatory

`ResidentConfig.observation_every_ticks` allows a resident organism to live at
its normal tick cadence while publishing Observatory snapshots less frequently.
The default remains one observation per tick for compatibility.

## Telemetry v4.1

Telemetry manifests now record `observation_hz` and `render_hz`.

Recorded cognition ticks may be sparse but remain strictly increasing. The
first submitted observation, rather than necessarily `start_tick + 1`, owns
the initial full checkpoint. Existing reconstruction therefore remains exact
for sampled ticks.

## Acceptance contract

P4 must preserve:

1. organism causal state and decisions irrespective of observation cadence;
2. physical integration count and motor hold duration;
3. no observer-to-organism feedback;
4. exact deterministic sampling pattern for fixed rates;
5. sparse telemetry reconstruction and integrity verification;
6. manual single-step visibility without changing the underlying rate plan.

P0 remains the causal equivalence gate. P5 may now replace repeated full
observer payloads with anchors plus deltas without changing any causal clock.
