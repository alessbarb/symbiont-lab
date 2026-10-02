---
id: root.glossary
title: "Glossary"
document_type: reference
domain: general
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
## Glossary of Epistemological and Experimental Terms

## Experimental Hierarchy

- **Protocol:** A defined scientific procedure and measurement methodology (e.g. `attention.causal`, `evidence.second-look`). Independent of software versions.
- **Experiment:** A specific hypothesis-driven investigation bound to concrete parameters, hypotheses, and success criteria (e.g. `attention.causal.v0242-revalidation`).
- **Run:** A single deterministic execution of an experiment or protocol under a single world seed and parameter configuration.
- **Study:** A collection of comparable runs across parameter sweeps and replication seeds.
- **Campaign:** A sequential progression of studies guided by cumulative findings across regimes.
- **Audit:** An explicit empirical verification of the scientific integrity and methodological correctness of the simulator and laboratory apparatus itself.

## Artifact Status Lifecycle

- **WORKING:** Mutable local run or prototype results residing in `.symbiont/`. Not tracked in version control.
- **VALIDATED:** Run or study that has passed all protocol invariants, integrity assertions, and replication criteria.
- **FROZEN:** Formally accepted scientific record archived in `research/`. Immutable baseline for publications and future comparisons.
- **SUPERSEDED:** Historical study preserved in `research/` whose methodological premise was found flawed or refined by a subsequent audit.

## Organism Vocabulary

- **Organism:** A single developmental identity (`organism_id`), distinct
  from process lifetime, checkpoint filename, and genome identity. See
  `docs/methodology/research-programme.md` §3 Lifecycle semantics.
- **Genome:** The closed, versioned, kernel-validated configuration for one
  individual's development. See `docs/design/cognicion-y-plasticidad.md`.
- **Phenotype:** The plastic cognitive graph (nodes/edges/weights) an
  individual develops during its life, distinct from its genome.
- **Habitat:** An explicit, bounded, authorized multi-organism resource and
  population boundary. See `docs/design/fisiologia-y-reproduccion.md`.
- **Runtime checkpoint:** The serialized organism/runtime state produced by
  `OrganismRuntime.checkpoint()` — consolidated state, never raw sensor
  histories. It carries its own state identity
  (`checkpoint_lineage.checkpoint_id`) and may *reference* artifacts stored
  elsewhere: private-model weights are not inside it. "Checkpoint" without a
  qualifier means this.
- **Portable Symbiont bundle:** The self-contained `.symbiont` transport
  package: the runtime checkpoint plus the private-model artifacts it needs,
  with a manifest that hashes every packaged byte. Bundle integrity (the
  package matches its manifest) and checkpoint identity (the accepted state
  matches its recorded save) are separate contracts; neither replaces the
  other.
- **Body checkpoint:** The physical Body state saved by the embodiment
  apparatus. It is Body-owned, is never part of the portable bundle, and is
  what a same-Body restart needs in addition to the runtime checkpoint.
- **EmbodimentEpisode:** One continuous period of one Symbiont in one Body.
  A new Body always starts a new episode; the previous one is closed and
  archived.
- **Observer reconstruction:** State rebuilt for display from telemetry or
  replay. It is explicitly marked as reconstructed and is never organism
  state.
- **Restart:** The same organism resumed from its runtime checkpoint on the
  same Body. It preserves consolidated state; it is not an uninterrupted run:
  the transition spanning the process boundary is not recorded and
  reacclimation follows.
- **Historical restore / owner-facing restore:** `from_checkpoint` reproduces
  the individual exactly as saved. The owner-facing restore additionally adopts
  canonical cognition when a legacy checkpoint lacks it, and records that
  transform in the lineage.
- **Re-embodiment:** The canonical move of a Symbiont into a fresh Body:
  knowledge is carried, Body state is replaced, execution authority is
  withdrawn.
- **Transplant (reduced seed):** The clean-embodiment apparatus's Body change.
  Embodiment-specific inference restarts from naive. Not the same contract as
  re-embodiment.
- **Unverified legacy origin:** Lineage marker carried by every save of an
  organism whose history includes a checkpoint accepted without a verifiable
  identity (schema 10 and earlier).
- **World:** The external side of the organism boundary, as a category. It has
  one constitutional implementation, the **World kernel** (`symbiont_world`),
  reached through the **World adapter** (`symbiont_lab.world`). A **World run**
  (`world.challenge`, `world.open`) is a run regime with complete consequences,
  hosted today by Physics3D; it does not involve the World kernel. Physics3D and
  synthetic Bodies are Body or study apparatus; habitats and host providers are
  boundaries the launcher supplies. See ADR-0060 and
  `docs/design/world/world-responsibility-map-v1.md`.
- **Continuity class:** What must happen to a piece of runtime state across a
  restart: `MUST_PRESERVE`, `MUST_RESET`, `MAY_RECOMPUTE`,
  `MUST_REAPPLY_CONFIG` or `MUST_INVALIDATE_AUTHORITY`. Every runtime field
  has exactly one, recorded in `src/symbiont/host/continuity.py`.
- **Percept:** A platform-neutral perception synthesized from a raw,
  platform-specific reading (see `docs/math/02-percepcion-aclimatacion-y-relaciones.md`).
