# Technical Design Index (`docs/design/`)

This directory contains architectural specifications, data contracts, and engineering designs governing the ontogenetic and phylogenetic development of **Symbiont**.

---

## Canonical Design Domains

- **Core & Cognition**: [`cognition/`](cognition/) — adaptive activation, graph topology, predictive circuits, and replay.
- **Embodiment & Sensorimotor**: [`embodiment/`](embodiment/) and [`sensorimotor/`](sensorimotor/) — body boundary, actuation, sensorimotor dynamics, and re-embodiment.
- **Lineage & Genome**: [`genome/`](genome/) — Genome v2, heritable loci, and epigenetic transmission.
- **World & Habitat**: [`world/`](world/) — environment boundaries, spatial ecology, and physicalization.
- **Observability & Telemetry**: [`observability/`](observability/) and [`telemetry/`](telemetry/) — read-only telemetry, stream adapters, and passive metrics.
- **Experimentation**: [`experimentation/`](experimentation/) — experimental decontamination, freeze contracts, and baseline integrity.
- **Archive**: [`archive/`](archive/) — historical superseded design drafts and protocol revisions.

---

## Design and Implementation Relationship

> [!IMPORTANT]
> A design document in `docs/design/` establishes formal contracts and hypotheses. For actual implementation status in source code, the canonical references are [`../architecture.md`](../architecture.md), [`../roadmap.md`](../roadmap.md), and [`../../ORGANISM.md`](../../ORGANISM.md).
