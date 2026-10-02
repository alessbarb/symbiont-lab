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

**Status:** OPEN — phases LI-P0 to LI-P6 implemented; awaiting owner review.
The design's acceptance gate is closed by its owner, not by this index.

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
not restate its acceptance gate. Implementation evidence per gate item is
listed in the design's implementation record.

### ARCH-1 — Canonical social epistemology ownership

**Status:** DECIDED — Option A (owner decision, 2026-10-02); implemented with
LI-1.

**Record:**
[design/core/social-epistemology-ownership-v1.md](design/core/social-epistemology-ownership-v1.md).

The audit found two organism-side social evidence systems with different
consumers and persistence behavior. The modeled ledger is now the single
canonical owner in the organism runtime; the core ledger remains only as the
model of the legacy `Agent` simulation. Whether the legacy envelope transport
stays in the runtime is recorded as open in that document.

### GOV-1 — Repository-enforced publication to main

**Status:** ACTIVE — stable aggregate CI gate and main ruleset are deployed;
end-to-end acceptance remains incomplete.

**Governing decision:**
[adr/ADR-0057-enforce-governed-main-publication.md](adr/ADR-0057-enforce-governed-main-publication.md).

GitHub enforces a validated-commit boundary on `main` with deletion and
non-fast-forward protection and no bypass actors. PR #239 exposed that requiring
all dynamic CI contexts individually can deadlock when a conditional matrix is
skipped before expansion. The stable `governed-ci-gate` is now present in CI, and
the active ruleset requires that context. Remaining acceptance work is to verify
that an unchecked update is rejected and that a fresh ORDINARY candidate is
promoted through the governed path. Do not infer either property from the
workflow or ruleset configuration alone.

### DOC-1 — Persistence terminology and legacy cleanup

**Status:** IMPLEMENTED with LI-P6 — terminology recorded in the glossary and
the persistence chapter; superseded code removed after consumer searches.

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

- functional transfer advantage after re-embodiment (unapproved preregistration
  draft:
  [design/experimentation/reembodiment-functional-transfer-v1.md](design/experimentation/reembodiment-functional-transfer-v1.md));
- causal behavioral contribution of the private model (unapproved preregistration draft:
  [design/experimentation/private-model-causal-contribution-v1.md](design/experimentation/private-model-causal-contribution-v1.md));
- matched-budget utility of model ancestry (unapproved preregistration draft:
  [design/experimentation/model-ancestry-matched-budget-v1.md](design/experimentation/model-ancestry-matched-budget-v1.md));
- causal behavioral contribution of generative cognition (unapproved preregistration draft:
  [design/experimentation/generative-cognition-causal-contribution-v1.md](design/experimentation/generative-cognition-causal-contribution-v1.md)).

Mechanical preservation alone must not be presented as positive evidence for
those capabilities.
