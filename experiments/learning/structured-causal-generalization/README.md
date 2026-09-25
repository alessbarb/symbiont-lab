# L7.9 v2 — Structured causal generalization

L7.9 v1 used a low-cardinality periodic motor generator. Whole-vector hashes
repeated often, accidentally turning the legacy action token into an efficient
lookup key. v2 tests the actual failure mode observed in a running Symbiont:
high-cardinality motor combinations whose whole-vector identities are mostly
unseen in future time.

Both arms receive the exact same latent state, requested motor values, delivered
motor values, outcomes, temporal split, seeds, 1M parameter ceiling and 48-step
training ceiling.

**Legacy:** the entire motor vector is hashed into one atomic action identity.

**Structured:** one stable `action.motor.composite` marker plus reusable opaque
per-channel requested/delivered magnitude tokens.

Training and evaluation remain outcome-only.

The study reports held-out loss and baseline gain, plus diagnostics that make
the intended generalization challenge explicit: unique train actions,
unseen-test-action fraction, motor-token OOV fraction, vocabulary size and
resolved parameter count.


## Purpose

This README defines this location's scope within the experiment hierarchy.

## Belongs here

Protocols, configuration, documentation, and identifiable results from reproducible runs.

## Does not belong here

No pytest-collectable tests, production code, or final scientific interpretation.

## Criterion for creating a file

Add only a file that records a reproducible protocol element, an execution, or a result; mechanical contracts belong in `tests/experiments/`.

## Execution

Use the explicit command documented by the protocol or CLI; do not execute this folder through pytest.

## Limits

The contents are evidence bounded by the protocol and do not demonstrate generalization by themselves.
