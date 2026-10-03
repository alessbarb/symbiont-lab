# Validation report

All runs are in this repository; the source repository was never executed.

## Test suite

`pytest -o addopts= -n 8` over `tests` and, once it moved, the Observatory
back-end tests. The baseline command is the `canonical-full` CI job.

| Stage | Result |
|---|---|
| Baseline, old layout (`593c2a02`) | 4456 passed (4190 + 266 observatory), 10 skipped, 2 xfailed, 0 failed |
| Byte-identical copies in the new trees, old code still present | 5 failed: `test_checkout_isolation` pins child processes to `src/`, i.e. it detected the mixed runtime |
| New layout only, paths adapted | 4466 passed, 10 failed (8 depended on uncommitted git state, 2 caused by the new `api.py`, fixed) |
| First modality/embodiment extraction; aliases and forwarders retired | 4477 passed, 8 failed (git-state dependent) |
| Legacy simulation, lab demo and Observatory front-end removed; packages renamed; committed | 3932 passed, 0 failed |
| Desktop workbench removed | 3925 passed, 0 failed |
| Checkpoint migrations 1–10 removed | 3857 passed, 0 failed |
| Bodies, apparatus, re-embodiment → embodiment; fixtures → environment | 3857 passed, 0 failed |
| Genome schema 1 removed (payloads converted first) | 3857 passed, 0 failed |
| Telemetry v3/v4 removed | 3834 passed, 0 failed |
| World terrain/genesis → environment; Lab web view removed | 3834 passed, 0 failed |
| **Final**: four peer libraries, cross-domain code in `lab.integration`, Import Linter | **3846 passed, 0 failed, 10 skipped, 2 xfailed** |

| Tests split per domain; one pytest session per suite | 3875 passed, 0 failed |
| **OI-3 closed**: organism builds no sense source, host channels in `modality.host`, interoception split, backends imported by the package that declares them | **4023 passed, 0 failed**: symbiont 1777, embodiment 9, modality 14, environment 116, lab 1676, repository 431 |

Run as `python scripts/run_tests.py -- -o addopts= -n 8`, one session per suite.
The count rose in the last stage from new tests of the Lab's composition and
of the interoception split. Skips: the nine and one of the baseline, plus one
per library for a self-containment test that is only meaningful installed
alone. Expected failures: the baseline two, plus two strict xfails that pin an
EXPOSED-BY-MIGRATION finding (host telemetry costs the organism observation
energy; `open-issues.md`).

The fall from 4456 to 3846 passing tests is deletion of tests for code that was
removed at the owner's request. Tests of surviving code that were lost are
listed under "Coverage given up".

Failures seen along the way that were not regressions: seven governance
classification tests, one markdown-link test and six `agentctl` child-process
tests read committed git state (policy file from the baseline commit,
`git ls-files`, an environment built from the committed tree). They failed
while the work was uncommitted and pass since the first commit.

## Lint

`ruff check` and `ruff format --check` over `symbiont/src environment/src
modality/src embodiment/src lab/src tests scripts migration symbiont/tests`:
clean, 1146 files.

## Organism identity (§17)

The organism was shown identical to the pre-migration one (`593c2a02`) through
commit `2632ff40e`, the end of the migration: old code extracted with
`git archive`, each tree run in a separate interpreter, 13/13 checks passing.

This comparison can no longer be run and its tool was removed. After the
migration the owner changed persistence on purpose (`3b2a341d3`: checkpoint
schema 12, continuation-condition integrity) and observation cost
(`0d54a8e1d`), with no backward compatibility: current code rejects schema-11
checkpoints and the old code rejects schema 12. The table records what held at
`2632ff40e`; it is not a claim about the current tree.

| Check | Result |
|---|---|
| old save → old load | same state hash |
| old save → new load | same state hash, same serialized fields, same lineage |
| re-save by old code vs re-save by new code | byte-identical |
| new save → new load | same state hash |
| new save → old load | same state hash |
| checkpoint schema | 11, unchanged; serialized field set unchanged |
| composed by the Lab vs self-built by the old organism | 63 cases (9 option sets born, 54 restored with overrides): same state hash and checkpoint |

