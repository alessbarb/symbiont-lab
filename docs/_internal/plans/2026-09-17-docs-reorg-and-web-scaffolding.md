# Docs Reorganization + Web Publication Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relocate `docs/releases/`, `docs/superpowers/`, and split `docs/roadmap.md` into active-state vs. historical-log documents (all reference-repaired), then scaffold `docs/web/` (front door + `FUENTES.md` + a verification test) so chapter authoring can start on a green, enforced base.

**Architecture:** Pure file relocation + reference repair for `docs/releases/` and `docs/superpowers/` (mechanical, path-only). A heading-anchored split of `docs/roadmap.md` into `docs/roadmap.md` (kept) and `docs/history/roadmap-log.md` (extracted verbatim), followed by a semantic (not just mechanical) repair pass over every repo-wide reference to `docs/roadmap.md`. Then `docs/web/` scaffolding with an executable traceability contract (`FUENTES.md` + pytest verification), mirroring the existing AST-boundary-test pattern in `tests/experimental_integrity/`.

**Tech Stack:** Markdown, Python 3.11+/pytest for verification tests, git for moves (`git mv` to preserve history).

**Spec:** `docs/_internal/specs/2026-09-17-docs-reorg-web-publication-design.md` (this plan assumes Task 2 has already relocated the spec from `docs/superpowers/specs/` to `docs/_internal/specs/` by the time Task 6+ reference it — read both together).

## Global Constraints

- No semantic rewrites of canonical documentation content anywhere in this plan — only relocation and mechanical/semantic **path/link** repair (spec Non-goals).
- `docs/history/roadmap-log.md` receives extracted roadmap material **verbatim** — no paraphrasing, no summarizing.
- No project-management vocabulary ("Milestone X") is introduced in any new `docs/web/` file created in this plan (only `README.md` and `FUENTES.md` exist yet — no chapter prose in this plan).
- Every relocation task ends with a repo-wide grep proving zero dangling references to the old path.
- Commit after each task; do not batch multiple tasks into one commit.

---

### Task 1: Archive per-patch release notes and add a release index

**Files:**

- Move: `docs/releases/v0.76.8.md` … `docs/releases/v0.80.15.md` (all 65 files) → `docs/releases/archive/`
- Create: `docs/releases/README.md`
- Test: `tests/docs/test_releases_archive_index.py`

**Interfaces:**

- Produces: `docs/releases/README.md` — a table every later task (and `docs/README.md`, Task 5) can link to instead of a pinned single release file.

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_releases_archive_index.py
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_every_archived_release_is_indexed_exactly_once():
    archive_dir = REPO_ROOT / "docs" / "releases" / "archive"
    index_path = REPO_ROOT / "docs" / "releases" / "README.md"
    assert archive_dir.is_dir(), f"Not found: {archive_dir}"
    assert index_path.is_file(), f"Not found: {index_path}"

    archived = {p.name for p in archive_dir.glob("v*.md")}
    assert archived, "expected at least one archived release file"

    index_text = index_path.read_text(encoding="utf-8")
    counts = {name: len(re.findall(re.escape(name), index_text)) for name in archived}

    missing = [name for name, count in counts.items() if count == 0]
    duplicated = [name for name, count in counts.items() if count > 1]

    assert not missing, f"releases missing from README.md index: {sorted(missing)}"
    assert not duplicated, f"releases indexed more than once: {sorted(duplicated)}"


def test_no_loose_release_files_outside_archive():
    releases_dir = REPO_ROOT / "docs" / "releases"
    loose = [p.name for p in releases_dir.glob("v*.md")]
    assert not loose, f"release files must live under archive/, found loose: {loose}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_releases_archive_index.py -v`
