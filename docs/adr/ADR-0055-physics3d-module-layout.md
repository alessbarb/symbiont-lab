# ADR-0055 — Organize Physics3D modules by responsibility

- **Status:** Accepted
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** A9, `docs/roadmap.md`, and `docs/development/maintainability-baseline.md`

## Context

The A9 maintainability work has already isolated several Physics3D
responsibilities, but related modules remain as underscore-composed sibling
files. The application layer includes geometry, monitor conversion, run, and
session modules alongside `physics3d_monitor.py`. The Physics3D package also
contains a family of versioned telemetry formats, shared helpers, and tools as
flat sibling modules. Telemetry tests are similarly grouped by filename rather
than in a dedicated subsystem directory.

This layout makes ownership and navigation less clear and means that related
changes require updates across many flat import paths. The A9 baseline records
bounded extractions already completed and requires source-to-test mapping and
behavior-preserving evidence for each further structural change. It does not
authorize a broad rewrite, merge versioned telemetry contracts, or include
Observatory.

## Decision proposal

Organize only the established Physics3D application and telemetry families into
responsibility-based packages, preserving behavior and public compatibility:

1. Group application-owned Physics3D modules under
   `src/symbiont_lab/app/physics3d/`, with a `monitor/` subpackage for the
   monitor and its converters/viewer responsibilities. Keep run/session
   responsibilities as sibling modules in that package where their existing
   ownership and call graph support it.
2. Group the existing Physics3D telemetry implementation family under
   `src/symbiont_lab/physics3d/telemetry/`. Keep each format/version and tool
   responsibility distinct; this is a package-layout change, not permission to
   consolidate formats or alter schemas.
3. Group telemetry unit tests under
   `tests/unit/lab/physics3d/telemetry/`, retaining test module and test names
   unless a concrete import or collection constraint requires a change.
4. Add explicit `__init__.py` files to each new Python package. Define
   intentional re-exports there for compatibility; do not rely on implicit
   namespace packages or wildcard exports.
5. Update all production imports, test imports, entry points, documentation
   links, repository path manifests/indexes, and test selectors affected by the
   moves. Do not leave stale references to the old paths.

The exact file mapping must be verified against current callers, test
ownership, entry points, and links before implementation. Files are moved only
when they belong to these bounded families; underscore-separated names outside
this scope are not to be mechanically split. In particular, scientific study
identifiers and cohesive domain names remain unchanged unless separate evidence
supports another decision.

## Constraints and preserved invariants

- No runtime behavior, scientific mechanism, random-number consumption,
  ordering, checkpoint/schema semantics, provenance, or authority boundary may
  change as a result of this organization.
- Preserve existing import paths with explicit compatibility facades where
  they form a public or established caller surface. Remove such facades only
  in a separately reviewed change with migration evidence.
- Keep the dependency direction and epistemic boundaries in the canonical
  constitution. Observatory remains excluded.
- Make the work in small slices. For each slice, record owned responsibility,
  callers, compatibility surface, test ownership, and focused regression
  evidence in the A9 maintainability baseline.
- Do not claim A9 complete from file movement alone. Run focused tests for each
  slice and report full-suite status separately.

## Consequences

- Physics3D application and telemetry code will be navigable by package and
  responsibility rather than a flat set of compound filenames.
- Imports and documentation links will need coordinated updates, and explicit
  facades may temporarily preserve historical paths.
- Versioned telemetry modules remain separate contracts; this proposal does
  not introduce shared writer abstractions or alter their on-disk formats.
- This decision, if accepted, authorizes only the bounded package-layout work
  above under A9. It does not authorize unrelated refactors or scientific
  changes.

## Acceptance criteria

- [x] Project owner explicitly accepts this ADR on 2026-10-02 ("adelante").
- [x] A reviewed source-to-destination mapping covers every moved module,
  `__init__.py` export, caller, test, entry point, and documentation/path link.
- [x] Focused tests demonstrate unchanged behavior and import compatibility
  for each moved family.
- [x] Repository searches find no unintended active references to old paths.
- [x] Focused lint, formatting, and repository-layout checks pass; full-suite
  validation is reported independently.

## Decision

Accepted by the project owner on 2026-10-02. This authorizes only the bounded
package-layout work and validation described above; it does not authorize
behavior changes, unrelated refactors, or scientific acceptance.

Implementation validation was performed on 2026-10-02: focused tests passed
(**309 passed, 1 skipped, 8 deselected**), the repository layout and Markdown
link checks passed, and focused Ruff check/format checks passed. The full test
suite was not run.
