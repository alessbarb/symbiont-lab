# The artificial life model

This document expands two parts of the project's framing that are referenced but not fully explained in [`README.md`](../README.md): why Symbiont is described in biological vocabulary at all, and what "endogenous cognition" means as a computational substrate.

It also distinguishes **implemented analogues** from **planned organism functions**. Biological language in this project is a research model, not a claim that every listed process already exists.

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
| Homeostasis | Resource regulation, rollback, repair and viability control | partial / planned |
| Nutrition | Acquisition of potentially useful information | partial |
| Metabolism | Transformation and maintenance of information under finite compute | planned |
| Waste / excretion | Degradation and irreversible disposal of low-value state | planned |
| Dormancy | Minimal viable maintenance under pressure | planned |
| Death | Explicit irreversible closure of organism continuity | planned |
| Asexual reproduction | Clonal fission into daughter identities | planned |
| Sexual / paired reproduction | Genome recombination between compatible parents | planned |
| Heredity | Genetic, bounded epigenetic and cultural inheritance channels | planned |
| Ecology | Shared bounded habitats with finite resources and multiple organisms | planned |

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

## Reproduction and heredity

Future organism reproduction is intentionally distinct from existing laboratory evolution.

Two primary reproductive mechanisms are planned:

1. **clonal fission** — one organism closes its parent lifecycle and produces two daughter identities with the same genome and the same inheritable consolidated birth state;
2. **paired reproduction** — two compatible organisms contribute declared genome loci to a new validated offspring genome.

The project will keep genetic inheritance, optional bounded epigenetic inheritance and post-birth cultural transfer separate so their effects can be measured independently.

Reproduction is also distinct from propagation. A Symbiont may eventually express reproductive readiness, but materializing descendants remains an authorized habitat operation with explicit carrying capacity and resource allocation.

---

## Ecology

A digital ecology begins only after individual organisms have their own physiology and heredity.

A habitat provides finite shared resources, population bounds and declared interaction channels. Within those constraints the project can study whether organisms compete, coexist, specialize, cooperate, exchange knowledge, form mutual dependencies or fail to persist.

Cooperation is therefore a possible ecological outcome, not a required behavior encoded into the organism in advance.
