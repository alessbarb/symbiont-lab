# Tick performance baseline (L6.9.1 / L6.9.2 — measure only, no code changed)

Benchmark: `scripts/bench_organism_tick.py` — fixed seed, fixed base genome,
generously energy-provisioned body (so lifespan never gates the measurement),
no World. `python scripts/bench_organism_tick.py --organisms 1 10 --ticks 1000`.

## L6.9.1 — canonical benchmark

Sensing/actuation only, no cognitive graph attached (`cognitive_bridge=None`):

| organisms | ticks | wall s | ticks/s | ms/tick | peak RSS Δ |
|---|---|---|---|---|---|
| 1  | 1000  | 2.36  | 423.6 | 2.36 | +2.0 MB |
| 10 | 1000  | 23.69 | 422.2 | 2.37 | +11.6 MB (~1.1 MB/organism) |

Scales linearly across organisms (no cross-organism cost — expected, no World).

With a real cognitive graph attached (`load_base_cognition`, base genome): **~6.8 ms/tick**, roughly 3x the sensing-only cost. Cognition is the dominant term once it's actually running.

## L6.9.2 — profiler (cProfile, 500 ticks, sorted by cumulative and by self time)

### Confirmed from your hypothesis list

- **`CognitiveGraph`/`CognitiveBridge.tick` is the single largest cost**: `cognition_bridge.py:2428(tick)` — 0.276s tottime / 1.48s cumtime out of 4.0s total (~37% cumulative). Matches §4.
- **Redundant sorting**: `sorted()` called 30,628 times in 500 ticks (~61/tick), 0.16s tottime. Consistent with `SensorimotorLearner.primitives`/`cognitive_primitives` re-sorting on every access (§6), though the profile doesn't isolate which call sites dominate — worth a targeted check before assuming it's all sensorimotor.
- **`_representation_maturity`** (cognition_bridge.py:421) called 88,947 times in 500 ticks — ~178 calls/tick, 0.276s cumtime. That's a node-count-scale re-evaluation every tick; a strong incremental/cache candidate (§6/§7 territory).
- **Observability inside the hot path**: `narrative.py:narrate_host` + its genexpr cost ~0.12s+0.11s cumtime (500 ticks), `sensory/system.py:phenotype_view` ~0.11s tottime. Non-trivial, confirms §9 — this runs on every tick regardless of whether anything observes it.
- **Repeated dict construction / lookup pressure**: `dict.get` called 1,225,433 times in 500 ticks (~2450/tick). Consistent with §1's "rebuilt indices every tick" diagnosis, though attributing this to specific named dicts (`readings_by_capability` etc.) needs line-level profiling (py-spy/line_profiler), not just cProfile's function-level view.

### Not confirmed / not measured yet

- **`relative_cost`/O(n²) in attention allocation (§2)** and **the `attempted` outcomes O(n²) loop (§3)**: neither function appears anywhere in the top 35 by either cumulative or self time, in this benchmark. Either genuinely cheap at this sensor-set size, or this benchmark's sensor richness is too small to expose it (both are quadratic in *sensor/allocation count*, and this run uses a small default sensor set). Needs a benchmark variant with a richer discovered sensor set before ruling it out.
- **CognitiveGraph internals (array/index representation, §4/§5)**: confirmed the *function* is expensive; have not yet profiled *inside* `CognitiveGraph.activate` at edge/node granularity to confirm the specific "iterate edges twice" claim. Next step if we proceed: line-level profile of `cognition/graph.py`.

### New finding not in your list

- **`Percept.__post_init__` string validation is a measurable, non-trivial cost**: `host/percepts.py` — `any(char.isspace() for char in self.name)` (and the same for `sensor_id`/`modality_id`) runs a full Python-level character scan on every `Percept` construction. In 500 ticks: ~1,040,000 calls to `str.isspace()`, ~0.09s self time, plus the genexpr wrapper ~0.09s — roughly 5-8% of total profiled time, for validation of internally-generated hash-like strings that structurally cannot contain whitespace (they're `sha256(...).hexdigest()`-derived). Cheap, safe, zero-semantic-risk fix candidate (e.g. a compiled regex or `set(s) & _WHITESPACE` instead of a Python-level per-char genexpr) — same category as your §1/§3 "cero cambio algorítmico" bucket.

## What this baseline is for

Every later change in the perf phase must reproduce this: same `ticks/s` improvement claim backed by re-running `bench_organism_tick.py`, and losslessness backed by `OrganismRuntime.state_hash()` equality tick-by-tick against this same seed/genome/tick-budget (L6.9.8 in your plan) — the continuity-equivalence tooling from L5.5 (`state_hash()`, `tests/unit/core/test_continuity_equivalence.py`) already gives us the comparison primitive; it just needs to be run at every intermediate tick, not only at save/load boundaries.

## Not done

No code changed. Line-level profiling (py-spy/line_profiler) of `CognitiveGraph.activate` and a richer-sensor-set benchmark variant (to actually exercise §2/§3's suspected O(n²) paths) are the natural next measurement steps before touching anything.
