# The artificial life model

This document expands two parts of the project's framing that are referenced
but not fully explained in [`README.md`](../README.md): why Symbiont is
described in biological vocabulary at all, and what "endogenous cognition"
actually means as a computational substrate.

---

## Artificial life, not simulated biology

Symbiont does not attempt to reproduce a biological organism in software.

There is no simulated cell, brain, metabolism, genome sequence, or nervous system that the implementation tries to imitate literally.

Instead, the project explores whether principles associated with living systems can have useful digital counterparts:

| Biology             | Symbiont                                     |
| ------------------- | -------------------------------------------- |
| Environment         | Local digital host or synthetic world        |
| Receptors           | Developed senses                             |
| Sensory development | Adaptive sense selection                     |
| Neural activity     | Cognitive activation                         |
| Synapses            | Plastic graph edges                          |
| Plasticity          | Weight and structural adaptation             |
| Attention           | Bounded allocation of observation effort     |
| Homeostasis         | Hard resource and developmental limits       |
| Memory              | Consolidated learned state                   |
| Forgetting          | Aging, pruning and bounded retention         |
| Development         | Lifetime change of the phenotype             |
| Genome              | Declarative developmental constraints        |
| Phenotype           | Developed cognitive and sensory structure    |
| Metaplasticity      | Adaptation of learning behavior              |
| Ecology             | Environment and, eventually, other organisms |

These are **functional analogies**, not claims of biological equivalence.

Symbiont is therefore best understood as a research organism within the field of **Artificial Life** — a piece of software whose development itself is the object of study.

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

* activation,
* eligibility,
* edge weights,
* prediction error,
* metaplastic parameters,
* bounded structural creation,
* pruning,
* lifecycle state.

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

For the full technical specification of this kernel (node/edge types, hard
limits, learning rules, structural plasticity, and safe-mode), see
[`docs/design/endogenous-plasticity.md`](design/endogenous-plasticity.md).
