# ADR-0034: Content-Addressed Immutable Scientific Archive

## Status

Accepted

## Context

Computational scientific reproducibility is compromised when study manifests, organism checkpoints, evaluation digests, or benchmark results can be modified in-place, overwritten by successive runs, or silently altered by schema updates. To guarantee tamper-proof reproducibility, scientific artifacts must possess immutable provenance and verifiable content integrity.

## Decision

1. **Content-addressed artifact storage.** All experimental outputs, checkpoint snapshots, and study bundles managed by `symbiont_lab.archive` are identified by content-addressed cryptographic digests (SHA-256):
   - Checkpoint bundles are stored under content-addressed paths (`<checkpoint_id>-<sha256_prefix>`);
   - Run manifests link to the exact starting and ending state hashes (ADR-0009);
   - Digest documents preserve input dataset signatures.
2. **Append-only storage semantics.** The archive layer strictly forbids in-place updates, file overwriting, or file deletions. Once an artifact is finalized, its permissions are locked to read-only.
3. **Immutable study runs.** Re-running an identical experimental configuration generates a new, distinct run directory with its own timestamp and content-addressed manifest. Historical runs are preserved eternally.
4. **Metadata separation.** Human-readable researcher labels and observer-only aliases live strictly in external archive metadata (`metadata.json`), completely decoupled from the organism's portable binary checkpoint.

## Consequences

- Absolute, tamper-evident auditability for all published scientific evidence.
- Any change in environment physics, organism weights, or study parameters yields a distinct, traceable cryptographic identity.
- Prevents accidental loss of baseline replication data during development iterations.

## Introduced in

v0.25.0 / Milestone AR (Archive Architecture).

## Evidence

`src/symbiont_lab/archive/`, `docs/design/observability/symbiont-lab-experience-and-world-architecture-specification-v1.md`, `tests/unit/lab/test_study_archive.py`.
