---
title: Experienced world — evidence audit and minimal acquisition contract
status: draft
canonical: false
---

# Experienced world

Audit baseline: `4383a7eca70ee3165de79a467f0a29c6a834612f`.
This document separates implemented observation improvements from a proposed
cognitive capability. It is not evidence that spatial learning already exists.

## What main actually contains

| Capability | Code and exported evidence | What it does not establish |
|---|---|---|
| Physical surroundings | `physics3d/world_observation.py`: engine collision shapes, transforms, contacts, resource field | Organism object identity or recognition |
| Receptor sampling | `physics3d/apparatus.py`: `observed_tick_values`, union of provider calls this tick | Every available receptor was sampled; the union is not a sequence of calls |
| Emitted perception | `physics3d/runtime.py`: `runtime.percepts` | Nonzero value is not required for perception; zero is valid evidence |
| Receptor lineage | `physics3d/observer_semantics.py`: sensory source IDs, exact/composite source mapping | External source separation; an apparatus source is not an environmental object |
| Signal identity | `runtime.signal_references` from organism perception | A stable signal token is not a persistent physical source |
| Signal learning | `core/signals/knowledge.py`, `knowledge_types.py`, `prediction.py`: claims, evidence counts, status, related signals, horizons, baselines | Spatial familiarity or coordinates |
| Self / BodySchema | `core/embodiment/body_schema.py`: opaque parts and acquired dependencies; `self_model` snapshot | An anatomical skeleton or external map. Do not reconstruct private salted part IDs in the UI |
| Action / dynamics | `actuation/footprint.py`, `agency/availability.py`, `core/embodiment/dynamics.py`: causal effects, bindings, predictive residuals | Learned displacement in a shared environmental reference frame |
| Episodes / private modeling | `modeling/episodic.py`, `temporal.py`: sequences, retrieval, contingencies and temporal hypotheses | Proven object permanence, occupancy or localization |
| Spatial memory / prediction | No object-localized authoritative export in the inspected runtime | Cannot enable Known World / spatial Predictions from signal confidence |

The apparatus in `physics3d/articulated.py::sample_receptors` samples joint
angle/velocity, orientation and linear/angular velocity, binary contact by body
region, a scalar field and bounded contact loads. It does **not** sample base
position, range, bearing, object ID, texture, light or category. It does expose
orientation and velocity in the current engine convention; that is an existing
sensor contract, not evidence of an acquired frame of reference. Changing that
contract is a separate embodiment decision.

The resource field is isotropic. Equal intensities can come from many positions.
Contact channels merge contacts for a body region, including self-contact. There
is no direct material or friction receptor. Surface friction may alter motion
and load during interaction; recognizing it requires experience and validation.

## Implemented observation path

`observation/world_scene.py` joins only explicit exported references:

1. apparatus receptor to sensor through observer lineage;
2. sensor/percept name to signal through `runtime.signal_references`;
3. signal to its existing `runtime.signal_knowledge` record;
4. claims retain their original status, evidence count, revision and related ID.

Missing references stay unavailable. No hash guessing, nearest-neighbor matching
or geometric proximity supplies a cognitive edge. Composite lineage remains
marked composite: several input receptors do not identify a unique cause.

In World locates the selected experience at its recorded **pre-action** receptor
anchor. Other related receptors remain highlighted. A compact callout shows
sampling, percept emission and claim status. The inspector exposes exact IDs
and evidence limitations. Dashed links are explicitly observer placement of
source attribution or exported signal relationships, never learned spatial edges.
Contacts remain **post-action**. These two phases must not be used as a causal
proof of each other. There is no invented propagation animation or guessed
latency. Render frequency does not change observation or simulation frequency.

Knowledge records are carried in rich spatial observations and participate in
existing revisioned deltas. Geometry is not resent on each render frame. The
current evidence map is replaced when changed; sparse per-signal patches are a
future optimization if measured payload costs justify them.

## Reproducible physical environments

`physics3d/environments.py` defines versioned laboratory recipes:

- `flat-v1`: current plane and resource, with no extra fixtures.
- `contact-garden-v1`: two low platforms with different friction, one block and
  one barrier. All are real static PyBullet collision/visual shapes. The plane
  and resource continue to be owned by their existing runtime components.

The environment changes opportunities, not objectives. No reward, target
trajectory, semantic input or genome state is introduced. Layout is fixed,
independent of organism RNG. A seed still controls the organism; the environment
recipe controls these fixtures. Future recipe changes require a new version.

Home exposes the server's recipe catalog for a fresh body. A resumed body restores
its saved world. The CLI also accepts `--environment contact-garden-v1`.
For an isolated CLI run, choose separate organism, body and telemetry paths:

```sh
symbiont-body-3d --headless --ticks 100 --no-slm --no-monitor \
  --environment contact-garden-v1 \
  --symbiont-file /tmp/contact-garden/organism.symbiont \
  --body-state-file /tmp/contact-garden/body.json \
  --telemetry-file /tmp/contact-garden/telemetry
```

