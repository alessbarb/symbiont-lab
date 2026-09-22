# Napkin Runbook

## Execution & Validation
1. **[2026-09-22] Use `python3` explicitly in this workspace.**
   Do instead: run Python checks as `PYTHONPATH=src python3 ...`.
2. **[2026-09-22] Preserve legacy `symbiont.core` imports during package moves.**
   Do instead: add explicit aliases or compatibility wrappers and validate both old and new paths.

## Repository Architecture
1. **[2026-09-22] `symbiont.core` is organized by domain packages.**
   Do instead: place new code under `cognition`, `embodiment`, `foundation`, `host`, `lineage`, `orchestration`, `signals`, or `social`.
