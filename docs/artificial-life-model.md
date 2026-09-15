# The artificial life model

This document expands two parts of the project's framing that are referenced but not fully explained in [`README.md`](../README.md): why Symbiont is described in biological vocabulary at all, and what "endogenous cognition" means as a computational substrate.

It distinguishes the functional analogues implemented through Milestone H from capabilities that remain outside the current roadmap. Biological language in this project is a research model, not a claim of biological equivalence.

---

## Artificial life, not simulated biology

Symbiont does not attempt to reproduce a biological organism literally in software.

There is no simulated cell, brain, stomach, DNA chemistry or nervous system that the implementation tries to imitate anatomically.

Instead, the project explores whether principles associated with living systems can have useful digital counterparts:

| Biology / life function | Symbiont counterpart | State |
| --- | --- | --- |
| Environment | Local digital host, synthetic world or future bounded habitat | implemented / expanding |
| Receptors | Developed senses | implemented |
| Sensory development | Adaptive sense selection | implemented |
| Neural activity | Cognitive activation | implemented |
| Synapses | Plastic graph edges | implemented |
| Plasticity | Weight and structural adaptation | implemented |
| Attention | Bounded allocation of observation effort | implemented |
| Memory | Consolidated learned state | implemented |
| Forgetting | Aging, pruning and bounded retention | implemented |
| Development | Lifetime change of phenotype | implemented |
| Genome | Declarative developmental constraints | implemented |
| Phenotype | Developed cognitive and sensory structure | implemented |
| Metaplasticity | Adaptation of learning behavior | implemented |
| Homeostasis | Resource regulation, rollback, repair and viability control | implemented |
| Nutrition | Acquisition of potentially useful information | implemented |
| Metabolism | Transformation and maintenance of information under finite compute | implemented |
| Waste / excretion | Degradation and irreversible disposal of low-value state | implemented |
| Dormancy | Minimal viable maintenance under pressure | implemented |
| Death | Explicit irreversible closure of organism continuity | implemented |
| Asexual reproduction | Habitat-authorized clonal budding from developmental pressure | implemented |
| Sexual / paired reproduction | Genome recombination between compatible parents | implemented |
| Heredity | Genetic, bounded epigenetic and cultural inheritance channels | implemented |
| Ecology | Shared bounded habitats with finite resources and multiple organisms | implemented |

These are **functional analogies**, not claims of biological equivalence.

Symbiont is therefore best understood as a research organism within the field of **Artificial Life** — a piece of software whose development, maintenance, inheritance and eventual ecology are themselves objects of study.

---

## Functional analogy, not decorative vocabulary

A biological term is useful in Symbiont only when it points to a computational role with measurable consequences.

For example:

- **metabolism** must mean more than "the program uses CPU"; it must regulate intake, transformation, maintenance cost and resource pressure;
- **excretion** must mean more than garbage collection; it must represent deliberate irreversible disposal of state whose continued maintenance is no longer justified;
- **homeostasis** must mean more than hard limits; the organism must alter activity to remain viable under changing internal pressure;
- **reproduction** must mean more than copying a directory; it must create a new organism identity with explicit heredity and lineage semantics;
- **death** must mean more than process exit; it must irreversibly close one organism identity's continuity;
- **ecology** must mean more than message passing; multiple organisms must share finite resources and be able to affect one another through declared ecological channels.

This criterion is intended to prevent biological language from becoming metaphorical decoration around conventional software features.

---

## Endogenous cognition

Symbiont contains a plastic cognitive graph whose structure can change during the lifetime of an organism.

The graph uses a closed vocabulary of node and edge types defined by an immutable kernel.

```text
SENSE
  │
  ▼
CONCEPT / STATE / PREDICTOR / GATE
  │
  ▼
READOUT
```

Experience can affect:

- activation,
- eligibility,
- edge weights,
- prediction error,
- metaplastic parameters,
- bounded structural creation,
- pruning,
- lifecycle state.

Learning is label-free.

External experimental ground truth is not supplied to cognition as a teaching signal.

The organism changes its **phenotype**, not its implementation.

