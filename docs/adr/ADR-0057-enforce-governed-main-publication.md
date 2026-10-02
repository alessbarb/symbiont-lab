# ADR-0057 — Enforce Governed Publication at the Repository Boundary

- **Status:** Accepted
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** ADR-0050, ADR-0051, ADR-0056, docs/governance/publication-policy.toml
- **Implementation decision:** validated-commit boundary, without update restriction or bypass actor

## Context

The repository has a governed publication path:

~~~text
agentctl publish
-> candidate branch
-> CI validation
-> promotion checks
-> fast-forward to main when allowed
~~~

The promotion workflow refuses automatic promotion of SCIENTIFIC,
CONSTITUTIONAL and FROZEN changes and protects the governance control plane.

Before this ADR was implemented, GitHub had no active repository ruleset for
main. An actor with write permission could therefore write an unchecked commit
directly to main.

The project needs a repository-side guarantee that unvalidated commits cannot
enter main, while preserving proportional CI and avoiding a privileged
publication credential broader than necessary.

## Decision

The repository boundary will enforce a **validated-commit policy**, not an
exclusive-publisher policy.

The accepted invariant is:

> A commit may update main only when the repository-required validation checks
> for that exact commit have succeeded.

The repository does **not** require that agentctl be the only technical actor
capable of moving an already-validated commit to main.

agentctl remains the canonical and expected publication path because it also
provides:

- governance classification;
- candidate construction;
- freshness checks;
- control-plane protection;
- automatic promotion restrictions by change class;
- provenance and publication ergonomics.

GitHub rulesets provide the lower-level safety boundary: an unchecked commit
must not enter main.

## Repository ruleset

The accepted ruleset is:

~~~text
name: Protect main governed publication
target: refs/heads/main
enforcement: active
bypass actors: none

restrict deletions: enabled
block force pushes: enabled
require status checks: enabled
restrict updates: disabled
require pull request: disabled
strict/up-to-date policy: disabled
~~~

The ruleset requires one stable aggregate context produced by
`.github/workflows/ci.yml`:

~~~text
governed-ci-gate
~~~

`governed-ci-gate` always materializes. It depends on `validation-plan`, the
always-on quality/governance job, and every conditional validation lane. It
checks the aggregate result of each job id against the plan outputs:

- a lane selected by `validation-plan` must finish `success`;
- an unselected lane may be `skipped` (or `success` if extra validation ran);
- any selected `failure`, `cancelled`, or missing successful result fails the gate;
- matrix jobs are evaluated through their aggregate job result rather than by
  requiring dynamically expanded child contexts.

This avoids a GitHub ruleset deadlock where an unselected matrix job publishes
only a skipped parent context such as `host-portability (${{ matrix.os }})` and
therefore never emits the concrete `macos-latest` / `windows-latest` contexts.

`performance-report (informational)` is intentionally outside the aggregate gate
because it is explicitly non-blocking.

## Why Restrict updates remains disabled

GitHub's `Restrict updates` rule permits updates only from bypass actors.

The repository's current promotion workflow uses the standard GitHub Actions
`GITHUB_TOKEN`. That actor is not exposed as a selectable bypass app in this
repository's ruleset UI.

The alternatives were:

1. introduce a dedicated GitHub App and grant it bypass authority; or
2. keep bypass empty and enforce validation at the commit boundary.

The project owner explicitly selected option 2 on 2026-10-02.

This avoids creating and maintaining a privileged promotion credential solely
to make agentctl technically exclusive.

## Security model

The resulting model is deliberately layered.

### Repository boundary

GitHub enforces:

~~~text
unchecked commit
-> main
-> rejected
~~~

A commit that already satisfied every required check may technically be pushed
to main by a normal actor with write permission, provided the update is also a
permitted fast-forward.

That is an accepted property of this design, not an unacknowledged bypass.

### Governance publication path

The expected path remains:

