# Physics3D Constitution Audit

This study characterizes the existing Physics3D apparatus without tuning it.

It answers five questions before any change to motor learning:

1. What mass and expected weight does the loaded PyBullet body actually have?
2. Does the settled body receive a ground reaction consistent with that weight?
3. How far do collision shapes penetrate the ground solver plane?
4. Is the passive body mechanically stable after the birth settling phase?
5. How do work, displacement, contact force and penetration scale as more
   independent motor DoF are driven concurrently?

The study is observer-side. It does not modify the organism, reward it, alter
its sensors, or change gravity, mass, torque, friction or solver parameters.

## Run

Install the Physics3D extra and the editable project, then run:

```bash
pip install -e '.[physics3d]'
symbiont-physics-audit --output physics3d-constitution-audit.json
```

Canonical defaults:

- gravity: 9.81 m/s²
- physics: 240 Hz
- passive observation: 480 substeps
- motor drive: 240 substeps per condition
- motor amplitude: 0.35
- concurrent independent DoF: 1, 2, 4, 8, 16, 31

Each motor-dimensionality condition starts from a fresh body and repeats the
same passive settling protocol before actuation.

## Interpretation

The JSON reports:

- loaded total mass and expected weight (`m × g`);
- settling duration;
- COM/base drift while passive;
- mean/max ground normal reaction;
- reaction/weight ratio;
- mean/max ground penetration;
- base linear/angular drift;
- mechanical work under concurrent motor dimensionality;
- base path and net displacement;
- peak joint speed;
- peak ground reaction and penetration.

Small negative contact distances are normal in an iterative rigid-body solver.
The regression gate rejects centimetric ground penetration (>10 mm); the
measured values should be interpreted quantitatively rather than assuming the
Three.js drawing is physical truth.

The motor-dimensionality sweep is characterization, not an optimization gate.
Its purpose is to detect whether high-dimensional simultaneous actuation
produces disproportionately large physical/sensory consequences that could bias
sensorimotor learning toward global primitives.

## Viewer note

PyBullet is authoritative for physics. Three.js is an observer renderer.

PyBullet coordinates map to Three.js as:

```text
Bullet (x, y, z) -> Three (x, z, -y)
```

Therefore Bullet +Y rotations map to Three -Z. The Body viewer applies that
handedness explicitly for roll/deviation joints.
