# ADR-0004: Separated RNG Streams

## Status
Accepted

## Context
When running stochastic simulations with multiple random subsystems (host profiles, agent traits, reporters, event scheduling, observation generation, drift), modifying parameters in one subsystem (e.g. reporter poisoning fraction) can shift the global random sequence if a single RNG stream is shared. This causes cross-contamination of experimental effects.

## Decision
Derive orthogonal, independent `random.Random` streams per namespace via SHA-256 (`derive_seed(master_seed, namespace)`). Adding or modifying stochasticity in one namespace leaves all other streams completely bitwise-identical across runs with the same master seed.

## Consequences
- Strict counterfactual comparability across interventions.
- Verified in engine integrity regression tests.

## Introduced in
v0.19.0

## Evidence
`tests/test_engine_integrity_v021.py`, `src/symbiont/environment/rng.py`.
