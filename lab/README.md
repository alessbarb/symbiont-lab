# Lab

Where the pieces are composed, experiments run, and evidence is produced.
The Lab is the only composition root: it depends on the four domain libraries,
which do not depend on each other or on the Lab.

| Path | Contents |
|---|---|
| `src/lab/` | import package `lab` (formerly `symbiont_lab`): studies, experiments, CLI, server, workbench, physics3d, world, observation |
| `src/lab/integration/` | adapters that know more than one domain: Physics3D apparatus, composed bodies, re-embodiment, world adapter |
| `src/lab/observatory/` | observation back-end (adapter, journal, schemas, world viewer) |
| `experiments/` | experiment specifications, runners and results |
| `research/` | evidence registry, audits, protocols |
| `examples/` | example genome, graph and replay |
