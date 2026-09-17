# Disruptive Docs Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `docs/` from ~220 files down to a much smaller set: merge 12 `docs/design/` files into 5 thematic documents, merge 2 architecture documents into 1, merge 139 release notes into a single `docs/CHANGELOG.md`, and delete `docs/_internal/` (36 files) entirely — with every downstream reference (docs, `README.md`, `ORGANISM.md`, `research/STATUS.md`, and 7 source/test file comments) repaired to match.

**Architecture:** Content-preserving concatenation, not rewriting — each merge keeps every absorbed document's original heading and body verbatim, separated by `---`, so risk reduces to "did the content survive," which is mechanically verifiable via diff. Reference repair is mechanical path substitution, following the same discipline established in the prior reorg (`docs/superpowers/` → `docs/_internal/`): change the path, never the surrounding sentence.

**Tech Stack:** Markdown, `git rm`/`git mv` (history preservation where the tool supports it — note: merges are N-files-into-1, so `git log --follow` will not trace through them; this is an accepted, disclosed tradeoff of consolidation, not an oversight), Python 3.11+/pytest for verification tests.

**Spec:** `docs/_internal/specs/2026-09-17-docs-disruptive-consolidation-design.md` — read this first. It has the full reference inventory (which file cites which path) that this plan's tasks work from; where this plan and the spec's inventory ever disagree, re-run the cited grep yourself — the inventory was captured at design time and may have drifted.

## Global Constraints

- No rewriting of the technical content being merged. Merging is
  concatenation with a source-title heading per section — the exceptions
  are `docs/design/README.md` (index, rewritten) and `docs/CHANGELOG.md`
  (new wrapper format around verbatim per-release content).
- `docs/design/biological-memory-consolidation.md`'s internal `§N` section
  numbers are never renumbered. Only its file *path* changes in the 7
  citing source/test files.
- Every reference-repair task ends with a repo-wide grep proving zero
  dangling references to the paths it removed.
- Task "Delete docs/_internal/" (Task 9) executes **last** — it deletes
  this very plan and its spec. Do not reorder it earlier.
- Commit after each task; do not batch multiple tasks into one commit.

---

### Task 1: Merge docs/architecture/ + artificial-life-model.md into docs/architecture.md

**Files:**
- Create: `docs/architecture.md`
- Delete: `docs/architecture/README.md`, `docs/architecture/entidad-symbiont.md`, `docs/artificial-life-model.md`
- Modify: `docs/README.md` (§2 and §3), `docs/web/FUENTES.md` (taxonomy table `normative` row)
- Test: `tests/docs/test_architecture_merge.py`

**Interfaces:**
- Produces: `docs/architecture.md` — later tasks (none in this plan) do not depend on this file's internal structure, only its existence at this path.

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_architecture_merge.py
from __future__ import annotations

from .conftest import REPO_ROOT


def test_architecture_directory_and_old_file_are_gone():
    assert not (REPO_ROOT / "docs" / "architecture").exists()
    assert not (REPO_ROOT / "docs" / "artificial-life-model.md").exists()


def test_merged_architecture_file_contains_all_three_sources_verbatim():
    text = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    # One hard-to-fake line from each absorbed document:
    assert "El repositorio Symbiont Lab está estructurado como un monorepo" in text
    assert "## 1. Marco Epistemológico y Fundamento de Vida Artificial" in text
    assert "## Artificial life, not simulated biology" in text


def test_portal_index_points_at_merged_file():
    text = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "docs/architecture.md" in text or "architecture.md" in text
    assert "architecture/entidad-symbiont.md" not in text
    assert "artificial-life-model.md" not in text or "docs/architecture.md" in text


