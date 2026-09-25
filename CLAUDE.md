# CLAUDE.md

Guidance for coding agents working in Symbiont Lab.

## Scope

Symbiont Lab is a Python 3.11+ research prototype evolving from a synthetic ecology into a benevolent digital organism on a **consenting local host**. Real-host capability is deliberately narrow: local, aggregate, read-only and least-privileged.

The project owner has explicitly approved two further boundaries:

1. **developmental sensing** — Symbiont may discover numeric observation surfaces inside bounded, vetted OS virtual interfaces, assign them opaque identities, characterize them statistically, learn their usefulness and select a bounded sensory repertoire without being handed platform semantics;
2. **transparent residence** — Symbiont may run continuously as an ordinary user process, persist bounded abstract checkpoints, recover after restart and be supervised by an explicitly installed `systemd --user` unit. It may never install itself, conceal itself, resist removal, elevate privileges or modify unrelated system state.

Still unconditionally prohibited: network scanning or autonomous peer discovery, propagation, stealth/evasion, exploitation, credential access, arbitrary filesystem traversal, collection of user content or identifying metadata, quarantine/remediation, autonomous host writes/actions, or reasoning that generates/executes real system actions.

## Real perception invariants

- Consent and resource limits are checked continuously.
- Providers may inspect only vetted aggregate observation surfaces; they never expose paths, usernames, command lines, addresses, file contents or other host identity/user content to cognition.
- Cognition consumes normalized readings/percepts, never OS APIs.
- Platform providers never import cognition.
- Candidate signals begin semantically unknown. Meaning/utility should be learned from behavior where possible rather than encoded in sensor names.
- Candidate discovery is bounded; only learned, selected senses enter routine cognition.
- Raw telemetry is not persisted. Checkpoints contain bounded descriptive/learned state only.
- Failure of one provider cannot stop the organism.
- No threat conclusion is made during initial sensory acclimation.
- Observatory remains passive: organism state may flow outward for display; the display does not control cognition.

Stop for an explicit owner decision before adding a new permission class, identifying/user-content collection, network exchange, unbounded overhead, privilege changes or any new real-world action boundary.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest

symbiont-lab simulate --hosts 100 --steps 300 --seed 7
symbiont-lab organism run --ticks 20
symbiont-lab organism live
python observatory/resident.py --interval 15
symbiont-lab dashboard --port 8765
```

## Test organization, migration, and change policy

The test layout is part of the repository contract. Each relevant test or
protocol directory has a local English `README.md` describing its purpose,
allowed content, exclusions, file-creation criterion, execution command, and
limits. Follow that README before changing the directory. Do not add README
files to `__pycache__`, caches, generated outputs, or temporary directories.

### Current pytest configuration

`pyproject.toml` is intentionally conservative:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not slow'"
markers = [
  "experiment_contract: mechanical contract for an experiment protocol or runner",
  "slow: test intentionally exercises a longer or more expensive path",
]
```

This has three important consequences:

1. pytest discovers only under `tests/`; `experiments/` is not an implicit
   test suite;
2. slow tests are opt-in and must be marked rather than silently removed from
   coverage;
3. a registered marker has no effect unless the relevant tests actually use
   it.

Use these commands according to the question being answered:

```bash
# Fast development feedback
pytest tests/unit tests/docs tests/smoke

# Module integration and experimental safety boundaries
pytest tests/integration tests/experimental_integrity

# Mechanical protocol and runner contracts
pytest tests/experiments

# Historical compatibility and migrations
pytest tests/compatibility

# Complete scientific studies; explicit and not part of routine validation
pytest tests/integration/studies

# Collection and performance diagnostics
pytest --collect-only -q
pytest --durations=50 -q
pytest -m slow
```

Scientific campaigns, populations, longitudinal studies, and evidence
production are launched explicitly through the CLI documented by the relevant
`experiments/` README. They must not be made part of the default pytest loop.

### Placement contract

Use the narrowest applicable location:

| Question | Location |
| --- | --- |
| Does this verify one isolated software unit? | `tests/unit/` |
| Does this verify module interaction? | `tests/integration/` |
| Does this verify a public or package boundary? | `tests/contract/` |
| Does this protect RNG, ground truth, provenance, or safety? | `tests/experimental_integrity/` |
| Does this preserve a fixed historical failure? | `tests/regression/` |
| Is this a short end-to-end health check? | `tests/smoke/` |
| Does this verify a protocol or runner mechanically? | `tests/experiments/` |
| Does this migrate a supported historical artifact? | `tests/compatibility/` |
| Does this execute a campaign or produce evidence? | `experiments/` via CLI |
| Does this interpret or audit results? | `research/` |

