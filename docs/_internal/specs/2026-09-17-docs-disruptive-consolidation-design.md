# Design: disruptive docs/ consolidation (phase 2 of the reorg)

Status: proposed, not yet implemented. No files have been moved or changed.

## Context

The prior reorg (`2026-09-17-docs-reorg-web-publication-design.md`) was
purely mechanical: relocate, split, and scaffold, with an explicit
non-goal of "no semantic rewrites." The owner has now asked for a
genuinely disruptive pass: fewer files, real consolidation, not just
tidier paths. This spec covers four consolidations, all inside `docs/`
except where source code must be repaired as a consequence.

## Goals

1. Delete `docs/_internal/` entirely (36 files: 22 plans + 14 specs).
   Non-normative working artifacts with no future reading value; git
   history is the record, not a renamed-in-place directory.
2. Consolidate `docs/design/`'s 12 content files (excluding its own
   `README.md`) into 5 thematic documents, by verbatim concatenation with
   a source-title heading per merged section — not a deep rewrite of
   ~5,071 lines of existing technical content.
3. Consolidate `docs/releases/archive/`'s 139 individual release files
   into one `docs/CHANGELOG.md`, replacing `docs/releases/` entirely.
4. Merge `docs/architecture/entidad-symbiont.md` (488 lines) and
   `docs/artificial-life-model.md` (211 lines) into one
   `docs/architecture.md`, replacing the `docs/architecture/` directory.

## Non-goals

- No rewriting of the technical content being merged — merging is
  concatenation with light connective framing (a title heading and a
  one-line source note per section), preserving the original prose.
  Exception: `docs/design/README.md` and `docs/CHANGELOG.md`'s own
  narrative wrapper text are new prose by necessity (an index and a
  changelog format need original framing) — the underlying per-release
  and per-design content they point to is not rewritten.
- No renumbering of `docs/design/biological-memory-consolidation.md`'s
  internal `§N` section numbers. Seven source/test files cite this
  content by file path + `§N` (e.g. `docs/design/biological-memory-
  consolidation.md §16`). Preserving the number and only repairing the
  file path (mechanical, per the established precedent from phase 1) is
  strictly cheaper and lower-risk than renumbering and rewriting seven
  code comments' section references.
- `docs/adr/` is untouched — ADRs are individually numbered records by
  convention; consolidating them would destroy per-decision traceability
  for no stated benefit.
- `docs/math/`, `docs/methodology/`, `docs/safety/`, `docs/web/`
  (chapter content itself, not its cross-references) are untouched.

## Execution order note (self-reference)

This spec and its implementation plan live inside `docs/_internal/specs/`
and `docs/_internal/plans/` — the very directory item 1 deletes. **Item 1
must execute last**, not first: every other item's task briefs are
extracted from the plan text before dispatch (per the subagent-driven-
development process), so the plan and this spec only need to remain
readable on disk up through the point tasks stop being dispatched from
them. Deleting `docs/_internal/` (spec, plan, and the 34 unrelated legacy
files alike) as the final task is consistent with this design's own
philosophy: git history is the durable record of why this consolidation
happened, not a surviving planning file.

## 1. Delete docs/_internal/ (execute this section LAST — see note above)

```bash
git rm -r docs/_internal/
```

Repair the two references that point into it:
- `docs/README.md` §7 mentions `docs/_internal/` non-normative status in
  the `docs/web/` section — becomes a one-line note that no such directory
  exists in this repo (history lives in git, not a folder), or the
  sentence is removed if it no longer serves a purpose. Executor's
  judgment at implementation time, kept minimal.
- `docs/_internal/README.md` and `docs/web/FUENTES.md`'s "Prohibida:
  `docs/_internal/`" line: since the directory no longer exists, this
  row becomes vacuous. Change it to state instead that only the five
  source types in the taxonomy table are ever valid — the absence of a
  `docs/_internal/`-shaped exclusion is now enforced by the directory's
  nonexistence, not by a rule needing to name it.
