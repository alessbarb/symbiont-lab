# Design: docs/ reorganization + web publication line

Status: proposed, not yet implemented. No files have been moved or changed.

## Problem

`docs/` mixes canonical portal content with working artifacts and unbounded
historical logs, making it harder to navigate:

- `docs/releases/` holds 65+ individual per-patch release files inline with
  conceptual documentation. `docs/README.md` additionally pins a specific
  release (`v0.80.15.md`) by hand as "the current release," coupling the
  portal to a moving target.
- `docs/superpowers/plans/` and `docs/superpowers/specs/` are internal
  implementation working artifacts (past plans/specs), not canonical
  documentation about the project. They are referenced from other repo
  locations (see Reorganization mechanics below), so relocating them is not
  a pure rename.
- `docs/roadmap.md` (991 lines) mixes active normative state (north star,
  invariants, active milestones I/J/K, decision gates, merge policy) with:
  the completed-development table (lines 96-131), all of Milestones A-H in
  full (lines 168-629, already closed/completed), and a large `## Tracking`
  section of per-patch narrative entries (line 683 onward, v0.79.26 through
  v0.80.15). Only the north star, invariants, active I/J/K state, decision
  gates, and merge policy are actually "current normative state" by the
  project's own definition.
- `docs/glossary.md` (17 lines) currently covers only the experimental
  hierarchy and the `WORKING/VALIDATED/FROZEN/SUPERSEDED` lifecycle — it does
  not yet serve as organism vocabulary.

Separately, there is no public-facing documentation line about what a
Symbiont is and what has been observed experimentally, grounded strictly in
code and `research/`.

## Goals

1. Reorganize `docs/` (relocate + repair references, no semantic rewrites)
   so canonical normative/architecture content is separated from historical
   logs and internal working artifacts.
2. Establish `docs/web/` as a new documentation line for public/web
   publication: one unified sequence of chapters, each written in a blended
   pedagogical-and-scientific style, with mathematical foundations folded in
   per topic rather than isolated in their own chapter.

## Non-goals

- No static site generator/build pipeline in this pass (plain Markdown only,
  per owner decision — format can change later without restructuring content).
- No semantic rewrites of canonical documentation content. Mechanical
  path/link repairs caused by relocation are explicitly allowed and required
  (see below) — this is a correction from the previous revision of this
  spec, which said "no content rewrites" without accounting for
  cross-references that must keep working.
- No new claims not traceable to code or `research/` artifacts.
- No project-management vocabulary ("Milestone X") inside `docs/web/` content
  — status is expressed by the maturity/epistemic vocabulary defined below
  instead.

## docs/ reorganization

| Change | From | To |
| --- | --- | --- |
| Archive per-patch release notes | `docs/releases/*.md` | `docs/releases/archive/*.md` |
| New release index | — | `docs/releases/README.md` (table: version → one-line summary, linking into `archive/`; replaces the hand-pinned "current release" link in `docs/README.md`) |
| Internal working artifacts | `docs/superpowers/` | `docs/_internal/` (this spec moves with it once approved) |
| Split roadmap: active state | `docs/roadmap.md` (kept) | North star, permanent invariants, active milestones (I/J/K), decision gates, merge policy only |
| Split roadmap: historical log | `docs/roadmap.md` (extracted, unmutilated) | `docs/history/roadmap-log.md` — the 2026-09-14 developmental restructures narrative, the completed-development table, **all of Milestones A-H in full**, and the **entire `## Tracking` section** |
| Glossary expansion | `docs/glossary.md` | Same file, expanded with terms from `entidad-symbiont.md`, `roadmap.md`, and the permanent invariants (organism, genome, phenotype, habitat, checkpoint, percept, etc.), each citing where it is defined in code |

`docs/history/roadmap-log.md` receives the extracted material verbatim —
this is a relocation, not a summary. Nothing is mutilated or paraphrased
during the move.

### Reorganization mechanics: reference repair

Relocating `docs/superpowers/` breaks existing references, confirmed to
exist in:

