# Agent authority policy

## Principle

Agents execute authorised work; they do not choose project direction.

## L0 — Read-only

May inspect, search, audit, compare and propose. No repository modification.

## L1 — Maintenance

May perform changes that do not alter scientific or runtime semantics: spelling, links, formatting, indexes, accurate descriptive documentation, non-semantic test maintenance and local typing/lint clean-up.

L1 must not change claims, protocols, thresholds, runtime behaviour or architectural ownership.

## L2 — Contract-preserving implementation

May repair or implement behaviour whose desired result is already established by a prior authority source such as an accepted ADR, roadmap item, frozen design, regression contract or constitutional invariant.

Examples include approved durability fixes, execution-fingerprint fields, removing nominal label dependence from E8 physical RNG, or fixing loss of body-independent state during re-embodiment.

L2 may not invent a new scientific success criterion or mechanism.

## L3 — Scientific mechanism change

Includes changes to cognition, learning, agency, physiology, sensory experience, model promotion policy, World experience, or any mechanism under scientific study.

Requires documented evidence, explicit design, owner approval, preregistration where results will be used scientifically, and implementation only after approval.

No L3 change is justified merely because an experiment was negative.

## L4 — Constitutional / safety change

Includes host permission expansion, network access/exchange, credentials, persistence/propagation authority, evaluator/subject boundary, reproduction authority, global resource-ceiling ownership, global reward/fitness, lifecycle identity semantics, constitutional invariants, and project roadmap authority.

Requires explicit owner decision and accepted ADR.

## Authority sources

From strongest to weakest:

1. current explicit owner instruction;
2. accepted constitution/ADR;
3. canonical roadmap and project-state;
4. frozen experiment design/preregistration;
5. active implementation contracts;
6. research interpretation;
7. historical documents.

A later low-authority source does not override a higher one.

## Minimal-authority rule

When several solutions exist, choose the one requiring the least scientific authority. Restoring a violated invariant is preferred to redesigning the organism.

## Session manifests

A modifying agent should create an untracked local manifest when tooling is available:

```toml
session_id = "..."
base_commit = "..."
task = "..."
authority = "L2"
allowed_paths = ["src/symbiont_lab/world/**", "tests/experimental_integrity/**"]
protocol_change = false
claim_change = false
may_run_scientific_campaigns = false
```

Then use:

```bash
python scripts/agentctl.py check --staged --authority L2 --manifest .agent-session.toml
```

The manifest narrows authority; it never expands the level granted by the owner.

## Git

Do not destroy unrelated work, force push, rewrite published evidence or delete negative results. Preserve scientific provenance in logical commits.
