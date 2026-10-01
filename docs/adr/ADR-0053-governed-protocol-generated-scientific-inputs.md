# ADR-0053 — Govern protocol-generated scientific inputs

- **Status:** Accepted
- **Date:** 2026-10-01
- **Decision owner:** project owner
- **Relates to:** ADR-0050, ADR-0051, ADR-0052, A2 and A8 in `docs/roadmap.md`

## Context

`agentctl run start` currently requires `--snapshot-source` and treats an
archived organism/body state as the only scientific input. That is appropriate
for studies whose initial state is externally materialized. It does not model
protocols that deterministically generate all experimental state from code and a
declared seed.

E8 is such a protocol: it constructs its `Symbiont`, `Body`, `GroundTruth` and
`PopulationGenesisRuntime` inside the study from the seed. It does not consume a
pre-existing organism or body. Reusing another study's snapshot or creating a
dummy snapshot would misstate provenance. E8 therefore cannot currently be
launched through the governed launcher without an inaccurate input declaration.

This is a control-plane contract change. ADR-0051 hardens the existing launcher
but does not authorize a second scientific input mode. This proposal is separate
from both ADR-0051 and the scientific remediation in PR #212; #212 remains
classified SCIENTIFIC and must not absorb `agentctl` or governance changes.

## Decision proposal

Model scientific input as an explicit tagged choice, with the minimal supported
variants:

1. **`snapshot`** — an archived starting state containing the required organism
   and body data, with its existing content hashes and source provenance.
2. **`protocol-generated`** — no external starting state is supplied; the pinned
   protocol constructs its initial state as a function of the pinned commit,
   declared effective configuration and seed. No `{input}` scientific artifact
   exists in this mode. The launcher may retain technical run directories for
   isolation and receipts, but they are not protocol inputs and must not be
   exposed or represented as such.

Expose the choice on `agentctl run start` as `--input-mode` and enforce exactly
one valid form:

```text
--input-mode snapshot --snapshot-source <state-dir>
--input-mode protocol-generated
```

`--snapshot-source` is required in snapshot mode and rejected in
protocol-generated mode. Do not add a generic `--no-snapshot` escape hatch or
silently infer the input mode.

For `protocol-generated` runs:

- the mode is valid only when the scientific command declares no external
  starting-state dependency. The launcher does not prove this claim
  automatically; using this mode for a study that reads a checkpoint, subject
  file or other external initial state is provenance fraud, not merely a
  configuration error;
- the receipt and effective configuration use a single structured
  `scientific_input` value, for example
  `{"mode":"protocol-generated","external_state":false}`;
- the effective configuration includes this declaration and does not invent
  organism/body hashes or snapshot provenance;
- the commit, locked environment, execution fingerprint, experiment ID, seed,
  resource limits, worktree isolation, timeout, and verified-child bootstrap
  remain mandatory and unchanged;
- child verification binds the declared input mode as part of the canonical
  effective configuration digest.

For `snapshot` runs, preserve the current behavior and record a structured
`scientific_input` value containing `mode = "snapshot"`, `external_state =
true` and a nested `snapshot` object with existing provenance and hashes, for
example `{"mode":"snapshot","external_state":true,"snapshot":{...}}`.
Use one discriminated `ScientificInput` model for both receipt and effective
configuration so invalid mixed states cannot be constructed. A separate flat
`input_mode` field is optional convenience only; it must not become a second
source of truth.

Add launcher tests demonstrating that protocol-generated mode rejects a
snapshot source, records unambiguous provenance, still verifies the direct child
and fingerprint, and does not weaken or change snapshot-mode behavior.

Add a small E8 runner that accepts exactly one seed and invokes the existing
preregistered study with `steps=300`. Each run therefore yields a one-seed
result with `invariant_rate` equal to `0.0` or `1.0`, not an ambiguous global
rate. Launch the ten preregistered seeds individually with `agentctl run start
--scope confirmation --input-mode protocol-generated`, keeping launcher seed
and study seed identical. Preserve each run receipt and result. Aggregation must
verify exactly the preregistered seed set `101, 127, 149, 173, 211, 257, 307,
353, 401, 457`, with no duplicates or missing results; all receipts must name
the same candidate commit; each `receipt.seed` must equal `result.seed`; and
every result must have `integrity_pass = true` and `replay_deterministic =
true`. Do not change the seed set, horizon, threshold or interpretation rule.

