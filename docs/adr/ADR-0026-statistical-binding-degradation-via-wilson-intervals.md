# ADR-0026: Statistical Binding Degradation via Wilson Intervals

## Status

Accepted

## Context

When an organism experiences physical trauma, joint decoupling, or sensory recalibration, previously valid causal bindings (e.g., that motor channel $M_i$ produces effect $E_j$) cease to hold true. Heuristic thresholding or point-estimate invalidation can result in either catastrophic over-invalidation (false alarms due to scarce sample sizes) or stubborn preservation of broken models.

## Decision

1. **Self-referential historical comparison.** A causal binding is evaluated strictly against its own empirical performance within its active revision; rest states or passive baselines are never used for invalidation.
2. **Frozen reference baseline.** Upon becoming valid in revision $r$, the first $N_{\text{ref}} = 8$ executions establish a frozen reference success rate $k_{\text{ref}} / n_{\text{ref}}$.
3. **Non-overlapping degradation sample.** Subsequent executions after the reference is frozen form a cumulative evaluation sample ($k_{\text{new}} / n_{\text{new}}$). Executions must be non-overlapping commitments with independent evidence windows.
4. **Wilson score interval criterion.** A binding is marked `INVALIDATED` (`EVIDENCE_CONTRADICTED`) if and only if:
   - $n_{\text{new}} \ge N_{\text{min}} = 8$;
   - The Wilson score 99% upper bound ($z = 2.576$) of $k_{\text{new}} / n_{\text{new}}$ falls strictly below the Wilson score 99% lower bound of $k_{\text{ref}} / n_{\text{ref}}$.
5. **Immutable provenance trace.** Every binding state transition emits a content-addressed provenance event in the causal DAG identifying the invalidating commitment sequence.

## Consequences

- Formally bounds the repeated-evaluation false-alarm rate below 1%.
- Eliminates hardcoded arbitrary degradation thresholds by grounding revision in rigorous statistical confidence intervals.
- The organism cleanly and reliably drops broken effectors without destabilizing intact competencies.

## Introduced in

Milestone RC (Revision Coherence / Binding Degradation v1).

## Evidence

`docs/design/core/binding-degradation-v1.md`, `tests/unit/lab/test_embodiment_causal_revision.py`, `tests/experimental_integrity/test_revision_authority_boundaries.py`.
