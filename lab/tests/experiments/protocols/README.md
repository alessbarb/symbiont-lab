# Protocols

## Purpose

Schema and validation contracts for declared protocols.

## Belongs here

Deterministic, small tests with explicit fixtures and a verifiable question for this layer.

## Does not belong here

No full campaigns, generated runs, interpreted results, or hidden dependencies on `experiments/`.

## Criterion for creating a file

Create a file only when its question belongs to this layer and cannot be expressed by a smaller test. Runner or protocol contracts belong in `tests/experiments/`; campaign execution belongs in `experiments/`.

## Execution

`pytest tests/experiments/protocols`

## Limits

Passing this layer does not demonstrate scientific validity or generalization.
