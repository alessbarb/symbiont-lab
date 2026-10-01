## Governance classification

- [ ] ORDINARY
- [ ] SCIENTIFIC
- [ ] CONSTITUTIONAL
- [ ] FROZEN evidence is not modified in place

## Decision boundary

For SCIENTIFIC or CONSTITUTIONAL work, identify the owner decision, Accepted ADR,
preregistration, roadmap item or invariant that governs review. Do not create or
reference a repository grant.

## Scientific impact

- Protocol changed: yes / no
- Claims changed: yes / no
- Evidentiary run consumed: yes / no
- Frozen artefact changed: yes / no

## Concurrency

Confirm no RUNNING campaign protected path was modified.

## Validation

GitHub Actions is the technical validation gate. Optional local checks:

```bash
python scripts/agentctl.py verify
```

## Claim review

State the strongest claim supported after this change and its evidence level/scope.

## Scientific execution

For held-out, confirmation or replication, identify the explicit owner decision and the
immutable execution receipt. No scientific-run grant is used.
