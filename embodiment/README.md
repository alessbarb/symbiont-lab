# Embodiment

How an organism is coupled to a concrete form of existence: bodies,
receptor/effector bindings, apparatus adapters. An embodiment contributes no
cognition.

Import package: `embodiment`. May depend on `modality`; never on `lab`
(enforced by `tests/experimental_integrity/test_five_domain_architecture.py`).

| Module | Contents |
|---|---|
| `embodiment.physics3d.humanoid` | anthropomorphic v6 body (PyBullet URDF, receptor contract) |
| `embodiment.physics3d.vision` | vision body kind: the v6 body with a head-mounted receptor array |

Candidates not yet moved, and what blocks them, are listed in
`migration/open-issues.md` (OI-3, OI-4).
