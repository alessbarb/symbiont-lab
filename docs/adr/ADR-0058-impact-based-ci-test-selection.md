# ADR-0058 — Impact-Based CI Test Selection

- **Status:** Proposed
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** ADR-0050, ADR-0051, ADR-0057, docs/governance/validation-matrix.toml
- **Scope:** CI test selection only; does not redefine scientific evidence or governance class

## Context

The current CI already uses the code delta to decide which validation **lanes**
must run.

`scripts/governance/ci_plan.py` computes:

~~~text
base..head diff
-> changed paths
-> governed change classification
-> validation-matrix sections
-> CI lanes
~~~

This avoids running every major subsystem for every change.

However, once a lane is selected, several jobs still execute broad suites. The
largest example is `software-core`, which currently runs:

~~~text
tests/unit
tests/integration
tests/regression
tests/smoke
~~~

even when the changed surface is narrow.

The result is correct but increasingly expensive. The next optimization target
is therefore not lane selection but **test selection within a selected lane**.

A naive file-name heuristic would be unsafe. Symbiont has cross-cutting
semantics around checkpointing, persistence, re-embodiment, cognition, social
state, governance and experiment control. A local source change can invalidate
tests that do not share its filename or directory.

The design must therefore optimize for:

> run the smallest test set whose relevance can be demonstrated, and widen
> conservatively whenever relevance cannot be demonstrated.

It must never optimize by silently assuming that an unselected test is
irrelevant.

## Decision proposal

Introduce a second planning stage called **impact-based test selection**.

The CI decision pipeline becomes:

~~~text
git diff base..head
        |
        v
governance classification
        |
        v
lane selection
        |
        v
impact analysis inside each selected lane
        |
        +--> directly mapped tests
        +--> dependency/import impact tests
        +--> mandatory sentinels
        +--> explicit semantic guards
        |
        v
selected test set
        |
        +--> confidence sufficient -> targeted execution
        |
        +--> confidence insufficient -> conservative fallback
        |
        v
governed-ci-gate
~~~

The system is allowed to make CI narrower only when it can explain why the
remaining tests are not required for this change.

## Core invariant

The optimization is **monotonic toward safety**.

~~~text
uncertainty increases
    -> test scope stays equal or becomes broader

uncertainty must never
    -> reduce test scope
~~~

Any unresolved import, dynamic discovery path, missing ownership mapping,
unsupported file type, changed test infrastructure, or planner error must widen
coverage.

## Scope

This ADR governs selection of ordinary software tests inside CI.

It does not alter:

- governance classification;
- SCIENTIFIC / CONSTITUTIONAL / FROZEN review semantics;
- equivalence evidence requirements;
- held-out or confirmation experiments;
- the meaning of a successful scientific study;
- release acceptance criteria.

Impact-based CI is software validation, not scientific evidence.

## Inputs

The impact planner consumes only reproducible repository state.

Required inputs:

- base commit;
- head commit;
- changed paths;
- changed Python symbols where statically recoverable;
- import graph at the candidate commit;
- governed validation matrix;
- explicit impact rules;
- test inventory;
- governance classification.

Optional future inputs may include historical coverage, but historical coverage
is not part of v1.

The first version must not depend on opaque external services or mutable
third-party caches to decide whether a test is required.

## Outputs

The planner produces a machine-readable manifest.

Example:

~~~json
{
  "schema_version": 1,
  "base": "<sha>",
  "head": "<sha>",
  "classification": "SCIENTIFIC",
  "changed_paths": [
    "src/symbiont/core/orchestration/resident.py"
  ],
  "selected_lanes": ["software_core", "architecture_integrity"],
  "selection": {
    "software_core": {
      "mode": "targeted",
      "tests": [
        "tests/unit/test_resident.py",
        "tests/unit/test_local_habitat.py",
        "tests/integration/test_resident_*.py"
      ],
      "sentinels": [
        "tests/smoke",
        "tests/regression/test_checkpoint_*.py"
      ],
      "reasons": [
        "direct source-to-test ownership",
        "importer impact",
        "persistence sentinel"
      ]
    }
  },
  "fallbacks": [],
  "confidence": "HIGH"
}
~~~

The manifest is evidence of **what CI chose to validate**, not evidence that a
scientific capability exists.

## Impact model

The selected tests for a lane are the union of four sources.

