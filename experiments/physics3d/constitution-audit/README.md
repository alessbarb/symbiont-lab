# Physics3D Constitution Audit

This study characterizes the current Physics3D apparatus and the motor surface
that drives it. It is observer-side and never supplies anatomy, utility, gait,
reward, targets or labels to Symbiont.

The canonical body now owns passive mechanical properties in the same sense as
mass, inertia and friction:

- gravity and collision geometry remain PyBullet truth;
- joints have bounded passive elastic neutral-rest tone plus explicit URDF joint damping;
- directional effector channels that drive opposite directions of one physical
  DoF are declared as opaque mutually-exclusive groups;
- the organism still sees only opaque actuator IDs.

A newborn Physics3D body must reach the declared passive settling criterion
before organism tick 0. Failure to settle is a failed apparatus initialization,
not a successful timeout.

## Questions

The audit separates questions that the previous single sweep conflated:

1. What mass and expected weight does the loaded body actually have?
2. Does passive settling converge, and with what residual velocities?
3. Does ground reaction support the measured weight?
4. How much solver penetration occurs at rest and under actuation?
5. How does response change as concurrent motor dimensionality rises at fixed
   per-DoF amplitude?
6. Does that dimensionality effect remain when total nominal torque capacity is
   held constant?
7. Which individual DoF saturate their velocity limit?
8. How much commanded actuator work is positive, negative, absolute and net?

## Run

```bash
pip install -e '.[physics3d]'

symbiont-physics-audit \
  --output physics3d-constitution-audit.json
```

Canonical defaults:

- gravity: 9.81 m/s²
- physics: 240 Hz
- passive observation: 480 substeps
- motor drive: 240 substeps per condition
- motor amplitude: 0.35
- concurrent DoF: 1, 2, 4, 8, 16, 31
- deterministic matched selections per dimensionality: 4
- single-DoF characterization: all 31 DoF

The output schema is version 2.

## Output

`constitution` reports mass, expected weight, motor DoF, directional channels,
mutually-exclusive motor groups and the full settling result.

`passive` reports:

- COM/base drift;
- ground reaction and reaction/weight ratio;
- mean/max ground penetration;
- mean/max number of ground contact points;
- residual linear, angular and joint velocity.

`fixed_amplitude_dimensionality` repeats each requested cardinality with
multiple deterministic joint selections while keeping the requested activation
amplitude constant. Total available torque is therefore allowed to grow.

`fixed_total_torque` runs the same cardinalities with one constant nominal
torque budget. This is the control required to distinguish "more active DoF"
from merely "more total available torque". The common budget is derived from
the lowest per-DoF torque capacity, so every selected joint can realize it
without hidden activation saturation.

`single_joint_characterization` evaluates every DoF independently and reports:

- nominal torque capacity;
- positive actuator work;
- negative actuator work magnitude;
- absolute actuator work;
- net actuator work;
- displacement/path;
- ground reaction and penetration;
- peak joint speed;
- fraction of observed substeps at >=98% of that joint's velocity limit.

## Work terminology

For commanded motor torque `tau` and angular velocity `omega`:

```text
signed work  = tau * omega * dt
positive     = sum(max(work, 0))
negative     = sum(max(-work, 0))
absolute     = positive + negative
net          = positive - negative
```

The legacy field `mechanical_work_joules` remains as a compatibility scalar
for metabolic accounting and is explicitly the **absolute commanded actuator
work/effort**, not net mechanical work. New telemetry exports all four
components.

Passive postural/end-range torque is a body property and is intentionally not
counted as commanded actuator work.

## Sensorimotor interpretation

Physics3D motor development uses sensorimotor schema v9.

Its important invariants are:

- opposite directional channels of one physical DoF cannot execute
  simultaneously;
- this exclusion is opaque: cognition receives no joint or anatomical label;
- motor-effect learning uses the complete currently perceived bodily state,
  not a lexicographic 64-signal slice;
- motor effect magnitude uses a fixed top-k consequence statistic so distributed
  motion is not automatically rewarded merely for changing more signals;
- primitive recurrence includes both activation magnitude and active-channel
  support, preventing dense patterns from diluting support differences;
- older learned sensorimotor schemas fail closed because their evidence was
  collected under different causal/statistical rules.

## Viewer boundary

PyBullet is authoritative for physical transforms and contact physics. Three.js
is an observer renderer.

```text
Bullet (x, y, z) -> Three (x, z, -y)
```

Authoritative PyBullet world link poses drive the live body visualization.
Contact telemetry distinguishes total body contacts, ground contacts,
self-contacts and resource contacts.

Small negative contact distances are normal in an iterative rigid-body solver.
Centimetric sinking remains a regression failure; measured penetration should
always be interpreted quantitatively.