- `tests/docs/test_internal_docs_not_authoritative.py` and the `docs/
  _internal` checks inside `tests/docs/test_web_sources_exist.py` /
  `test_portal_index_and_glossary.py`: these tests assert `docs/_internal`
  does NOT exist / is not authoritative. Once the directory is gone,
  `test_internal_dir_exists_and_superpowers_gone`'s first assertion
  (`is_dir()`) starts failing by construction — that whole test file's
  intent (verify the phase-1 relocation) is now moot. Delete
  `tests/docs/test_internal_docs_not_authoritative.py` in this phase, and
  update `test_no_source_resolves_under_internal` in
  `test_web_sources_exist.py` to keep the check (defensive: still refuse
  any future row that resolves under a `docs/_internal` path, even though
  none currently do and the directory doesn't exist) rather than deleting
  it — it costs nothing to keep and guards against reintroduction.

## 2. Consolidate docs/design/ into 5 files

| New file | Absorbs (verbatim, concatenated in this order) |
| --- | --- |
| `docs/design/percepcion-y-embodiment.md` | `diseno-descubrimiento-senales-symbiont.md`, `digital-body-schema-and-emergent-morphology.md`, `recurrent-restoration-contract.md` |
| `docs/design/cognicion-y-plasticidad.md` | `endogenous-plasticity.md`, `biological-memory-consolidation.md`, `canonical-birth-cognition.md` |
| `docs/design/fisiologia-y-reproduccion.md` | `milestone-i-fisiologia-integrada.md`, `reproduction-death-population.md` |
| `docs/design/sociabilidad-y-desarrollo-predictivo.md` | `milestone-k-sociabilidad-emergente.md`, `milestone-j-desarrollo-predictivo.md` |
| `docs/design/futuro-cultural.md` | `cultural-foundation-v1.md`, `private-slm-and-cultural-foundation.md` |

Merge mechanics for each new file: concatenate the absorbed files' full
content in the listed order, each preceded by a `---` separator (except
the first) and its own original `# Title` heading kept exactly as-is (so
each absorbed document remains a self-contained, findable section — do
not demote its `#` to `##` or otherwise renumber its internal headings).
Add one new top-of-file line above the first absorbed document's heading:
`> Consolidated from: <original-filename-1>, <original-filename-2>, ...`
— this is the only new prose per merged file besides the file's own new
top-level filename-derived title, which is not required (the first
absorbed doc's own `# Title` already serves as the visual title).

Rewrite `docs/design/README.md` to index the 5 new files instead of the
12 old ones. This file's content is a navigational index, not technical
prose being preserved — it is normal to rewrite its bullet list, not a
violation of the no-rewrite non-goal.

### Reference repair (docs)

Repoint every link/mention below from the old filename to its new merged
file (mechanical path edit; do not alter surrounding sentence wording
beyond the filename itself, same discipline as phase 1):

| Old reference | New target |
| --- | --- |
| `docs/design/endogenous-plasticity.md` (ORGANISM.md, README.md, docs/glossary.md, docs/history/roadmap-log.md, docs/web/FUENTES.md `kernel-inmutable-design` row) | `docs/design/cognicion-y-plasticidad.md` |
| `docs/design/biological-memory-consolidation.md` (ORGANISM.md, README.md, docs/glossary.md, docs/history/roadmap-log.md) | `docs/design/cognicion-y-plasticidad.md` |
| `docs/design/reproduction-death-population.md` (ORGANISM.md, README.md, docs/history/roadmap-log.md ×2, docs/glossary.md, docs/web/06-reproduccion-y-linaje.md, docs/web/FUENTES.md `reproduction-design` row) | `docs/design/fisiologia-y-reproduccion.md` |
| `docs/design/milestone-k-sociabilidad-emergente.md` (docs/web/07-ecologia-y-sociabilidad.md, docs/web/FUENTES.md `diseno-sociabilidad-k` row) | `docs/design/sociabilidad-y-desarrollo-predictivo.md` |
| `docs/design/milestone-j-desarrollo-predictivo.md` (docs/web/08-desarrollo-predictivo.md, docs/web/FUENTES.md `diseno-predictivo-j` row) | `docs/design/sociabilidad-y-desarrollo-predictivo.md` |
| `docs/design/cultural-foundation-v1.md` (research/STATUS.md) | `docs/design/futuro-cultural.md` |
| `docs/design/private-slm-and-cultural-foundation.md` (research/STATUS.md) | `docs/design/futuro-cultural.md` |

`docs/history/roadmap-log.md` is otherwise a verbatim historical extract
(phase-1 Global Constraint) — repairing these 4 dangling paths is a
mechanical link fix, the same precedent already established for
roadmap-references semantic repair in phase 1, not a content rewrite.

### Reference repair (source code and tests)

Exactly 7 lines, all citing `biological-memory-consolidation.md`'s file
path (section numbers `§10.2`, `§11`, `§16` stay unchanged — only the
path segment changes):

- `src/symbiont/core/weight_stability.py:2`
- `src/symbiont/host/consolidated_baseline.py:2`
- `src/symbiont/host/checkpoint.py:194`
- `src/symbiont/core/selfmodel.py:13`
- `src/symbiont/core/consolidation.py:1`
- `tests/smoke/test_cli.py:166`
- `tests/unit/host/test_checkpoint.py:51`

Each: replace `docs/design/biological-memory-consolidation.md` with
`docs/design/cognicion-y-plasticidad.md`, leave everything else on the
line (including `§N`) untouched.

## 3. Consolidate releases into docs/CHANGELOG.md

Replace `docs/releases/` (139 archived files + `README.md` index) with a
single `docs/CHANGELOG.md`. Structure: reverse-chronological (newest
first, matching the existing archive's version ordering), one `## vX.Y.Z`
heading per release with that release's original file content nested
underneath verbatim (not summarized — the existing `docs/releases/
README.md` already has a one-line summary per version; the changelog
keeps the full original content, since collapsing 139 files' full
technical content into one-liners would be a real content loss, not
mere consolidation).

```bash
git rm -r docs/releases/
```

Then generate `docs/CHANGELOG.md` by concatenating each archived file's
content under its own `## vX.Y.Z` heading, newest version first, with the
file's own original heading demoted one level (its `# vX.Y.Z ...` becomes
part of the `## vX.Y.Z` section, not a duplicate top-level heading).

Repair the one dangling internal cross-reference found in phase 1
(`docs/releases/archive/v0.76.25.md` references another release file by
path) by pointing it at the corresponding `## vX.Y.Z` anchor inside the
new `docs/CHANGELOG.md` instead.

Update `docs/README.md` §1 to reference `docs/CHANGELOG.md` instead of
`docs/releases/README.md`.

## 4. Merge into docs/architecture.md

Concatenate `docs/architecture/entidad-symbiont.md` (488 lines) first,
then `docs/artificial-life-model.md` (211 lines), each keeping its
original `#`-level heading and content verbatim, separated by `---`.
Keep `docs/architecture/README.md`'s epistemological-boundary framing
content by folding it in as the new file's opening section (it is short
and orientational, not competing technical content).

```bash
git rm -r docs/architecture/
git rm docs/artificial-life-model.md
```

Repair references:
- `docs/README.md` §2 and §3 (currently splits architecture and
  artificial-life content into separate portal sections — merge into one
  section pointing at `docs/architecture.md`).
- `docs/web/FUENTES.md`'s taxonomy table `normative` row currently lists
  `docs/architecture/` and `docs/artificial-life-model.md` as separate
  valid-source paths — update to `docs/architecture.md`.
- Any other file found by a repo-wide grep for `docs/architecture/` or
  `artificial-life-model` at execution time (the design-time grep found
  only `docs/README.md` and this spec's own sibling docs referencing
  each other; re-run the grep before executing, per the same discipline
  as phase 1).

## Risks / open items

- This is the highest-line-count merge in the project's docs history
  (~5,071 lines across the 12 design files alone). The verbatim-
  concatenation approach keeps risk to "did every source file's content
  survive intact," which is mechanically verifiable (line-count/content
  diff, same technique phase 1 used to verify the roadmap split byte-
  for-byte).
