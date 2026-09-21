# Developmental Cognitive Ecology validation campaign

This campaign validates the pre-exploration architecture in increasing order of
cost and scientific commitment. It deliberately separates **technical
execution** from **scientific gate passage**.

A command returning exit code 0 means the protocol executed and wrote immutable
artifacts under `.symbiont/runs/`. It does **not** mean the hypothesis passed.

## Stage 1 — structural scheduler invariant

Run:

```bash
symbiont-lab experiment run experiments/learning/structural-producer-fairness/experiment.toml
```

Proceed only when `metrics.json` reports:

```text
all_pass = true
```

This validates multiplicity neutrality and bounded producer waiting independently
from embodied cognition.

## Stage 2 — discrete temporal challengers

Run:

```bash
symbiont-lab experiment run experiments/learning/temporal-mechanism-challenge/experiment.toml
symbiont-lab experiment run experiments/learning/temporal-private-model-controls/experiment.toml
```

Interpretation is mechanism-local. Do not promote GRU, Transformer, stationary
VOMM or decayed VOMM into resident cognition from these results.

For causal interpretation, inspect the intact-versus-control margins separately
for each mechanism. A low held-out loss without causal-control separation is not
evidence of useful temporal modeling.

## Stage 3 — continuous temporal challenger

Run:

```bash
symbiont-lab experiment run experiments/learning/continuous-temporal-challenge/experiment.toml
symbiont-lab experiment run experiments/learning/continuous-temporal-controls/experiment.toml
```

The regime-shift challenge characterizes adaptation. The causal-control study
is the stronger gate. Inspect:

```text
all_seeds_causal_beats_controls
mean_causal_margin
```

Failure is retained as a negative result; do not retune the same preregistration.

## Stage 4 — embodied cognitive ecology

Run:

```bash
symbiont-lab experiment run experiments/learning/cognitive-ecology-embodiment/experiment.toml
```

Primary architecture field:

```text
all_architecture_gates_pass
```

Per seed, inspect at minimum:

```text
predictor_monopoly
peak_predictors
peak_shadow_predictions
final_concepts
final_readouts
final_motor_readout_nodes
final_primitive_readout_nodes
peak_structural_producers
maximum_structural_wait_ticks
expected_wait_bound_ticks
maturity_nascent
maturity_provisional
maturity_mature
maturity_stable
maturity_weakening
maturity_retiring
motor_origin_cognition
motor_origin_mixed
motor_origin_primitive
motor_origin_primitive_cognition
motor_origin_primitive_verification
motor_origin_babbling
cognitive_motor_primitives
cognitive_motor_output_edges
resource_progress
```

Passing the architecture gate does not prove useful motor cognition. In
particular, zero cognitive motor output remains a substantive negative result.

## Stage 5 — matched-twin causal behavior

Run only after Stage 4 has produced at least one **actually used** cognitive
motor output: direct cognition, mixed cognition, or
`motor_origin_primitive_cognition > 0`. The mere presence of cognitively
eligible primitives or primitive readout nodes is not sufficient:

```bash
symbiont-lab experiment run experiments/learning/embodied-behavioral-ablation/experiment.toml
```

The study reconstructs twins from the same completed organism checkpoint and
the same physical state. Cognitive learning is frozen in every twin.

Conditions:

```text
normal_frozen
motor_output_lesion_frozen
motor_output_shuffled_frozen   # only when >=2 targets exist in a family
```

Inspect:

```text
testable_trials
lesioned_edges
shuffled_edges
displacement_effect
resource_progress_effect
shuffled_displacement_effect
shuffled_resource_progress_effect
```

A seed with no naturally developed cognitive motor output is reported as
`not causally testable`; it is neither a positive nor negative ablation.

A second graph-tick motor-output delay is intentionally excluded. Resident
learned motor and primitive associations already use the canonical maximum
`delay_ticks=1`. Manufacturing another graph delay would require noncanonical
semantics or a runtime hook and would confound the matched-twin design.

## Stop conditions

Stop the campaign and record the result before changing mechanisms when any of
the following occurs:

1. Stage 1 violates producer fairness.
2. Stage 4 reproduces predictor monopoly.
3. Stage 4 exceeds the preregistered structural waiting bound.
4. All Stage 4 seeds fail to develop concepts/readouts.
5. All Stage 5 seeds are not causally testable.

Do not connect intrinsic motivation, learning-progress exploration, RSSM,
exact CTW/ACTW, or automatic temporal-mechanism promotion while any of these
gates remains unresolved.

## Provenance rule

For every run preserve:

- `manifest.json`;
- `metrics.json`;
- optional `summary.json`;
- the exact Git SHA recorded by the manifest;
- the preregistered TOML used for execution.

Do not overwrite failed runs or regenerate them after tuning under the same
protocol version.
