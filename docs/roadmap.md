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

**Status:** CLOSED — mechanical longitudinal continuity established within the
documented scope; owner decision, 2026-10-02.

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
listed in the design's implementation record. Closure does not assert
future-state equivalence after restart, retrospective identity verification for
pre-schema-11 checkpoints, useful transfer, adaptive advantage, or scientific
value of retained state. Apparatus-owned embodiment history remains protected by
the portable bundle rather than checkpoint identity.

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

**Status:** CLOSED — owner decision, 2026-10-02.

**Governing decision:**
[adr/ADR-0057-enforce-governed-main-publication.md](adr/ADR-0057-enforce-governed-main-publication.md).

GitHub enforces a validated-commit boundary on `main` with deletion and
non-fast-forward protection and no bypass actors. PR #239 exposed that requiring
all dynamic CI contexts individually can deadlock when a conditional matrix is
skipped before expansion. The stable `governed-ci-gate` is present in CI, and the
active ruleset requires that context. A fresh ORDINARY candidate was promoted
through the governed path in PR #260. The owner has closed GOV-1; this status does
not claim that a direct unchecked update was attempted or rejected.

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

## Current-state audit follow-up workstreams

A second audit on 2026-10-02, taken at `main@2ac4296d` after the longitudinal
remediation, found that the remaining risk is no longer loss of state but more
than one operational definition of what belongs to the organism. Its findings
record is
[research/audits/current/2026-10-02-current-state-architecture-audit.md](../research/audits/current/2026-10-02-current-state-architecture-audit.md),
which also carries the resolution record per finding.

### LC-1 — Lifecycle continuity contract

**Status:** IMPLEMENTED — merged 2026-10-02 (#266). The owner decisions listed
in the record are tracked as issues #273, #274 and #276.

**Record:**
[design/core/lifecycle-continuity-contract-v1.md](design/core/lifecycle-continuity-contract-v1.md).

Covers audit findings F-01, F-04, F-05 and F-06:

- one table of lifecycle operations against the executable continuity registers;
- the reduced seed's transplant semantics declared per attribute, with the
  attributes where it diverges from canonical re-embodiment pinned by a test;
- authorized transforms and an unverified legacy origin carried in the lineage
  of every later save;
- one owner-facing restore path for every runtime layer;
- a whole-lifecycle test per register entry.

Whether the two transplant semantics converge, and whether unverified legacy
checkpoints stop being accepted, are owner decisions and are not made here.

### OBS-1 — Observatory is passive by construction

**Status:** IMPLEMENTED — merged 2026-10-02 (#266, #270).

Covers audit findings F-07 and F-08. The resident and replay launchers moved out
of the `observatory` package into `symbiont_lab.cli`; a test fails if any
`observatory` module constructs, restores or drives an organism. A capture
manifest that cannot be written is reported and fails the launcher's exit code
after the organism has been saved, instead of being swallowed.

The moved launchers select the Observatory CI lane through
`governance/validation-matrix.toml`, and ADR-0018 carries an amendment naming
their new location.

### WORLD-1 — World responsibility map

**Status:** DECIDED — ADR-0060 (2026-10-02) fixes roles, vocabulary and the
placement rule; relocation and retirement are deferred there.

**Record:**
[design/world/world-responsibility-map-v1.md](design/world/world-responsibility-map-v1.md).

Covers audit finding F-09. Every environment family is listed with its owning
layer, role, consumers and state. The map removes nothing. Relocation of the
habitat classes, the status of Physics3D surroundings, retirement of the two
legacy environments and the reserved meaning of "World" are owner decisions. The
World programme stays maintenance-only.

W03 was closed by the owner on 2026-10-02
([w03-closure.md](../research/studies/ecology/w03-closure.md)) and no longer
constrains the legacy population path; that path is now held only by test code
and one viewer script.

## Evidence follow-ups after integrity remediation

These are not opened or authorized experiments by this roadmap. They are
planning reminders for questions already identified by the governed scientific
programme and the longitudinal-integrity design.

LI-1 is closed. The relevant scientific authorities may decide whether to
schedule work on:

- functional transfer advantage after re-embodiment (unapproved preregistration
  draft:
  [design/experimentation/reembodiment-functional-transfer-v1.md](design/experimentation/reembodiment-functional-transfer-v1.md));
- causal behavioral contribution of the private model (unapproved preregistration draft:
  [design/experimentation/private-model-causal-contribution-v1.md](design/experimentation/private-model-causal-contribution-v1.md));
- matched-budget utility of model ancestry (unapproved preregistration draft:
  [design/experimentation/model-ancestry-matched-budget-v1.md](design/experimentation/model-ancestry-matched-budget-v1.md));
- causal behavioral contribution of generative cognition (unapproved preregistration draft:
  [design/experimentation/generative-cognition-causal-contribution-v1.md](design/experimentation/generative-cognition-causal-contribution-v1.md));
- causal contribution of executive outcome evidence (unapproved preregistration draft:
  [design/experimentation/executive-outcome-learning-causal-contribution-v1.md](design/experimentation/executive-outcome-learning-causal-contribution-v1.md)).

The five drafts, their interventions, content controls and common rules are
grouped in
[design/experimentation/advanced-cognition-causal-efficacy-programme-v1.md](design/experimentation/advanced-cognition-causal-efficacy-programme-v1.md).

Mechanical preservation alone must not be presented as positive evidence for
those capabilities.

## Open follow-up issues

Tracked on GitHub; listing them here does not authorize any experiment.

| Issue | Subject | Relates to |
| --- | --- | --- |
| #273 | One enforced longitudinal contract for the reduced seed | LC-1 |
| #274 | Run the re-embodiment functional transfer experiment | Evidence follow-ups |
| #275 | Classify and isolate the legacy `Agent` simulation | ARCH-1, WORLD-1 |
| #276 | Retirement boundary for unverified schema-10 checkpoints | LC-1 |
| #277 | Workbench states for inactive, unavailable and broken telemetry | OBS-1 |
| #278 | Causal-efficacy experiments for advanced cognition | Evidence follow-ups |
| #279 | Cognitive scaling across organism age | Performance |
