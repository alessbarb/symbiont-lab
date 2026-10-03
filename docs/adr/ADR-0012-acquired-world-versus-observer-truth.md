# ADR-0012: Acquired World versus Observer Truth (ADR-EW-005)

## Status

Accepted

## Context

The Experience & World specification (§29 and gap decision D6) requires Challenge Worlds and integrated 3D environments to provide genuine spatial, ecological, and relational integration. In physical simulations, there is an acute architectural risk: populating the organism's internal spatial/relational model ("Acquired World") using ground-truth entity states, meshes, collision hulls, or object labels from the simulation engine (`PhysicsWorldObserver.entities`, `world_scene`). Doing so breaches ground-truth isolation (ADR-0002) and replaces autonomous discovery with downward injection.

## Decision

1. **Acquired World ownership.** The Acquired World belongs exclusively to the organism (`symbiont.core.domains`, `symbiont.modeling`). It is derived strictly from experiential evidence—sensorimotor correlations, proprioceptive feedback, luminance patterns, and local predictions accumulated across causal ticks.
2. **Zero entity injection.** The simulation engine (`Physics3DEnvironment`, physics backends) must never pass physical entity IDs, geometric meshes, bounding volumes, or semantic object labels down to `Symbiont`. The organism senses only opaque receptor arrays and contact forces.
3. **Observer truth separation.** `world_scene`, scene revisions, and `PhysicsWorldObserver` are observer-only apparatus constructs. They are used exclusively by the scientific apparatus (`symbiont_lab.observation`, `observatory`) for offline metric calculation, ground-truth logging, and passive visualization.
4. **Epistemic correlation path.** The Lab may correlate the organism's acquired representations with observer ground truth *strictly post-hoc* inside evaluation protocols (`symbiont_lab.evaluation`), never within the causal execution loop.
5. **No parallel world state.** The Observatory and Workbench must never synthesize or "assist" the organism's internal world representation; the organism's internal world model is strictly what its own evidence justifies.

## Consequences

- Ground-truth isolation (ADR-0002) is strictly maintained in complex 3D environments.
- Environmental affordances, obstacles, and resources must be discovered empirically through interaction.
- Evaluation metrics remain epistemologically clean and uncoupled from organism cognition.

## Introduced in

Milestone EW-B.

## Evidence

`tests/experimental_integrity/test_ground_truth_boundary.py`, `lab/tests/unit/observatory/test_world_integration.py`.
