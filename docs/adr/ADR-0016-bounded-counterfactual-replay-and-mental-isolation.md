# ADR-0016: Bounded Counterfactual Replay and Mental Isolation

## Status

Accepted

## Context

Generative cognition, mental simulation, and experience replay allow an organism to consolidate memory, evaluate counterfactual actions, and learn predictive models during idle or quiescent periods. However, unconstrained mental simulation poses severe risks: hallucinated states overwriting empirical sensory ground truth, counterfactual signals escaping to physical actuators, and runaway internal loops monopolizing processor execution budgets.

## Decision

1. **Epistemic context separation.** Mental replay runs strictly within an isolated counterfactual execution context (`CounterfactualContext`). Replay ticks are tagged as non-empirical and cannot modify live sensory buffers or empirical baseline distributions.
2. **Replay state host boundary.** Simulated states generated during replay must never leak into host interfaces, sensory histories, or observer-facing empirical streams. Efferent commands emitted during mental simulation are virtual and blocked from reaching the body's physical actuators.
3. **Autonomous replay stopping.** Replay is not an unconstrained background thread. Replay epochs are budgeted and dynamically terminated by internal stopping criteria:
   - Derivation of learning progress (diminishing loss reduction or novelty gradient);
   - Surprise convergence threshold;
   - Hard tick budget caps.
4. **No retrocausal overwriting.** Replay updates latent model parameters, but historical episodic records remain immutable. Mental simulation cannot rewrite past sensory logs.

## Consequences

- Prevents confabulation and delusion: the organism never confuses mental simulation with physical presence.
- Organism tick latency remains bounded and cooperative with host or simulation scheduling.
- Empirical evidence records retain rigorous scientific provenance.

## Introduced in

Milestone K.

## Evidence

`tests/experimental_integrity/test_generative_cognition_boundary.py`, `tests/experimental_integrity/test_replay_state_host_boundary.py`, `tests/unit/lab/test_autonomous_replay_stopping.py`.
