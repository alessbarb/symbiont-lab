# World, body and embodiment

## Why three entities are required

A body is not an organism and an embodiment is not a body. The distinction is easiest to see during change.

If the same Symbiont is moved from one anthropomorphic body to a crawler, the organism persists, the old physical body does not, and the relationship between organism and physical surface is rebuilt. Calling all three “the body” makes it impossible to say what was learned, what was retained and what must be reacquired.

## Physical body

In Physics3D the body is represented by PyBullet state plus an apparatus implementation. Body descriptors define the available receptor and effector sets. The runtime separately stores physical body identity and can reconstruct legacy identity from physical state when migrating older checkpoints.

The body can be affected without cognition. Gravity, collision, joint limits, surface contact and environmental forces are physical dynamics. The laboratory can inspect them even when no corresponding internal representation exists.

## Apparatus

The apparatus is the interface exposed by the body. On the incoming side it supplies receptor values. On the outgoing side it accepts validated actuator channels. Its labels and implementation details belong to the physical/laboratory description; the organism's sensory and motor representations need not preserve those semantics.

## Embodiment contract

The core `EmbodimentContract` binds a perceptual surface, actuator surface, timing contract and mutually exclusive actuator groups. In Physics3D this contract is derived from the actual apparatus counts and effector constraints. It therefore captures the actionable/sensible surface without claiming that the organism knows the anatomical meaning of those channels.

## Body schema

`BodySchemaEngine` is organism-owned inferred structure. It is not a mirror of the PyBullet model. It is built from relationships available through experience and should therefore be read as an internal model of sensorimotor organisation rather than a copy of external anatomy.

That difference is especially important in Observatory. A human-friendly skeletal view may draw a right arm because the observer knows the body's morphology. The organism's schema may contain only opaque channels, learned couplings and confidence about their relations.

## Reacclimation

A new embodiment can preserve historical organism state while making old sensorimotor assumptions temporarily unreliable. Reacclimation is the explicit period in which some learning or interpretation is gated while the organism establishes how the present surface behaves.

## What should survive a body change?

The answer is not “everything” or “nothing”. Persistence is mechanism-specific. Organism identity, genome and general cognitive history may survive; physical pose and body integrity do not. Body-schema and competence information require more careful rules because some of it may be transferable and some may be contract-specific. The persistence chapter documents those boundaries in detail.

### Principal sources

- `docs/design/embodiment/embodiment-v2.md`
- `docs/design/embodiment/perception-and-embodiment.md`
- `docs/design/embodiment/embodiment-memory-v1.md`
- `src/symbiont/core/embodiment/body_schema.py`
- `src/symbiont/core/embodiment/contract.py`
- `src/symbiont_lab/physics3d/apparatus.py`
- `src/symbiont_lab/physics3d/runtime.py`
