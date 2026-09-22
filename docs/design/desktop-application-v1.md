# Symbiont Lab desktop application

`symbiont-lab` is the primary human-facing application. Physics3D and
declarative experiments are scientific capabilities launched and observed by
the application, not independent UI owners.

## Boundary

```text
app -> experiments / studies / physics3d / world -> symbiont
```

The application may control apparatus lifecycle and visualization, but must not
create cognitive concepts, beliefs, motor primitives, learned labels or
internal rewards.

The former `physics3d/monitor.py` implementation is now owned by
`symbiont_lab.app.physics3d_monitor`; the old module is a compatibility facade.

## Entrypoints

```bash
symbiont-lab
symbiont-lab app
symbiont-lab experiment run experiments/.../experiment.toml
symbiont-body-3d
```

The first two open the desktop workbench. CLI commands remain available for
automation and reproducibility.

Tk owns the desktop process. Scientific runs execute in spawned child processes.
Only one foreground run is admitted initially. Physics3D termination uses its
existing SIGTERM-aware graceful checkpoint path.
