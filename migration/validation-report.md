# Validation report

All runs are in this repository; the source repository was never executed.

## Test suite

| Stage | Command | Result |
|---|---|---|
| Baseline, old layout (`593c2a02`) | `pytest -o addopts= tests` + `pytest observatory` | 4190 passed, 10 skipped, 2 xfailed + 266 passed, 0 failed |
| Copies in new trees, old code still present (`PYTHONPATH` to new trees) | same | 4185 passed, 5 failed: `test_checkout_isolation` pins child processes to `src/`, i.e. it detected the mixed runtime |
| New layout only, paths adapted | same | 4200 passed, 10 failed (8 commit-dependent, 2 caused by the new `api.py`, since fixed) |
| After first modality/embodiment extraction | same | 4212 passed, 8 failed (commit-dependent) |
| After alias/forwarder removal | same | 4211 passed, 8 failed (commit-dependent) |
| Legacy simulation, lab demo, Observatory front removed; packages renamed (uncommitted tree) | `pytest -o addopts= -n 8` over `tests` and `lab/src/lab/observatory/tests` | 3918 passed, 14 failed, 10 skipped, 2 xfailed |
| Same tree, committed | same | 3932 passed, 0 failed, 10 skipped, 2 xfailed |
| **Final**, desktop workbench removed | same | **3925 passed, 0 failed, 10 skipped, 2 xfailed** |

The drop from 4456 to 3925 passing tests is deletion of tests for removed
code: legacy simulation and its studies, the Observatory front-end, the lab
demo, the desktop workbench, archived tests. No test of surviving code was deleted to make the suite
pass, with three exceptions listed under "Coverage given up".

Skips and xfails are the same as in the baseline.

### The 14 failures seen before committing

None was a behavioural regression; each depended on git state that did not
exist until the work was committed. All 14 pass on the committed tree.

| Tests | Why |
|---|---|
| `tests/governance/test_publish_classification.py` (7) | the classifier loads `docs/governance/change-surfaces.toml` from the committed baseline (`git show <base>:…`), which still has the old paths. Verified in `scripts/governance/classify.py`. |
| `tests/docs/test_all_markdown_links_resolve.py` (1) | iterates `git ls-files '*.md'`, which still lists deleted files (`ORGANISM.md`). `migration/tools/fix_markdown_links.py --check` over the working tree reports 0 broken links. |
| `tests/unit/test_checkout_isolation.py::test_agentctl_run_start_records_verified_child_receipt` (6) | the child failed with `No module named 'lab'`: the scientific child environment is built from the committed tree, where the package was still `symbiont_lab`. |


## Lint

`ruff check` and `ruff format --check` over `symbiont/src environment/src
modality/src embodiment/src lab/src tests scripts migration symbiont/tests`:
clean (1163 files).

## Organism identity (§17)

`python migration/tools/identity_check.py --old <src of 593c2a02>` — 12/12 PASS.
Old code extracted with `git archive`, run in a separate interpreter.

| Check | Result |
|---|---|
| old save → old load | same state hash |
| old save → new load | same state hash, same serialized fields, same lineage |
| re-save by old code vs re-save by new code | byte-identical |
| new save → new load | same state hash |
| new save → old load | same state hash |
| checkpoint schema | 11, unchanged; serialized field set unchanged |

Real checkpoint fixtures (schema v1, v10), genome v1 and migration tests in
`tests/compatibility` pass in the new layout, as do the re-embodiment tests.
A full Physics3D equivalence campaign was not run (see `open-issues.md` OI-10).

## Organism independence (§18)

A wheel built from `symbiont/` alone, installed in an empty environment
(`cffi, cryptography, pycparser, pytest` and its dependencies, nothing else):
`symbiont/tests/test_independence.py` — 2 passed. It creates an organism, runs
it, saves, loads, checks the state hash, and asserts that `lab`, `environment`,
`modality`, `embodiment`, pybullet, torch, numpy and PIL are neither installed
nor loaded.

## Architecture gates (§19)

`tests/experimental_integrity/test_five_domain_architecture.py`, all passing:

- `symbiont` ✗→ `lab`, `environment`, `modality`, `embodiment`, pybullet, torch, numpy, PIL;
- `environment` ✗→ `symbiont`, `lab`, `modality`, `embodiment`, heavy libraries;
- `modality` ✗→ `symbiont`, `embodiment`, `environment`, `lab`;
- `embodiment` ✗→ `lab`;
- each source root holds exactly its domain package;
- ratchets on two known violations (organism core → concrete host providers;
  physics apparatus → cognition internals);
- `symbiont.api` resolves and carries no modality-specific types.

The 60+ pre-existing boundary tests in `tests/experimental_integrity` pass
against the new paths.

## Data moved without change

`lab/examples` and `lab/experiments` are byte-identical to `593c2a02` except
for the seven removed legacy specs. In `lab/research`, four markdown files had
relative links repaired; nothing else changed.

## Coverage given up

- `tests/experiments/runners/test_reproducibility_e2e.py`: end-to-end runner
  reproducibility was exercised only through the removed `simulate` protocol.
  No equivalent on a surviving protocol was written.
- `tests/smoke/test_unified_app_assets.py::test_unified_server_emits_live_organism_sse`
  relied on demo telemetry as its event source.
- `tests/unit/lab/world/test_w01_w02_experiment.py` imported a runner script of
  a completed experiment that still uses the old package names (OI-9).
