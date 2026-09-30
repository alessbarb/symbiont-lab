# Causal Equivalence Suite v1

## Purpose

This versioned suite defines bounded causal-equivalence scenarios for classifying
software changes. It supplies evidence for the registered scenarios, not a universal
classifier or scientific validation of organism capability.

## Belongs here

Immutable suite protocol material, scenario definitions, and real captured reference
snapshots required by the suite.

## Does not belong here

Do not put synthetic reference states, pytest tests, mutable live organism state, or
interpretations that exceed the registered scenarios here. Preserve captured evidence
as versioned artifacts.

## Criterion for creating a file

Add a file only when it is required by this versioned protocol or is a real, provenance-
complete reference snapshot captured through the documented tooling. Do not fabricate
or refresh a snapshot to make a candidate pass.

## Execution

Use `python scripts/agentctl.py equivalence status` for status. Run a scenario only
when the scientific-run registry and resource preflight allow it, using the command
documented below.

## Limits

An absent or non-assessable reference means the required scenario is not assessable;
it is not evidence of equivalence. PASS applies only to the covered scenarios and
semantic surface.

This suite supplies bounded evidence, not a universal classifier.

A sensitive change may be downgraded to ORDINARY only when every scenario required by
its semantic surface returns PASS. FAIL and every NOT_ASSESSABLE result remain
SCIENTIFIC.

## Deterministic training contract

Training scenarios run synchronously on CPU with one Torch compute thread, one interop
thread and deterministic algorithms in strict mode. If that contract cannot be
established, the result is `NOT_ASSESSABLE_NONDETERMINISM`, not FAIL.

Coverage is event-based. A training scenario must observe the configured number of
completed model trainings, and the promotion scenario must observe a real ACTIVE-model
transition. Merely running enough ticks is not sufficient.

## Reference snapshots

Snapshots must be captured from real organism states and are immutable/versioned. Live
organism directories are never reference baselines.

Each archive records the organism id, captured tick, body/embodiment metadata, source
commit and SHA-256 digests for the organism bundle, body state and model tree.

Do not synthesize or refresh a snapshot merely to make a candidate change pass.

Capture a real state with:

```bash
python scripts/agentctl.py snapshot capture \
  --source /path/to/state-dir \
  --destination experiments/equivalence/suite-v1/snapshots/S03-promotion-eligible \
  --body-kind anthropomorphic-v6-vision \
  --scenario promotion-eligible
```

The suite remains `capture-required` until these real state artefacts exist. That is a
deliberate NOT_ASSESSABLE state, not permission to invent fixtures.


## Operational status

Check the suite without running it:

```bash
python scripts/agentctl.py equivalence status
```

Run a current-code reference check only when no long scientific run is active and the
resource preflight passes:

```bash
python scripts/agentctl.py equivalence run --scenario promotion-eligible
```

The runner refuses to compete with a tracked RUNNING campaign. Each scenario declares
peak-memory, disk and CPU requirements; insufficient resources produce NOT_ASSESSABLE
rather than attempting the run.

A real source state may come from an older pinned commit:

```bash
python scripts/agentctl.py snapshot capture \
  --source /path/to/state-dir \
  --source-commit <commit-that-produced-it> \
  --destination experiments/equivalence/suite-v1/snapshots/S01-established-anthropomorphic \
  --scenario established-anthropomorphic
```

Use `snapshot verify --path ...` before accepting any captured reference.


### Inspecting candidate states

A portable `.symbiont` bundle may already contain its private-model artifacts. The
capture tool extracts those real embedded model files automatically when no external
`models/` directory is present.

The physical `body.json` remains mandatory. It must come from the same captured
embodiment; the learned BodySchema inside the organism is not a substitute.

Use:

```bash
python scripts/agentctl.py snapshot inspect --source /path/to/state-dir
```

A candidate with an organism bundle and embedded models but no `body.json` is reported
as non-capturable rather than being reconstructed or guessed.