def test_fuentes_taxonomy_points_at_merged_file():
    text = (REPO_ROOT / "docs" / "web" / "FUENTES.md").read_text(encoding="utf-8")
    assert "docs/architecture.md" in text
    assert "docs/architecture/" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_architecture_merge.py -v`
Expected: FAIL — `docs/architecture.md` does not exist yet.

- [ ] **Step 3: Build the merged file**

```bash
{
  cat docs/architecture/README.md
  echo
  echo "---"
  echo
  cat docs/architecture/entidad-symbiont.md
  echo
  echo "---"
  echo
  cat docs/artificial-life-model.md
} > docs/architecture.md
```

- [ ] **Step 4: Verify no content was lost**

```bash
wc -l docs/architecture/README.md docs/architecture/entidad-symbiont.md docs/artificial-life-model.md docs/architecture.md
```

Expected: `docs/architecture.md`'s line count equals the sum of the three
source files' line counts plus 4 (two `---` separator blocks, each adding
2 lines via the `echo`/`echo "---"`/`echo` pattern above — confirm the
exact arithmetic yourself against the real counts, do not assume).

- [ ] **Step 5: Delete the absorbed files**

```bash
git rm -r docs/architecture/
git rm docs/artificial-life-model.md
```

- [ ] **Step 6: Repair docs/README.md**

Replace current §2 ("Arquitectura del Sistema y la Entidad `symbiont`")
and §3's architecture-related bullets so both point at
`docs/architecture.md` instead of `docs/architecture/README.md` and
`docs/architecture/entidad-symbiont.md`. Merge what were two portal
sections (§2 architecture, part of §3 for artificial-life-model) into one
section referencing the single merged file — keep the rest of §3's
math-compendium content (unrelated to this merge) exactly as it is, only
remove the `artificial-life-model.md` bullet and fold its one-line
description into the new merged §2.

- [ ] **Step 7: Repair docs/web/FUENTES.md**

In the taxonomy table's `normative` row, change:
```
| `normative` | `docs/adr/`, `docs/architecture/`, `docs/design/`, `docs/roadmap.md`, `docs/artificial-life-model.md` | definiciones, fronteras, invariantes |
```
to:
```
| `normative` | `docs/adr/`, `docs/architecture.md`, `docs/design/`, `docs/roadmap.md` | definiciones, fronteras, invariantes |
```

- [ ] **Step 8: Grep for dangling references**

`docs/README.md` links via bare relative paths from inside `docs/`
(`architecture/README.md`, `artificial-life-model.md`, no `docs/` prefix)
— match those forms directly, not a `docs/architecture/`-prefixed pattern
that would miss them:

```bash
grep -rln "architecture/README\.md\|architecture/entidad-symbiont\.md\|artificial-life-model\.md" --include=*.md --include=*.py .
```

Expected: no hits (the merged `docs/architecture.md` filename does not
match any of these three patterns, so a clean result here confirms
nothing still points at the deleted paths).

- [ ] **Step 9: Run test to verify it passes**

Run: `pytest tests/docs/test_architecture_merge.py -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add docs/architecture.md docs/README.md docs/web/FUENTES.md tests/docs/test_architecture_merge.py
git commit -m "docs: merge architecture/ and artificial-life-model.md into docs/architecture.md"
```

---

### Task 2: Consolidate docs/design/ into percepcion-y-embodiment.md

**Files:**
- Create: `docs/design/percepcion-y-embodiment.md`
- Delete: `docs/design/diseno-descubrimiento-senales-symbiont.md`, `docs/design/digital-body-schema-and-emergent-morphology.md`, `docs/design/recurrent-restoration-contract.md`
- Test: `tests/docs/test_design_consolidation.py` (created in this task, extended by Tasks 3-6)

**Interfaces:**
- Produces: the `test_design_consolidation.py` file structure (one test
  function per merged file) that Tasks 3-6 each add their own function to
  — do not overwrite this task's functions, append.

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_design_consolidation.py
from __future__ import annotations

from .conftest import REPO_ROOT

DESIGN = REPO_ROOT / "docs" / "design"


def test_percepcion_y_embodiment_absorbs_three_sources_verbatim():
    assert not (DESIGN / "diseno-descubrimiento-senales-symbiont.md").exists()
    assert not (DESIGN / "digital-body-schema-and-emergent-morphology.md").exists()
    assert not (DESIGN / "recurrent-restoration-contract.md").exists()

    text = (DESIGN / "percepcion-y-embodiment.md").read_text(encoding="utf-8")
    assert "# Diseño técnico: significado emergente de señales en Symbiont" in text
    assert "# Digital Body Schema & Emergent Morphology" in text
    assert "# Contrato de restauración recurrente de Symbiont" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_design_consolidation.py -v`
Expected: FAIL — `percepcion-y-embodiment.md` does not exist.

- [ ] **Step 3: Build the merged file**

```bash
{
  echo "> Consolidated from: diseno-descubrimiento-senales-symbiont.md, digital-body-schema-and-emergent-morphology.md, recurrent-restoration-contract.md"
  echo
  cat docs/design/diseno-descubrimiento-senales-symbiont.md
  echo
  echo "---"
  echo
  cat docs/design/digital-body-schema-and-emergent-morphology.md
  echo
  echo "---"
  echo
  cat docs/design/recurrent-restoration-contract.md
} > docs/design/percepcion-y-embodiment.md
```

- [ ] **Step 4: Verify no content was lost**

```bash
wc -l docs/design/diseno-descubrimiento-senales-symbiont.md docs/design/digital-body-schema-and-emergent-morphology.md docs/design/recurrent-restoration-contract.md docs/design/percepcion-y-embodiment.md
```

Expected: merged file's line count equals the sum of the three sources
plus 6 (the new `> Consolidated from:` line + blank, and two `---`
separator blocks) — confirm the exact arithmetic against the real counts.

- [ ] **Step 5: Delete the absorbed files**

```bash
git rm docs/design/diseno-descubrimiento-senales-symbiont.md docs/design/digital-body-schema-and-emergent-morphology.md docs/design/recurrent-restoration-contract.md
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/docs/test_design_consolidation.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add docs/design/percepcion-y-embodiment.md tests/docs/test_design_consolidation.py
git commit -m "docs: consolidate 3 design docs into percepcion-y-embodiment.md"
```

Note: this task does NOT repair cross-references to the 3 deleted files —
Task 7 handles all `docs/design/` reference repair in one pass, once all
5 new files exist. Do not repair references here.

---

### Task 3: Consolidate docs/design/ into cognicion-y-plasticidad.md

