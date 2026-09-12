# ADR-0001: Two-Package Architecture Boundary

## Status
Accepted

## Context
As Symbiont Lab evolved, experiment orchestration, studies, statistical digests, visualization, and cognitive modeling were co-located in the same namespace (`symbiont`). This risked accidental information leakage from the lab/evaluator into simulated organisms and bloated runtime imports.

## Decision
Split the repository into two distinct Python packages under `src/`:
1. `symbiont`: Organism cognition, synthetic environment, and simulation engine.
2. `symbiont_lab`: Scientific apparatus, protocols, experiments, studies, archive, CLI, and dashboard.

`symbiont` must never import `symbiont_lab`.

## Consequences
- Strict decoupling allows the subject of study (`symbiont`) to exist independently of research apparatus.
- Import integrity tests guarantee zero upward dependencies.
- Legacy import shims maintain backwards compatibility during transition.

## Introduced in
v0.25.0

## Evidence
`tests/experimental_integrity/test_ground_truth_boundary.py` AST dependency check.