### Plastic data under an immutable kernel

This distinction is fundamental:

```text
immutable kernel
      │
      ├── legal node kinds
      ├── legal edge kinds
      ├── hard resource limits
      ├── safety invariants
      └── mutation rules
              │
              ▼
           genome
              │
              ▼
       initial phenotype
              │
              ▼
           experience
              │
              ▼
      developed phenotype
```

Symbiont does **not** generate source code, edit its executable implementation, dynamically create permissions, invent commands, or learn its way around kernel limits.

Self-development happens inside a deliberately closed computational substrate.

For the full technical specification of this kernel — node/edge types, hard limits, learning rules, structural plasticity and safe mode — see [`docs/design/endogenous-plasticity.md`](design/endogenous-plasticity.md).

---

## Digital physiology

The next developmental stage adds an explicit internal economy around existing learning and memory mechanisms.

The intended functional loop is:

```text
environment
    │
    ▼
information intake
    │
    ▼
valuation
    │
    ├── useful ─────► assimilation ─► activity / learning / memory
    │
    └── low value ──► rejection

retained state
    │
    ▼
maintenance cost
    │
    ├── justified ──► retain / repair
    │
    └── unjustified ► degrade ─► waste ─► excrete
```

The purpose is not to identify a literal digital calorie. It is to make finite computational resources part of organism physiology rather than an external deployment concern only.

---

## Death and continuity

A future Symbiont life cycle distinguishes process state from organism continuity.

Stopping a process is not death. Restarting a valid durable state is not birth. Death is an explicit terminal transition that closes one organism identity irreversibly.

A dead organism may leave an archival final record, but normal restore must not silently resume it. Any later reconstruction from historical material creates a new organism identity.

Death also participates in population ecology: live habitat resources are released when continuity closes, while bounded lineage/history records may remain.

---

## Reproduction and heredity

Resident reproduction is intentionally distinct from existing laboratory evolution.

Two primary reproductive mechanisms are implemented:

1. **clonal budding** — one viable parent remains alive while a new descendant receives the same genome, a new organism identity and a canonical empty germinal phenotype;
2. **paired reproduction** — two compatible organisms contribute declared genome loci to a new validated offspring genome.

Clonal budding does not copy the parent's developed CognitiveGraph, beliefs, sensory baselines, learned weights or lifetime memory. The purpose is to transmit genotype while allowing phenotype to develop independently.

Reproductive readiness is not triggered merely by age or by touching a node limit. It is intended to arise when a viable adaptive organism persistently accumulates valid developmental evidence that cannot be expressed because its bounded phenotype has exhausted relevant capacity.

A successful birth consumes the accumulated reproductive pressure that justified it and, once physiology exists, carries an explicit reproduction cost. This prevents one saturation event from becoming permanently reusable credit for repeated births.

The implementation keeps genetic inheritance, optional bounded epigenetic inheritance and post-birth cultural transfer separate so their effects can be measured independently.

Organism lineage is also separate from genome lineage. Two clonal descendants can share the exact same `genome_id` while having different `organism_id` values and independent life histories. A new genome identity is required only when heritable genome material changes.

Reproduction is distinct from propagation. A Symbiont may express reproductive readiness, but materializing descendants remains an authorized habitat operation with explicit carrying capacity, resource allocation and transactional lineage registration. A full habitat blocks birth rather than silently killing another organism to make room.

The detailed design is in [`docs/design/reproduction-death-population.md`](design/reproduction-death-population.md).

---

## Ecology

A digital ecology begins only after individual organisms have their own physiology and heredity.

A habitat provides finite shared resources, population bounds and declared interaction channels. Within those constraints the project can study whether organisms compete, coexist, specialize, cooperate, exchange knowledge, form mutual dependencies or fail to persist.

Carrying capacity is a hard habitat invariant, not an organism-controlled parameter. Births require habitat authorization, and death releases live allocation. Population dynamics therefore arise from bounded birth, resource pressure, survival and death rather than unrestricted process multiplication.

Cooperation is therefore a possible ecological outcome, not a required behavior encoded into the organism in advance.
