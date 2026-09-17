# Structured Communication Characterization v1

> Give Symbionts capabilities and constraints, not linguistic answers.

This line characterizes the generic communication substrate already closed as
**Emergent Structured Communication v1**. It does not add a language, grammar,
composition target, semantic labels, or a new organism capability.

## Boundary

**We provide:** channel, opaque symbols, bounded variable-length sequences,
memory, cost, limits, environment, and authorized contact opportunities.

**We do not provide:** meaning, grammar, roles, syntax, composition, optimal
messages, semantic slots, or linguistic rewards.

The organism selects silence, message content, length, order, and authorized
recipient through the existing local policy. The laboratory only supplies the
experiment, contact availability, resource ceilings, and evaluator-side
measurements. No evaluator state or latent environmental label enters
cognition.

## Study

`learning.structured-communication-characterization` is preregistered in
[`experiments/learning/structured-communication-characterization/experiment.toml`](../../experiments/learning/structured-communication-characterization/experiment.toml).
It uses seeds `101, 127, 149`, a 64-tick bounded trace, opaque content tokens,
and a small non-cartesian pressure matrix: no signal, random signal, baseline,
high complexity, tight vocabulary, high complexity plus tight vocabulary, high
communication cost, sequence-disabled, and full channel.

The characterization split reserves the final quarter of observed message
events for descriptive novelty analysis. This is not a training target and is
not supplied to the organism. Controls include no-signal, random-signal, and
single-symbol/sequence-disabled conditions. Holistic and partially structured
labels are evaluator classifications only; no label is a runtime objective.

## Measurements and interpretation

The result artifact records communication opportunities, silence, deliveries,
lengths, symbol/sequence reuse, entropy, evaluator-only mutual information,
prediction gain, cost, replay, and a conservative code classification per seed
and condition. A positive utility result does not imply syntax or language.
Productivity and compositionality remain open questions and are not claimed by
this study.

## Observatory

The passive Communication Live panel exposes bounded sequence counters,
decision history, opaque message IDs, local grounding rows, and cost. It never
shows evaluator meanings, weights, corpus data, or control actions. Missing
sequence fields remain compatible with older snapshots. Population-level and
scientific aggregate views must consume explicit exported telemetry; they are
not fabricated from individual snapshots.

## Validation status

The generic substrate audit found no factor slots, role assignments, semantic
mapping, hidden holdout target, or compositional reward. The only technical
change for this characterization is per-runtime selection of an existing
bounded maximum sequence length, persisted through checkpoint/clone. The
scientific result is descriptive, not a new closure claim.
