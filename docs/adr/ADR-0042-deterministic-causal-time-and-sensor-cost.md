# ADR-0042: Deterministic Causal Time and Sensor Cost (ADR-EW-006, EW-T)

## Status

Accepted by the owner on 2026-09-28. This ADR blocks EW-D.

## Context

Two paths let host speed and the OS clock write into organism state:

1. `HostSampler` measured `time.perf_counter()` around each provider call and passed the per-capability share on as `attributed_elapsed_s`. `PerceptionDomain` turned that share into `SensorState.acquisition_cost`, and `SelfModel` turned it into its sense cost estimate. Both feed sensory utility, self-model relative cost and attention.
2. `PerceptionDomain` called `current_time_bucket()`, which reads `datetime.now().hour`, to key `RhythmModel`. This contradicted ADR-0032 §3: an internal cyclic phase, *without querying OS wall-clock time*.

Consequence: two Physics3D runs that resume the same body from the same checkpoint X with the same seed diverged. In a probe on `origin/main` before this change, 83 state fields already differed after 24 ticks: dynamics-model relations, acclimation accumulators and narrative. The divergence scaled with CPU load, so a Vision-vs-no-Vision comparison would have been confounded by machine speed. State-X reproduction (Gate H) and engine-level observability independence (Gate I) could not pass.

## Decision

1. **Three kinds of time.**
   - *Causal time* belongs to the organism's life: `symbiont_tick`, physics substeps, `embodiment_tick` and derived phases. It may shape state.
   - *Host or wall time* comes from `time.time`, `monotonic`, `perf_counter` and `datetime.now`. It is external and is never an implicit causal authority.
   - *Observer performance* covers CPU milliseconds, latency and throughput. It is diagnostic only.
2. **Deterministic sensor cost.** `CapabilitySamplingOutcome` carries two separate costs:
   - `causal_acquisition_cost` is the provider's declared `sampling_cost_per_capability`, a constant of the apparatus constitution. It is charged to every attempted capability, including failed and missing ones, so the attribution topology is unchanged.
   - `observed_elapsed_s` is kept for profiling only. Nothing causal reads it, and it is never checkpointed.
   - The default is `DEFAULT_SAMPLING_COST_PER_CAPABILITY = 1e-5` cost units. It was calibrated once, on 2026-09-28, to the median wall-clock share the old code measured: 9.8e-6 s for the Physics3D body provider (n = 717) and 1.4e-5 s for the stdlib host provider (n = 48). The utility term `min(1, acquisition + transduction)` therefore keeps its regime. The value is never re-measured at run time.
   - `SelfModel` quantization keeps its 1.0 reference in cost units.
3. **Internal rhythm phase.** `RhythmModel` is keyed by `CyclePhase`: four neutral quadrants (`phase.0`–`phase.3`) of an internal macro cycle of `CYCLE_PERIOD_TICKS = 2048`. The phase is derived only from the persisted `symbiont_tick` and exposed as `TickContext.macro_phase`, so it survives restore and re-embodiment. Nothing in core reads rhythm baselines today, so the period does not alter other learning signals. The period is provisional and may later be entrained endogenously. `TimeBucket`, `time_bucket_for_hour` and `current_time_bucket` are retired.
4. **Migration.** The host checkpoint moves from schema 9 to 10. `_migrate_v9_to_v10` discards v9 rhythm projections and replay accumulators, because they were keyed by the OS clock and cannot be re-keyed without inventing an alignment. Rhythms are relearned from causal ticks.
5. **Declared exceptions.** These may read the host clock, and a lock-in test lists them. None of them can act in a Lab run that has no interoception provider, advisory or governor.
   - Reading providers under `host/providers/`: apparatus timestamps.
   - The profiling clock in `readings`, `lifecycle`, `second_look` and `EpistemicServices.sampling_clock`: it produces only `observed_elapsed_s`.
   - Safety guards: `RuntimeGovernor` rate limiting and consent, and the `Advisory` rate limit.
   - `LocalHabitat` capsule mailbox: file TTL and ids for local exchange.
   - Real-host interoception: tick latency is passed to the interoception provider only when one exists. External time, when it is perceived, enters as an explicit apparatus signal and never as an implicit clock.
   - The reading-timestamp fallback in `PerceptionDomain`: metadata that no causal computation reads.

## Consequences

- Resuming the same body from the same X twice gives identical organism state: 0 differing fields at 24 and at 240 ticks, against 83 before. Gates H and I are enforced by tests.
- **Results from before and after EW-T cannot be compared.** Every study's sensory utility and rhythm context change once. Studies based on earlier commits must be re-run to be compared with anything produced afterwards.
- Fresh-body runs still differ in identity fields, such as body/embodiment uuids and checkpoint lineage. These are identity, not causal dynamics.

## Introduced in

Milestone EW-T.
