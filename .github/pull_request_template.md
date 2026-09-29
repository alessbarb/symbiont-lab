## Authority classification

- [ ] L1 Maintenance
- [ ] L2 Contract-preserving implementation
- [ ] L3 Scientific mechanism change
- [ ] L4 Constitutional / safety change

## Authority source

For L2-L4, provide the prior owner grant and commit trailer:

```text
Grant ID:
Authority-Grant: <grant-id>
```

Also identify the owner decision, ADR, roadmap item, preregistration or existing contract that authorises the change.

## Scientific impact

- Protocol changed: yes / no
- Claims changed: yes / no
- Scientific campaign run: yes / no
- Frozen artefact changed: yes / no

If any answer is yes, identify the explicit authority and version boundary.

## Concurrency

List active work checked in `docs/governance/active-work.toml` and confirm that no RUNNING campaign was modified.

## Validation

List commands required by `docs/governance/validation-matrix.toml` and their results.
For modifying work include:

```bash
python scripts/agentctl.py check --staged --manifest .agent-session.toml
python scripts/agentctl.py verify
```

## Claim review

State the strongest claim supported after this change and its evidence level/scope.


## Scientific execution grant

If this change consumes or reports a scientific run, record the distinct
`kind = "scientific-run"` grant, exact run id/scope and execution receipt. A
code-change grant is not sufficient.
