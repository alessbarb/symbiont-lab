# Scientific study records

This directory contains evidence records for executed research programmes. It
is grouped by scientific question rather than by date.

A study record should make its status and scope visible without requiring the
reader to inspect implementation code:

```text
research/studies/<programme>/<study>/
├── README.md       question, status, conclusion and limitations
├── PROTOCOL.md     executed preregistration snapshot, when available
├── ANALYSIS.md     analysis and interpretation, when separate
├── RESULTS.json    frozen result artifact, when available
├── MANIFEST.json   code/seed/config provenance, when available
└── checksums.txt   integrity record, when available
```

Existing reports are preserved verbatim where possible. A moved historical
report is still evidence for the protocol and commit that produced it; its
location does not broaden its scientific scope.

## Current programmes

- `biological-closure/` — physiology, interoception and ecology studies.
- `cognition/` — individual signal and prediction studies.
- `private-models/` — Private SLM utility and adaptation.
- `culture/` — social claims, cumulative culture and autonomous agency.
- `communication/` — symbolic communication and population telemetry.
- `ecology/` — longitudinal population studies and discovery.

Executable runners live under `src/symbiont_lab/` or `experiments/`, never in
this evidence tree.
