# ADR-0050 — Verified child launch for hermetic scientific execution

- **Status:** Accepted
- **Date:** 2026-10-01
- **Decision owner:** project owner
- **Relates to:** ADR-0046, ADR-0047, ADR-0048, A2 in `docs/roadmap.md`

## Context

Roadmap gate A2 requires scientific runs to record and verify their execution
identity. `ExecutionFingerprint` represents the repository root and commit, dirty
state, Python executable and version, package origins, dependency-lock digest,
effective-configuration digest, experiment identifier and seed.

The governed `agentctl run start` launcher currently pins a worktree and input
snapshot, then starts the supplied command. Pinning the checkout and setting
`PYTHONPATH` do not, by themselves, prove that the process uses the declared
interpreter, source tree or dependency lock. Arbitrary commands also have no
common Python-level mechanism through which to verify that identity before work.

## Proposal

Change the governed launcher as follows:

1. Accept only a direct Python script, `-m` module or `-c` entry point. Resolve
   both the requested executable and `sys.executable` canonically (following
   symlinks) and require them to identify the same interpreter.
2. Require an explicit run seed. Use the run ID as the experiment identifier by
   default, with an optional explicit experiment identifier.
3. Capture the declared `ExecutionFingerprint` from the pinned worktree using the
   selected interpreter. Bind the effective configuration digest to the run
   command, scope and archived input-snapshot identity. Represent command arguments
   as an ordered JSON string array (`argv`), not shell text. Serialize the effective
   configuration as UTF-8 canonical JSON with sorted object keys, compact separators,
   non-ASCII characters preserved and non-finite numbers rejected. Include stable
   snapshot content digests and source commit, not capture timestamps or temporary
   paths.
4. Start the study entry point through a Python bootstrap. Before invoking the
   target, capture the actual fingerprint and compare every field with the
   launcher declaration. Preserve standard `sys.argv`, `sys.path[0]`,
   `__name__ == "__main__"` and exit behavior for script, module and code modes.
   On mismatch, fail closed without executing the target.
5. Record the declared fingerprint in the run execution receipt.

This proposal covers the process directly launched by `agentctl run start`. It
does not claim that arbitrary descendants spawned by a study are verified; any
future requirement to constrain or verify descendant processes needs a separate
design.

## Rationale

The bootstrap centralizes verification instead of relying on each study script to
remember to call a helper. Restricting the entry point to Python gives the launcher
a predictable place to verify identity before study code begins. Comparing the
active interpreter with the requested executable avoids silently substituting a
different runtime. Recording the declaration preserves the evidence used for the
check alongside the run receipt.

## Alternatives considered

- **Keep accepting arbitrary commands and only set `PYTHONPATH`.** Rejected:
  import preference is not verification, and non-Python commands cannot execute
  the fingerprint check.
- **Require each study to call `assert_matches_declared`.** Rejected for the
  governed entry point: a study could omit or delay the check, so enforcement
  would vary by script.
- **Verify all descendant processes in this change.** Deferred: process-tree
  enforcement is a broader platform and lifecycle contract and is not necessary
  to verify the direct governed child.

## Consequences

### Benefits

- The direct scientific child fails before study code if its interpreter, source,
  commit, lock digest or run declaration differs from the pinned expectation.
- Run identity and seed are explicit launcher inputs and are preserved in the
  execution fingerprint.
- Study authors do not need to implement their own entry-point verification.

### Costs and limitations

- Existing launcher invocations must provide `--seed` and a Python entry point.
- Shell, native-binary and arbitrary wrapper entry points are no longer accepted
  by the governed launcher; they need a separately reviewed integration path.
- Child processes spawned by the study are outside this guarantee.
- This verification establishes consistency with the declared pinned execution;
  it is not a security boundary against malicious study code or a compromised
  host.

## Acceptance criteria

- [x] Project owner explicitly accepts this ADR.
- [ ] The launcher rejects non-Python and mismatched-interpreter commands before
      creating or executing a scientific run.
- [ ] The direct child verifies the declaration before running its target and
      refuses a deliberate mismatch.
- [ ] The run receipt contains the full declared fingerprint.
- [ ] Tests cover accepted script/module/code forms, invalid commands, successful
      verification, mismatch rejection and receipt provenance.
- [ ] Roadmap A2 remains partial until launcher-level tests demonstrate the
      contract; it is not closed by the comparison helper alone.

## Decision

Accepted by the project owner on 2026-10-01. Implementation and launcher-level
validation remain outstanding; A2 stays partial until the acceptance criteria are
met.
