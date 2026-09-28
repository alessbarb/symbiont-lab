# ADR-0014: Single Motor Authority and Executive Action Contract

## Status

Accepted

## Context

Complex artificial organisms feature multiple internal drives: instinctual reflexes, exploratory motor babbling, goal-directed planning, homeostatic self-preservation, and prospective agency. If subsystems can directly invoke hardware or simulation actuators, the organism suffers from command collisions, race conditions, metabolic incoherence, and impossible causal credit assignment.

## Decision

1. **Single motor authority.** Every embodiment instance exposes exactly one canonical actuation gateway (`MotorAuthority` / `ExecutiveAuthority`).
2. **Tripartite separation: proposal, arbitration, efference.**
   - *Proposal:* Internal cognitive modules generate uncommitted action proposals or motor vectors.
   - *Arbitration:* The executive motor authority reconciles competing proposals against anatomical joint constraints, metabolic energy budgets, and vital state.
   - *Efference:* The arbitrated command is issued to the body contract, and an immutable efference copy is recorded for causal learning.
3. **No backdoor actuation.** No cognitive module, background loop, or host provider may bypass the motor authority to directly actuate joints, move velocity targets, or manipulate external state.
4. **Metabolic gating.** When the organism is in severe resource pressure or dormancy, the motor authority downscales or zeroes actuator torques, enforcing physiological limits over cognitive intention.

## Consequences

- Causal learning can strictly attribute sensorimotor outcomes using the true efference copy rather than unarbitrated intentions.
- Guaranteed physical and mechanical consistency of bodily motions.
- Simplifies behavioral ablation and counterfactual studies by providing a single point of experimental intervention.

## Introduced in

Milestone J.

## Evidence

`tests/experimental_integrity/test_single_motor_authority.py`, `tests/experimental_integrity/test_executive_authority.py`, `tests/experimental_integrity/test_reduced_symbiont_action_authority.py`.