~~~text
selected_tests =
    direct_ownership
  ∪ dependency_impact
  ∪ mandatory_sentinels
  ∪ semantic_guards
~~~

### 1. Direct ownership

A source surface may declare tests that directly own it.

Examples:

~~~text
src/symbiont/core/orchestration/resident.py
    -> tests/unit/test_resident.py

src/symbiont_lab/physics3d/reembodiment.py
    -> tests/unit/lab/physics3d/test_reembodiment*.py
    -> relevant integration tests
~~~

Ownership mappings must live in versioned repository configuration.

They may use file paths or globs.

The planner must not infer ownership only from filename similarity.

### 2. Dependency/import impact

For Python source changes, build a static import graph:

~~~text
changed module
    -> direct importers
    -> transitive importers up to governed boundary
    -> tests importing any impacted module
~~~

The graph should use AST-level Python imports rather than grep.

The first implementation may conservatively treat unresolved dynamic imports as
a fallback trigger.

Dependency impact must be bounded so that one low-level utility does not
silently select almost the entire repository without explanation. If the
transitive closure crosses a configured breadth threshold, the lane falls back
to its broader suite.

### 3. Mandatory sentinels

Some tests are intentionally broader than the direct delta.

Sentinels exist because certain invariants are too important to trust only to a
dependency graph.

Examples by concern:

- checkpoint / restore;
- portable bundle persistence;
- re-embodiment continuity;
- architecture boundaries;
- runtime contracts;
- CLI smoke;
- governance publication;
- experiment mechanics.

Sentinels are selected by governed surface and classification, not by historical
pass rate.

### 4. Semantic guards

Certain paths or symbols imply additional test families even when imports do not
show the relationship.

Examples:

~~~text
checkpoint / restore / schema / migration
    -> persistence + compatibility tests

reembodiment / body schema / embodiment authority
    -> reembodiment continuity tests

social evidence / epistemic ledger / exchange sequence
    -> social persistence + communication tests

governance / workflow / classifier / publish
    -> governance tests + CI control sentinels
~~~

These guards are explicit configuration. They prevent important semantic
relationships from being hidden behind runtime registration, serialization or
indirect consumers.

## Confidence model

The planner assigns one of three confidence levels per selected lane.

### HIGH

All changed files are understood, dependency analysis completed, ownership is
known where required, and no fallback condition was encountered.

Targeted execution is allowed.

### MEDIUM

The delta is understood but at least one relationship is conservative or
indirect.

Targeted tests are allowed only with an expanded sentinel set.

### LOW

The planner cannot prove that targeted selection is safe.

The lane must use its existing broad suite.

The confidence value is not a probabilistic score and must not be used as a
scientific confidence statement.

## Mandatory fallback conditions

A selected lane must fall back to its broad suite if any of the following are
true:

- the impact planner itself changed;
- `validation-matrix.toml` changed;
- test ownership configuration changed;
- pytest configuration or collection behavior changed;
- `pyproject.toml` or dependency resolution changed in a way that affects the lane;
- a changed source file cannot be mapped to a Python module;
- static import parsing fails;
- a changed module uses unresolved dynamic import/registration relevant to the lane;
- import impact exceeds a configured breadth threshold;
- a test file is deleted or renamed and its ownership cannot be reconstructed;
- the change affects shared test fixtures used by many tests;
- the planner produces an empty test set for a selected behavioral lane;
- the planner detects a repository state it does not understand.

For CONSTITUTIONAL changes, the default remains broader validation unless an
explicit later decision narrows it.

## Test changes

Changes under `tests/**` require special handling.

A changed test must always run itself.

If the changed test owns or exercises a source surface, the planner may also run
the associated implementation sentinels.

Deleting a test cannot be treated as "nothing to run". Test deletion requires
ownership analysis and may widen the lane to prove that coverage is not
accidentally removed.

Changing shared fixtures, conftest files, plugins or collection configuration
must trigger fallback.

## Lane behavior

### software-core

Targeted mode may select:

- directly owned unit tests;
- importer-affected tests;
- relevant integration tests;
- required persistence/runtime sentinels;
- smoke tests.

It should no longer run all unit and integration tests merely because one core
module changed.

### physics3d

Targeted mode may select subsystem-specific physics tests plus required
determinism/equivalence mechanics where applicable.

