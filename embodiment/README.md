# Embodiment

A self-contained library of concrete mechanisms of embodiment and physical
coupling: bodies, their receptor and effector contracts, mount points. It has no
dependency on Symbiont, Modality, Environment or Lab.

Embodiment does not know which organism uses a body, which modality observes
it, which environment it runs in, or which experiment is active. Anything that
needs that knowledge is integration code and lives in `lab.integration`.

Import package: `embodiment`. Enforced by
`tests/experimental_integrity/test_five_domain_architecture.py`; checked alone by
`embodiment/tests`.

| Module | Contents |
|---|---|
| `embodiment.physics3d.humanoid` | anthropomorphic v6 body (PyBullet URDF, receptor contract) |
| `embodiment.physics3d.articulated`, `alternative_bodies` | generic articulated bodies; crawler and asymmetric bodies |
| `embodiment.physics3d.bodies` | body descriptors and the registry class |
| `embodiment.physics3d.vision` | vision body kind: the v6 body with a head mount (link, pose, receptor slots and ids); what fills the mount is injected |
| `embodiment.physics3d.longitudinal` | bounded epoch summaries across embodiments |
