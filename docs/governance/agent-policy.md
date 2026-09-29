# Agent authority policy

## Principle

Agents execute authorised work; they do not choose project direction.

## Levels

### L0 — Read-only

Inspection, audit, comparison and proposals. No repository modification.

### L1 — Maintenance

Documentation, links, formatting, indexes and non-semantic maintenance. L1 may not
change runtime semantics, scientific claims, protocol parameters, architecture
ownership or project direction.

### L2 — Contract-preserving implementation

Implementation or repair whose desired behaviour is already fixed by an accepted ADR,
roadmap item, frozen design, regression contract or constitutional invariant.

### L3 — Scientific mechanism change

Changes to cognition, learning, agency, physiology, sensory experience, model policy,
World experience or another mechanism under study. Requires approved design and, when
used as scientific evidence, preregistration before implementation/execution.

### L4 — Constitutional / safety / direction change

Changes to permanent invariants, host/network/persistence authority, evaluator
boundary, lifecycle identity, reproduction authority, project priorities, governance
or global resource ownership.

## Grants

L2-L4 authority is never accepted from a command-line `--authority` flag.

The owner creates a grant in `docs/governance/authority-grants.toml` in a **prior
commit**. A grant contains:

- unique id;
- status;
- exact base commit;
- maximum authority;
- allowed path globs;
- purpose.

The implementation commit names that grant in its local session manifest and commit
trailer:

```text
Authority-Grant: <grant-id>
```

`agentctl` reads the grant from the parent/base commit. A grant edited in the same
change cannot authorise that change. Because the grant is tied to an exact base commit,
it is single-use by construction after one new commit advances HEAD.

L1 is the default when no elevated grant exists.

## Session manifest

Use an untracked `.agent-session.toml`:

```toml
session_id = "..."
task = "..."
grant_id = "..."
allowed_paths = ["..."]
protocol_change = false
claim_change = false
may_run_scientific_campaigns = false
```

The manifest may narrow a grant, never widen it.

## Authority precedence

1. explicit current owner decision;
2. accepted Constitution/ADR;
3. roadmap and project-state;
4. frozen experiment design;
5. implementation contract;
6. research interpretation;
7. historical documents.

## Minimal-authority rule

Choose the solution requiring the least scientific authority. Restoring a violated
invariant is preferred to redesigning the organism.

## Control-plane rule

Governance code/configuration is protected. An agent cannot first weaken
`agentctl`, CI, hooks, CODEOWNERS or governance metadata and then use that weakened
version to approve the same change.

## Git

Do not destroy unrelated work, rewrite published evidence, delete negative results or
force-push scientific history. Preserve provenance in logical commits.