Scientific equivalence requirements remain governed separately and cannot be
satisfied merely because targeted physics tests pass.

### modeling

Targeted mode may select private-model lifecycle tests, trainer/adaptation tests
and ancestry tests according to impacted modules and semantic guards.

### observatory

Targeted mode may select server/workbench/UI tests by affected package plus
architecture sentinels.

### world

Targeted mode may select only the affected world tests while the world subsystem
remains active.

### governance

Governance/control-plane changes remain deliberately broad in v1.

The planner itself, CI workflow, agentctl, classification and ruleset-related
changes must not self-select a narrow test set that validates only the code they
just changed.

## Classification floor

Governance classification places a lower bound on validation breadth.

### ORDINARY

May use HIGH-confidence targeted execution.

### SCIENTIFIC

May use targeted execution for implementation tests, but must retain:

- architecture integrity when required;
- runtime contracts when required;
- protocol mechanics when required;
- governed equivalence evidence when required by classification;
- any domain-specific scientific sentinel.

Targeted software tests do not reduce scientific review requirements.

### CONSTITUTIONAL

v1 defaults to broad control-plane validation and behavioral sentinels.

No impact planner change may narrow its own validation in the same commit.

### FROZEN

Existing frozen-evidence rules remain authoritative.

Impact selection does not authorize modifying frozen evidence.

## Architecture

Introduce:

~~~text
scripts/governance/test_impact.py
docs/governance/test-impact-policy.toml
tests/governance/test_test_impact.py
~~~

### test_impact.py

Responsibilities:

- load the base/head diff;
- construct changed-module inventory;
- build/import dependency graph;
- resolve direct ownership;
- apply semantic guards;
- add classification sentinels;
- evaluate fallback conditions;
- emit deterministic JSON and GitHub outputs.

It must be a pure planner: it does not execute tests.

### test-impact-policy.toml

Contains only declarative policy:

- ownership mappings;
- semantic guards;
- mandatory sentinels;
- breadth thresholds;
- fallback surfaces;
- lane defaults.

Example:

~~~toml
schema_version = 1

[lane.software_core]
fallback = [
  "tests/unit",
  "tests/integration",
  "tests/regression",
  "tests/smoke",
]

[[ownership]]
source = "src/symbiont/core/orchestration/resident.py"
tests = ["tests/unit/test_resident.py"]

[[semantic_guard]]
paths = ["src/symbiont/**/persistence.py", "src/symbiont/**/checkpoint*.py"]
tests = [
  "tests/contract/**",
  "tests/compatibility/**",
]

[classification.SCIENTIFIC]
sentinels = [
  "tests/experimental_integrity/**",
]
~~~

The exact contents require repository inventory before implementation.

## CI integration

`ci_plan.py` remains responsible for deciding **which lanes exist**.

`test_impact.py` decides **what each selected test lane runs**.

This separation is intentional:

~~~text
ci_plan.py
    -> governance/risk routing

test_impact.py
    -> software test minimization within that routing
~~~

The impact manifest becomes an output/artifact of the validation-plan phase.

A lane receives either:

~~~text
mode=targeted
tests=<explicit paths>
~~~

or:

~~~text
mode=fallback
tests=<existing broad suite>
reason=<fallback cause>
~~~

## governed-ci-gate integration

The stable repository-required check introduced by ADR-0057 remains the final
aggregator.

`governed-ci-gate` must verify that:

- impact planning completed successfully;
- every selected lane ran;
- every selected targeted test set succeeded;
- any requested fallback actually ran the broad suite;
- no required lane silently produced an empty selection;
- informational jobs remain non-blocking.

The gate does not need to know individual test names; it trusts the versioned
planner contract and lane result.

## Full-suite strategy

Targeted CI must not become the only mechanism that ever exercises the full
repository.

The project should preserve a canonical full-suite safety net outside the normal
fast path.

Proposed policy:

~~~text
candidate / PR
    -> impact-based CI

scheduled main validation
    -> canonical-full

release boundary
    -> canonical-full

high-risk explicit fallback
    -> canonical-full or equivalent broad lane
~~~

A scheduled full suite is valuable for detecting mistakes in the impact graph
itself.

A failure found only by scheduled full validation is evidence that impact
selection was incomplete and must result in a new ownership/guard rule or a
broader fallback.

## Historical coverage

Coverage-guided test selection is deferred.

