# Repository governance

## Normal agent path

For ordinary work the complete operational loop is:

```text
agentctl context
      ↓
implement requested change
      ↓
targeted local checks only when useful
      ↓
agentctl publish
      ↓
GitHub Actions
      ↓
auto-promote ORDINARY / external review SCIENTIFIC or CONSTITUTIONAL
```

Start with:

```bash
python scripts/agentctl.py context
```

The output is intentionally compact. It refreshes trusted `origin/main` once and
returns base/head, worktree state, current gate, RUNNING work/conflicts and the next
publication action. `--json` is available for agents and scripts.

Do not reconstruct governance by rereading every policy document. Read additional
material only if the task crosses a scientific protocol, FROZEN, RUNNING or
constitutional boundary.

Publish with:

```bash
python scripts/agentctl.py publish --message "..."
```

`publish` is the single source of truth for final-diff classification and equivalence.
CI is the sole technical validation gate; full local duplication is not required.

## Classes

- ORDINARY — green/current candidate may auto-promote.
- SCIENTIFIC — equivalence may downgrade it; otherwise external review.
- FROZEN — version, never rewrite.
- CONSTITUTIONAL — Accepted ADR + external review.

## Scientific execution

```bash
python scripts/agentctl.py run start --commit <sha> --id <run-id> \
  --scope <scope> --snapshot-source <state-dir> -- <command>
```

Pinned code/input, resource ceilings, RUNNING locks and execution receipts remain
enforced. Held-out, confirmation and replication remain explicit owner decisions.

## Historical grants

The old ledger remains under `docs/history/governance/` for provenance only. It is not
part of the active control plane.