- `docs/design/README.md` and `docs/CHANGELOG.md`'s wrapper prose are
  the two genuinely-new-prose exceptions to the no-rewrite non-goal —
  reviewers should hold these to normal editorial quality, not to the
  verbatim-preservation bar.
- Deleting `tests/docs/test_internal_docs_not_authoritative.py` shrinks
  phase 1's own test coverage; this is intentional (the test's premise —
  verifying the `_internal` relocation — is invalidated by deleting the
  directory it was relocated to), not a silent regression.
- Open item, not resolved by this spec: once `docs/_internal/` is gone,
  future implementation plans/specs (this project's own SDD workflow)
  have no designated home — the `writing-plans` skill's hardcoded default
  is `docs/superpowers/plans/...`, which this project moved away from in
  phase 1. This spec does not pick a replacement; the next time a plan
  needs to be written, its author decides (a fresh top-level
  `.superpowers/`-style location outside `docs/`, or reviving a
  `docs/_internal/`-shaped directory just for the active plan, deleted
  again on completion) rather than defaulting silently.

## Next step

Use the writing-plans skill to produce an implementation plan, executed
via subagent-driven-development in a fresh worktree, mirroring phase 1's
process: mechanical/verifiable tasks first (deletions, concatenation),
reference repair tasks per consolidation area, then a final whole-branch
review given the source-code-touching blast radius.