- `src/symbiont/core/selfmodel.py:107` — a code comment pointing at
  `docs/superpowers/specs/2026-09-14-v053-self-model-design.md §4.3`.
- Multiple files under `docs/superpowers/plans/*.md` that cross-link to
  `docs/superpowers/specs/*.md` (e.g. "Spec: `docs/superpowers/specs/...`").
- `docs/README.md`'s own listing of `superpowers/plans/`.

The implementation plan must grep the whole repo for `docs/superpowers` (and
similarly `docs/releases/` outside the release files themselves) before
executing any move, and update every hit to the new path as a mechanical
edit. This is the allowed exception carved out in Non-goals above: the
prose of `selfmodel.py`'s comment or a plan's cross-link sentence does not
change, only the path string.

### Reorganization mechanics: semantic repair of roadmap.md references

Splitting `roadmap.md` is a different case from the path renames above: the
links that reference it will not break technically (the file still exists),
but many will become **semantically wrong** once A-H and `## Tracking` move
out. After the split, grep the whole repo for references to `docs/roadmap.md`
and classify each by intent:

- references to current/active state (north star, invariants, I/J/K, decision
  gates, merge policy) keep pointing at `docs/roadmap.md`;
- references to completed milestones, historical sequence, or tracking
  entries must be repointed to `docs/history/roadmap-log.md`;
