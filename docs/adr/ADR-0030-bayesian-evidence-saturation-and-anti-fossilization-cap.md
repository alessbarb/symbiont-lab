# ADR-0030: Bayesian Evidence Saturation and Anti-Fossilization Cap

## Status

Accepted

## Context

Standard Bayesian belief models update prior distributions by accumulating observation counts monotonically ($N \to \infty$). In an artificial organism operating over thousands or millions of ticks in a stationary environment, the accumulated pseudo-evidence count reaches astronomical levels. When a genuine environmental regime shift occurs, the belief's variance becomes virtually zero ($\sigma^2 \propto 1/N$), requiring an impossible number of contradictory observations to adapt. The organism becomes epistemically "fossilized" (Bayesian paralysis).

## Decision

1. **Hard evidence ceiling (`max_evidence = 32.0`).** In `BeliefModel`, accumulated evidence weight is strictly bounded:
   $$N_{t+1} = \min(N_t + w_{\text{obs}}, N_{\max}), \quad \text{where } N_{\max} = 32.0$$
2. **Dynamic responsiveness preservation.** Once accumulated evidence saturates at $32.0$, subsequent confirming observations continue to update the running mean estimate via exponential moving weighting, but cannot increase the total confidence weight beyond the ceiling.
3. **Finite response horizon.** Under a significant regime shift, an unexpected observation with $|Z| \ge 2.0$ immediately triggers a dissent entry (`DissentRecord`, ADR-0006), and the bounded evidence weight allows full posterior distribution recalibration within a few dozen ticks.
4. **No infinite certainty.** The organism is mathematically prevented from declaring any environmental relation or hypothesis as absolute or immutable truth.

## Consequences

- Prevents cognitive calcification and preserves lifelong adaptive plasticity.
- Guarantees bounded recovery time after abrupt environmental shifts.
- Ensures numerical stability in variance computations across arbitrary lifespans.

## Introduced in

v0.22.0 (Belief & Dissent Architecture).

## Evidence

`src/symbiont/core/cognition/beliefs.py` (L44, L82), `docs/architecture.md` (L588), `docs/explanation/math/05-bayesian-beliefs-and-dissent.md`.
