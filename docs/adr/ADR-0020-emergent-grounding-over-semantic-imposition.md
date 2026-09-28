# ADR-0020: Emergent Grounding over Semantic Imposition

## Status

Accepted

## Context

In multi-agent and social artificial life, communication is frequently implemented by assigning pre-baked human semantic labels to communicative tokens (e.g. `FOOD`, `DANGER`, `FLEE`) or defining shared global message dictionaries. This creates an illusion of communication, as agents do not solve the symbol grounding problem or develop genuine communicative agency; they simply act as programmed message dispatchers.

## Decision

1. **Opaque communicative substrates.** Inter-organism signals (acoustic pulses, discrete tokens, chemical markers) carry zero predefined observer semantics, type annotations, or lexical labels.
2. **Zero downward semantics.** The simulator and Lab apparatus never inject ground-truth meanings into signals, nor do they reward organisms directly for emitting specific symbols.
3. **Emergent symbol grounding.** Semantic alignment is an emergent, endogenous property:
   - Organisms learn associations between received signals and subsequent environmental states through local predictive modeling;
   - Emission of signals is driven by internal agency and social coordination drives;
   - Mutual understanding is reflected in reciprocal prediction accuracy and behavioral synchronization.
4. **Peer trust and dissent tracking.** Organisms track social reliability locally using empirical belief models (`BeliefModel`) and explicit dissent records (`DissentRecord`), isolating ungrounded or deceptive peer reports without global oracles.

## Consequences

- Communication protocols are scientifically authentic and genuinely grounded in embodied experience.
- The Lab must measure cultural transmission and symbolic development through information-theoretic and behavioral coordination metrics, not lexical matching.

## Introduced in

Milestone C (Emergent Structured Communication).

## Evidence

`tests/unit/test_autonomous_cultural_agency.py`, `tests/unit/test_symbols.py`, `tests/unit/test_cumulative_culture.py`.
