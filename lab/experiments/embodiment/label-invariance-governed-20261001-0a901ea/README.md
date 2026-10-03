# Governed E8 Confirmation Record

## Purpose

This versioned directory preserves the governed confirmation campaign for
E8 Label Invariance. The preregistered protocol remains in
[`../label-invariance/experiment.toml`](../label-invariance/experiment.toml);
the protocol and runner hashes, pinned candidate, input mode, horizon, and seed
set are recorded in [`manifest.json`](manifest.json).

## Belongs here

Each `seed-N.json` is the one-seed study result and each `receipt-N.json` is its
matching `agentctl run start` execution receipt. [`aggregate.json`](aggregate.json)
contains the validator output for the exact preregistered set. The
[`campaign-report.md`](campaign-report.md) summarizes execution conditions and
the bounded result.

## Does not belong here

Do not place production code, pytest tests, or a changed protocol in this
versioned evidence directory.

## Criterion for creating a file

Files here record reproducible campaign configuration, execution, or results.
This directory is immutable campaign evidence, not a new protocol or a
generalization claim.

## Execution

Reproduction uses the explicit governed command recorded by the protocol and
manifest; this directory is not executed through pytest.

## Limits

The evidence is bounded to the pinned candidate, protocol, and preregistered
seeds. It does not establish generalization beyond them.