**Files:**
- Create: `docs/design/cognicion-y-plasticidad.md`
- Delete: `docs/design/endogenous-plasticity.md`, `docs/design/biological-memory-consolidation.md`, `docs/design/canonical-birth-cognition.md`
- Modify: `src/symbiont/core/weight_stability.py:2`, `src/symbiont/host/consolidated_baseline.py:2`, `src/symbiont/host/checkpoint.py:194`, `src/symbiont/core/selfmodel.py:13`, `src/symbiont/core/consolidation.py:1`, `tests/smoke/test_cli.py:166`, `tests/unit/host/test_checkpoint.py:51`
- Test: `tests/docs/test_design_consolidation.py` (append), `tests/docs/test_biological_memory_citations.py` (new)

**Interfaces:**
- Consumes: `tests/docs/test_design_consolidation.py` from Task 2 — append a new function, do not replace the file.

- [ ] **Step 1: Write the failing tests**

Append to `tests/docs/test_design_consolidation.py`:

```python
def test_cognicion_y_plasticidad_absorbs_three_sources_verbatim():
    assert not (DESIGN / "endogenous-plasticity.md").exists()
    assert not (DESIGN / "biological-memory-consolidation.md").exists()
    assert not (DESIGN / "canonical-birth-cognition.md").exists()

    text = (DESIGN / "cognicion-y-plasticidad.md").read_text(encoding="utf-8")
    assert "# Symbiont — diseño técnico de plasticidad endógena" in text
    assert "# Biological memory consolidation — v0.59.5 design" in text
    assert "# Canonical birth cognition" in text
```

Create `tests/docs/test_biological_memory_citations.py`:

```python
from __future__ import annotations

from .conftest import REPO_ROOT

CITING_FILES = [
    "src/symbiont/core/weight_stability.py",
    "src/symbiont/host/consolidated_baseline.py",
    "src/symbiont/host/checkpoint.py",
    "src/symbiont/core/selfmodel.py",
    "src/symbiont/core/consolidation.py",
    "tests/smoke/test_cli.py",
    "tests/unit/host/test_checkpoint.py",
]


def test_all_citing_files_point_at_the_merged_design_doc():
    for rel_path in CITING_FILES:
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "docs/design/cognicion-y-plasticidad.md" in text, (
            f"{rel_path} does not cite the merged design doc"
        )
        assert "docs/design/biological-memory-consolidation.md" not in text, (
            f"{rel_path} still cites the old (deleted) design doc path"
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/docs/test_design_consolidation.py tests/docs/test_biological_memory_citations.py -v`
Expected: both FAIL.

- [ ] **Step 3: Build the merged file**

```bash
{
  echo "> Consolidated from: endogenous-plasticity.md, biological-memory-consolidation.md, canonical-birth-cognition.md"
  echo
  cat docs/design/endogenous-plasticity.md
  echo
  echo "---"
  echo
  cat docs/design/biological-memory-consolidation.md
  echo
  echo "---"
  echo
  cat docs/design/canonical-birth-cognition.md
} > docs/design/cognicion-y-plasticidad.md
```

- [ ] **Step 4: Verify no content was lost**

```bash
wc -l docs/design/endogenous-plasticity.md docs/design/biological-memory-consolidation.md docs/design/canonical-birth-cognition.md docs/design/cognicion-y-plasticidad.md
```

Expected: merged total = sum of the three sources + 6, same accounting
pattern as Task 2 Step 4.

- [ ] **Step 5: Delete the absorbed files**

```bash
git rm docs/design/endogenous-plasticity.md docs/design/biological-memory-consolidation.md docs/design/canonical-birth-cognition.md
```

- [ ] **Step 6: Repair the 7 source/test citations**