`experiments/` is not a second pytest tree. Do not place `test_*.py` there.
`tests/experiments/` tests runner contracts and schema/mechanical behavior; it
does not establish scientific conclusions. Runs must leave identifiable
manifests and results. Research documents preserve interpretation and
traceability rather than becoming fixtures or executable tests.

### Active contracts versus historical compatibility

The active runtime contract is:

- Genome v2;
- competence-based sensorimotor behavior;
- explicit separation between Symbiont, Body, and Embodiment;
- current telemetry schemas and APIs;
- deterministic checkpoint continuation for the causal state of a run.

Do not reintroduce compatibility aliases into active `src/` code merely to
make an old test pass. For example, do not restore `parent_ids`, `loci_values`,
`HeritableGenome`, `initial_concepts`, `primitives`,
`recurrent_primitive_candidates`, or `_babble_cardinality` as active runtime
contracts.

When historical support is required, use a named, isolated migrator such as
the v1-to-v2 Genome migration and cover it in `tests/compatibility/`. A
compatibility test must make clear which artifact version it accepts, which
current representation it produces, and which legacy fields are intentionally
discarded.

### When to modify, move, or delete tests

Modify or move a test when its assumptions describe a deliberately retired
contract. Typical signals are an old schema version, obsolete kernel range,
removed field, old canonical birth identifier, or a prior Body/Embodiment
boundary. Update the fixture to the active API and preserve migration
coverage separately if the old artifact remains supported.

Do not weaken or delete a test for an active invariant. In particular, treat
failures involving persistence, replay determinism, RNG state, identity,
isolation, domain-specific validation, ground-truth separation, or safety
limits as possible `src/` defects. First reduce the failure to a focused
reproduction, compare the continuous and restored trajectories, then repair
the causal state boundary and retain the strict regression assertion.

Delete a test only if it is dead/uncollectable, has no distinct behavior, or
is fully replaced by stronger coverage. Before deleting it, search for unique
historical, safety, or migration coverage and move that coverage to the
correct explicit suite. A failing historical test is not disposable merely
because the active runtime no longer accepts its input.

Tests should use observable behavior rather than private implementation
details. If a private field is currently asserted, replace it with assertions
about the public repertoire, selection, recurrence, learning, result, or
boundary behavior unless the private state itself is the documented contract.
Use a small deterministic fixture and mark campaigns, long replays, 3D
physics, training, populations, and real-server checks with `@pytest.mark.slow`.
Use `@pytest.mark.experiment_contract` for mechanical protocol/runner tests.

### Procedure for changing the suite

1. Read the nearest test/protocol README and inspect the current pytest
   configuration.
2. Run `git status --short --branch`; do not stage unrelated user changes.
3. Classify the failure as stale contract, historical compatibility, test
   organization, or active `src/` behavior.
4. Change the smallest boundary: migrate the fixture/test for removed
   contracts; change `src/` only for a failing active invariant.
5. Add or update a focused regression/compatibility test as appropriate.
6. Run the focused layer, collection, and `git diff --check`. Run duration
   diagnostics before optimizing expensive studies.
7. Run `graphify update .` after code changes.
8. Review the exact staged diff and commit by logical change, not by session.
9. Push the verified logical commits; leave unrelated worktree files
   untouched and report any remaining failures explicitly.

Do not claim a full-suite pass from collection success or from a focused run.
Report collection, focused tests, full-suite/study tests, performance data,
and scientific validation as separate evidence.

## Architecture

Two epistemologically decoupled packages live under `src/`:

- **`symbiont`** — organism/research subject: cognition, host boundary, environment and simulation.
- **`symbiont_lab`** — scientific apparatus: experiments, studies, archive, CLI and evaluation.

`observatory/` is a passive local viewer/adapter. **`symbiont` never imports `symbiont_lab` or Observatory.** Ground truth belongs exclusively to evaluator/apparatus and never feeds back into cognition. Preserve the AST dependency tests enforcing these boundaries.

### Host development

`host/contracts.py` defines permission/capability boundaries. `host/providers/` may discover/sample platform surfaces. `host/adaptive.py` is the semantic-free developmental layer: it sees opaque safe candidates, learns statistical usefulness and chooses which become senses. `core/runtime.py` wires selected senses into cognition. `core/resident.py` supplies a visible foreground lifecycle with periodic atomic checkpointing and clean shutdown.

### Deterministic synthetic research

Synthetic experiments continue to use namespaced RNG streams from `environment/rng.py`; ground truth stays evaluator-side. Existing experimental-integrity and historical regression tests remain authoritative. Real-host features must not perturb synthetic same-seed reproducibility.

### Persistent state

Persistent organism state is allowed only as explicit local abstract memory. Use the checkpoint API and atomic writes; never persist raw sensor histories. The provided systemd unit is an owner-installed user service, not self-installing persistence.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
