# ADR-0057 — Enforce Governed Publication at the Repository Boundary

- **Status:** Proposed
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** ADR-0050, ADR-0051, ADR-0056, docs/governance/publication-policy.toml

## Context

The repository currently has a strong governed publication path:

~~~text
agentctl publish
-> candidate branch
-> CI validation
-> promotion checks
-> fast-forward to main when allowed
~~~

The promotion workflow refuses automatic promotion of SCIENTIFIC,
CONSTITUTIONAL and FROZEN changes and protects the governance control plane.

However, GitHub currently reports no branch protection and no repository
ruleset for main. An actor with write permission can therefore write directly
to main and bypass the governed candidate route.

That means the current system guarantees:

> work that uses the governed publication route is checked by that route

but does not technically guarantee:

> every change that reaches main passed the governed route

The distinction matters because the project repeatedly relies on the stronger
statement when discussing scientific integrity.

## Decision proposal

Make repository-side enforcement consistent with the existing publication
model.

At minimum, main must reject ordinary direct writes that bypass the governed
publication mechanism.

The exact GitHub mechanism may be branch protection, repository rulesets, or an
equivalent supported control, provided the resulting behavior satisfies the
acceptance criteria below.

## Required properties

### 1. Main is not an unrestricted write target

Direct pushes to main by normal contributor/agent credentials must not be the
ordinary publication path.

### 2. The existing candidate flow remains usable

ORDINARY work that passes the governed candidate validation may still be
promoted without adding unnecessary duplicate validation.

Repository protection must not force the same test suite to run twice merely
because promotion uses a bot/workflow identity.

### 3. Scientific review semantics remain unchanged

SCIENTIFIC, CONSTITUTIONAL and FROZEN changes must continue to require their
existing review/decision path.

This ADR does not lower or redefine those classifications.

### 4. Promotion authority is narrow

Any workflow or identity allowed to update main despite protection must have only
the authority required to publish a validated candidate.

It must not become a general bypass credential.

### 5. Stale candidates remain rejected

The existing freshness property remains mandatory:

~~~text
validated candidate parent == current main
~~~

If main changes after validation, the candidate must be revalidated against the
new base.

### 6. Control-plane changes do not self-authorize

Changes to:

- workflow enforcement;
- agentctl publication logic;
- classification policy;
- ruleset/protection configuration;
- trusted promotion identities;

remain CONSTITUTIONAL.

A proposed control-plane change must not disable its own review requirement as
part of the same unreviewed publication.

## CI interpretation

Repository enforcement must not redefine a green CI run as universal scientific
evidence.

The current CI system intentionally builds a validation plan from the changed
surface. A successful run means that the applicable governed validation passed.

It does not mean every experiment, slow suite, equivalence scenario or held-out
campaign ran.

Documentation and UI wording should preserve that distinction.

## Relationship to equivalence

Equivalence evidence remains scoped to the scenarios that were actually
available and executed.

A result such as NOT_ASSESSABLE_SNAPSHOT_SET is a legitimate statement that
equivalence evidence was unavailable for that scenario. It must not be converted
into either PASS or FAIL merely to satisfy a repository gate.

Repository protection therefore depends on the governed classifier and required
evidence policy, not on treating equivalence as a universal classifier.

## Alternatives considered

### Keep the current convention-only model

Rejected as the desired end state because it cannot make the project's
strongest publication guarantee true.

### Require all CI jobs on every change

Rejected because it recreates the duplicate/over-validation problem already
addressed by the governed validation plan.

### Require pull requests for every ordinary change

Not required by this ADR. The goal is controlled publication, not a specific UI
workflow. The existing candidate model may remain the normal path if repository
protection can authorize its promotion safely.

## Consequences

Positive:

- the repository boundary matches the documented governance model;
- direct accidental or agent-driven bypass becomes harder;
- "nothing reaches main outside the governed path" can become an enforceable
  technical property within the configured credential model;
- candidate freshness and proportional validation remain usable.

Costs:

- GitHub protection/ruleset configuration becomes part of the trusted control
  plane;
- promotion credentials and permissions require explicit maintenance;
- emergency/manual override procedures, if retained, must be documented and
  auditable.

## Acceptance criteria

- [ ] main has an active repository-side protection/ruleset.
- [ ] normal direct pushes to main are rejected.
- [ ] the validated ORDINARY candidate promotion path still succeeds.
- [ ] a stale validated candidate cannot update main.
- [ ] SCIENTIFIC, CONSTITUTIONAL and FROZEN changes cannot use ordinary
      auto-promotion.
- [ ] governance-control changes retain external review.
- [ ] the chosen configuration does not duplicate the full validation suite
      unnecessarily.
- [ ] tests or an auditable verification procedure demonstrate each property.

## Decision

Pending explicit project-owner acceptance.
