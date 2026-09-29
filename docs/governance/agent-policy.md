# Agent authority policy

## Principle

Agents execute authorised work; they do not choose project direction. Technical write
access is not scientific authority.

## Levels

- **L0 — Read-only:** inspection, audit and proposals.
- **L1 — Maintenance:** no runtime, scientific, protocol, claim or architecture change.
- **L2 — Contract-preserving implementation:** prior owner grant required.
- **L3 — Scientific mechanism/protocol change:** prior owner grant and approved design/preregistration required.
- **L4 — Constitutional/safety/direction/control-plane change:** prior owner grant required.

## Owner-root grant issuance

Normal L2-L4 work uses a grant already present in the parent commit. Grant issuance is
an administrative root action and is valid only when one commit:

1. changes only `authority-grants.toml`;
2. appends exactly one OPEN grant without rewriting prior grants;
3. sets `base_commit` to the issuance commit's parent;
4. carries `Owner-Grant-Issuance: <grant-id>`;
5. is observed in CI under the GitHub actor named by `owner-root.toml`.

This is not cryptographic separation if an agent possesses the owner's credential.
Protected-branch review remains the external root of trust where available.

## Session manifest

The ignored local `.agent-session.toml` narrows the task and grant. It never expands
authority.

## Scientific execution

Long/evidentiary runs require `kind = "scientific-run"` grants fixing exact code,
run id, argv, scope and resource ceilings. `agentctl run exec` requires an exact
matching command, a clean tree and `may_run_scientific_campaigns = true`.

A code-change grant cannot authorize a campaign. Held-out and confirmation data are
owner-authorized data consumption, not ordinary agent commands.

## Frozen evidence

If a directory under `experiments/` contains archived `results.json`, the entire
directory is L4: runner, fixtures, protocol and result move together as immutable
evidence. New work uses a new version/directory.

Design, research and contract/integrity-test surfaces require elevated authority.

## Validation receipts

`agentctl validate --staged` derives required commands from
`validation-matrix.toml` and records a receipt bound to the exact staged Git tree.
`agentctl check --staged` rejects a changed staged tree without a matching receipt.

## Minimal-authority rule

Choose the solution requiring the least scientific authority. Restoring a violated
invariant is preferred to redesigning the organism.
