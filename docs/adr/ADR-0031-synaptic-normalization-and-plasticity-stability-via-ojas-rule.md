# ADR-0031: Synaptic Normalization and Plasticity Stability via Oja's Rule

## Status

Accepted

## Context

Standard Hebbian synaptic learning ($\Delta w_{ij} = \eta y_i x_j$) exhibits an inherent positive feedback instability: active inputs reinforce active weights, driving synaptic weights to unbounded positive or negative infinity ($w \to \pm \infty$). In artificial neural substrates and continuous ALife organisms, unbounded weight growth leads to neuron saturation, catastrophic loss of selectivity, and numerical overflow (`NaN` / `Inf`) during long execution campaigns.

## Decision

1. **Oja's modified Hebbian rule.** All plastic synaptic weight adaptations enforce Oja's weight normalization formulation:
   $$\Delta w_{ij} = \eta \cdot y_i \left( x_j - y_i \cdot w_{ij} \right)$$
   This intrinsically stabilizes the Euclidean norm of the weight vector ($\sum_j w_{ij}^2 \to 1$), extracting principal components without explicit post-hoc matrix normalization.
2. **Hard saturation boundary (`WEIGHT_RANGE = [-2.0, 2.0]`).** Every synaptic weight is strictly clamped to the interval $[-2.0, 2.0]$ following any update step:
   $$w_{ij} \leftarrow \text{clamp}(w_{ij}, -2.0, 2.0)$$
3. **Bounded eligibility traces (`ELIGIBILITY_BOUND = 10.0`).** Causal eligibility traces accumulating pre- and post-synaptic correlations are bounded to $[-10.0, 10.0]$ to prevent gradient explosion during delayed reward/feedback credit assignment.
4. **Finite integration constants (`TAU_RANGE = [0.1, 10.0]`).** Neuronal leaky integrator time constants ($\tau$) are constrained to a closed interval to ensure numerical stability under Euler integration steps.

## Consequences

- Mathematical guarantee of bounded numerical dynamics and zero `NaN`/`Inf` occurrences across infinite lifespans.
- Synaptic competition naturally specializes receptive fields without requiring global normalization coordinators.
- Eliminates manual learning rate decay scheduling.

## Introduced in

v1.0.0 / Cognitive Limits Specification.

## Evidence

`src/symbiont/cognition/types.py` (L28, L32), `src/symbiont/cognition/learning.py` (L9), `symbiont/docs/explanation/math/09-endogenous-plasticity-and-recurrent-networks.md`.
