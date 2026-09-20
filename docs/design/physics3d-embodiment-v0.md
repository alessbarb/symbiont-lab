# Physics3D Embodiment v1

Status: implemented canonical-runtime integration

## Purpose

Physics3D is a lightweight physical embodiment apparatus for the canonical
Symbiont organism. It exists to study what a Symbiont can discover and learn
when its ordinary runtime inhabits a real articulated 3D body.

PyBullet is not a second cognitive runtime and does not contain a behavioural
policy. It supplies physical state, gravity, collision and actuator
consequences.

## Canonical architecture

```text
PyBullet physical state
        |
        v
PhysicsReadingProvider
        |
        v
HostLifecycle
        |
        v
PrivateModelOrganismRuntime.tick()
  |     |       |        |
  |     |       |        +-- Private SLM experience
  |     |       +----------- BodySchemaEngine v2
  |     +------------------- physiology / homeostasis / metabolism
  +------------------------- cognition / motor discovery
        |
        v
MotorIntent -> ActuatorSystem -> Actuation
        |
        v
apparatus-owned actuator binding
        |
        v
PyBullet torque -> physical consequences -> next tick
```

There is exactly one organism runtime in this path.

The former Physics3D prototype directly executed
`Symbiont.step() -> EmbodimentSession -> Body.apply_activations()`. That path
was useful for the first visual prototype but duplicated the canonical organism
and bypassed its physiology, BodySchemaEngine, canonical actuation and Private
SLM. It is retired from Physics3D.

Frozen historical studies that intentionally use the older
`Symbiont + Body + Individual` research surface remain reproducible; they are
not silently rewritten.

## Physical body

The current PyBullet apparatus is procedural and deliberately cheap to render.
It contains pelvis, torso, head, paired arm segments and paired leg segments,
with eight physical revolute joints.

Anatomical identity exists only in `physics3d/humanoid.py`.

The organism receives 31 opaque read-only physical signals:

- joint position/velocity measurements;
- base orientation;
- base linear and angular motion;
- bounded contact indicators.

They cross into the runtime as ordinary opaque local signal capabilities. No
anatomical label is exposed.

The apparatus offers sixteen physical motor ports. The Physics3D birth genome
therefore has sixteen opaque canonical motor slots. Motor-slot ordinal is bound
to physical-port ordinal by the apparatus. The runtime does not receive the
physical meaning of that binding.

The physical apparatus pairs those ports antagonistically at each joint. A
single canonical `Actuation` therefore becomes a positive or negative torque
on one physical joint, while all non-commanded torques are explicitly zeroed
on that tick.

## Motor learning

Physics3D uses the existing canonical actuation machinery:

- `ActuatorProposer`;
- `MotorIntentSelector`;
- `ActuatorSystem`;
- pending proprioceptive consequences;
- actuator health/reliability/cost;
- canonical metabolic charging.

The initial Physics3D organism uses `motor_exploration_mode="spontaneous"`.
This avoids an experimenter-authored body-specific movement plan. Occasional
endogenous twitches provide sparse causal motor evidence; learned cognition may
later drive the active motor repertoire.

No `walk()`, `balance()`, limb names or desired posture enters cognition.

## BodySchema

The monitor now reports the canonical `BodySchemaEngine v2`, not the retired
`InferredBodySchema` from the first Physics3D prototype.

The evaluator displays:

- normalized existence confidence across learned body parts;
- number of learned parts;
- number of exported learned dependencies.

The full schema remains the runtime's bounded organism-owned representation.
PyBullet anatomy is never copied into it.

## Private SLM

Physics3D uses `PrivateModelOrganismRuntime`, so private experience capture is
part of the same organism tick as perception, cognition and actuation.

Canonical opaque motor `Actuation` is captured as organism-owned experience
without anatomical semantics. The Private SLM therefore receives experiences
from the embodied life rather than a separate laboratory stream.

Training remains an external bounded authority, as in the rest of Symbiont:

```text
organism ExperienceLedger
        |
        | organism-owned TrainingRequest
        v
low-priority background worker
        |
        v
PrivateModelFactory
        |
        v
held-out evaluation
   |                 |
 fail              pass
   |                 |
 SHADOW           ACTIVE
```

On CPU, the worker runs at lowered OS priority and one Torch thread so training
does not compete aggressively with the 3D physics loop.

Defaults:

- minimum private records: 64;
- training cadence: 4096 ticks;
- architecture: GRU v1;
- context window: 32;
- requested parameters: 1,000,000;
- requested epochs: 2;
- requested steps: 12;
- device: CPU.

