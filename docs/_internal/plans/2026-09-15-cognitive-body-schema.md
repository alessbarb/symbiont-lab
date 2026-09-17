# PR6 — Cognitive Body Schema implementation plan

Status: implemented on `feat/pr6-cognitive-body-schema`.

1. Project bounded dynamic cognitive activity into organism-local opaque channels.
2. Learn persistent coarse cognitive regions from repeated activity/coactivity evidence.
3. Learn revisable `co_acts_with` and `precedes` dependencies from temporal evidence only.
4. Persist bounded private learning state and migrate historical BodySchema v1 checkpoints to v2.
5. Extend Observatory BodySchema v1/v2 wire validation without changing snapshot v3 semantics.
6. Render sensory parts, cognitive regions and functional dependencies exclusively from organism-owned Self data.
7. Cover privacy, bounds, checkpoint continuity, saturation, restart discontinuities and v1/v2 compatibility.
8. Review the complete branch adversarially before merge; do not infer CI success from runner-infrastructure failures.
