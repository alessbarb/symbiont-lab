# ADR-0023: Atomic Transactional Step and Ecological Conservation Laws

## Status

Accepted

## Context

Simulated artificial ecologies featuring continuous dynamics (evaporation, topography, runoff, resource replenishment, biomass deposition upon death) risk state corruption or partial updates during runtime exceptions, collision collapses, or aborted ticks. Furthermore, spontaneous resource spawning without conservation limits undermines evolutionary pressure and carrying capacity studies.

## Decision

1. **Transactional tick boundary.** Every step in the simulated physical environment executes within an atomic, reversible transaction (`IntegratedWorldTickTransaction`). If any constraint check fails or an exception occurs during the tick, the entire world state (occupant positions, surface moisture, detritus, ecological pressure, resources) rolls back deterministically to tick $t$.
2. **Deterministic dynamic geography.** Active geography cells track:
   - `surface_water`: bounded accumulation governed by rainfall, terrain slope, and evaporation;
   - `detritus`: material deposited strictly upon verified organism death;
   - `ecological_pressure`: local load accumulated by bodily occupation.
3. **Conservation of matter and renewal.**
   - Living-to-dead transitions deposit physical detritus and local disturbance in the death cell;
   - Dynamic effective fertility is computed deterministically from base terrain fertility, detritus, water, and pressure;
   - Resource renewal scales with effective fertility. Resources never generate *ex nihilo* or through unconstrained global replenishment.
4. **Constitutional hash validation.** Any modification to dynamic ecological physics alters the Genesis constitution `interaction_rules_hash`, preventing incompatible checkpoints from resuming silently under altered laws.

## Consequences

- Absolute simulation determinism and guaranteed crash consistency across tick executions.
- Ecological carrying capacity enforces genuine population pressure and resource competition.

## Introduced in

Milestone W1 / World Ecology v1.

## Evidence

`docs/design/world/world-ecology-v1.md`, `tests/unit/world/test_transaction_integrity.py`, `environment/tests/unit/world/test_laws.py`.
