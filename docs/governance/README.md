# Repository governance

## Purpose

Keep ordinary engineering cheap while making scientific evidence and constitutional
boundary crossings explicit.

## Normal workflow

    python scripts/agentctl.py publish --message "..."

The command rebases onto current main, classifies the final diff, runs required bounded
equivalence and publishes one candidate. No grant ancestry or per-commit permission
lookup exists.

## Operational classes

- ORDINARY — validate and auto-promote when current and green.
- SCIENTIFIC — equivalence may downgrade to ORDINARY; otherwise external review.
- FROZEN — version, never edit in place.
- CONSTITUTIONAL — Accepted ADR + external owner review.

## Scientific execution

    python scripts/agentctl.py run start --commit <sha> --id <run-id> \
      --scope <scope> --snapshot-source <state-dir> -- <command>

The launcher pins code and input, checks resources/concurrency and writes a receipt.
Held-out, confirmation and replication remain owner decisions by policy without a grant
or self-asserted approval flag.

## Historical grants

The former ledger is preserved at
`docs/history/governance/authority-grants-v1.toml` for historical provenance only.
No active code reads it.

## Root of trust

Human identity/approval lives outside the repository. Only ORDINARY candidates may
auto-promote. SCIENTIFIC and CONSTITUTIONAL candidates require external review.

## Commands

```bash
python scripts/agentctl.py publish --message "..."
python scripts/agentctl.py equivalence status
python scripts/agentctl.py run start ...
python scripts/agentctl.py verify
```

`validate` is an optional local reproduction helper; CI is the technical validation gate.

## Constitutional publication

CONSTITUTIONAL candidates require an Accepted ADR. `publish` records
`Governance-ADR:` provenance; external review supplies the real approval boundary.

## Trusted run coordination

`run start` and `equivalence run` pin one trusted origin/main governance reference.
RUNNING campaigns, immutable snapshots, resource ceilings and execution receipts remain
enforced.
