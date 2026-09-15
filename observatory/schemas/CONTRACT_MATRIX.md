# Observatory contract matrix

This matrix is the concise compatibility view for the closed JSON contracts. The
JSON Schema files remain normative; this page prevents the version rules from being
repeated inconsistently across projection, replay and UI documentation.

## Snapshot versions

| `schema_version` | Required organism projection | Forbidden organism projection | Signal knowledge |
| ---: | --- | --- | --- |
| 1 | Base organism fields are optional | `cognition`, `body_schema`, `signal_knowledge` | Not accepted |
| 2 | `organism.cognition` | `organism.body_schema`, `organism.signal_knowledge` | Not accepted |
| 3 | `organism.body_schema` | None of the three extensions | Accepted as an optional bounded projection |

All versions are closed objects. Unknown fields are rejected by
`schemas/snapshot.schema.json`; the projection layer may still drop an input before
validation when it exceeds its defensive bounds.

## Nested bounds

- `body_schema` is validated by `body_schema.schema.json` and carries its own
  versioned representation; it does not expose host capability names or checkpoint
  salts.
- `signal_knowledge` is limited to 64 profiles, with at most four claims per profile
  and bounded identifiers/text as defined in `snapshot.schema.json`.
- Replay envelopes are bounded independently by `replay.schema.json` (1–10,000
  snapshots and a 5 MiB file limit in the browser loader).

## Compatibility policy

Readers should accept only the versions listed above and preserve the distinction
between an omitted projection and an empty projection. A producer that adds a new
organism extension must allocate a new snapshot schema version or update this matrix
and its compatibility tests together; silently widening an older version is not
allowed.
