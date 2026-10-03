# Reference snapshots

This directory is intentionally empty until complete **real** state directories are
captured.

A valid reference requires:

```text
organism.symbiont
body.json
```

The portable organism bundle already carries its model artifacts. A sibling `models/`
directory is optional and is archived when present. The snapshot manifest hashes the
embedded model tree separately from any external model directory.

Capture archives the files atomically, records SHA-256 digests and the commit that
produced the state, then makes the archived files read-only.

Do not reconstruct `body.json` from the organism's learned BodySchema and do not
invent model files merely to make the suite runnable. If the original physical/body
state is unavailable, that candidate is not a reproducible reference.

Expected slots:

- S01-established-anthropomorphic
- S02-private-model-training
- S03-promotion-eligible
- S04-reembodied-established
- S05-developed-cognition

Use `python scripts/agentctl.py equivalence status` to see which slots are missing or
invalid.
