# Canonical birth cognition

## Decision

Every owner-facing resident Symbiont has cognition.

The canonical birth contract is:

```text
canonical genome      inherited developmental rules
        +
empty germinal graph  no owner-authored semantics
        ↓
developed opaque senses become SENSE nodes
        ↓
experience creates latent structure
        ↓
reversible homeostasis preserves developmental viability
        ↓
checkpoint             individual phenotype
```

The two packaged resources are:

- `src/symbiont/cognition/defaults/base-genome.json`
- `src/symbiont/cognition/defaults/base-graph.json`

They are package data and are loaded through `symbiont.cognition.birth` rather
than by repository-relative filesystem paths.

## Genome v1

`genome_symbiont_base_v1` deliberately contains developmental dispositions,
not host semantics:

- zero initial concepts;
- soft budget of 64 total graph nodes and 384 edges;
- at most 32 cognitive SENSE nodes at once;
- disconnected SENSE retention of 256 ticks before normal stale eviction;
- structural consolidation every 32 ticks;
- bounded Oja learning rate and eligibility decay;
- growth evidence threshold 0.18;
- minimum structural support 16;
- prune threshold 0.01;
- tentative lifetime 128 ticks;
- small bounded generational mutation policy.

The dedicated SENSE budget is intentionally smaller than the total node
budget. Sensory discovery can still range over the host's full bounded signal
surface; graph SENSE nodes are the current cognitive interface, not an
append-only archive of every sense ever selected. The remaining node capacity
is therefore available for latent cognition.

Hard safety/resource ceilings remain `KernelLimits`; a genome can only be more
restrictive than the kernel, never less.

The compatibility range is intentionally restricted to the current 0.59
kernel series (`>=0.59,<0.60`). A future kernel series must explicitly review
and revise the birth genome rather than inheriting compatibility by accident.

## Germinal graph

The canonical graph is exactly:

```json
{"nodes": [], "edges": []}
```

It contains no `system_load`, `storage_pressure`, human-labelled concept,
readout meaning, path, provider identity or host ontology.

The examples under `examples/cognition/` remain useful owner-authored fixtures;
they are not the resident's natural birth topology.

## Development from an empty graph

`CognitiveBridge` treats an empty graph as germinal and enables endogenous
sense admission. Percept names already developed by the governed
`AdaptiveSenseModel` may then become `SENSE` nodes. In native resident mode
these names are opaque `sense_*` identities. Admission is bounded by
`development.sense_node_budget`, the total soft node budget and
`KernelLimits.max_nodes`.

A non-empty owner-authored graph is closed to implicit sense admission by
default. It receives only nodes the owner declared, preserving the meaning and
reproducibility of explicit cognition fixtures. This mode is persisted in the
cognitive checkpoint so a germinal graph that has already grown SENSE nodes
continues developing after restart instead of being mistaken for a closed
owner graph.

Sense admission is a routing boundary, not a learned structural mutation: the
sensory subsystem has already decided that the percept exists. The topology
revision still advances because Observatory must see the structural change.

Repeated co-activation of opaque SENSE nodes accumulates RAM-only concept
candidate support. SENSE↔SENSE evidence is not placed in the generic edge pool,
because a SENSE can never be the target of a cognitive edge. At a normal
consolidation boundary, a supported pair may create a latent `CONCEPT`. The
first concept also creates the semantics-free `readout_core`, and the concept
is connected to it with a small tentative delayed edge. No human meaning is
assigned to either node. Generated latent IDs are opaque and deterministic
with respect to existing graph occupancy, preserving laboratory reproducibility
without encoding host content.

Generic edge support is based on real transmitted contribution, not on the
destination node already exceeding the global node-activity threshold. This
allows a newly born weak edge to accumulate evidence while its target is still
below the activation level used for higher-level coactivation decisions.

Growth is bounded by:

- `development.sense_node_budget`;
- `development.soft_node_budget`;
- `development.soft_edge_budget`;
- `structure.grow_threshold`;
- `structure.minimum_support`;
- the hard per-consolidation mutation cap;
- all existing `CognitiveGraph` validation and kernel ceilings.

New edges are immediately seeded into the durable weight-stability tracker so
a checkpoint taken directly after structural growth is valid and cannot expose
an unconsolidated live weight by accident. If an edge is later removed, its
RAM-only stability evidence is discarded; an edge recreated with the same
endpoint tuple starts a fresh synaptic lifetime.