- a reference that spans both (e.g. "see roadmap.md for full milestone
  history and current state") must link both documents.

This semantic repair is part of the mechanical move, not a content rewrite —
the same exception already carved out in Non-goals.

## What docs/web/ is relative to existing docs

`docs/web/` does not replace or duplicate `docs/architecture/entidad-symbiont.md`,
`docs/math/`, or `docs/roadmap.md`. Those remain the canonical, normative
sources. `docs/web/` is a narrative front door for readers outside the
engineering context: it never restates a number, threshold, or result without
citing exactly where that value comes from, and it links out to the
technical document instead of re-deriving it. This avoids a fourth parallel
description of the organism that would need to be kept in sync by hand.

`docs/_internal/README.md` (the relocated `docs/superpowers/README.md`, or a
new file if none exists) must state explicitly that its contents are
historical/non-normative working artifacts and **must not** be cited as
evidence in `docs/web/FUENTES.md`. The full valid-source taxonomy is defined
in the FUENTES.md section below.

## docs/web/ — public documentation line

Plain Markdown, no site generator, one unified chapter sequence (no
pedagogical/scientific folder split — each chapter blends both registers).

```text
docs/web/
  README.md
  FUENTES.md
  01-que-es-un-symbiont.md
  02-cuerpo-y-percepcion.md
  03-cognicion-y-plasticidad.md
  04-atencion-y-decision.md
  05-fisiologia.md
  06-reproduccion-y-linaje.md
  07-ecologia-y-sociabilidad.md
  08-desarrollo-predictivo.md
  09-metodologia-y-limites.md
```

### README.md — front door with named reading paths

Mirrors the pattern `docs/math/README.md` already uses for itinerarios A/B/C,
scaled to three reader profiles instead of one:

- **Lector curioso** — 01 → 07 → 09 (what it is, why it is not a decorative
  metaphor, permanent limits)
- **Investigador** — 09 → relevant experimental chapters → open gaps
- **Implementador** — 02 → 03/04 → host boundary and kernel-limit references

### Fixed chapter spine (01-08)

Every chapter 01-08 follows the same internal structure, so the
pedagogical/scientific blend is enforced structurally rather than left to
prose discipline:

1. **Qué es** — plain description of the concept.
2. **Mecanismo** — how it works, referencing the actual module/class.
3. **Qué hay implementado** — current state, tagged with the maturity and
   epistemic-boundary vocabulary below.
4. **Evidencia** — the specific study, test, or audit that demonstrates the
   claim, from `research/studies/`, `research/audits/`, or the test suite.
5. **Qué sigue abierto (de este mecanismo)** — gaps specific to the
   mechanism this chapter covers, not general disclaimers. Cross-cutting
   limitations belong in chapter 09, not repeated here.
6. **Respaldo formal** — link to the relevant `docs/math/NN-*.md` chapter(s)
   when the mechanism has a formal treatment there.

Chapter-to-source mapping:

| Chapter | Primary source | Math backing |
| --- | --- | --- |
| 01 Qué es un Symbiont | ADR-0001, ADR-0002, `artificial-life-model.md` | — |
| 02 Cuerpo y percepción | `entidad-symbiont.md` (host/providers), acclimation/percept releases | `math/02`, `math/03` (Welford, drift) |
| 03 Cognición y plasticidad | cognitive graph, genome kernel, memory consolidation design docs | `math/07`, `math/08`, `math/09` (metacognición, automodelo, Oja) |
| 04 Atención y decisión | attention budget, second-look, evidence revision | `math/04`, `math/05`, `math/06` (mochila, bayes, consenso) |
| 05 Fisiología | `milestone-i-fisiologia-integrada.md`, physiology studies | — |
| 06 Reproducción y linaje | `reproduction-death-population.md` | — |
| 07 Ecología y sociabilidad | `milestone-k-sociabilidad-emergente.md`, social studies | `math/06` (consenso) |
| 08 Desarrollo predictivo | `milestone-j-desarrollo-predictivo.md`, shadow-prediction studies | `math/10` (selección causal) |

### Chapter 09 — transversal, not a spine chapter

09 does not use the fixed spine. It covers only what is genuinely
cross-cutting: the pre-registration protocol (`docs/methodology/`,
`research/protocols/`), the audit inventory (`research/audits/`), the
methodological decision history (`research/decisions/`), and open
generalization gaps that apply across mechanisms (e.g. "no evidence yet of
emergent behavior outside the synthetic regime"). Mechanism-specific gaps
stay in their own chapter's step 5 so each chapter remains scientifically
self-contained; 09 does not become a catch-all disclaimer dump.

### Maturity and epistemic-boundary vocabulary (replaces "Milestone" labels)

Two independent dimensions, both copied verbatim in meaning from
roadmap/release wording — never a new judgment:

**Maturity** (mutually exclusive):

- `implementado` — shipped and covered by tests/studies.
- `parcial` — partially implemented, matching roadmap's "implementación
  parcial".
- `diferido` — designed but deliberately not enabled (e.g. network transport
  "implemented locally; network deferred").

**Epistemic boundary** (orthogonal, may co-occur with any maturity level):

- `evaluator-only` — exists only as an external evaluator-side harness, never
  fed back into organism cognition. A capability can be fully `implementado`
  and still be `evaluator-only` — this is not a lesser maturity, it is a
  deliberate boundary (ADR-0002: ground truth stays outside cognition).

Tags are attached to individual claims/capabilities, not to a whole chapter —
one chapter may contain both `[implementado]` and `[parcial]` claims side by
side, e.g. "the ledger itself is `[implementado]`; cross-habitat replication
of it is `[diferido]`."

### FUENTES.md — traceability as a mechanism, not a promise

`FUENTES.md` classifies each source by **type**, not only by path, because
different claim kinds require different evidence:

| Tipo | Fuentes válidas | Para qué |
| --- | --- | --- |
| `normative` | `docs/adr/`, `docs/architecture/`, `docs/design/`, `docs/roadmap.md`, `docs/artificial-life-model.md` | definitions, boundaries, invariants |
| `formal` | `docs/math/` | mathematical backing |
| `implementation` | `src/`, `observatory/`, etc. + tests | what is actually implemented |
| `empirical` | `research/` + tests/studies | experimentally observed results |
| prohibida | `docs/_internal/` | never authoritative for `docs/web/` |
| histórica | `docs/releases/archive/`, `docs/history/` | historical context, not proof of current state |

Rule: an **empirical** claim — "was observed," "improved," "resists,"
"emerges," etc. — cannot be backed by a `normative` or `implementation`
source alone; it requires at least one `empirical` row. A `normative` source
is sufficient for a definitional claim ("what a habitat is"); it is not
sufficient for a claim about what happened when the organism ran.

Table shape: a stable ID and a resolvable locator on both ends of the
reference, now with an explicit type column:

| Claim ID | Tipo | Chapter anchor | Source |
| --- | --- | --- | --- |
| `oja-update` | `formal` | `03#oja-update` | `docs/math/09-plasticidad-endogena-y-redes-recurrentes.md` |
| `oja-update-impl` | `implementation` | `03#oja-update` | `src/symbiont/.../learning.py::update_weights` |
| `clonal-budding` | `normative` | `06#clonal-budding` | `docs/design/reproduction-death-population.md#clonal-budding` |
| `clonal-budding-observed` | `empirical` | `06#clonal-budding` | `research/studies/...` + test name |

Chapters use explicit anchors (`<a id="oja-update"></a>`) rather than relying
on how a renderer slugifies headings, so the anchor cannot silently drift.

A verification test (e.g. `tests/docs/test_web_sources_exist.py`) checks, for
every row:

1. the chapter anchor (`NN#anchor-id`) exists as a literal `<a id="...">` in
   that chapter file;
2. the source path exists in the repo;
3. when a `::symbol` is declared, that symbol exists in the source file
   (function/class/method name present);
4. when the source is a Markdown `#anchor`, that anchor exists in the target
   file;
5. no claim ID is duplicated;
6. no source path resolves under `docs/_internal/` (per the "not valid
   evidence" rule above);
7. every claim ID tagged (in its chapter) as an empirical statement has at
   least one row of type `empirical`.

This mirrors how the project already enforces the `symbiont`/`symbiont_lab`
import boundary with AST tests — traceability becomes an enforced contract,
not a style rule.

### Releases index consistency check

Alongside the source-verification test, add a check that every file in
`docs/releases/archive/*.md` appears exactly once in `docs/releases/README.md`,
so the new index cannot silently drift out of sync with the archive the way
the old hand-pinned "current release" link in `docs/README.md` would have.

## Risks / open items

- Reference repair (selfmodel.py comment, plan cross-links, docs/README.md)
  must be done as part of the mechanical move, not as a follow-up — a repo
  grep for `docs/superpowers` and `docs/releases/v0.` is required before
  executing the move and again after, to confirm zero dangling references.
- `docs/web/` content authoring is a substantial writing effort per chapter;
  this design only fixes structure, spine, and sourcing mechanism, not
  chapter drafts.
- `FUENTES.md` and its verification test must exist and pass before the
  first chapter is considered done — chapter 01 is the model that proves the
  editorial/traceability approach before it is multiplied by eight.

## Next step

On approval, use the writing-plans skill to produce an implementation plan,
strictly sequential:

1. Mechanical move of `docs/releases/` and `docs/superpowers/`, with
   repo-wide reference repair and a before/after grep confirming no dangling
   paths remain.
2. Full roadmap split (north star/invariants/active state stays;
   completed-development table, Milestones A-H, and `## Tracking` move
   verbatim to `docs/history/roadmap-log.md`), followed by the semantic
   repair pass over every repo-wide reference to `docs/roadmap.md`
   (reclassify by intent: current-state / historical / both) + releases
   index + `docs/releases/README.md`/archive consistency test + glossary
   expansion.
3. `docs/web/` scaffolding: `README.md` (three reading paths), `FUENTES.md`
   (empty table with the source-type taxonomy header), and the
   source-verification test (including the empirical-claim-requires-
   empirical-row check) — all green before any chapter prose exists.
4. `01-que-es-un-symbiont.md`, written end-to-end with its `FUENTES.md` rows
   and passing verification, as the proof of the editorial model.
5. Chapters 02-09, one at a time, each closing its own `FUENTES.md` rows
   before the next chapter starts. No parallel drafting across chapters.