Expected: FAIL — `docs/releases/archive` not found (directory doesn't exist yet).

- [ ] **Step 3: Move the release files with git mv**

```bash
mkdir -p docs/releases/archive
git mv docs/releases/v0.76.8.md docs/releases/archive/v0.76.8.md
# repeat for every docs/releases/v*.md file — script it:
for f in docs/releases/v*.md; do
  git mv "$f" "docs/releases/archive/$(basename "$f")"
done
```

- [ ] **Step 4: Create the release index**

Generate `docs/releases/README.md` with one row per archived file, in
version order, one-line summary taken from that release file's own title/
first heading (read each file to write its summary — do not invent
content). Shape:

```markdown
# Release Notes Archive

Per-patch release notes, archived here to keep the canonical documentation
portal focused on current normative state. See `docs/roadmap.md` for the
active development state and `docs/history/roadmap-log.md` for the full
milestone history.

| Version | Summary |
| --- | --- |
| [v0.76.8](archive/v0.76.8.md) | <one-line summary from that file> |
| ... | ... |
| [v0.80.15](archive/v0.80.15.md) | <one-line summary from that file> |
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/docs/test_releases_archive_index.py -v`
Expected: PASS

- [ ] **Step 6: Grep for dangling references to the old flat path**

```bash
grep -rn "docs/releases/v0" --include=*.md --include=*.py . | grep -v "docs/releases/archive/"
```

Expected: no hits outside `docs/releases/archive/` itself (internal
cross-references inside archived files pointing at siblings in the same
`archive/` directory are fine and need no edit since they move together).
If a hit appears elsewhere (e.g. `docs/README.md`), fix it in this task as
a mechanical path edit — do not defer to Task 5.

- [ ] **Step 7: Commit**

```bash
git add docs/releases/ tests/docs/test_releases_archive_index.py
git commit -m "docs: archive per-patch releases and add release index"
```

---

### Task 2: Relocate docs/superpowers/ to docs/_internal/ with reference repair

**Files:**

- Move: `docs/superpowers/` (entire tree, including `plans/`, `specs/`) → `docs/_internal/`
- Modify: `src/symbiont/core/selfmodel.py:107`
- Modify: every `docs/_internal/plans/*.md` file that cross-links `docs/superpowers/specs/...`
- Modify: `docs/README.md` (superpowers listing)
- Create: `docs/_internal/README.md` (if none exists after the move)
- Test: `tests/docs/test_internal_docs_not_authoritative.py`

**Interfaces:**

- Produces: `docs/_internal/README.md` stating its contents are non-normative — Task 8's `FUENTES.md` verification test relies on this directory being excluded from valid evidence sources.

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_internal_docs_not_authoritative.py
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_internal_dir_exists_and_superpowers_gone():
    assert (REPO_ROOT / "docs" / "_internal").is_dir()
    assert not (REPO_ROOT / "docs" / "superpowers").exists()


def test_internal_readme_declares_non_normative():
    readme = REPO_ROOT / "docs" / "_internal" / "README.md"
    assert readme.is_file(), f"Not found: {readme}"
    text = readme.read_text(encoding="utf-8").lower()
    assert "non-normative" in text or "no normativ" in text
    assert "fuentes.md" in text or "docs/web" in text


def test_no_dangling_superpowers_path_references():
    hits: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if path.is_dir():
            continue
        if "/.git/" in str(path) or "__pycache__" in str(path):
            continue
        if path.suffix not in {".py", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "docs/superpowers" in text:
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert not hits, f"dangling docs/superpowers references: {hits}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_internal_docs_not_authoritative.py -v`
Expected: FAIL — `docs/_internal` not found.

- [ ] **Step 3: Move the directory**

```bash
git mv docs/superpowers docs/_internal
```

- [ ] **Step 4: Repair the code comment reference**

In `src/symbiont/core/selfmodel.py:107`, change the path string
`docs/superpowers/specs/2026-09-14-v053-self-model-design.md` to
`docs/_internal/specs/2026-09-14-v053-self-model-design.md`. Do not touch
any other wording in that comment (Global Constraints: no semantic rewrites).

- [ ] **Step 5: Repair cross-links inside docs/_internal/plans/*.md**

Every occurrence of `docs/superpowers/specs/` inside
`docs/_internal/plans/*.md` becomes `docs/_internal/specs/`. This is a
path-only edit:

```bash
grep -rl "docs/superpowers" docs/_internal/plans/*.md | \
  xargs sed -i 's#docs/superpowers/specs/#docs/_internal/specs/#g'
```

- [ ] **Step 6: Repair docs/README.md's listing**

Update `docs/README.md`'s section 6 line that currently reads:

```markdown
- **Planes Históricos:** [`superpowers/plans/`](superpowers/plans/) conserva planes de trabajo anteriores como evidencia de trazabilidad histórica (los campos `pending` reflejan el estado en el instante en que fueron redactados).
```

to point at `_internal/plans/` instead, keeping the rest of the sentence
unchanged (mechanical path edit only).

- [ ] **Step 7: Create or amend docs/_internal/README.md**

If `docs/_internal/README.md` does not already exist after the move (check
first — `docs/superpowers/` may not have had its own README), create it:

```markdown
# Internal Working Artifacts

This directory holds historical implementation plans and specs
(`plans/`, `specs/`) produced while building past releases. They are
**non-normative**: they describe how something was built at a point in
time, not the current state of the system.

Content here must never be cited as evidence in `docs/web/FUENTES.md` —
see that file's source-type taxonomy for the list of valid evidence
sources (`docs/adr/`, `docs/architecture/`, `docs/design/`,
`docs/roadmap.md`, `docs/math/`, `src/`, `research/`, and the test suite).
```

If a README already exists, add this same disclaimer as a new top section
without altering its existing content.

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/docs/test_internal_docs_not_authoritative.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add docs/_internal/ docs/README.md src/symbiont/core/selfmodel.py \
        tests/docs/test_internal_docs_not_authoritative.py
git commit -m "docs: relocate superpowers/ to _internal/ and repair references"
```

---

### Task 3: Split docs/roadmap.md into active state + historical log (verbatim)

**Files:**

- Modify: `docs/roadmap.md`
- Create: `docs/history/roadmap-log.md`
- Test: `tests/docs/test_roadmap_split.py`

**Interfaces:**

- Consumes: nothing from Tasks 1-2.
- Produces: `docs/history/roadmap-log.md` — Task 4 repairs references to point here where semantically appropriate.

The current `docs/roadmap.md` has these level-2 heading line numbers
(confirmed via `grep -n "^## " docs/roadmap.md` before this task starts —
re-run that grep first in case the file has drifted since this plan was
written, and adjust the ranges below accordingly):

```text
12   ## North star
26   ## 2026-09-14 developmental restructures      -> moves to history
72   ## Permanent invariants                        -> stays
94   ## Merge sequence                               -> moves to history
168  ## Milestone A — Safe real perception           -> moves to history
176  ## Milestone B — Adaptive host model             -> moves to history
182  ## Milestone C — Autonomous inquiry...           -> moves to history
190  ## Milestone D — Operational embodiment          -> moves to history
198  ## Milestone E — Developmental embodiment        -> moves to history
214  ## Milestone E2 — Endogenous plasticity          -> moves to history
244  ## Milestone F — Digital physiology              -> moves to history
376  ## Milestone G — Reproduction & heredity         -> moves to history
489  ## Milestone H — Digital ecology                 -> moves to history
565  ## Birth, identity, dormancy and death           -> stays
590  ## Merge policy                                  -> stays
610  ## Decision gates                                -> stays
630  ## Milestone I — ... (implementación parcial)    -> stays
643  ## Milestone J — ... (implementación parcial)    -> stays
657  ## Milestone K — ... (implementación parcial)    -> stays
683  ## Tracking                                      -> moves to history
```

So `docs/roadmap.md` keeps, in this order: lines 1-25 (title, intro, North
star), 72-93 (Permanent invariants), 565-682 (Birth/identity, Merge policy,
Decision gates, Milestones I/J/K), and nothing after line 682.
`docs/history/roadmap-log.md` receives, in this order: lines 26-71
(2026-09-14 narrative), 94-167 (Merge sequence: completed table + short
F/G/H tables), 168-564 (Milestones A through H full prose), and 683-end
(Tracking).

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_roadmap_split.py
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_roadmap_keeps_only_active_state():
    text = (REPO_ROOT / "docs" / "roadmap.md").read_text(encoding="utf-8")
    for must_have in (
        "## North star",
        "## Permanent invariants",
        "## Birth, identity, dormancy and death",
        "## Merge policy",
        "## Decision gates",
        "## Milestone I — Fisiología integrada",
        "## Milestone J — Desarrollo predictivo",
        "## Milestone K — Sociabilidad emergente",
    ):
        assert must_have in text, f"missing from active roadmap.md: {must_have}"
    for must_not_have in (
        "## Milestone A — Safe real perception",
        "## Milestone F — Digital physiology",
        "## Milestone H — Digital ecology",
        "## Tracking",
        "### Completed development",
    ):
        assert must_not_have not in text, f"should have moved out: {must_not_have}"


def test_roadmap_log_has_full_history_verbatim():
    log_path = REPO_ROOT / "docs" / "history" / "roadmap-log.md"
    assert log_path.is_file(), f"Not found: {log_path}"
    text = log_path.read_text(encoding="utf-8")
    for must_have in (
        "## 2026-09-14 developmental restructures",
        "### Completed development",
        "## Milestone A — Safe real perception",
        "## Milestone H — Digital ecology",
        "## Tracking",
        # spot-check a specific, hard-to-fake historical entry survives verbatim:
        "v0.79.26 — K measurement refinement",
    ):
        assert must_have in text, f"missing from roadmap-log.md: {must_have}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_roadmap_split.py -v`
Expected: FAIL — `docs/history/roadmap-log.md` not found, and `roadmap.md`
still contains `## Milestone A`.

- [ ] **Step 3: Extract the historical blocks verbatim**

```bash
mkdir -p docs/history
{
  sed -n '26,71p' docs/roadmap.md
  echo
  sed -n '94,167p' docs/roadmap.md
  echo
  sed -n '168,564p' docs/roadmap.md
  echo
  sed -n '683,$p' docs/roadmap.md
} > /tmp/roadmap-log-body.md
```

Prepend a short, factual header (not a rewrite of the extracted content,
just orientation for the new file) and write `docs/history/roadmap-log.md`:

```markdown
# Symbiont roadmap — historical log

This is the extracted, verbatim historical portion of `docs/roadmap.md`:
completed milestones (A through H), the completed-development merge-sequence
table, and the per-patch tracking log. Active development state (north
star, permanent invariants, active milestones I/J/K, decision gates, merge
policy) remains in `docs/roadmap.md`.

---

<contents of /tmp/roadmap-log-body.md pasted here unchanged>
```

- [ ] **Step 4: Rewrite docs/roadmap.md to keep only the active blocks**

```bash
{
  sed -n '1,25p' docs/roadmap.md
  echo
  sed -n '72,93p' docs/roadmap.md
  echo
  sed -n '565,682p' docs/roadmap.md
} > /tmp/roadmap-active.md
mv /tmp/roadmap-active.md docs/roadmap.md
```

Add one line near the top (after the North star section, before Permanent
invariants) linking to the extracted history:

```markdown
Full milestone history (A-H) and the per-patch tracking log are archived in
[`docs/history/roadmap-log.md`](history/roadmap-log.md).
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/docs/test_roadmap_split.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add docs/roadmap.md docs/history/roadmap-log.md tests/docs/test_roadmap_split.py
git commit -m "docs: split roadmap.md into active state and historical log"
```

---

### Task 4: Semantic repair of every reference to docs/roadmap.md

**Files:**

- Modify: `README.md`, `ORGANISM.md`, `research/README.md`, `docs/README.md`
- Test: `tests/docs/test_roadmap_references_repaired.py`

**Interfaces:**

- Consumes: `docs/history/roadmap-log.md` from Task 3.

Confirmed current references (re-run `grep -rln "docs/roadmap.md" --include=*.md --include=*.py .` before starting, in case new ones appeared) and their classification:

| File:line | Current wording (paraphrased) | Classification | Action |
| --- | --- | --- | --- |
| `research/README.md:5` | "see docs/roadmap.md first" (general orientation pointer) | current-state | leave pointing at `docs/roadmap.md` — no change |
| `ORGANISM.md:9` | "Full milestone history and design are in docs/roadmap.md" | **spans both** | add a second link to `docs/history/roadmap-log.md` alongside the existing one |
| `README.md:458` | "for partially-implemented Milestones I and J, see docs/roadmap.md" | current-state (I/J stayed) | leave pointing at `docs/roadmap.md` — no change |
| `README.md:756` | "docs/roadmap.md — research roadmap and milestone exit conditions" | **spans both** (exit conditions for A-H now live in the log) | add a second bullet/link to `docs/history/roadmap-log.md` |

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_roadmap_references_repaired.py
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_spans_both_references_link_the_history_log_too():
    organism = (REPO_ROOT / "ORGANISM.md").read_text(encoding="utf-8")
    assert "docs/roadmap.md" in organism
    assert "docs/history/roadmap-log.md" in organism

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/history/roadmap-log.md" in readme
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_roadmap_references_repaired.py -v`
Expected: FAIL — `docs/history/roadmap-log.md` not yet referenced from
`ORGANISM.md` or `README.md`.

- [ ] **Step 3: Repair ORGANISM.md:9**

Change the sentence to reference both, e.g.:

```markdown
Full milestone history and design are in [`docs/roadmap.md`](docs/roadmap.md)
(active state) and [`docs/history/roadmap-log.md`](docs/history/roadmap-log.md)
(completed milestones A-H), ...
```

(keep the rest of the original sentence's wording/links unchanged — only
insert the second link and its four-word qualifier).

- [ ] **Step 4: Repair README.md:756**

Add a sibling bullet right after the existing `docs/roadmap.md` line in that
list:

```markdown
- [`docs/roadmap.md`](docs/roadmap.md) — research roadmap and active milestone exit conditions (I/J/K).
- [`docs/history/roadmap-log.md`](docs/history/roadmap-log.md) — completed milestone history (A-H) and per-patch tracking log.
```

- [ ] **Step 5: Leave research/README.md:5 and README.md:458 untouched**

Verify by re-reading them that they genuinely refer to current active state
(I/J, or generic orientation) — do not edit them.

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/docs/test_roadmap_references_repaired.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add ORGANISM.md README.md tests/docs/test_roadmap_references_repaired.py
git commit -m "docs: repair roadmap.md references after historical log split"
```

---

### Task 5: Update docs/README.md portal index and expand docs/glossary.md

**Execution order note:** run this task **after Task 8**, not in numeric
order — Step 4 below adds a link to `docs/web/README.md`, which does not
exist until Task 6 creates it. Tasks 1-4 have no such dependency and can run
in numeric order; renumber this task as "Task 9" and shift the former
Task 9 (full-suite regression check) to run last, after this one.

**Files:**

- Modify: `docs/README.md`
- Modify: `docs/glossary.md`
- Test: `tests/docs/test_portal_index_and_glossary.py`

**Interfaces:**

- Consumes: `docs/releases/README.md` (Task 1), `docs/_internal/` (Task 2), `docs/history/roadmap-log.md` (Task 3), `docs/web/README.md` (Task 6).

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_portal_index_and_glossary.py
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_portal_index_points_at_new_paths():
    text = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "releases/README.md" in text
    assert "releases/v0.80.15.md" not in text
    assert "history/roadmap-log.md" in text
    assert "_internal/plans" in text
    assert "superpowers/plans" not in text


def test_glossary_covers_organism_vocabulary():
    text = (REPO_ROOT / "docs" / "glossary.md").read_text(encoding="utf-8").lower()
    for term in ("organism", "genome", "phenotype", "habitat", "checkpoint", "percept"):
        assert term in text, f"glossary missing organism term: {term}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_portal_index_and_glossary.py -v`
Expected: FAIL — `docs/README.md` still says `releases/v0.80.15.md` and
`superpowers/plans`; glossary lacks organism terms.

- [ ] **Step 3: Update docs/README.md section 1**

Replace the release line and add the history-log line:

```markdown
- [`roadmap.md`](roadmap.md) — **Fuente canónica del estado activo de desarrollo (north star, invariantes, hitos I/J/K vigentes).**
- [`history/roadmap-log.md`](history/roadmap-log.md) — **Historia completa de hitos A-H y bitácora de tracking por versión.**
- [`releases/README.md`](releases/README.md) — Índice de notas de release archivadas.
- [`../ORGANISM.md`](../ORGANISM.md) — Registro histórico y evolutivo de las capacidades del organismo.
- [`glossary.md`](glossary.md) — Glosario técnico y vocabulario epistémico compartido.
```

Update section 6's "Planes Históricos" line (from Task 2, Step 6 — confirm
it already says `_internal/plans/`; if Task 2 was executed by a different
worker session, apply that edit now instead).

- [ ] **Step 4: Add section 7 for docs/web/ (link only — content arrives in the follow-up plan)**

```markdown
---

## 7. Documentación de Publicación Web

- [`web/README.md`](web/README.md) — **Puerta narrativa pública sobre qué es un Symbiont y qué muestra la experimentación**, sin sustituir el portal técnico. Cada capítulo cita su fuente exacta en [`web/FUENTES.md`](web/FUENTES.md).
```

Both link targets already exist at this point because this task runs after
Task 8 (see the execution-order note at the top of this task).

- [ ] **Step 5: Expand docs/glossary.md**

Add a new section after the existing two, citing code definitions (verify
each path/symbol exists before writing it in):

```markdown
## Organism Vocabulary

- **Organism:** A single developmental identity (`organism_id`), distinct
  from process lifetime, checkpoint filename, and genome identity. See
  `docs/roadmap.md` § Birth, identity, dormancy and death.
- **Genome:** The closed, versioned, kernel-validated configuration for one
  individual's development. See `docs/design/endogenous-plasticity.md`.
- **Phenotype:** The plastic cognitive graph (nodes/edges/weights) an
  individual develops during its life, distinct from its genome.
- **Habitat:** An explicit, bounded, authorized multi-organism resource and
  population boundary. See `docs/design/reproduction-death-population.md`.
- **Checkpoint:** A durable, atomic snapshot of consolidated organism state
  used for restart/recovery — never raw sensor histories. See
  `docs/design/biological-memory-consolidation.md`.
- **Percept:** A platform-neutral perception synthesized from a raw,
  platform-specific reading (see `docs/math/02-percepcion-aclimatacion-y-relaciones.md`).
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/docs/test_portal_index_and_glossary.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add docs/README.md docs/glossary.md tests/docs/test_portal_index_and_glossary.py
git commit -m "docs: update portal index and expand organism glossary"
```

---

### Task 6: Scaffold docs/web/README.md with three named reading paths

**Files:**

- Create: `docs/web/README.md`
- Test: `tests/docs/test_web_readme.py`

**Interfaces:**

- Produces: the chapter filename list other tasks (7-8, and the future
  chapter-authoring plan) link against.

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_web_readme.py
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAPTERS = [
    "01-que-es-un-symbiont.md",
    "02-cuerpo-y-percepcion.md",
    "03-cognicion-y-plasticidad.md",
    "04-atencion-y-decision.md",
    "05-fisiologia.md",
    "06-reproduccion-y-linaje.md",
    "07-ecologia-y-sociabilidad.md",
    "08-desarrollo-predictivo.md",
    "09-metodologia-y-limites.md",
]


def test_readme_lists_every_chapter_and_three_reading_paths():
    text = (REPO_ROOT / "docs" / "web" / "README.md").read_text(encoding="utf-8")
    for chapter in CHAPTERS:
        assert chapter in text, f"README missing link to {chapter}"
    for path_name in ("Lector curioso", "Investigador", "Implementador"):
        assert path_name in text, f"README missing reading path: {path_name}"
    assert "milestone" not in text.lower(), "no project-management vocabulary in docs/web/"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_web_readme.py -v`
Expected: FAIL — `docs/web/README.md` not found.

- [ ] **Step 3: Write docs/web/README.md**

```markdown
# Symbiont — documentación de publicación

Esta sección es la puerta narrativa pública sobre qué es un Symbiont y qué
muestra la experimentación real. No sustituye la documentación técnica
canónica (`docs/architecture/`, `docs/math/`, `docs/roadmap.md`): cada
capítulo cita su fuente exacta en [`FUENTES.md`](FUENTES.md) y enlaza al
documento técnico en vez de repetir sus números.

## Rutas de lectura

- **Lector curioso** — [01](01-que-es-un-symbiont.md) →
  [07](07-ecologia-y-sociabilidad.md) → [09](09-metodologia-y-limites.md):
  qué es, por qué no es una metáfora decorativa, y qué límites permanentes
  se respetan siempre.
- **Investigador** — [09](09-metodologia-y-limites.md) → capítulos
  experimentales relevantes ([05](05-fisiologia.md),
  [06](06-reproduccion-y-linaje.md), [07](07-ecologia-y-sociabilidad.md),
  [08](08-desarrollo-predictivo.md)) → huecos abiertos.
- **Implementador** — [02](02-cuerpo-y-percepcion.md) →
  [03](03-cognicion-y-plasticidad.md) / [04](04-atencion-y-decision.md):
  frontera de host, ciclo de tick y límites de kernel.

## Capítulos

1. [Qué es un Symbiont](01-que-es-un-symbiont.md)
2. [Cuerpo y percepción](02-cuerpo-y-percepcion.md)
3. [Cognición y plasticidad](03-cognicion-y-plasticidad.md)
4. [Atención y decisión](04-atencion-y-decision.md)
5. [Fisiología](05-fisiologia.md)
6. [Reproducción y linaje](06-reproduccion-y-linaje.md)
7. [Ecología y sociabilidad](07-ecologia-y-sociabilidad.md)
8. [Desarrollo predictivo](08-desarrollo-predictivo.md)
9. [Metodología y límites](09-metodologia-y-limites.md)

Cada capítulo declara, por afirmación, su madurez (`implementado` /
`parcial` / `diferido`) y, cuando aplica, su frontera epistémica
(`evaluator-only`). Ver [`FUENTES.md`](FUENTES.md) para la trazabilidad
verificable de cada afirmación.
```

(Chapter files 01-09 do not exist yet — that is fine, `test_web_readme.py`
only checks the README's own text, not that the linked files exist. Task 8's
verification test is the one that will eventually check chapter content
once chapters are authored in the follow-up plan.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/docs/test_web_readme.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/web/README.md tests/docs/test_web_readme.py
git commit -m "docs: scaffold docs/web/ front door with three reading paths"
```

---

### Task 7: Scaffold docs/web/FUENTES.md with the source-type taxonomy

**Files:**

- Create: `docs/web/FUENTES.md`
- Test: `tests/docs/test_fuentes_taxonomy.py`

**Interfaces:**

- Produces: the empty table shape and taxonomy header that Task 8's
  verification test parses, and that the future chapter-authoring plan
  appends rows to.

- [ ] **Step 1: Write the failing test**

```python
# tests/docs/test_fuentes_taxonomy.py
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALID_TYPES = {"normative", "formal", "implementation", "empirical"}


def test_fuentes_declares_the_taxonomy():
    text = (REPO_ROOT / "docs" / "web" / "FUENTES.md").read_text(encoding="utf-8")
    for type_name in VALID_TYPES:
        assert type_name in text, f"FUENTES.md missing source type: {type_name}"
    assert "docs/_internal" in text, "FUENTES.md must state _internal/ is prohibited as evidence"
    assert "| Claim ID |" in text, "FUENTES.md must declare the claim table header"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_fuentes_taxonomy.py -v`
Expected: FAIL — `docs/web/FUENTES.md` not found.

- [ ] **Step 3: Write docs/web/FUENTES.md**

```markdown
# Fuentes — trazabilidad de docs/web/

Cada afirmación no trivial en `docs/web/` tiene una fila aquí, con un ID
estable y un localizador resoluble en ambos extremos. Un test
(`tests/docs/test_web_sources_exist.py`) verifica automáticamente que cada
ruta/símbolo/ancla citados existen de verdad.

## Tipos de fuente válidos

| Tipo | Fuentes válidas | Para qué |
| --- | --- | --- |
| `normative` | `docs/adr/`, `docs/architecture/`, `docs/design/`, `docs/roadmap.md`, `docs/artificial-life-model.md` | definiciones, fronteras, invariantes |
| `formal` | `docs/math/` | respaldo matemático |
| `implementation` | `src/`, `observatory/` + tests | comportamiento realmente implementado |
| `empirical` | `research/` + tests/estudios | resultados observados experimentalmente |

**Prohibida:** `docs/_internal/` nunca es fuente válida para `docs/web/`.

**Regla:** una afirmación empírica ("se observó", "mejoró", "resiste",
"emerge") no queda respaldada solo por una fuente `normative` o
`implementation`; necesita al menos una fila `empirical`.

## Claims

| Claim ID | Tipo | Chapter anchor | Source |
| --- | --- | --- | --- |
| _(vacío — las filas se añaden capítulo a capítulo en el plan de redacción)_ | | | |
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/docs/test_fuentes_taxonomy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/web/FUENTES.md tests/docs/test_fuentes_taxonomy.py
git commit -m "docs: scaffold FUENTES.md source-type taxonomy for docs/web/"
```

---

### Task 8: Executable FUENTES.md verification test

**Files:**

- Create: `tests/docs/test_web_sources_exist.py`

**Interfaces:**

- Consumes: `docs/web/FUENTES.md`'s claim table (Task 7) and any chapter
  files under `docs/web/*.md` (none exist yet — the test must tolerate an
  empty claim table without failing, and must be ready to enforce once the
  follow-up chapter-authoring plan starts adding rows).

- [ ] **Step 1: Write the test (no separate "make it fail" step needed —**
  **there are zero claim rows yet, so an empty-table pass is the correct**
  **starting state; the meaningful failure mode is exercised in Step 2**
  **with a synthetic bad row)**

```python
# tests/docs/test_web_sources_exist.py
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FUENTES_PATH = REPO_ROOT / "docs" / "web" / "FUENTES.md"
VALID_TYPES = {"normative", "formal", "implementation", "empirical"}


def _parse_claim_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    in_claims_table = False
    for line in text.splitlines():
        if line.strip().startswith("| Claim ID |"):
            in_claims_table = True
            continue
        if in_claims_table and line.strip().startswith("| ---"):
            continue
        if in_claims_table and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 4:
                continue
            claim_id, tipo, anchor, source = cells
            if claim_id.startswith("_(") or not claim_id:
                continue
            rows.append(
                {"claim_id": claim_id, "tipo": tipo, "anchor": anchor, "source": source}
            )
        elif in_claims_table and not line.strip().startswith("|"):
            break
    return rows


def _chapter_path(anchor: str) -> Path:
    chapter_num = anchor.split("#", 1)[0]
    matches = list((REPO_ROOT / "docs" / "web").glob(f"{chapter_num}-*.md"))
    assert len(matches) == 1, f"expected exactly one chapter file for {chapter_num}, found {matches}"
    return matches[0]


def _resolve_source(source: str) -> Path:
    """Split 'path::symbol' or 'path#anchor' into (path, extra)."""
    for sep in ("::", "#"):
        if sep in source:
            path_part, _extra = source.split(sep, 1)
            return REPO_ROOT / path_part
    return REPO_ROOT / source


@pytest.fixture(scope="module")
def claim_rows() -> list[dict[str, str]]:
    text = FUENTES_PATH.read_text(encoding="utf-8")
    return _parse_claim_rows(text)


def test_no_duplicate_claim_ids(claim_rows):
    ids = [row["claim_id"] for row in claim_rows]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"duplicate claim IDs in FUENTES.md: {duplicates}"


def test_every_row_has_a_valid_type(claim_rows):
    for row in claim_rows:
        assert row["tipo"] in VALID_TYPES, f"{row['claim_id']}: invalid tipo {row['tipo']!r}"


def test_no_source_resolves_under_internal(claim_rows):
    for row in claim_rows:
        assert "docs/_internal" not in row["source"], (
            f"{row['claim_id']}: docs/_internal/ is never valid evidence"
        )


def test_chapter_anchor_exists_in_chapter_file(claim_rows):
    for row in claim_rows:
        chapter_file = _chapter_path(row["anchor"])
        anchor_id = row["anchor"].split("#", 1)[1]
        text = chapter_file.read_text(encoding="utf-8")
        assert f'<a id="{anchor_id}"></a>' in text, (
            f"{row['claim_id']}: anchor {anchor_id!r} not found as literal "
            f'<a id="..."> in {chapter_file.name}'
        )


def test_source_path_exists(claim_rows):
    for row in claim_rows:
        source_path = _resolve_source(row["source"])
        assert source_path.exists(), f"{row['claim_id']}: source path not found: {source_path}"


def test_declared_symbol_exists_in_source(claim_rows):
    for row in claim_rows:
        if "::" not in row["source"]:
            continue
        path_part, symbol = row["source"].split("::", 1)
        source_path = REPO_ROOT / path_part
        text = source_path.read_text(encoding="utf-8")
        pattern = rf"\b(def|class)\s+{re.escape(symbol)}\b"
        assert re.search(pattern, text), (
            f"{row['claim_id']}: symbol {symbol!r} not found in {source_path}"
        )


def test_declared_markdown_anchor_exists_in_target(claim_rows):
    for row in claim_rows:
        if "#" not in row["source"] or "::" in row["source"]:
            continue
        path_part, anchor = row["source"].split("#", 1)
        target_path = REPO_ROOT / path_part
        text = target_path.read_text(encoding="utf-8")
        assert f'<a id="{anchor}"></a>' in text or f"id=\"{anchor}\"" in text, (
            f"{row['claim_id']}: markdown anchor {anchor!r} not found in {target_path}"
        )
```

- [ ] **Step 2: Run the test against the current (empty) FUENTES.md**

Run: `pytest tests/docs/test_web_sources_exist.py -v`
Expected: PASS (zero claim rows parsed, every test is vacuously true).

- [ ] **Step 3: Sanity-check the parser catches a bad row**

Temporarily add one deliberately-broken row to `docs/web/FUENTES.md`:

```markdown
| bad-claim | normative | 01#missing-anchor | docs/does/not/exist.md |
```

Run: `pytest tests/docs/test_web_sources_exist.py -v`
Expected: FAIL (`test_source_path_exists` reports the missing path — proves
the test actually enforces the contract instead of always passing).

Remove the deliberately-broken row before committing.

- [ ] **Step 4: Commit**

```bash
git add tests/docs/test_web_sources_exist.py
git commit -m "test: enforce FUENTES.md traceability contract for docs/web/"
```

---

### Task 9: Full-suite regression check

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

```bash
pytest -q
```

Expected: all tests pass, including every `tests/docs/*` test added in
Tasks 1-8 and the pre-existing suite (confirms no relocation broke an
existing import or reference not caught by the greps above).

- [ ] **Step 2: Final repo-wide dangling-reference sweep**

```bash
grep -rn "docs/superpowers" --include=*.md --include=*.py .
grep -rln "docs/releases/v0" --include=*.md --include=*.py . | grep -v "docs/releases/archive/"
```

Expected: both commands produce zero output.

- [ ] **Step 3: Commit (only if Steps 1-2 required fixes; otherwise skip)**

```bash
git add -A
git commit -m "docs: fix regressions found in full-suite reorg sweep"
```

## Out of scope for this plan

Chapters `01-que-es-un-symbiont.md` through `09-metodologia-y-limites.md`
are **not** written here. Per the approved spec's own sequencing ("no
parallel drafting across chapters"), chapter 01 is written and traceability-
verified on its own as the next plan, once Tasks 1-9 above are green —
proving the editorial model before multiplying it by eight.
