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
- structural consolidation every 32 ticks;
- bounded Oja learning rate and eligibility decay;
- growth evidence threshold 0.18;
- minimum structural support 16;
- prune threshold 0.01;
- tentative lifetime 128 ticks;
- small bounded generational mutation policy.

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
these names are opaque `sense_*` identities. Admission is bounded by both the
genome soft node budget and `KernelLimits.max_nodes`.

A non-empty owner-authored graph is closed to implicit sense admission by
default. It receives only nodes the owner declared, preserving the meaning and
reproducibility of explicit cognition fixtures. This mode is persisted in the
cognitive checkpoint so a germinal graph that has already grown SENSE nodes
continues developing after restart instead of being mistaken for a closed
owner graph.

Sense admission is a routing boundary, not a learned structural mutation: the
sensory subsystem has already decided that the percept exists. The topology
revision still advances because Observatory must see the structural change.

Repeated co-activation of opaque SENSE nodes accumulates RAM-only support. At a
normal consolidation boundary, a supported pair may create a latent
`CONCEPT`. The first concept also creates the semantics-free `readout_core`,
and the concept is connected to it with a small tentative delayed edge. No
human meaning is assigned to either node. Generated latent IDs are opaque and
deterministic with respect to the existing graph occupancy, preserving
laboratory reproducibility without encoding host content.

Growth is bounded by:

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
> the individual.

Two organisms can therefore start from the same canonical birth and develop
different topologies solely because their experienced opaque signals differ.
