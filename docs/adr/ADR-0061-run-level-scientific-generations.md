# ADR-0061 — Governed Runs Publish One Committed Generation

- **Status:** Accepted
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** ADR-0050, ADR-0051, ADR-0053, research programme A4, `src/symbiont_lab/experiments/generations.py`
- **Scope:** How the governed scientific launcher makes a finished run visible. No study, protocol, organism or checkpoint format changes.

## Context

Research programme A4 requires that scientific state made of several files
becomes visible as one committed generation: after a crash a consumer must find
either the previous state or the complete new one, never a mixture.

A transactional `GenerationStore` already exists with crash-boundary tests, but
nothing used it. The governed launcher (`agentctl run start`) wrote a run's
outputs into a `work/` directory while the study ran and a separate
`execution.json` receipt afterwards. A consumer could read outputs of a run whose
receipt was never written, or a receipt beside partially written outputs.

Two integration points were possible:

1. **Per run.** The launcher commits the outputs and the receipt of a finished
   run as one generation.
2. **Per checkpoint inside a run.** Each multi-file save of a running study
   (organism bundle, Body state, model artifacts, telemetry index) becomes a
   generation.

## Decision

1. **Per run.** When the scientific child has run, the launcher commits the
   whole `work/` directory together with the receipt as generation 0 of
   `<run>/generations/`, sealed by a digest-bearing `COMPLETE` marker and made
   visible by atomically publishing `CURRENT`.
2. **The committed generation is the result.** After a successful commit the
   `work/` directory is removed. `open_run_generation(run_root)` is the consumer
   entry point; it verifies the file set and every digest before returning.
3. **A failed commit is a run without a result.** No `CURRENT` exists, the
   receipt at the run root records `COMMIT_FAILED` with the error, the launcher
   returns non-zero, and `work/` is kept for inspection. A crash after `CURRENT`
   was replaced leaves a complete, valid generation, and the run is reported as
   committed.
4. **The receipt at the run root stays** (`<run>/execution.json`) as an index: it
   names the generation and the digest of its `COMPLETE` marker. Runs recorded
   before this decision have no `generations/` directory and are read as before;
   they are not migrated.
5. **A failed or timed-out study is still committed.** The generation records the
   return code. A negative or aborted run is a result and must be as atomic as a
   successful one.
6. **The run lock is released only after the commit.**

## What this does not cover

- **Checkpoints written by a study while it runs** (option 2). A crash in the
  middle of a run can still leave a partially written organism bundle inside
  `work/`; because `work/` is only committed when the child has exited, such a
  state is never *published*, but it is also not protected step by step. That
  integration touches the Physics3D save path, the bundle format and the
  equivalence surface, and is a separate decision.
- **Generations beyond the first.** One run publishes one generation. The store
  supports more; nothing in the launcher produces them.
- **Runs outside the launcher.** Exploratory runs started directly are unaffected.

## Consequences

- A governed run is visible as a complete, verified unit or not at all.
- Outputs can no longer be read from `work/` after a run; tooling must use the
  generation path named in the receipt.
- Research programme A4 is satisfied for the governed run path and remains open
  for in-run checkpoints.

## Tests

- `tests/unit/lab/experiments/test_scientific_generations.py`: directory commit,
  collision refusal, crash injection at every publication boundary.
- `tests/unit/test_checkout_isolation.py`: the launcher's commit, a crash before
  publication (no visible result, outputs kept), a crash after `CURRENT` is
  replaced (complete generation), and an end-to-end launcher run that ends with
  a committed generation.