In each of the 7 files listed in this task's Files section, replace the
exact substring `docs/design/biological-memory-consolidation.md` with
`docs/design/cognicion-y-plasticidad.md`. Do not touch anything else on
those lines (section numbers like `§16`, `§10.2`, `§11` stay exactly as
written — they are still correct because the merge preserved the
absorbed document's internal numbering verbatim).

```bash
for f in src/symbiont/core/weight_stability.py \
         src/symbiont/host/consolidated_baseline.py \
         src/symbiont/host/checkpoint.py \
         src/symbiont/core/selfmodel.py \
         src/symbiont/core/consolidation.py \
         tests/smoke/test_cli.py \
         tests/unit/host/test_checkpoint.py; do
  sed -i 's#docs/design/biological-memory-consolidation\.md#docs/design/cognicion-y-plasticidad.md#g' "$f"
done
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/docs/test_design_consolidation.py tests/docs/test_biological_memory_citations.py -v`
Expected: both PASS.

- [ ] **Step 8: Run the affected source test suites to confirm no behavior changed**

Run: `.venv/bin/pytest -q tests/smoke/test_cli.py tests/unit/host/test_checkpoint.py -v`
Expected: PASS (these tests exercise real behavior; the comment edit must
not have touched any executable line — confirm by re-reading the diff for
each file before running, not just after).

- [ ] **Step 9: Commit**

```bash
git add docs/design/cognicion-y-plasticidad.md tests/docs/test_design_consolidation.py tests/docs/test_biological_memory_citations.py \
        src/symbiont/core/weight_stability.py src/symbiont/host/consolidated_baseline.py src/symbiont/host/checkpoint.py \
        src/symbiont/core/selfmodel.py src/symbiont/core/consolidation.py tests/smoke/test_cli.py tests/unit/host/test_checkpoint.py
git commit -m "docs: consolidate 3 design docs into cognicion-y-plasticidad.md; repair 7 source citations"
```

---

### Task 4: Consolidate docs/design/ into fisiologia-y-reproduccion.md

**Files:**
- Create: `docs/design/fisiologia-y-reproduccion.md`
- Delete: `docs/design/milestone-i-fisiologia-integrada.md`, `docs/design/reproduction-death-population.md`
- Test: `tests/docs/test_design_consolidation.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/docs/test_design_consolidation.py`:

```python
def test_fisiologia_y_reproduccion_absorbs_two_sources_verbatim():
    assert not (DESIGN / "milestone-i-fisiologia-integrada.md").exists()
    assert not (DESIGN / "reproduction-death-population.md").exists()

    text = (DESIGN / "fisiologia-y-reproduccion.md").read_text(encoding="utf-8")
    assert "# Milestone I — Fisiología integrada" in text
    assert "# Reproduction, death and bounded population" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_design_consolidation.py -v`
Expected: FAIL on the new function.

- [ ] **Step 3: Build the merged file**

```bash
{
  echo "> Consolidated from: milestone-i-fisiologia-integrada.md, reproduction-death-population.md"
  echo
  cat docs/design/milestone-i-fisiologia-integrada.md
  echo
  echo "---"
  echo
  cat docs/design/reproduction-death-population.md
} > docs/design/fisiologia-y-reproduccion.md
```

- [ ] **Step 4: Verify no content was lost**

```bash
wc -l docs/design/milestone-i-fisiologia-integrada.md docs/design/reproduction-death-population.md docs/design/fisiologia-y-reproduccion.md
```

Expected: merged total = sum of the two sources + 4 (header line + blank
+ one `---` separator block).

- [ ] **Step 5: Delete the absorbed files**

```bash
git rm docs/design/milestone-i-fisiologia-integrada.md docs/design/reproduction-death-population.md
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/docs/test_design_consolidation.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add docs/design/fisiologia-y-reproduccion.md tests/docs/test_design_consolidation.py
git commit -m "docs: consolidate 2 design docs into fisiologia-y-reproduccion.md"
```

---

### Task 5: Consolidate docs/design/ into sociabilidad-y-desarrollo-predictivo.md

**Files:**
- Create: `docs/design/sociabilidad-y-desarrollo-predictivo.md`
- Delete: `docs/design/milestone-k-sociabilidad-emergente.md`, `docs/design/milestone-j-desarrollo-predictivo.md`
- Test: `tests/docs/test_design_consolidation.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/docs/test_design_consolidation.py`:

```python
def test_sociabilidad_y_desarrollo_predictivo_absorbs_two_sources_verbatim():
    assert not (DESIGN / "milestone-k-sociabilidad-emergente.md").exists()
    assert not (DESIGN / "milestone-j-desarrollo-predictivo.md").exists()

    text = (DESIGN / "sociabilidad-y-desarrollo-predictivo.md").read_text(encoding="utf-8")
    assert "# Milestone K — Sociabilidad emergente" in text
    assert "# Milestone J — Desarrollo predictivo autónomo" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_design_consolidation.py -v`
Expected: FAIL on the new function.

- [ ] **Step 3: Build the merged file**

```bash
{
  echo "> Consolidated from: milestone-k-sociabilidad-emergente.md, milestone-j-desarrollo-predictivo.md"
  echo
  cat docs/design/milestone-k-sociabilidad-emergente.md
  echo
  echo "---"
  echo
  cat docs/design/milestone-j-desarrollo-predictivo.md
} > docs/design/sociabilidad-y-desarrollo-predictivo.md
```

- [ ] **Step 4: Verify no content was lost**

```bash
wc -l docs/design/milestone-k-sociabilidad-emergente.md docs/design/milestone-j-desarrollo-predictivo.md docs/design/sociabilidad-y-desarrollo-predictivo.md
```

Expected: merged total = sum of the two sources + 4.

- [ ] **Step 5: Delete the absorbed files**

```bash
git rm docs/design/milestone-k-sociabilidad-emergente.md docs/design/milestone-j-desarrollo-predictivo.md
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/docs/test_design_consolidation.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add docs/design/sociabilidad-y-desarrollo-predictivo.md tests/docs/test_design_consolidation.py
git commit -m "docs: consolidate 2 design docs into sociabilidad-y-desarrollo-predictivo.md"
```

---

### Task 6: Consolidate docs/design/ into futuro-cultural.md

**Files:**
- Create: `docs/design/futuro-cultural.md`
- Delete: `docs/design/cultural-foundation-v1.md`, `docs/design/private-slm-and-cultural-foundation.md`, `docs/design/cumulative-culture-v1.md`
- Modify: `research/STATUS.md`
- Test: `tests/docs/test_design_consolidation.py` (append)

**Note:** `docs/design/cumulative-culture-v1.md` (80 lines) landed on `main`
after this plan's spec was written (concurrent work, already merged). It
is thematically cultural and belongs in this same group — this task
absorbs 3 source files, not the 2 the spec's inventory originally listed.
Before starting, re-run `ls docs/design/*.md` yourself to confirm this is
still the full and only drift from the spec's inventory.

- [ ] **Step 1: Write the failing test**

Append to `tests/docs/test_design_consolidation.py`:

```python
def test_futuro_cultural_absorbs_three_sources_verbatim():
    assert not (DESIGN / "cultural-foundation-v1.md").exists()
    assert not (DESIGN / "private-slm-and-cultural-foundation.md").exists()
    assert not (DESIGN / "cumulative-culture-v1.md").exists()

    text = (DESIGN / "futuro-cultural.md").read_text(encoding="utf-8")
    assert "# Cultural Foundation v1" in text
    assert "# Private SLM & Cultural Foundation" in text
    assert "# Cumulative Culture v1" in text


def test_research_status_points_at_merged_file():
    text = (REPO_ROOT / "research" / "STATUS.md").read_text(encoding="utf-8")
    assert "docs/design/futuro-cultural.md" in text
    assert "cultural-foundation-v1.md" not in text
    assert "private-slm-and-cultural-foundation.md" not in text
    assert "cumulative-culture-v1.md" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_design_consolidation.py -v`
Expected: FAIL on both new functions.

- [ ] **Step 3: Build the merged file**

```bash
{
  echo "> Consolidated from: cultural-foundation-v1.md, private-slm-and-cultural-foundation.md, cumulative-culture-v1.md"
  echo
  cat docs/design/cultural-foundation-v1.md
  echo
  echo "---"
  echo
  cat docs/design/private-slm-and-cultural-foundation.md
  echo
  echo "---"
  echo
  cat docs/design/cumulative-culture-v1.md
} > docs/design/futuro-cultural.md
```

- [ ] **Step 4: Verify no content was lost**

```bash
wc -l docs/design/cultural-foundation-v1.md docs/design/private-slm-and-cultural-foundation.md docs/design/cumulative-culture-v1.md docs/design/futuro-cultural.md
```

Expected: merged total = sum of the three sources + 6.

- [ ] **Step 5: Delete the absorbed files and repair research/STATUS.md**

```bash
git rm docs/design/cultural-foundation-v1.md docs/design/private-slm-and-cultural-foundation.md docs/design/cumulative-culture-v1.md
```

In `research/STATUS.md`, replace all three:
- `../docs/design/private-slm-and-cultural-foundation.md` → `../docs/design/futuro-cultural.md`
- `../docs/design/cultural-foundation-v1.md` → `../docs/design/futuro-cultural.md`
- `../docs/design/cumulative-culture-v1.md` → `../docs/design/futuro-cultural.md`

(relative-path form, since `research/STATUS.md` links via `../docs/...` —
confirm the exact relative prefix used in the live file before editing).

Note: multiple links may now point at the same `futuro-cultural.md` target
from different sentences in `research/STATUS.md` — that is expected and
correct (three formerly-distinct design docs now share one file), not a
duplicate-link defect to clean up.

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/docs/test_design_consolidation.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add docs/design/futuro-cultural.md research/STATUS.md tests/docs/test_design_consolidation.py
git commit -m "docs: consolidate 3 design docs into futuro-cultural.md; repair research/STATUS.md"
```

---

### Task 7: Rewrite docs/design/README.md and repair all remaining docs/design/ references

**Files:**
- Modify: `docs/design/README.md`, `ORGANISM.md`, `README.md`, `docs/glossary.md`, `docs/history/roadmap-log.md`, `docs/web/06-reproduccion-y-linaje.md`, `docs/web/07-ecologia-y-sociabilidad.md`, `docs/web/08-desarrollo-predictivo.md`, `docs/web/FUENTES.md`
- Test: `tests/docs/test_design_reference_repair.py`

**Interfaces:**
- Consumes: all 5 new `docs/design/*.md` files from Tasks 2-6 (must run
  after all five; do not dispatch this task before Tasks 2-6 are complete).

- [ ] **Step 1: Re-run the reference inventory grep yourself**

Match bare filenames, not full paths — `docs/web/06-08` cite the old
files both as `docs/design/X.md` and `../design/X.md` on the same line,
and a full-path pattern would only catch the first form:

```bash
grep -rn "endogenous-plasticity\.md\|biological-memory-consolidation\.md\|reproduction-death-population\.md\|milestone-k-sociabilidad-emergente\.md\|milestone-j-desarrollo-predictivo\.md" --include=*.md --include=*.py .
```

(the old and new filenames share no substring, so this bare-filename
pattern cannot false-positive on the new merged files)

Compare the output against this plan's Files list above. If a hit appears
in a file not listed here, add it to this task's edits before proceeding
— the spec's inventory was captured at design time and may have drifted.

- [ ] **Step 2: Write the failing test**

```python
# tests/docs/test_design_reference_repair.py
from __future__ import annotations

import subprocess

from .conftest import REPO_ROOT

# Bare filenames, not full paths: docs/web/06-08 cite the old files both
# as `docs/design/X.md` (display text) and `../design/X.md` (link target)
# on the same line — a full-path substring check would miss the second
# form. Matching the bare filename catches both.
OLD_PATHS = [
    "endogenous-plasticity.md",
    "biological-memory-consolidation.md",
    "reproduction-death-population.md",
    "milestone-k-sociabilidad-emergente.md",
    "milestone-j-desarrollo-predictivo.md",
    "diseno-descubrimiento-senales-symbiont.md",
    "digital-body-schema-and-emergent-morphology.md",
    "recurrent-restoration-contract.md",
    "canonical-birth-cognition.md",
    "milestone-i-fisiologia-integrada.md",
    "cultural-foundation-v1.md",
    "private-slm-and-cultural-foundation.md",
    "cumulative-culture-v1.md",
]


def test_no_tracked_file_references_an_old_design_path():
    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "*.py", "*.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    hits: list[str] = []
    for rel in tracked:
        if rel == "tests/docs/test_design_reference_repair.py":
            continue
        text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        for old_path in OLD_PATHS:
            if old_path in text:
                hits.append(f"{rel}: {old_path}")
    assert not hits, f"dangling old design/ path references:\n" + "\n".join(hits)


def test_design_readme_indexes_the_five_new_files():
    text = (REPO_ROOT / "docs" / "design" / "README.md").read_text(encoding="utf-8")
    for new_file in (
        "percepcion-y-embodiment.md",
        "cognicion-y-plasticidad.md",
        "fisiologia-y-reproduccion.md",
        "sociabilidad-y-desarrollo-predictivo.md",
        "futuro-cultural.md",
    ):
        assert new_file in text, f"docs/design/README.md missing index entry: {new_file}"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/docs/test_design_reference_repair.py -v`
Expected: FAIL — old paths are still referenced everywhere.

- [ ] **Step 4: Rewrite docs/design/README.md**

Replace its file-by-hito bullet list (currently indexing the 12 old
files) with an index of the 5 new files, keeping the file's existing
opening framing paragraph and its closing note about `../roadmap.md` /
`../../ORGANISM.md` being the canonical implementation-status source
(that framing is still accurate and is not being replaced).

- [ ] **Step 5: Repair every reference using mechanical filename substitution**

`docs/web/06-08` cite the same old file twice per line — once as
backticked display text (`docs/design/X.md`) and once as the actual link
target (`../design/X.md`) — so the substitution must match the **bare
filename**, not a full path with a fixed prefix, or the link-target half
will silently survive. Use the bare filename as both the `MAP` key and
inside each replacement's filename segment:

```bash
declare -A MAP=(
  ["endogenous-plasticity.md"]="cognicion-y-plasticidad.md"
  ["biological-memory-consolidation.md"]="cognicion-y-plasticidad.md"
  ["reproduction-death-population.md"]="fisiologia-y-reproduccion.md"
  ["milestone-k-sociabilidad-emergente.md"]="sociabilidad-y-desarrollo-predictivo.md"
  ["milestone-j-desarrollo-predictivo.md"]="sociabilidad-y-desarrollo-predictivo.md"
)
for old in "${!MAP[@]}"; do
  new="${MAP[$old]}"
  for f in ORGANISM.md README.md docs/glossary.md docs/history/roadmap-log.md \
           docs/web/06-reproduccion-y-linaje.md docs/web/07-ecologia-y-sociabilidad.md \
           docs/web/08-desarrollo-predictivo.md docs/web/FUENTES.md; do
    if grep -q "$old" "$f" 2>/dev/null; then
      sed -i "s#${old}#${new}#g" "$f"
    fi
  done
done
```

Because this matches the bare filename regardless of what precedes it,
it correctly rewrites `docs/design/endogenous-plasticity.md` to
`docs/design/cognicion-y-plasticidad.md` AND `../design/endogenous-
plasticity.md` to `../design/cognicion-y-plasticidad.md` in the same
pass — both halves of `docs/web/06-08`'s doubled citation form. Re-run
Step 1's grep afterward (using the same bare-filename patterns) to
confirm zero remaining hits in any form.

- [ ] **Step 6: Re-run the full grep to confirm zero dangling references**

Same bare-filename pattern as Step 1:

```bash
grep -rn "endogenous-plasticity\.md\|biological-memory-consolidation\.md\|reproduction-death-population\.md\|milestone-k-sociabilidad-emergente\.md\|milestone-j-desarrollo-predictivo\.md" --include=*.md --include=*.py .
```

Expected: no output.

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/docs/test_design_reference_repair.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add docs/design/README.md ORGANISM.md README.md docs/glossary.md docs/history/roadmap-log.md \
        docs/web/06-reproduccion-y-linaje.md docs/web/07-ecologia-y-sociabilidad.md docs/web/08-desarrollo-predictivo.md \
        docs/web/FUENTES.md tests/docs/test_design_reference_repair.py
git commit -m "docs: rewrite design/README.md index and repair all references to the 5 merged files"
```

---

### Task 8: Consolidate docs/releases/ into docs/CHANGELOG.md

**Files:**
- Create: `docs/CHANGELOG.md`
- Delete: `docs/releases/` (README.md + archive/*.md, 140 files)
- Modify: `docs/README.md` (§1)
- Test: `tests/docs/test_changelog_consolidation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_changelog_consolidation.py
from __future__ import annotations

from .conftest import REPO_ROOT


def test_releases_directory_is_gone():
    assert not (REPO_ROOT / "docs" / "releases").exists()


def test_changelog_exists_and_has_every_version_heading():
    changelog = REPO_ROOT / "docs" / "CHANGELOG.md"
    assert changelog.is_file()
    text = changelog.read_text(encoding="utf-8")
    # Spot-check the oldest and newest archived versions, plus one from the
    # middle of the sequence — a real gap would show up in at least one of
    # these three positions.
    for version_heading in ("## v0.76.8", "## v0.79.50", "## v0.80.15"):
        assert version_heading in text, f"CHANGELOG.md missing: {version_heading}"


def test_portal_index_points_at_changelog():
    text = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "docs/CHANGELOG.md" in text or "CHANGELOG.md" in text
    assert "releases/README.md" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_changelog_consolidation.py -v`
Expected: FAIL — `docs/CHANGELOG.md` does not exist.

- [ ] **Step 3: Note the pre-existing broken link in v0.76.25.md**

`docs/releases/archive/v0.76.25.md:14` contains
`[docs/design/milestone-i-sociabilidad-emergente.md](../design/milestone-i-sociabilidad-emergente.md)`
— this is a **pre-existing typo** (should be `milestone-k-`, not
`milestone-i-`; no file by either the typo'd name or the correct original
name exists after Task 7's consolidation regardless). This was already a
dead link before this plan touched anything — not something this
consolidation broke. While concatenating this file's content in Step 4,
opportunistically repair it to point at
`docs/design/sociabilidad-y-desarrollo-predictivo.md` (the file Task 7
renamed the correct `milestone-k-sociabilidad-emergente.md` target into)
— but do not block this task on it, and note it in your task report as a
pre-existing-bug fix, not a consolidation requirement.

- [ ] **Step 4: Build the changelog**

List archived files newest-first (the existing `docs/releases/README.md`
index is already in that order — reuse its ordering rather than
re-deriving one) and concatenate, demoting each file's own top-level
`# vX.Y.Z ...` heading to `## vX.Y.Z ...` so it nests under a running
document instead of competing as a second top-level title:

```bash
{
  echo "# Symbiont Lab Changelog"
  echo
  echo "Consolidated from docs/releases/archive/ (139 individual release notes)."
  echo
  for f in $(ls -v -r docs/releases/archive/*.md); do
    echo "---"
    echo
    sed 's/^# /## /' "$f"
    echo
  done
} > docs/CHANGELOG.md
```

(`ls -v -r` sorts by version number descending, newest first — confirm
against `docs/releases/README.md`'s existing table order before trusting
this; if the natural-sort order disagrees anywhere, e.g. `v0.80.00` vs
`v0.79.99`, fix the generated file's order to match the README's already-
verified table order instead.)

- [ ] **Step 5: Apply the Step 3 fix**

In `docs/CHANGELOG.md`, find the v0.76.25 section and replace
`[docs/design/milestone-i-sociabilidad-emergente.md](../design/milestone-i-sociabilidad-emergente.md)`
with
`[docs/design/sociabilidad-y-desarrollo-predictivo.md](design/sociabilidad-y-desarrollo-predictivo.md)`
(relative path adjusted: from `docs/CHANGELOG.md`, `docs/design/` is
reached via `design/`, not `../design/`).

- [ ] **Step 6: Verify no content was lost**

```bash
wc -l docs/releases/archive/*.md | tail -1
wc -l docs/CHANGELOG.md
```

Expected: `docs/CHANGELOG.md`'s line count is at least the sum shown by
the first command (it will be somewhat higher due to the added `---`
separators, blank lines, and the new title/intro — confirm it is not
*lower*, which would indicate lost content).

- [ ] **Step 7: Delete the releases directory**

```bash
git rm -r docs/releases/
```

- [ ] **Step 8: Repair docs/README.md §1**

Replace the `releases/README.md` reference with `CHANGELOG.md`, keeping
the rest of that bullet's wording accurate to what the changelog now is
(a single consolidated file, not an index of archived files).

- [ ] **Step 9: Run test to verify it passes**

Run: `pytest tests/docs/test_changelog_consolidation.py -v`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add docs/CHANGELOG.md docs/README.md tests/docs/test_changelog_consolidation.py
git commit -m "docs: consolidate 139 release notes into docs/CHANGELOG.md"
```

Note: `tests/docs/test_releases_archive_index.py` (from the prior reorg)
now fails by construction, since it asserts `docs/releases/archive/`
exists. Delete it in this same task — its premise (verifying the archive
+ index structure) is superseded by the changelog:

```bash
git rm tests/docs/test_releases_archive_index.py
```

Fold this `git rm` into this task's Step 10 commit.

---

### Task 9: Delete docs/_internal/ (execute LAST)

**Files:**
- Delete: `docs/_internal/` (36 files, including this plan and its spec)
- Modify: `docs/README.md` (§7's `_internal` mention), `docs/web/FUENTES.md` (the "Prohibida" line and its taxonomy intro), `tests/docs/test_web_sources_exist.py` (keep the defensive check, update its comment)
- Delete: `tests/docs/test_internal_docs_not_authoritative.py`
- Test: `tests/docs/test_internal_is_gone.py`

**Interfaces:**
- Consumes: nothing from earlier tasks in this plan.
- This is the LAST task dispatched. Confirm Tasks 1-8 all show `complete`
  in the ledger before starting this one.

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_internal_is_gone.py
from __future__ import annotations

from .conftest import REPO_ROOT


def test_internal_directory_does_not_exist():
    assert not (REPO_ROOT / "docs" / "_internal").exists()


def test_fuentes_no_longer_names_a_nonexistent_prohibited_directory():
    text = (REPO_ROOT / "docs" / "web" / "FUENTES.md").read_text(encoding="utf-8")
    assert "docs/_internal" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_internal_is_gone.py -v`
Expected: FAIL — `docs/_internal/` still exists.

- [ ] **Step 3: Update docs/web/FUENTES.md**

Replace the line:
```
**Prohibida:** `docs/_internal/` nunca es fuente válida para `docs/web/`.
```
with:
```
Solo los cinco tipos de la tabla anterior son fuente válida — no existe
ningún directorio de trabajo interno del que citar en este repositorio.
```

- [ ] **Step 4: Update tests/docs/test_web_sources_exist.py**

Keep `test_no_source_resolves_under_internal` as a defensive check (it
costs nothing and guards against a `docs/_internal`-shaped path being
reintroduced later), but update its docstring/comment to note the
directory no longer exists at all — the check is now purely preventative,
not verifying an existing exclusion.

- [ ] **Step 5: Update docs/README.md §7**

Remove or rework the sentence naming `docs/_internal/`'s non-normative
status (it no longer exists, so the caveat about it is moot) — keep the
rest of §7's `docs/web/` description intact.

- [ ] **Step 6: Delete the obsolete test**

```bash
git rm tests/docs/test_internal_docs_not_authoritative.py
```

- [ ] **Step 7: Delete docs/_internal/**

```bash
git rm -r docs/_internal/
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/docs/test_internal_is_gone.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add docs/web/FUENTES.md tests/docs/test_web_sources_exist.py docs/README.md tests/docs/test_internal_is_gone.py
git commit -m "docs: delete docs/_internal/ and remove its now-vacuous references"
```

This commit's `git rm -r docs/_internal/` includes this very plan file
and its spec — that is intentional (see the spec's "Execution order note"
section).

---

### Task 10: Full-suite regression and final dangling-reference sweep

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

```bash
.venv/bin/pytest -q
```

Expected: all tests pass. This confirms no consolidation broke an import,
a fixture path, or a reference not caught by the per-task greps above.

- [ ] **Step 2: Final repo-wide sweep for every old path this plan removed**

Design-doc filenames are matched bare (not `docs/design/`-prefixed) since
`docs/web/06-08` cite them via `../design/X.md` relative links too:

```bash
grep -rn "docs/_internal\|docs/releases/archive\|architecture/README\.md\|architecture/entidad-symbiont\.md\|artificial-life-model\.md\|endogenous-plasticity\.md\|biological-memory-consolidation\.md\|reproduction-death-population\.md\|milestone-k-sociabilidad-emergente\.md\|milestone-j-desarrollo-predictivo\.md\|diseno-descubrimiento-senales-symbiont\.md\|digital-body-schema-and-emergent-morphology\.md\|recurrent-restoration-contract\.md\|canonical-birth-cognition\.md\|milestone-i-fisiologia-integrada\.md\|cultural-foundation-v1\.md\|private-slm-and-cultural-foundation\.md\|cumulative-culture-v1\.md" --include=*.md --include=*.py .
```

Expected: no output.

- [ ] **Step 3: Confirm the new docs/ tree shape**

```bash
find docs -maxdepth 2 -type d | sort
ls docs/design/*.md docs/*.md
```

Expected: no `docs/_internal/`, no `docs/architecture/`, no
`docs/releases/`; `docs/design/` has exactly 6 files (5 merged + its own
`README.md`); `docs/CHANGELOG.md` and `docs/architecture.md` exist at the
top level.

- [ ] **Step 4: Commit (only if Steps 1-2 required fixes; otherwise skip)**

```bash
git add -A
git commit -m "docs: fix regressions found in disruptive-consolidation sweep"
```

## Out of scope for this plan

`docs/adr/`, `docs/math/`, `docs/methodology/`, `docs/safety/`, and the
content of `docs/web/`'s 9 chapters are not touched beyond the specific
link repairs named in Task 7. `git log --follow` will not trace merged
design/architecture/release files through their consolidation — this is
a disclosed, accepted tradeoff (per the spec), not something this plan
attempts to preserve.
