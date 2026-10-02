# Project Roadmap

> **Status:** active project-planning index
> **Scope:** engineering, research operations, documentation, and maintenance
> **Authority:** this file tracks work; it does not establish scientific direction, protocol, evidence, acceptance criteria, or authorization.

## Purpose

This roadmap is the ordinary project-planning view: it helps contributors find
active work, implementation dependencies, and current project status. Updates
to status or sequencing here do not change scientific meaning or authorize
experiments.

The governed scientific programme, including its research sequence, capability
gates, claim vocabulary, and milestone context, is recorded separately in
[`methodology/research-programme.md`](methodology/research-programme.md). That
record is classified as scientific. Experiment-specific protocols,
preregistrations, evidence, and owner decisions remain authoritative in their
respective governed records; this planning index cannot amend them.

## Current project state

The machine-readable status summary is
[`governance/project-state.toml`](governance/project-state.toml). Engineering
milestones, implementation status, and dependencies are maintained in the
relevant workstream baselines and design register. The roadmap may link to those
records but does not replace them.

Completed milestone history is preserved in
[`history/roadmap-log.md`](history/roadmap-log.md). Historical results remain
valid only within the exact scope in which they were obtained.

## Planning rules

- Record workstream status and dependencies here or in the linked machine-readable
  project state; use the appropriate issue, design, or maintainability baseline
  for detailed execution tracking.
- Link to the canonical protocol or decision when a planning item depends on a
  scientific gate. Do not restate or modify that gate here.
- An implementation milestone does not imply scientific validity or acceptance.
- A negative, closed, frozen, paused, or unscheduled programme retains the state
  recorded by its governing artifact; a roadmap edit cannot reopen it.
## Active remediation workstreams

The 2026-10-02 longitudinal audit identified integrity and governance debt that
must be tracked independently from new capability work. The canonical findings
record is
[research/audits/current/2026-10-02-longitudinal-integrity-audit.md](../research/audits/current/2026-10-02-longitudinal-integrity-audit.md).

### LI-1 — Longitudinal integrity

**Status:** OPEN — design proposed.

**Priority:** P0 remediation.

**Governing design:**
[design/core/longitudinal-integrity-v1.md](design/core/longitudinal-integrity-v1.md).

This workstream covers:

- checkpoint lineage authenticity verification;
- strict current-schema restore instead of silent fresh-state substitution;
- complete state-ownership and continuity classification;
- persistence of active social/epistemic state;
- communication replay-guard and sequence continuity;
- restart provenance/reapplication for runtime-only learning controls;
- explicit raw-checkpoint versus portable-bundle semantics;
- cold-restart semantic equivalence with developed cognition;
- re-embodiment continuity with Body authority correctly invalidated;
- bounded treatment of historically contaminated temporal state.

Dependencies and execution order live in the governing design. The roadmap does
not restate its acceptance gate.

### ARCH-1 — Canonical social epistemology ownership

**Status:** OPEN — analysis required before implementation.

**Blocked by / feeds:** LI-1 social persistence repair.

The audit found two organism-side social evidence systems with different
consumers and persistence behavior. The next step is a consumer/ownership matrix
and an explicit decision whether they are:

- one capability that must have one canonical owner;
- intentionally distinct non-overlapping capabilities;
- or active plus legacy/migration-only state.

This work must not be resolved by indefinitely checkpointing two overlapping
sources of truth.

### GOV-1 — Repository-enforced publication to main

**Status:** ACTIVE — repository ruleset configured; end-to-end verification pending.

**Governing decision:**
[adr/ADR-0057-enforce-governed-main-publication.md](adr/ADR-0057-enforce-governed-main-publication.md).

GitHub now enforces a validated-commit boundary on `main`: required governed CI
checks, deletion protection and non-fast-forward protection are active with no
bypass actors. `Restrict updates` remains intentionally disabled under ADR-0057,
so agentctl is the canonical governance publisher rather than the only technically
possible publisher of an already-validated fast-forward SHA. Remaining work is
end-to-end verification of unchecked rejection and ordinary candidate promotion.

### DOC-1 — Persistence terminology and legacy cleanup

**Status:** BLOCKED by LI-1 ownership inventory.

After continuity ownership is proven, documentation and APIs should use
unambiguous terms for:

- runtime checkpoint;
- portable Symbiont bundle;
- Body checkpoint;
- EmbodimentEpisode;
- observer reconstruction.

Code identified as superseded or dead during the audit should be removed only
after consumer searches and tests prove it is no longer authoritative.

## Evidence follow-ups after integrity remediation

These are not opened or authorized experiments by this roadmap. They are
planning reminders for questions already identified by the governed scientific
programme and the longitudinal-integrity design.

After LI-1 closes, the relevant scientific authorities may decide whether to
schedule work on:

- functional transfer advantage after re-embodiment;
- causal behavioral contribution of the private model;
- matched-budget utility of model ancestry;
- causal behavioral contribution of generative cognition.

Mechanical preservation alone must not be presented as positive evidence for
those capabilities.