It may later supplement static impact analysis:

~~~text
test -> files executed
~~~

but must not initially replace repository-declared ownership or semantic guards.

Reasons for deferral:

- coverage can miss unexecuted branches;
- historical data can become stale;
- setup/import behavior can distort file relationships;
- mutable CI history is weaker authority than versioned policy.

A future version may use historical coverage to add tests, not silently remove
tests, until its reliability is separately demonstrated.

## Determinism and auditability

For the same:

- base SHA;
- head SHA;
- repository contents;
- policy version;

the planner must emit byte-equivalent normalized selection output.

The manifest records:

- planner version/schema;
- base/head;
- changed paths;
- selected lanes;
- selected tests;
- sentinels;
- reasons;
- confidence;
- fallback reasons.

This makes CI minimization reviewable instead of implicit.

## Performance targets

The optimization should be measured against current lane runtimes.

Initial engineering targets:

- ORDINARY narrow core changes: reduce test execution time materially compared
  with full `software-core`;
- unchanged safety sentinels must not dominate the saved time;
- planner runtime should remain small relative to test execution;
- fallback rate should decrease only as explicit coverage knowledge improves.

No fixed percentage reduction is accepted until baseline data is collected.

## Rollout

### Phase 0 — Observe only

Implement the planner but do not use it to skip tests.

For every CI run:

- compute targeted selection;
- execute current broad suites;
- record what the planner would have selected;
- compare failures with hypothetical selection.

This phase validates the selector without risking false negatives.

### Phase 1 — Target ORDINARY low-risk surfaces

Enable targeted execution for a small set of high-confidence surfaces.

Examples should be chosen from repository inventory, not assumed in advance.

Broad suites remain the fallback.

### Phase 2 — Expand core ownership

Add import-impact and semantic guards for core/runtime surfaces.

Use observed misses from canonical-full to improve policy.

### Phase 3 — SCIENTIFIC implementation tests

Allow targeted software tests for selected SCIENTIFIC changes while preserving
all scientific governance/evidence requirements.

### Phase 4 — Continuous calibration

Scheduled canonical-full runs audit the selector.

Any missed regression creates a policy defect that must be corrected before
further narrowing.

## Acceptance criteria for implementation

Before targeted selection can become a publication gate:

- [ ] every repository source path relevant to targeted lanes is either understood
      or explicitly falls back;
- [ ] planner output is deterministic;
- [ ] planner has unit tests for direct ownership, import impact, semantic guards
      and every fallback condition;
- [ ] test deletion and fixture changes cannot produce an empty false-safe plan;
- [ ] planner/control-plane changes cannot narrow their own validation;
- [ ] observe-only runs demonstrate that hypothetical targeted selection would
      have caught all failures seen by broad CI over the observation window;
- [ ] governed-ci-gate rejects planner failure or empty required selections;
- [ ] canonical-full remains available as a scheduled/release safety net;
- [ ] the policy documents how a missed regression feeds back into ownership or
      fallback rules.

## Alternatives considered

### Run only tests whose filename matches the changed file

Rejected.

This is fast but structurally unsafe for indirect consumers, persistence,
registration and cross-cutting invariants.

### Use only pytest dependency plugins

Not accepted as the sole authority.

A plugin may help implement impact analysis, but governance must remain
versioned and inspectable in the repository.

### Use only historical coverage

Deferred.

It is useful evidence but too dependent on past execution paths to be the v1
authority for removing tests.

### Keep only lane-level optimization

Safe but leaves substantial avoidable CI cost, especially in broad core suites.

### Run the full suite on every change

Strong but inefficient and contrary to the proportional-validation direction
already established by the project.

## Consequences

Positive:

- CI cost becomes proportional to demonstrated impact;
- narrow changes stop paying for unrelated test suites;
- test selection is explicit and auditable;
- unknowns widen coverage instead of silently reducing it;
- the existing lane/governance model is preserved;
- canonical-full becomes a calibration safety net rather than the default path.

Costs:

- ownership and semantic-guard policy require maintenance;
- static dependency analysis cannot understand every runtime relationship;
- the planner becomes part of the CONSTITUTIONAL control plane;
- scheduled full validation remains necessary to audit selector quality;
- implementation should begin with an observation period rather than immediate
  test removal.

## Decision

Proposed for project-owner review.
