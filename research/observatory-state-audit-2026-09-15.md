# Observatory state audit — 2026-09-15

Read-only inventory of `/home/alessbarb/.local/state/symbiont/observatory`.

## Findings

- 135 files, approximately 1.53 GB.
- 56 instance artifacts (28 instances plus 28 topology files).
- 28 manifests, all with `manifest_version: 3`.
- 51 journal segments across multiple run ids.
- 12,438 NDJSON entries; all parsed successfully and all carried snapshot
  `schema_version: 3`.
- Snapshot ticks ranged from 1 to 4,400.
- No heartbeat directory/artifacts were present at audit time.

The dominant risk was cross-run journal accumulation: the previous retention
limit was applied independently to each run id, while every resident restart
creates a new run id. The journal now applies a global 512 MiB cap, deleting only
whole old segments and never the active segment. Existing state was not modified
by this audit.

The large existing journals are retained for the owner to decide on separately;
this change only bounds future growth.
