# Compatibility layer

**There is none.** The owner asked for no legacy and no compatibility shims
while the migration was in progress, so the plan in `INSTRUCTIONS.md` §10
(temporary re-exports from old paths) was not applied.

What was done instead:

- Every importer was rewritten to the new path by
  `migration/tools/move_module.py` and `migration/tools/rewrite_dotted.py`.
  No module forwards an old import path to a new one.
- The 65 pre-existing aliases and facades were retired the same way
  (`migration/alias-map.json`).
- The old layout is recoverable from the source repository
  (`/home/alessbarb/workspace/repos/incubating/symbiont-lab`, untouched) and from
  commit `593c2a02`, which this repository's history contains.

## What keeps old data usable

Persisted formats did not change, so no data shim is needed:

- organism checkpoints (schema 11) written by the old code load in the new code
  with the same state hash, and a re-save is byte-identical to the old code's
  re-save (`migration/tools/identity_check.py`);
- inline genome payloads were converted from schema 1 to schema 2 and verified
  to load to the same genome (same genome hash and genotype hash) before the
  schema-1 migration was removed;
- no persisted format stores a Python module path, so the package renames do
  not affect saved state.

## One ordering dependency kept on purpose

`symbiont/src/symbiont/__init__.py` imports `symbiont.core` after defining
`__version__`. It is not a compatibility shim: it preserves the import order
the organism had before (the removed `symbiont.simulation` import used to
trigger it), which a pre-existing import cycle depends on. See OI-6.

## Consequences of having no shim

- Data written in removed formats no longer loads: organism checkpoints of
  schema 1–10, genomes of schema 1, checkpoints carrying a `HeritableGenome`
  payload, and Physics3D telemetry v3/v4. This includes anything of that age
  under `.symbiont/` in the source repository. Schema-11 checkpoints and v4.1
  telemetry are unaffected.
- External code or notebooks that import `symbiont_lab`, `symbiont_world`,
  `observatory` or the old `symbiont.core.<name>` aliases must be updated.
- Experiment runner scripts inside completed experiments
  (`lab/experiments/world/genesis-v1/run_*.py`, `view_world.py`) still import
  the old names. They were left unmodified as evidence and do not run against
  this tree (OI-9).