Disable for an ablation with:

```bash
symbiont-body-3d --no-slm
```

The monitor exposes record count, model count, ACTIVE state, current background
training status and any training/attachment error.

## Portable Symbiont

The canonical organism is stored as one portable bundle:

```text
~/.local/state/symbiont/physics3d/
├── subject.symbiont             # portable organism + Private SLM artifacts
├── subject.body-v2.json         # canonical PyBullet embodiment only
├── subject.telemetry-v2.ndjson  # canonical passive evaluator telemetry
└── models/                      # local materialized cache of bundled SLM artifacts
```

`subject.symbiont` is a ZIP container with:

- the canonical `PrivateModelOrganismRuntime` checkpoint;
- private model manifests;
- private model weights;
- the tokenizer sidecars required to reconnect inference.

It does not contain the PyBullet pose or anatomy.

Consequently:

```bash
# Resume same organism and, when tick-compatible, same physical pose
symbiont-body-3d

# Same persisted organism, new physical body
symbiont-body-3d --fresh-body

# Explicitly create a different organism
symbiont-body-3d --new-symbiont
```

The bundle is written atomically. Model weights are stored without recompression
to reduce checkpoint CPU cost.

### Legacy first Physics3D subject

The earlier prototype wrote `subject.symbiont.json` using the parallel
`Symbiont/Individual` stack. That file is deliberately not auto-migrated into
the canonical runtime, because doing so would fabricate a mapping between two
different cognitive state representations.

If present, it is preserved untouched as historical evidence. The canonical
Physics3D path starts a new `subject.symbiont` instead.

## Monitor

The GUI uses two separate processes:

- PyBullet renders only physical reality;
- Tkinter renders evaluator telemetry.

The monitor receives bounded snapshots through a non-blocking queue. If it falls
behind, stale monitor frames are discarded rather than slowing physics.

It displays:

- canonical tick and embodiment mode;
- BodySchema confidence, parts and dependencies;
- current cognitive prediction error;
- active physical motor output;
- aggregate joint motion and contacts;
- body height;
- checkpoint age;
- Private SLM records, models, ACTIVE/training state and error status;
- strongest opaque motor activity;
- rolling prediction-error and BodySchema-confidence traces.

Disable only the monitor with:

```bash
symbiont-body-3d --no-monitor
```

The monitor is evaluator-only and has no route back into the runtime.

## Installation

Physics3D now includes both PyBullet and the Private SLM runtime dependency:

```bash
pip install -e '.[physics3d]'
```

Interactive:

```bash
symbiont-body-3d
```

Headless long run:

```bash
symbiont-body-3d --headless --ticks 100000
```

## Experimental boundary

Physics3D currently provides real mechanics but not yet a complete ecological
energy loop.

What is real now:

- gravity;
- rigid-body collision;
- joint dynamics;
- friction;
- physical contact;
- canonical motor actuation;
- canonical runtime physiology/homeostasis/metabolism;
- organism-owned BodySchema development;
- private experience and SLM state.

What remains deliberately incomplete:

- mechanical work is not yet converted from measured PyBullet torque/velocity
  into physiological resource cost;
- there is no food/resource ecology in the empty room;
- feet/hands and joint limits remain simplified;
- Physics3D telemetry is not yet published to Observatory.

Those gaps must remain explicit rather than being hidden behind arbitrary
rewards or hand-authored locomotion goals.

## Next scientific work

1. Run the canonical Physics3D subject and verify that BodySchema parts and motor
   repertoire develop from real physical signals.
2. Verify that Private SLM records accumulate, background candidates train and
   ACTIVE/SHADOW transitions are visible.
3. Characterize motor causal evidence before changing thresholds.
4. Add physically measured joint-work cost to canonical metabolism.
5. Add realistic joint limits, feet and hands without adding behavioural goals.
6. Perform transplant experiments with `--fresh-body`.
7. Add causal ablations: disabled motor consequence, permuted physical binding
   and delayed consequence.
8. Publish passive Physics3D state to Observatory.


## Migration boundary

The first visual Physics3D prototype used these files:

```text
subject.symbiont.json
subject.body.json
subject.telemetry.ndjson
```

The canonical-runtime implementation does not overwrite them. It uses
`subject.symbiont`, `subject.body-v2.json` and
`subject.telemetry-v2.ndjson`. This preserves the complete earlier run as
historical evidence and prevents telemetry from two different runtime
architectures being mixed in one time series.