## Reversible structural lifecycle

A germinal graph is not append-only. Its consolidation cycle is:

```text
observe / learn
      ↓
prune expired edges
      ↓
GC orphan CONCEPT / READOUT nodes
      ↓
evict stale disconnected SENSE nodes
      ↓
recompute free capacity
      ↓
grow concepts, then legal generic edges
      ↓
commit the complete batch atomically
```

`remove_node` is a kernel-validated structural mutation. A node may be removed
only after all of its incident edges have already been removed in the projected
batch. This keeps graph reconstruction atomic and prevents dangling topology.

A germinal SENSE has a `last_seen_tick` lease. Disconnected SENSE nodes may be
reclaimed after `sense_retention_ticks`, and excess disconnected SENSE nodes
are reclaimed when an older checkpoint exceeds the current sensory budget.
Connected SENSE nodes are not silently detached merely to satisfy a lease.

A born concept records durable structural provenance as
`ConceptLineage {concept_id, parent_ids, born_tick}`. The lineage remains
available even if its current edges later disappear, so concept identity does
not accidentally depend on transient wiring. If a CONCEPT or READOUT remains
isolated beyond the structural grace period, it becomes eligible for node GC
and releases its slot.

Candidate evidence that has not crossed a structural consolidation boundary
remains working memory rather than durable topology.

## Developmental viability and recovery

`CognitiveGraph` validity answers whether each node, edge, delay and bound is
legal. Germinal viability additionally asks whether the individual can still
develop. The bridge therefore derives a topology-health state:

- `GERMINAL` — no latent cognitive structure yet;
- `DEVELOPING` — latent structure exists but no complete SENSE→READOUT path;
- `CONNECTED` — at least one structural SENSE→READOUT path exists;
- `ADAPTIVE` — at least one such path consists of established supported edges;
- `DEGENERATE` — a germinal topology is syntactically valid but trapped by a
  zero-edge latent structure, exhausted node budget, or excess sensory
  occupancy without a viable path;
- `RECOVERING` — bounded maintenance is reclaiming a previously degenerate
  topology.

Checkpoint restore classifies the topology before new growth. A legacy
worker-3-style graph that is full, contains orphan latent nodes and has zero
edges enters recovery without reconstructing any lost edge or inventing
missing lineage. Normal reacclimation remains in force; when structural
maintenance resumes, recovery removes only structure whose current topology
proves reclaimable and proceeds under the ordinary mutation cap.

Observatory receives the derived topology-health class and recovery flag as
bounded cognition telemetry. It still receives structural topology separately
and never receives raw learned weights through this state contract.

Owner-authored graphs (`develop_senses == false`) are explicitly excluded from
automatic node GC, sensory eviction and recovery. Health may describe them,
but the germinal lifecycle does not rewrite owner-declared structure.

## Continuity and legacy adoption

A checkpoint that already carries a genome and cognitive bridge always wins.
The canonical birth files are never re-applied on restart and therefore never
reset a learned phenotype.

Owner-facing resident restore paths (`symbiont-lab organism ...` and
`observatory/resident.py`) also adopt the canonical genome and empty graph when
loading a legacy checkpoint written before cognition existed. Existing
acclimation, sensory development, self-model, evidence and tick continuity are
restored first; only the absent cognitive layer is supplied. The next
checkpoint makes that adoption durable.

Generic `OrganismRuntime.from_checkpoint()` deliberately retains exact
historical behavior and does **not** adopt cognition automatically. This keeps
laboratory reproduction of old genome-less individuals possible.

## Owner overrides

`--genome-file` replaces the canonical genome for a first birth.
`--graph-file` replaces the germinal graph and requires an explicit
`--genome-file`. Existing checkpoints ignore birth overrides because the
individual's persisted phenotype has precedence.

A non-empty override graph is treated as owner-authored and does not
spontaneously acquire undeclared SENSE nodes. An explicitly empty override
graph retains germinal behavior and may develop opaque SENSE nodes.

## Invariant

> Genome is inheritance. The germinal graph is tabula rasa. The checkpoint is
> the individual. Structural forgetting must never destroy the ability to
> learn again.

Two organisms can therefore start from the same canonical birth and develop
different topologies solely because their experienced opaque signals differ,
while failed structural hypotheses can release capacity for later development.
