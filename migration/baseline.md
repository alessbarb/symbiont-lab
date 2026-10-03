# Baseline (Phase 0)

State of the project before any file was copied or moved. Measured in this
repository (a clone of the source), never in the source repository, which was
left untouched.

## Provenance

| Item | Value |
|---|---|
| Source repository | `/home/alessbarb/workspace/repos/incubating/symbiont-lab` |
| Source branch | `main` |
| HEAD SHA | `593c2a028d20ab01cc5d81baf7335993e672ca23` |
| `origin/main` SHA | `593c2a028d20ab01cc5d81baf7335993e672ca23` (as last fetched in the source; not refreshed) |
| Source working tree | clean (`## main...origin/main`, no modified or untracked files) |
| Source worktrees (left alone) | `.symbiont/wt-cee`, `.symbiont/wt-parts`, `.symbiont/wt-r8`, `/tmp/symbiont-agentctl-pr` |
| Python | 3.12.13 (venv), `.python-version` = `3.12` |
| uv | 0.11.3 |
| `uv.lock` sha256 | `9aba8f9362e8792458a6ac348d2024e1b54f6ccff58ec6f83ee7860bf9d6d477` |
| Environment | `uv sync --frozen --extra dev --extra physics3d` |

This repository was created with `git init`, then `git fetch` from the source
(29 remote branches, 82 tags). Push is disabled on both remotes (`source`,
`origin`). The working branch is `migration/five-domain-architecture`.

The destination did not contain the five domain directories that
`INSTRUCTIONS.md` §4 expected to exist; they were created during the migration.

## Test baseline

Commands are the `canonical-full` CI job (`.github/workflows/ci.yml`), run with
`-n 8`:

| Command | Result |
|---|---|
| `pytest -o addopts= tests -q` | **4190 passed, 10 skipped, 2 xfailed** (226 s) |
| `pytest observatory -q` | **266 passed** (15 s) |

### Pre-existing failures

None.

### PRE-EXISTING skips and expected failures

- 9 skipped: `tests/docs/test_design_consolidation.py` (6) and
  `tests/docs/test_design_reference_repair.py` (3), "Obsolete after English migration".
- 1 skipped: `tests/unit/host/test_portable_surfaces.py:35`, "native host only".
- xfail: `tests/experimental_integrity/test_metabolic_cost_coherence.py::test_retention_at_full_sensory_capacity_fits_the_basal_budget`
  (retention prices not yet calibrated, ADR-0062 register §3).
- xfail: `tests/unit/core/test_concept_support_consumption.py::test_failed_concept_requires_fresh_post_gc_support_before_rebirth`
  (open source defect: a weakened, unused concept is not garbage-collected).

## Structure before the migration

```text
src/symbiont/         258 files   organism (import name `symbiont`)
src/symbiont_world/    12 files   world (import name `symbiont_world`)
src/symbiont_lab/     395 files   lab (import name `symbiont_lab`)
observatory/          112 files   observation UI + adapter (root-level package)
tests/                609 files
experiments/          377 files   experiment specs, runners, results
research/              91 files   scientific evidence registry
examples/               3 files
scripts/               22 files   agentctl, governance, benchmarks
docs/                 241 files
ORGANISM.md, deploy/              removed by the owner in the destination
```

One distribution, `symbiont-lab` 0.90.0, packaged all four import packages
from `src/` and `.`.

## Test suites

| Suite | Test files | Scope |
|---|---|---|
| `tests/unit` | 337 | per-package units (core 75, lab 129, cognition 35, host 21, actuation 19, ...) |
| `tests/integration` | 85 | cross-package, studies, physics3d, equivalence |
| `tests/experimental_integrity` | 63 | architecture and boundary guards (source-scanning) |
| `tests/compatibility` | 6 | real checkpoint v1/v10, genome v1, migrations, telemetry v40 |
| `tests/experiments` | 10 | protocol/runner/pilot contracts |
| `tests/governance`, `tests/docs` | 21 | governance tooling and documentation integrity |
| `tests/regression`, `tests/smoke`, `tests/archive` | 20 | regressions, CLI smoke, archived |
| `observatory/tests` | 38 | observatory |

## Entry points

`symbiont-lab` (`symbiont_lab.cli.main`), `symbiont-lab-gui`, `symbiont-world`,
`symbiont-body-3d`, `symbiont-physics-audit`, `symbiont-reembodiment-study`,
`symbiont-telemetry-benchmark`, `symbiont-telemetry-convert`, and
`scripts/agentctl.py`.

## Persisted formats

- Organism checkpoint: JSON, `schema_version` 11, written by
  `OrganismRuntime.save` through `symbiont.host.checkpoint` (migrations v1→v11,
  `checkpoint_lineage`, `runtime_provenance`).
- Genome / germline: JSON (`symbiont.genetics`, `symbiont.cognition.checkpoint`).
- World checkpoint: `symbiont_world.checkpoint`.
- Run manifests and `ExecutionFingerprint` (`symbiont_lab.experiments.manifest`),
  which record `repo_root`, the resolved `symbiont` / `symbiont_lab` file paths
  and the `uv.lock` hash.
- Physics3D telemetry (`symbiont_lab.physics3d.telemetry`, compatibility fixture v40).

No format stores Python module paths: there is no `pickle`, and no
`__module__` / class-path serialization in the persistence code. The only
`__qualname__` use is a telemetry label in `runtime.py`.

## External dependencies

- Runtime: `cryptography>=42` (organism capsule signatures), `rich>=15` (lab CLI).
- Extras: `modeling` (torch), `physics3d` (pybullet, torch, numpy, pillow).
- The organism package imports no third-party module other than `cryptography`.