A8 remains open unless all ten governed runs report `invariant_rate = 1.0` and
`replay_deterministic = true`. A failing or incomplete run does not authorize
changing the E8 threshold or selecting a subset of seeds.

## Rationale

Input provenance should describe the actual source of experimental state, not
force every experiment into an archived-state model. An explicit generated
input declaration retains the launcher's identity, environment and resource
guarantees while making the absence of external state auditable. Keeping the
mode narrow avoids turning it into a generic bypass for snapshot validation.
In this mode, the scientific starting state is the deterministic output of the
pinned protocol, declared configuration and seed; an implementation detail of
the launcher is not an input artifact.

## Alternatives considered

- **Reuse an existing snapshot.** Rejected because it belongs to a different
  study and is not consumed by E8; its presence would imply false input
  provenance.
- **Create a dummy E8 snapshot.** Rejected because E8 creates its initial state
  internally and the dummy files would be scientifically irrelevant.
- **Add a generic `--no-snapshot` option.** Rejected because it obscures why no
  state is present and risks bypassing snapshot requirements for studies that
  need materialized inputs.
- **Run E8 directly outside `agentctl`.** Rejected for the acceptance rerun
  because it would omit the governed commit, environment, resource, identity and
  receipt guarantees.
- **Put launcher changes in PR #212 or rely on ADR-0051.** Rejected because
  #212 is a scientific candidate and ADR-0051 does not define
  protocol-generated input provenance.

## Consequences

### Benefits

- The launcher can govern self-contained protocols without fabricated input
  snapshots.
- Receipts distinguish archived external state from protocol-generated state
  in one extensible `scientific_input` structure.
- E8's launcher seed and study seed can be matched one-to-one and audited.
- Existing snapshot-based runs retain their provenance and verification path.

### Costs and limitations

- The launcher and receipt schema gain an additional explicit input mode.
- Protocol-generated mode asserts absence of external starting state; it does
  not prove that assertion automatically or establish that study code is
  scientifically valid. Misdeclaring a study with external starting-state
  dependencies is provenance fraud. Existing host-safety limits still apply.
- Ten governed E8 runs and their evidence aggregation remain required after
  implementation; accepting this ADR alone does not close A8.

## Acceptance criteria

- [x] Project owner explicitly accepts this ADR.
- [x] CLI enforces the mutually exclusive snapshot and protocol-generated
  forms; mode inference and generic snapshot bypasses are absent.
- [x] Both modes record explicit, accurate input provenance in the receipt and
  effective configuration.
- [x] Protocol-generated mode retains child identity/fingerprint verification,
  resource controls, isolation and timeout behavior.
- [x] Tests cover protocol-generated provenance and verification, rejection of
  a supplied snapshot in that mode, and unchanged snapshot behavior.
- [ ] Implement and integrate the control-plane change in a separate PR; do not
  modify PR #212. Merge the launcher change to `main` before starting the E8
  campaign, then pin every governed run to the same reviewed scientific
  candidate commit from #212.
- [x] A single-seed E8 runner uses the preregistered protocol and `steps=300`;
  launcher seed equals the seed consumed by the study.
- [ ] All ten governed E8 results and receipts are preserved and aggregated;
  aggregation verifies the exact preregistered seeds, no duplicates/missing
  results, one common candidate commit, receipt/result seed equality, and
  `integrity_pass` plus replay determinism for each run; A8 closes only if all
  ten per-seed invariant rates are `1.0`.
- [x] Focused and governance/static checks pass; the canonical suite and
  campaign results are reported separately.

## Decision

Accepted by the project owner on 2026-10-01. Acceptance authorizes the separate
implementation PR described above. It does not authorize any change to PR #212,
does not itself launch the E8 campaign, and does not close A8; closure still
requires all ten governed per-seed results and receipts to satisfy the stated
acceptance criteria.
