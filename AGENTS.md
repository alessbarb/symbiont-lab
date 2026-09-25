# Repository Guidelines

## Scope

Symbiont Lab is a Python 3.11+ research monorepo containing two decoupled packages:

- **`symbiont`** (Research Subject): cognition, synthetic ecology, simulation and a consent-bound local-host organism runtime.
- **`symbiont_lab`** (Scientific Apparatus): experiments, studies, archive, CLI and passive visualization.

The local-host direction is intentionally developmental: Symbiont may discover bounded, aggregate, read-only signal surfaces, assign them opaque identities, learn their statistical behavior and usefulness, and decide which ones deserve routine attention. Cognition must not be handed platform semantics when it can learn from the signal itself.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest

symbiont-lab simulate --hosts 100 --steps 300 --seed 7
symbiont-lab organism run --ticks 20
symbiont-lab organism live
symbiont-lab dashboard --port 8765
python observatory/resident.py --interval 15
```

## Test organization and maintenance

The test tree is an explicit contract. Read the nearest `README.md` before
adding, moving, deleting, or weakening a test.

### Test configuration

Pytest is configured in `pyproject.toml` with:

- `testpaths = ["tests"]`, so the root `experiments/` tree is never collected
  as a pytest suite;
- `addopts = "-m 'not slow'"`, so expensive tests are opt-in by default;
- `experiment_contract` for mechanical protocol and runner contracts;
- `slow` for tests that intentionally run campaigns, long simulations,
  populations, full replays, 3D physics, model training, or real servers.

Useful validation layers are:

```bash
pytest tests/unit tests/docs tests/smoke
pytest tests/integration tests/experimental_integrity
pytest tests/experiments
pytest tests/integration/studies
pytest --collect-only -q
pytest --durations=50 -q
pytest -m slow
```

The full scientific study suite is explicit and must not become the default
developer loop. Runs that produce scientific evidence belong under
`experiments/` and are launched through their documented CLI, not collected
by pytest.

### Where tests belong

- `tests/unit/`: isolated behavior of one software unit;
- `tests/integration/`: interaction between software modules;
- `tests/contract/`: public and boundary contracts;
- `tests/experimental_integrity/`: RNG, ground truth, provenance, and safety
  boundaries;
- `tests/regression/`: preserved failures and previously fixed behavior;
- `tests/smoke/`: short end-to-end health checks;
- `tests/experiments/`: mechanical contracts for protocols and runners;
- `tests/compatibility/`: explicit historical payloads and migrations only;
- `experiments/`: executable campaigns, configuration, manifests, and run
  outputs; never `test_*.py` files intended for pytest;
- `research/`: analysis, audits, interpretation, and evidence; never test
  fixtures or executable pytest suites.

### Modify, remove, or preserve a test

Modify a test when the test encodes a contract deliberately removed from the
active runtime, such as Genome v1 fields, old kernel versions, `primitive`
aliases, or obsolete Body/Embodiment APIs. Update the fixture to the current
contract and preserve historical coverage in `tests/compatibility/` when that
artifact is still supported.

Do not modify an assertion merely to make a failure disappear when it checks
an active invariant: deterministic replay, persistence, isolation, identity,
domain validation, RNG behavior, ground-truth separation, or safety limits.
Investigate `src/` in those cases and add a focused regression test.

Delete a test only when it has no distinct contract, is uncollectable dead
code, or duplicates a stronger current test. Before deletion, check whether it
is the only coverage for a historical migration or safety boundary; move that
coverage rather than losing it. Never delete a historical test solely because
the current runtime no longer supports its input.

Every new test must answer one question, use the smallest deterministic
fixture, and be placed according to the local README. Mark expensive tests
`slow`; mark runner/protocol contracts `experiment_contract`. Do not expose
private implementation details such as `_babble_cardinality` as a test
contract when observable behavior is sufficient.

### Compatibility and replay rules

Genome v2, competence-based sensorimotor behavior, the current
organism/Body/Embodiment boundary, and current telemetry are the active
contracts. Historical inputs are supported only through named migrators and
explicit compatibility suites. Checkpoint restoration must preserve enough
causal state for deterministic continuation under the same inputs, RNG, and
world/body conditions. Do not weaken replay assertions to accommodate lossy
restoration without an explicit architecture decision.

### Change and commit discipline

Before editing, inspect `git status --short --branch` and preserve unrelated
worktree changes. Group commits by logic, for example:

1. test layout and documentation;
2. fixture/test contract migration;
3. source bug fixes required by active invariants;
4. CI or performance changes.

Run focused validation and `git diff --check` for each logical group. Review
the staged diff before committing. Push only the grouped commits after
verification; never stage unrelated user files or generated documentation.

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and reasoning may use only observations, local memory, collective reports, coarse fingerprints and derived trust. Evaluator-only metrics must never feed back into organism decisions. `symbiont` must never import or depend upon `symbiont_lab`.

## Safety boundaries

Real-host code is limited to explicit, local, least-privileged, read-only aggregate observation. It must not collect identity or user-content metadata. Autonomous discovery is restricted to vetted observation surfaces and may never broaden itself into arbitrary filesystem traversal, process content inspection, credentials, network scanning, peer discovery or permission seeking.

A **transparent resident lifecycle is allowed** when explicitly installed by the host owner: foreground/user-service execution, bounded periodic checkpoints, clean SIGINT/SIGTERM shutdown and `systemd --user` supervision are in scope. It must never install itself, hide, evade removal, escalate privileges or modify unrelated OS state.

Keep pathogens, reporters and interventions synthetic. Do not introduce network scanning/exchange, propagation, stealth/evasion, exploitation, credential access, quarantine/remediation or autonomous real-world actions. The reasoning layer must not generate or execute real system actions.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
