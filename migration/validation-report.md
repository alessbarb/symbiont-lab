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

Skips and xfails are the same ten and two as in the baseline.

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

`python migration/tools/identity_check.py --old <src of 593c2a02>`, old code
extracted with `git archive` and run in a separate interpreter. Run on the
final tree: 12/12 PASS.

| Check | Result |
|---|---|
| old save → old load | same state hash |
| old save → new load | same state hash, same serialized fields, same lineage |
| re-save by old code vs re-save by new code | byte-identical |
| new save → new load | same state hash |
| new save → old load | same state hash |
| checkpoint schema | 11, unchanged; serialized field set unchanged |

The four inline genome payloads converted from schema 1 to schema 2 were
checked before the old loader was removed: equal `Genome` object, equal genome
hash, equal genotype hash.

Re-embodiment tests pass from their new location in `embodiment`.

Not run: a full Physics3D equivalence campaign through `agentctl` (OI-10).

## Self-containment of the four libraries (§18)

Each library was built as a wheel on its own and installed in an empty
environment containing no other first-party package. Its own tests assert that
none of the others is installed or loaded.

| Library | Installed with it | Own tests |
|---|---|---|
| `symbiont` | `cryptography`, `cffi`, `pycparser` | 2 passed: create, run, save, load, state hash preserved |
| `embodiment` | nothing | 3 passed: body contracts complete; vision body leaves the array to the caller |
| `modality` | nothing | 2 passed: receptor adjacency over opaque ids |
| `environment` | nothing | 3 passed: fixture recipes resolve; seeded randomness |

These own-tests are small. The bulk of the unit tests still lives in `tests/`
and runs against the whole workspace (OI-8).

## Architecture gates (§19)

Import Linter, `lint-imports`: 3 contracts kept, 0 broken (618 files analysed).

1. The four domain libraries are mutually independent.
2. Domain libraries do not depend on the Lab.
3. pybullet, torch, numpy and PIL are imported only by the Lab.

A deliberate `from modality.vision import …` inside `embodiment` made contract 1
fail with exit code 1, and reverting it restored the pass.

`tests/experimental_integrity/test_five_domain_architecture.py` runs the linter,
repeats the matrix as a hard gate, checks that the four `pyproject.toml` declare
no first-party dependency and that each source root holds exactly its package,
and keeps one ratchet on debt inside the organism (core → concrete host
providers).

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