The 63-case row compares the organism as born and as restored. It is not a
trajectory comparison: ticked dynamics over real host readings are not
deterministic, in either tree. The first rows do run five ticks before saving.

After the organism stopped building its own sources, every construction site
was re-checked for a silently host-blind organism: the rewrite tool reports no
remaining direct construction in `lab/src`, `lab/tests` or `tests`; the one
site inside the organism (a resident budding a child) now takes its
constructor from whoever composed the resident; the CLI run path was exercised
fresh, created with a state file and restored, with the host source attached
each time. No host channel declares a sampling cost the Lab adapter would
hide.

The four inline genome payloads converted from schema 1 to schema 2 were
checked before the old loader was removed: equal `Genome` object, equal genome
hash, equal genotype hash.

Re-embodiment tests pass from their new location in the organism.

Not run: a full Physics3D equivalence campaign through `agentctl` (OI-10).

## Self-containment of the four libraries (§18)

`python scripts/check_isolation.py` (also a CI step): for each library, a
temporary environment outside the repository, the library installed alone from
a copy with its declared extra, its tests copied to an empty directory, a probe
that no other first-party package is importable, then its full test suite.

| Library | Installed with it | Own suite, alone |
|---|---|---|
| `symbiont` | `cryptography` | 1778 passed, 4 xfailed |
| `embodiment` | `pybullet` (extra) | 10 passed |
| `modality` | `pybullet` (extra) | 15 passed, 1 skipped |
| `environment` | `pybullet` (extra) | 117 passed |

## Architecture gates (§19)

Import Linter, `lint-imports`: 3 contracts kept, 0 broken (618 files analysed).

1. The four domain libraries are mutually independent.
2. Domain libraries do not depend on the Lab.
3. The organism imports no physics, tensor or imaging backend.

A deliberate `from modality.vision import …` inside `embodiment` made contract 1
fail with exit code 1, and reverting it restored the pass.

`tests/experimental_integrity/test_five_domain_architecture.py` runs the linter,
repeats the matrix as a hard gate, checks that the four `pyproject.toml` declare
no first-party dependency and that each source root holds exactly its package,
and asserts that the organism holds no concrete host provider.

The pre-existing boundary tests in `tests/experimental_integrity` pass against
the new paths.

## Data moved without change

`lab/examples` and `lab/experiments` are byte-identical to `593c2a02` except
for the seven removed legacy specs. In `lab/research`, four markdown files had
relative links repaired; nothing else changed.

## Coverage given up

Tests of code that still exists, deleted because their fixtures depended on
something removed:

| Lost test | Surviving code now less covered |
|---|---|
| `tests/experiments/runners/test_reproducibility_e2e.py`, `test_generic_fallback_protocol_uses_declared_seeds_not_defaults` | experiment runner end-to-end reproducibility and seed handling (were exercised through the removed `simulate` / `evidence.replicated` protocols) |
| `tests/unit/host/test_legacy_admission_policy.py`, `tests/unit/lab/experiments/test_snapshot_origin.py` | admission of checkpoints flagged `unverified_legacy_origin` (subjects were built from schema-10 payloads) |
| four tests in `test_telemetry_tools.py` | `benchmark_run`, `compare_runs`, acceptance gates on a real run (inputs were built with the v4 writer and the converter) |
| two assays in `lab/tests/integration/studies/test_primitive_effects.py` | `analyze_primitive_effects` on recurrent and between-state effects (inputs were written with the v3 writer); the v4.1 assay remains |
| `test_unified_server_emits_live_organism_sse` | live organism SSE through the server (used demo telemetry as its source) |
| `tests/unit/lab/world/test_w01_w02_experiment.py` | none in `lab/src`; it imported a runner script of a completed experiment that still uses the old package names (OI-9) |
