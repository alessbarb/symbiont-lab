# Adversarial audit: Structured Communication Characterization v1

Date: 2026-09-17  
Scope: `learning.structured-communication-characterization`

## Audit questions

- Are symbols opaque and bounded?
- Does the harness select claims, sequences, roles, or meanings?
- Are latent state labels, holdout labels, or utility metrics inputs to policy?
- Are length, order, and silence available without being prescribed?
- Can replay and checkpoint preserve the same decision trace?
- Does Observatory remain passive and separate organism from evaluator views?

## Findings

The substrate uses content-addressed opaque symbol IDs and canonical sequence
hashes. Sequence length is variable within a hard ceiling; the runtime can
select a smaller ceiling for a control without assigning semantic positions.
The policy receives local context tokens and authorized neighbors only. The
study keeps state values in evaluator-local arrays for analysis and does not
pass them to the runtime. No role, slot, grammar, factor mapping, target
message, or linguistic reward was found in the characterization path.

The harness controls contact availability and records outcomes, but it does not
choose emitted content. The random and no-signal branches are explicitly
controls, not autonomous evidence. The Observatory renderer displays opaque
IDs and local grounding/cost fields only; no evaluator meaning is projected.

## Limitations

The current study is an individual-pair characterization trace. It does not
claim population-wide structure, causal compositionality, or productive
generalization. Cost is recorded as a channel accounting variable; this study
does not close a separate cost-sensitivity gate. A future fleet export may add
population graph and evaluator-analysis views, but those must use real bounded
telemetry rather than infer relationships from a single snapshot.

## Disposition

No methodological scaffold was found that requires removal before the
characterization run. Any later claim of productive structured communication
requires an independent preregistered replication.
