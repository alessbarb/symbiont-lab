# Existence, lifecycle and time

Symbiont has several clocks because several things can begin and end independently. Confusing those clocks leads directly to conceptual errors such as treating a re-embodied organism as newborn or treating an old body as evidence that the Symbiont itself is senescent.

## Organism time

`OrganismRuntime` maintains `tick_count`. A tick advances the organism's causal history. Rest can alter the mode of generative cognition, but it does not create metabolic resources and does not erase organism history.

## Body time

The living body carries age and physiology. `PhysiologyDomain.advance_body_age()` is invoked after the organism tick has completed. Body ageing therefore belongs to the current physical embodiment, not to the identity of the Symbiont as a whole.

## Embodiment time

A `TickContext` carries both `symbiont_tick` and embodiment identity. Before executing a tick the runtime validates that the context belongs to the current Symbiont and current `EmbodimentEpisode`. Reacclimation is also advanced at the beginning of each tick, making the transition into a body a bounded developmental condition rather than a reset of the organism.

## Physics time

Physics3D has its own integration rate. `PyBulletEmbodimentRuntime` uses a solver time step and multiple physics substeps per organism tick. Presentation sampling can run at a separate cadence again. This allows the body to move continuously enough for stable mechanics without inventing extra cognition ticks.

## Experimental time

A laboratory run has its own start, duration, seed, world and stopping criteria. Experimental time is metadata about observation, not an intrinsic clock that should feed the organism unless the experiment explicitly exposes an equivalent signal through a legitimate perceptual surface.

## Death, dormancy and re-embodiment

The runtime refuses further ticks after `VitalState.DEAD`. By contrast, the end of a body or embodiment is not automatically the death of the Symbiont. Longitudinal re-embodiment therefore has to preserve organism-owned state while replacing body-specific and embodiment-specific state.

The current design and implementation distinguish these cases deliberately. A fresh body can be created around a restored organism checkpoint, after which the new embodiment contract is established and body-specific state is reinitialised or reacclimated.

## Why the distinction matters scientifically

If an experiment observes better action after re-embodiment, the researcher must ask what persisted. Was it organism-level competence, a body-specific controller, a body schema, a contract-specific memory, or merely a laboratory configuration? Without explicit time and ownership domains the experiment cannot answer that question reliably.

### Principal sources

- `docs/design/embodiment/symbiont-body-temporal-separation-v1.md`
- `docs/design/embodiment/longitudinal-reembodiment-v1.md`
- `src/symbiont/core/domains/context.py`
- `src/symbiont/core/orchestration/runtime.py`
- `src/symbiont_lab/physics3d/runtime.py`
