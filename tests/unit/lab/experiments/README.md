# Lab Experiment Software Tests

## Purpose

This directory contains deterministic unit tests for software that prepares,
validates, or records experiment-related lab state. These tests check mechanisms,
not scientific outcomes.

## Belongs here

Small tests of lab experiment domain logic that can run with isolated fixtures and
without launching a campaign or requiring captured scientific evidence.

## Does not belong here

Do not put campaign protocols, generated evidence, long-running studies, or tests
whose purpose is to establish scientific efficacy here. Campaign execution belongs
under `experiments/`; shared runner contracts belong in `tests/experiments/`.

## Criterion for creating a file

Create a test only for a deterministic software contract with a bounded assertion.
If answering the question requires organism runs, seed sweeps, or interpretation,
use the registered experiment workflow instead.

## Execution

Run with `uv run pytest tests/unit/lab/experiments`.

## Limits

Passing tests establish only the tested software behavior. They do not validate a
protocol, reproduce a campaign, or support a scientific claim.
