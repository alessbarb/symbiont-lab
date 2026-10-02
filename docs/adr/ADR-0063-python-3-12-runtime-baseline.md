# ADR-0063 — Python 3.12 Runtime Baseline and Toolchain Alignment

- **Status:** Accepted
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** `pyproject.toml`, `pyrightconfig.json`, `.github/workflows/ci.yml`, `ADR-0050`, `ADR-0058`

## Context

The repository previously declared `requires-python = ">=3.11"`. In practice, local environments, pinned toolchains, `.python-version`, and standard GitHub Actions CI jobs have standardized on Python 3.12 (specifically Python 3.12.13).

Maintaining Python 3.11 backwards compatibility in package configurations and lockfiles incurred maintenance debt:
- Extra wheel resolutions and marker branches in `uv.lock`.
- Toolchain configuration fragmentation (Ruff targeting `py311`, Pyright targeting `3.11`).
- CI compatibility lanes spending execution cycles testing an obsolete Python 3.11 environment.

## Decision

1. **Minimum Runtime Baseline:** Establish Python 3.12 as the minimum supported Python version (`requires-python = ">=3.12"`).
2. **Toolchain Alignment:**
   - Set Pyright target version to `3.12` in `pyrightconfig.json`.
   - Set Ruff target version to `py312` in `pyproject.toml`.
   - Align dependencies to current versions (`rich>=15`, `ruff>=0.16`, `pyright>=1.1.404`).
3. **CI and Execution Matrix:**
   - Update `.github/workflows/ci.yml` `python-compatibility` matrix to test `['3.12', '3.13']`.
   - Retire Python 3.11 options from workflow dispatch inputs in `.github/workflows/research.yml`.
4. **Documentation & Pilots:** Update developer setup documentation and pilot scripts to state Python 3.12+.

## Consequences

- Python 3.11 is no longer supported or tested.
- `uv.lock` is streamlined, eliminating Python 3.11-specific wheel entries.
- Production and research runtime guarantees match the deployed and tested Python 3.12 execution environment.