A complete versioned recipe is saved as `lab_world` in the physical checkpoint
and in observer run configuration. It is not saved in the organism bundle.
This extends the existing physical checkpoint container; it does not move world
ownership into Body. Historical physical checkpoints resolve to `flat-v1`.
A conflicting explicit environment on resume is rejected before physics starts.
Saved geometry must match the named recipe; edited or unsupported recipes fail
instead of silently changing the experiment. Native body IDs are not persisted.

Mechanical tests check all current body descriptors: adding distant fixtures
leaves readings identical; moving the apparatus into actual contact changes a
contact receptor while preserving the opaque receptor surface. These are
apparatus detectability tests, **not** evidence of autonomous discrimination,
learning, navigation or transfer. Friction discrimination has not been proved.

## Minimal proposed cognitive capability — not implemented

The first useful acquisition target is an **experienced context graph**, not a
semantic object map. It must be implemented within the organism and consume only
its existing opaque observations, executed actions and observed consequences.
The laboratory may evaluate it but may not supply its nodes or transitions.

### Inputs and ownership

Reuse `signal_references`, signal claims, experience records, action effect
footprints and embodiment epochs. A context observation contains tick, epoch,
actual sampled/emitted signal IDs and values/quality, and executed action evidence
IDs where available. Missing sensing is missing evidence, never a zero vector.
No World entity ID, recipe ID, pose, collision identity, geometry, human label or
observer mapping is accepted. Do not duplicate the event ledger or signal store:
context support points to existing evidence records with bounded retention.

### Acquired state

A context has an organism-local monotonic ID, revision, support references,
last independently observed tick, tentative/validated/stale state and uncertainty.
Its signature groups recurring observation patterns conditioned on action history;
all grouping starts empty. Similar signatures can be aliased contexts. Do not
merge them solely because signal intensity matches.

Transitions link two acquired contexts and the actually executed action/effect,
with evidence windows, successes, alternatives, missing-observation counts and
prediction residuals. Context edges initially mean observed recurrence or
transition, **not distance, direction or object motion**. Store hypotheses
separately from validated transition evidence.

The online update must have declared memory/update budgets and deterministic
ordering. Confidence must be calibrated against held-out independent windows,
with a minimum support requirement fixed before evaluation. Pruning must retain
provenance of retirement without recycling IDs. Checkpoint/restore preserves
IDs, revisions, pending predictions, evidence-window boundaries and residuals.
An embodiment change invalidates applicability of body-conditioned transitions;
it does not erase all cognition or mark all prior knowledge false.

### Additional gates for source separation and spatial claims

Source differentiation requires repeated disambiguating interactions: compatible
and incompatible observations under interventions, explicit alternative-source
hypotheses and a test against a single-source/aliasing baseline. Recurrence alone
does not prove permanence. A permanence hypothesis needs disappearance,
reappearance, negative evidence only when observable, and competing explanations.
The present scalar field plus merged contacts can leave sources unidentifiable;
the correct outcome then is unresolved ambiguity.

Spatial relations require an acquired relative frame and a validated mapping from
self-motion evidence to changes in observations. Do not integrate simulator
velocity into a UI-created cognitive map. If a future organism mechanism learns
such a mapping, it owns the estimates, uncertainty and correction history. An
observer coordinate transform is optional metadata, never cognitive input.

### Acceptance before enabling spatial overlays

1. Learn recurring contexts without laboratory identities or coordinates.
2. Beat persistence/frequency baselines on preregistered held-out transitions;
   compare learning disabled, action evidence removed and observation shuffled.
3. Preserve ambiguity for symmetric worlds and aliased scalar observations.
4. Distinguish missing sensing, a sensed zero and negative evidence.
5. Test disappear/reappear and changed-world cases before claiming permanence.
6. Preserve state and causal provenance across checkpoints and re-embodiment.
7. Trace every displayed prediction to an acquired model revision, origin tick,
   horizon and evidence. Match actual observations before computing discrepancy.
8. Measure memory, update cost and calibration across multiple seeds and worlds.

## Known World / Predictions activation contract

Do not create a second truth database. Project the acquired context graph with
node IDs, revisions, support, uncertainty and transition provenance. A validated
context graph without spatial localization belongs in a relational view; it is
not a warrant to place familiar objects in the Three.js world.

A future spatial export must declare its organism-owned reference frame, relative
estimates and uncertainty; predictions add model revision, issued tick, horizon,
expected signal/context and matched outcome status. Only a justified observer
alignment may place it in the physical scene, clearly labeled as such. Without
alignment, show the relational evidence and explain the missing spatial link.
Without the acquired state itself, keep the layers unavailable. Current work
therefore enriches Perception and its inspector; it does not enable spatial
Known World or Predictions prematurely.
