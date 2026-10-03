# Integrated Habitat Runtime v1 — P0 integration audit

## Scope

This audit addresses `P0-INT-001` from the final organism audit. The change is
integration/orchestration only: it connects existing lifecycle, physiology,
learning, Private SLM, culture, grounding, communication and telemetry APIs.
It does not add a cognitive, social, cultural or linguistic capability.

`v0.80.16` remains unchanged and no release is created by this work.

## Canonical architecture

`IntegratedHabitatRuntime` is the canonical bounded habitat entry point in
`symbiont_lab.integration`. It owns population membership, the explicit end-
of-tick boundary, authorized local contact, lifecycle bookkeeping,
checkpoint envelopes and outbound telemetry. Each resident is an independent
`ModeledOrganismRuntime` with its own genome, physiology, experience and
social/model/grounding state. Existing organism-side methods retain decisions
about messages, claims, composites and grounding; the habitat only supplies
the environment, contact opportunities and lifecycle orchestration.

The configured habitat uses a deterministic, lab-only empty host surface so
real-host wall-clock/load observations cannot affect this bounded integration
contract. This is an environment selection, not a new sensor or cognition
feature.

## Lifecycle contract

At a step boundary the runtime ticks the current live residents, removes
residents in the existing terminal physiology state, applies the explicitly
flagged lifecycle smoke fixture when requested, refreshes authorized ordered
pairs, invokes existing autonomous symbol/sequence/cultural entry points, then
increments the single habitat tick and records a bounded summary. Checkpoints
are accepted only at this end-of-tick boundary.

The lifecycle fixture is evaluator-side technical coverage only. It invokes
existing reproductive-pressure/depletion APIs to exercise one birth and one
death in the same canonical path; it is not evidence of emergent reproduction.
The default habitat does not force those events.

Sequence transport capacity is renewed as a bounded per-tick window. Its
observable telemetry remains a separate bounded lifetime ring/history. This
prevents an accidental cumulative transport-counter exhaustion during long
runs without making communication unlimited.

## Findings and fixes

* **P0-INT-001:** resolved at the canonical API/smoke level. A single habitat
  path now contains dynamic population membership, physiology, individual
  learning entry points, Private SLM registries, cultural ledgers, grounding,
  structured communication and population telemetry.
* Deterministic integration IDs and body-schema salts remove identity noise
  from replay while historical UUID allocation remains unchanged.
* Child host lifecycle state is forked with fresh runtime history, preventing
  acquired host-observation state from leaking across clonal birth.
* Checkpoint restoration preserves internal self-model sense identifiers
  instead of silently dropping them.
* The integrated transport window is reset per tick while all configured
  history ceilings remain enforced.

These are integration, determinism or state-isolation corrections; no new
organism policy or capability was introduced.

## Evidence

The integration smoke uses seeds `101`, `127` and `149`. Each run exercises
one bounded birth and death fixture, communication, receiver grounding,
checkpoint restore, continuation replay and telemetry ON/OFF comparison. The
current result artifact records, for every seed:

* `finite_state = true`;
* `bounded = true`;
* `checkpoint_round_trip = true`;
* `replay_equal = true`;
* `observer_equivalent = true`.

The targeted integration battery has ten tests. Additional long-run checks
completed for seed `101` at 1,000 and 10,000 ticks. At 10,000 ticks the
bounded history remained at 256 summaries, telemetry at 2,048 events and the
serialized checkpoint was approximately 1.87 MB. The 10,000-tick observation
is not extrapolated to other seeds.

## Replay and observer equivalence

Replay compares the documented integrated continuation contract: habitat tick,
live/dead identities, bounded summaries, telemetry events and transport
continuation state. It does not claim byte identity for intentionally lossy
descriptive internals of the existing base-organism checkpoint format.

Observer equivalence runs fresh same-seed habitats with telemetry enabled and
disabled and compares the relevant organism/habitat state while excluding the
telemetry stream itself. The result is a measured contract, not an assumption.

## Integration classification

**A — INTEGRATED**, in the declared technical sense: a canonical runtime
executes the existing capabilities together inside one population lifecycle
and has a bounded smoke path covering lifecycle, communication, grounding,
checkpoint and replay.

This classification does not claim that the lifecycle fixture demonstrates
natural population ecology, nor does it close the separate final freeze audit.

## Remaining limitations

* The lifecycle birth/death path is a deterministic evaluator fixture for
  integration coverage, not an autonomous reproduction study.
* The smoke retains per-organism Private SLM registries and gateways, but does
  not inject a training corpus merely to manufacture model records.
* Long-duration evidence in this change includes 1,000 and 10,000 ticks for
  seed `101`; broader ecological replication remains a research concern.
* Interactive browser QA was not executed in this validation environment and
  remains `NOT_RUN`; existing server/rendering tests do not substitute for it.
* No release or tag is created here; `v0.80.16` remains frozen.

## Decision

The P0 integration defect is technically resolved and the canonical runtime
is ready for the final adversarial freeze audit to be rerun. Freeze itself is
not declared by this artifact. Browser QA and the final audit verdict remain
separate gates.
