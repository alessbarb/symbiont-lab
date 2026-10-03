# ADR-0021: Experimental Decontamination: Innate Constitution vs Discovered Meaning

## Status

Accepted

## Context

In Artificial Life research, experimenters frequently compromise autonomy by injecting downward semantic knowledge: labeling resources and hazards, pre-defining typed actions with human-authored intentions, establishing guided motor probing schedules, or providing free metabolic replenishment whenever the agent exhibits "desirable" cognitive states. In Symbiont, claims of autonomous discovery require strict proof that affordances and meanings were discovered by the organism rather than planted by the apparatus.

## Decision

1. **Constitutional boundary (P0).** The experimenter provides only the biological and physical substrate:
   - Body morphology and sensory transduction transfer functions;
   - Opaque motor effectors with finite energetic costs;
   - Metabolic capacities, homeostatic dynamics, and physical accounting;
   - Mathematical learning/plasticity rules and closed kernel limits;
   - World topology and simulation physics.
   These parameters form the immutable constitutional fingerprint and must never be reported as learned discoveries.
2. **Prohibition of semantic injection (P0).** The organism receives zero human semantic labels, resource identities, hazard identities, or external utility priors.
3. **Spontaneous exploration over scripted probing (P1).** The runtime shall not schedule artificial ON/OFF motor rotation windows, paired actuator sequences, or experimenter-authored exploration protocols (`motor_exploration_mode = spontaneous`). Motor discovery must arise from intrinsic somatic variability.
4. **Physical material exchange without cognitive rewards (P2).**
   - The World exchanges only physical quantities: scalar absorbed magnitude from contact/work, mechanical impact damage, and anonymous proprioceptive feedback.
   - The simulation never replenishes metabolic reserves as a reward for cognitive success or "correct" predictions.

## Consequences

- Affordances, threats, and nutritional opportunities are genuinely grounded in physical consequences.
- Eliminates confirmation bias and spurious cognitive achievements in scientific evaluations.

## Introduced in

Milestone E (Decontamination P0–P2).

## Evidence

`docs/design/experimentation/experimental-decontamination-p0.md`, `environment/tests/unit/world/test_constitution.py`, `lab/tests/unit/lab/test_canonical_sensorimotor_agency.py`.