~~~text
working tree
-> agentctl publish
-> agentctl/** candidate
-> governed CI
-> promotion workflow
-> main
~~~

This path provides stronger governance semantics than the repository ruleset
alone.

A human or agent deliberately publishing a validated SHA directly instead of
using agentctl may satisfy the repository integrity boundary while still
violating the project's normal governance process.

The distinction is:

~~~text
repository integrity
    = no unvalidated commit reaches main

governance process
    = changes are classified, reviewed and promoted through the declared path
~~~

The project does not claim that the ruleset cryptographically makes agentctl the
only possible publisher.

## Required properties

### 1. Unvalidated commits cannot enter main

A commit lacking any required status check must be rejected by the repository
boundary.

### 2. No general bypass credential exists

The ruleset has no bypass actors.

Neither the project owner nor normal agents receive a permanent bypass.

### 3. The existing candidate flow remains usable

ORDINARY work that passes governed candidate validation may still be promoted
without rerunning the same validation after promotion.

The promoted SHA is the same SHA that CI validated.

### 4. Scientific review semantics remain unchanged

SCIENTIFIC, CONSTITUTIONAL and FROZEN changes continue to require their existing
review and decision paths.

Passing repository status checks does not downgrade their governance class or
authorize automatic promotion.

### 5. Stale candidates remain rejected

The promotion workflow continues to require:

~~~text
validated candidate parent == current main
~~~

and exactly one candidate commit ahead of main.

The ruleset's non-fast-forward protection supplies an additional repository-side
barrier against divergent stale updates.

### 6. Control-plane changes do not self-authorize

Changes to:

- workflow enforcement;
- agentctl publication logic;
- classification policy;
- ruleset/protection configuration;
- required check policy;
- trusted publication semantics;

remain CONSTITUTIONAL.

## CI interpretation

A green CI result means the governed validation plan applicable to that commit
passed.

It does not mean that every experiment, slow suite, equivalence scenario or
held-out campaign ran.

Conditional CI jobs remain part of the governed validation graph, but they are
not individually configured as static repository-required contexts. The
validation plan decides which jobs execute for a given change surface, and the
stable `governed-ci-gate` certifies that the selected plan completed successfully.

The ruleset must not convert the informational performance report into a hard
publication gate.

## Relationship to equivalence

Equivalence evidence remains scoped to the scenarios that were actually
available and executed.

A result such as `NOT_ASSESSABLE_SNAPSHOT_SET` is a legitimate statement that
equivalence evidence was unavailable for that scenario. It must not be converted
into PASS or FAIL merely to satisfy the repository boundary.

Repository validation and scientific evidence remain distinct concepts.

## Alternatives considered

### A. Dedicated promotion GitHub App with Restrict updates

Rejected for the current repository.

This would make agentctl promotion technically exclusive, but introduces:

- a privileged installation identity;
- private key or token lifecycle;
- additional secret handling;
- another trusted component;
- operational maintenance solely to enforce publisher identity.

The marginal benefit does not currently justify that complexity because commit
validation is the property the project actually needs at the repository
boundary.

This option may be reconsidered if the repository later has multiple writers,
external collaborators or a materially stronger publisher-isolation threat
model.

### B. Validated-commit boundary without Restrict updates

**Accepted.**

Required checks, deletion protection and non-fast-forward protection are
enforced on main, with no bypass actors.

agentctl remains the canonical publication process but is not claimed to be the
only technically possible publisher of an already-validated SHA.

### Require pull requests for every ordinary change

Rejected.

The project uses a candidate-and-promotion workflow and does not need a PR UI
requirement for ordinary publication.

### Require all CI work on every change

Rejected.

This would defeat proportional validation and recreate unnecessary duplicate
cost.

### Convention-only governance

Rejected.

Without repository-required checks, an entirely unvalidated commit could enter
main.

## Consequences

Positive:

- unvalidated commits are blocked at the repository boundary;
- no privileged bypass identity or dedicated promotion App is required;
- the existing agentctl promotion design remains simple;
- the exact validated SHA can be promoted without duplicate testing;
- direct force-pushes and branch deletion are blocked;
- proportional CI remains intact.

Trade-offs:

- agentctl is the canonical publisher by governance, not by exclusive repository
  capability;
- a writer can technically publish an already-validated fast-forward SHA to
  main;
- repository integrity therefore does not by itself prove that agentctl was used;
- audit/provenance remains responsible for detecting process deviations.

This trade-off is explicitly accepted.

## Acceptance criteria

- [x] main has an active repository ruleset.
- [x] the ruleset targets only `refs/heads/main`.
- [x] the ruleset has no bypass actors.
- [ ] the ruleset requires only the stable `governed-ci-gate` context after this
      workflow change is merged.
- [x] force pushes are blocked.
- [x] branch deletion is blocked.
- [x] the informational performance job is not a required check.
- [x] `Restrict updates` remains disabled by explicit owner decision.
- [ ] an end-to-end test demonstrates that a new unchecked commit cannot update
      main.
- [ ] an end-to-end ORDINARY candidate demonstrates that the validated agentctl
      promotion path still succeeds under the active ruleset.
- [ ] a stale candidate rejection is demonstrated or retained by existing
      automated coverage.

## Decision history

### 2026-10-02 — initial acceptance

The project owner accepted repository-side enforcement for main.

### 2026-10-02 — implementation refinement

After configuring the ruleset and evaluating the available bypass actors, the
project owner explicitly selected the validated-commit model (option B):

- keep the bypass list empty;
- do not enable `Restrict updates`;
- require governed CI checks for main;
- block force pushes and deletion;
- retain agentctl as the canonical governance publication path;
- do not claim that agentctl is the only technically possible publisher.

This refinement supersedes any earlier wording in this ADR that required
exclusive publisher identity.

### 2026-10-02 — stable aggregate required check

PR #239 exposed a GitHub Actions/ruleset mismatch in the first ruleset
configuration. When a conditional matrix job such as host portability was not
selected, GitHub skipped the matrix before expansion and did not publish the
concrete child contexts required by the ruleset. Those contexts remained
permanently Expected even though the governed CI run itself completed
successfully.

The accepted remediation is one always-present `governed-ci-gate` job that
evaluates the aggregate results of the validation-plan lanes. After this
workflow change is merged, the repository ruleset must be manually changed from
the individual dynamic contexts to only `governed-ci-gate`.
