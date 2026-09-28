# ADR-0029: Collinearity Pruning and Sensory Manifold Selection

## Status

Accepted

## Context

When exposed to an unfamiliar host environment or complex simulated habitat, an organism may discover hundreds of available sensory channels. In real operating systems and physics engines, many signals measure the exact same underlying physical state (e.g. multiple core CPU load metrics, redundant spatial coordinates, or co-linear joint angles). Ingesting all redundant signals exhausts the organism's finite attention budget ($1.0$), dilutes causal learning rates, and increases computational overhead without providing new information.

## Decision

1. **Online covariance tracking.** Pairwise signal dependencies are tracked online using Welford's bivariate covariance accumulator without buffering historical samples:
   $$r_{xy} = \frac{\text{Cov}(X, Y)}{\sqrt{\text{Var}(X) \cdot \text{Var}(Y)}}$$
2. **Hard collinearity ceiling (`redundancy_threshold = 0.97`).** If the absolute Pearson correlation between any two active sensory channels reaches or exceeds $0.97$ ($|r_{xy}| \ge 0.97$):
   - The channels are recognized as measuring the same physical phenomenon;
   - One channel is declared redundant and pruned from active sampling.
3. **Information utility arbitration.** When pruning redundant channels, retention is determined strictly by informational utility:
   $$\text{Utility} = 0.65 \cdot \text{NormalizedVariance} + 0.35 \cdot \text{MotionRate}$$
   The channel with lower utility is placed in dormancy.
4. **Periodic re-evaluation.** Pruned channels remain registered in dormancy and are periodically probed at low frequency to detect regime shifts or decorrelation.

## Consequences

- Compresses arbitrary input spaces into minimal non-redundant sensory manifolds.
- Preserves the finite attention budget for genuinely independent causal dimensions.
- Prevents cognitive overload in sensor-rich host and simulation environments.

## Introduced in

Milestone S / Adaptive Sensory Specialization.

## Evidence

`src/symbiont/host/adaptive.py` (L351, L794), `docs/architecture.md` (L179, L590), `tests/unit/host/test_sampling.py`.
