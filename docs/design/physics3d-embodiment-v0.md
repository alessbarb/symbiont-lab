# Physics3D Embodiment v0

Status: implemented prototype

## Purpose

Provide a lightweight, physically simulated 3D embodiment apparatus for Symbiont
without introducing a full game engine.

The initial target is not locomotion success. It is to let a virgin Symbiont inhabit
an articulated anthropomorphic body and discover sensorimotor contingencies from
opaque channels.

## Architecture

```text
Symbiont
   │
   │ opaque in.N / out.N
   ▼
EmbodimentSession
   │
   ▼
Body
   │
   ▼
PyBullet apparatus
   ├─ gravity
   ├─ rigid bodies
   ├─ revolute joints
   ├─ contact physics
   └─ GUI or DIRECT/headless execution
```

PyBullet is apparatus-side. Anatomical names and joint identity never enter
Symbiont cognition.

## Current body

The procedural v0 body contains:

- pelvis;
- torso;
- head;
- two upper/lower arms;
- two thighs/shins;
- eight actuated revolute joints.

The physical apparatus knows this anatomy. The Symbiont does not.

Each physical joint is driven by two opaque effector ports:

```text
positive activation - negative activation -> signed joint torque
```

This preserves the meaning of zero activation as zero drive. A single output
channel is never given a semantic direction such as "flex knee".

## Receptors

The apparatus currently projects 31 bounded physical receptor values:

- position and velocity for each of eight motor joints;
- base orientation quaternion;
- base linear velocity;
- base angular velocity;
- five body/contact indicators.

These are connected to `ReceptorPort` instances and then translated through
`EmbodimentSession` into `in.N` channels.

No anatomical label, PyBullet joint id or world-space semantic name crosses that
boundary.

## Effectors

Sixteen physical effector ports are exposed: two per motor joint.

`EmbodimentSession` presents them to cognition as `out.N`. The apparatus maps
paired physical ports to signed torque only after the opaque output has crossed the
embodiment boundary.

## Initial experiment boundary

v0 is a biomechanics/embodiment experiment, not yet an ecological survival
experiment.

Therefore:

- gravity and collision are real;
- motor commands produce real torque;
- contact/proprioceptive consequences are real;
- physiological energy cost is temporarily zero;
- basal metabolism and degradation are temporarily zero.

This omission is explicit. It prevents the first embodiment experiment from being
dominated by an arbitrary energy model before joint work has a physically measured
cost. A later milestone should charge physiology from measured mechanical work.

## GUI and headless modes

Install:

```bash
pip install -e '.[physics3d]'
```

Interactive:

```bash
symbiont-body-3d
```

Headless:

```bash
symbiont-body-3d --headless --ticks 100000
```

GUI is for observation. DIRECT/headless mode is the scientific execution path for
long runs and weak hardware.

## Relationship to World and Observatory

This prototype is intentionally separate from the persistent ecological
`symbiont-world`.

- Observatory remains the sole UI for the existing World.
- Physics3D is the apparatus for embodied 3D experiments.
- There is no path from the Physics3D viewer back into cognition.
- There is not yet a bridge between Genesis ecology and the PyBullet room.

Future work may create a 3D World adapter, but it must preserve the same rule:
physical structure belongs to Body/World; cognition receives only opaque
consequences.

## Next milestones

1. Add explicit joint limits and richer anthropomorphic degrees of freedom.
2. Measure physical work and couple it to Body physiology.
3. Add ground-pressure and richer contact receptor surfaces.
4. Add bounded 3D environmental objects and terrain.
5. Publish passive Physics3D telemetry to Observatory.
6. Run preregistered controls comparing normal causal coupling with shuffled or
   disabled motor consequences.


## Portable Symbiont artifact

The cognitive organism is durable independently of any body.

The default Physics3D run maintains three separate files:

```text
~/.local/state/symbiont/physics3d/
├── subject.symbiont.json        # portable cognitive identity
├── subject.body.json            # current PyBullet pose/velocity only
└── subject.telemetry.ndjson     # passive apparatus observations
```

`subject.symbiont.json` contains organism-owned continuity: learned perceptual
statistics, sensorimotor model, agency evidence, inferred BodySchema, Self model,
genome/germline state where present, RNG state and cognitive tick continuity.

It deliberately excludes:

- body identity;
- anatomy;
- PyBullet object/joint ids;
- mass or geometry;
- physical pose;
- EmbodimentSession identity or port bindings.

Therefore the same file can be implanted into a different body.

Normal restart restores both the cognitive file and the physical body state when
their saved tick matches:

```bash
symbiont-body-3d
```

To transplant the persisted Symbiont into a newly constructed body while retaining
all cognitive experience:

```bash
symbiont-body-3d --fresh-body
```

A completely new cognitive subject requires an explicit reset:

```bash
symbiont-body-3d --new-symbiont
```

Checkpoint files are written atomically every 1000 ticks by default and again on a
clean/interrupt-driven exit. Physical and cognitive files are tick-matched before
the physical pose is accepted, preventing accidental assembly of states from two
different moments.

Telemetry is append-only and evaluator-side. It records position, orientation,
prediction error, BodySchema confidence, active effector count, aggregate joint
motion and contact count. None of these evaluator summaries are routed back to
cognition.
