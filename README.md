# Symbiont Lab

**Experimental Artificial Life & Digital Organism Research**

> What happens if software is not told what its world means, but is instead given bounded ways to sense it, remember it, adapt to it, and develop within it?

**Symbiont Lab** is an experimental Artificial Life project exploring the development of persistent digital organisms.

A Symbiont can inhabit a consenting local computer, discover safe aspects of its environment, develop its own sensory repertoire, learn relationships and rhythms, allocate attention, maintain a model of its own perceptual health, form and revise beliefs, and modify a bounded cognitive structure through experience.

It is not a system-monitoring agent with biological terminology layered on top.

The research question is more fundamental:

**Can increasingly organism-like behavior emerge from developmental processes rather than being explicitly programmed as behavior?**

---

## The idea

Most software begins with a predefined model of its environment.

A monitoring application may be told:

```text
CPU usage
memory usage
disk pressure
network activity
```

and then be given rules describing what those things mean.

Symbiont is moving in the opposite direction.

On a supported host, its developmental path is closer to:

```text
consenting local environment
          │
          ▼
bounded safe surfaces
          │
          ▼
opaque signals
          │
          ▼
sensory development
     ┌────┴────┐
     │         │
 usefulness  redundancy
     │         │
     └────┬────┘
          ▼
adaptive sensing
          │
          ▼
relations and rhythms
          │
          ▼
attention + investigation
          │
          ▼
beliefs and self-model
          │
          ▼
plastic cognitive graph
          │
          ▼
learning + structural change
          │
          ▼
memory consolidation
          │
          ▼
continued development
```

The organism does not need to know that an opaque signal represents a particular Linux file, device, metric, or subsystem in order to learn from its behavior.

Meaning is intentionally separated from raw access to the host.

---

## Artificial life, not simulated biology

Symbiont does not attempt to reproduce a biological organism in software. There is no simulated cell, brain, metabolism, genome sequence, or nervous system that the implementation tries to imitate literally — instead, the project explores whether principles associated with living systems (senses, plasticity, attention, memory, forgetting, development) can have useful *functional* digital counterparts, without claiming biological equivalence.

That development runs as a plastic cognitive graph — nodes and edges that learn weights and bounded structure from experience, label-free — operating under an immutable kernel: a closed vocabulary of legal node/edge kinds, hard resource limits and mutation rules that the organism cannot learn its way around. The organism changes its **phenotype**, never its implementation; it does not generate source code, edit itself, or invent permissions.

For the full biological-analogy table and the endogenous cognition architecture, see [`docs/artificial-life-model.md`](docs/artificial-life-model.md).

---

## What makes a Symbiont different

### It develops senses

A resident Symbiont is not required to begin with a semantic sensor list.

On Linux, the host layer can discover a bounded set of explicitly vetted, aggregate, read-only numeric surfaces and expose them to development under opaque identities.

The organism learns which signals are available, variable, informative, redundant, costly, or unreliable.

Some senses become active.

Others remain exploratory.

Others become dormant.

Dormant senses retain a bounded possibility of being revisited so early developmental mistakes do not have to become permanent blindness.

---

### It learns relationships

Signals are not treated only as independent measurements.

Symbiont can learn bounded same-time and lagged associations between its senses and use those relationships when deciding how to allocate its limited perceptual resources.

Association does not automatically become causation.

That distinction is deliberate.

---

### It has limited attention

Observation is not free.

Symbiont operates under explicit resource budgets and must decide where additional sensing effort is useful.

Attention is therefore a resource-allocation process rather than a hidden classification system.

Uncertainty, information, cost, health and developmental state can influence where observation effort goes next.

---

### It can investigate

The organism can temporarily perform a higher-resolution **second look** at something it already has permission to observe.

This process is:

* local,
* bounded,
* read-only,
* cancellable,
* restricted to already-authorized perception.

Evidence gathered during investigation can revise an existing belief without erasing disagreement with prior evidence.

Contradiction is information.

---

### It models itself

Symbiont maintains a limited model of its own perceptual apparatus.

It can learn properties such as:

* sensory availability,
* observation cost,
* perceptual health,
* maturity,
* confidence,
* recency.

This allows the organism to reason not only about what it perceives, but about the reliability of the process doing the perceiving.

The self-model remains bounded and operational.

It is not a claim of consciousness or subjective self-awareness.

---

## Genome and phenotype

A Symbiont has two conceptually different forms of state.

### Genome

The genome contains inherited developmental parameters and limits.

It defines what kinds of development are possible for that organism.

It does not encode the final learned mind.

### Phenotype

The phenotype is what actually develops during a lifetime:

* selected senses,
* sensory relationships,
* learned baselines,
* self-model state,
* cognitive weights,
* cognitive topology,
* consolidated memory.

Two organisms beginning from the same genome can therefore diverge when exposed to different environments.

That divergence is one of the central experimental subjects of the project.

---

## Memory is not serialization

A restart should not be equivalent to freezing every microscopic variable and restoring it exactly.

Recent Symbiont development therefore distinguishes **persistent memory** from **runtime state**.

Stable learned information can be consolidated into durable representations, while transient activation and exact recent measurements are deliberately allowed to disappear.

For example:

```text
experience
    │
    ├── transient activity ──────────── discarded
    │
    ├── unstable adaptation ────────── not yet memory
    │
    ├── stable learned structure ───── consolidated
    │
    └── exceptional salient event ─── bounded fast path
                                         │
                                         ▼
                                      checkpoint
```

After restart, the organism reacclimates instead of pretending that a reconstructed approximation was an actual previous experience.

This makes persistence part of the biological model rather than merely an implementation convenience.

---

## One organism, two epistemic worlds

The repository deliberately separates the organism from the apparatus studying it.

```text
┌──────────────────────────────────────┐
│              symbiont                │
│                                      │
│            the organism              │
│                                      │
│ perception · cognition · memory      │
│ attention · self-model · runtime     │
│                                      │
│          cannot see below            │
└──────────────────┬───────────────────┘
                   │
          strict one-way boundary
                   │
┌──────────────────▼───────────────────┐
│            symbiont_lab              │
│                                      │
│       the scientific apparatus       │
│                                      │
│ experiments · evaluation · studies   │
│ evolution · archives · reproduction  │
└──────────────────────────────────────┘
```

The organism does not import the laboratory.

Synthetic ground truth belongs to the evaluator.

Experimental labels do not leak back into cognition.

This boundary is tested automatically.

It exists to prevent a particularly dangerous experimental mistake: believing that an organism discovered something which the experiment itself secretly told it.

---

## Laboratory evolution

Individual lifetime development and laboratory evolution are intentionally different processes.

A resident Symbiont can adapt its phenotype.

It **cannot reproduce itself**.

Generational evolution belongs exclusively to the laboratory apparatus:

```text
genome population
       │
       ▼
multiple environments
       │
       ▼
evaluation
       │
       ▼
Pareto selection
       │
       ▼
bounded genome mutation
       │
       ▼
new laboratory generation
```

Selection and reproduction therefore remain observable experimental operations rather than capabilities secretly possessed by a resident organism.

---

## Current state

Current release: **v0.59.5** — Milestones A through E2 are complete, most recently closed by biological memory consolidation (checkpoint schema v6, consolidated statistics, a salient-event fast path).

| Milestone | Capability                            | Status      |
| --------- | -------------------------------------- | ----------- |
| A         | Safe real perception                   | ✓           |
| B         | Adaptive host model                    | ✓           |
| C         | Autonomous inquiry and explanation     | ✓           |
| D         | Operational embodiment                 | ✓           |
| E         | Developmental embodiment               | ✓           |
| E2        | Endogenous plasticity + consolidation  | ✓           |
| F         | Cooperative species                    | not started |

Today, a Symbiont can develop on an unfamiliar consenting host, build a bounded sensory repertoire, learn sensory relationships, allocate observation effort, maintain a perceptual self-model, operate a plastic cognitive graph and consolidate learned state across restarts.

The current system should **not** be interpreted as evidence of consciousness, sentience or biological life.

It is an experimental digital organism architecture designed to make those distinctions measurable rather than rhetorical.

For the complete developmental history, see [ORGANISM.md](ORGANISM.md).

For planned research, see [docs/roadmap.md](docs/roadmap.md).

---

## Running Symbiont

Symbiont requires **Python 3.11+**.

### Install from the repository

```bash
git clone https://github.com/alessbarb/symbiont-lab.git
cd symbiont-lab

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

### Explore the available host surface

```bash
symbiont-lab host discover
```

### Observe real host readings

```bash
symbiont-lab host sample
```

### Run the organism

```bash
symbiont-lab organism run \
  --ticks 20 \
  --state-file organism-state.json
```

### Run as a resident process

```bash
symbiont-lab organism live \
  --state-file ~/.local/state/symbiont/organism.json \
  --interval 15 \
  --stdout
```

Resident development uses the safe developmental sensing path by default.

Stop it with `Ctrl-C` or `SIGTERM`. Durable state is checkpointed atomically during normal shutdown.

---

## Running the cognitive substrate

The cognitive system consists of a declarative genome and a plastic cognitive graph.

Example files are included in:

```text
examples/cognition/
├── genome.json
└── graph.json
```

Run them with:

```bash
symbiont-lab organism run \
  --ticks 20 \
  --min-samples 1 \
  --genome-file examples/cognition/genome.json \
  --graph-file examples/cognition/graph.json
```

The graph is developmental, but its initial legal substrate is explicit.

Once state exists, the learned phenotype is restored from the checkpoint rather than rebuilt from the original files.

---

## The Observatory

Symbiont includes a passive Observatory for inspecting the organism while it develops.

The direction of control is intentionally one-way:

```text
Symbiont ─────► Observatory
          state

Observatory ─X─► Symbiont
            commands
```

The Observatory may display what is happening.

It does not become part of cognition and does not control development.

See [`observatory/`](observatory/) for the visualization application.

---

## Experiments

The same repository contains a synthetic research environment for controlled studies.

Run a simulation:

```bash
symbiont-lab simulate --hosts 100 --steps 300 --seed 7
```

Run a declarative experiment:

```bash
symbiont-lab experiment run path/to/experiment.toml
```

Run a registered study:

```bash
symbiont-lab study run attention.replicated \
  --seeds 101,127,149
```

Reproduce an archived execution:

```bash
symbiont-lab reproduce .symbiont/runs/<run_id>/manifest.json
```

Verify experimental invariants:

```bash
symbiont-lab audit verify
```

Execution manifests preserve the information required to inspect and reproduce laboratory runs without exposing evaluator knowledge to the organism.

---

## Repository structure

```text
symbiont-lab/
│
├── src/
│   ├── symbiont/              # the organism
│   │   ├── core/              # beliefs, attention, runtime, self-model
│   │   ├── host/               # safe real-world perception
│   │   ├── cognition/          # endogenous cognitive plasticity
│   │   ├── environment/        # synthetic ecology
│   │   └── simulation/         # simulation primitives
│   │
│   └── symbiont_lab/           # scientific apparatus
│       ├── experiments/
│       ├── studies/
│       ├── evolution/
│       ├── archive/
│       └── cli/
│
├── observatory/                # passive organism visualization
├── experiments/                # declarative experiment definitions
├── examples/                   # runnable examples
├── research/                   # research records
├── docs/
│   ├── adr/                    # architectural decisions
│   └── design/                 # technical research designs
│
├── ORGANISM.md                 # complete organism evolution
└── README.md
```

The most important architectural rule is simple:

> **`symbiont` is the subject. `symbiont_lab` is the scientist.**

The subject must never secretly become the scientist.

---

## Safety model

Symbiont is intentionally constrained to a narrow environment.

Real-host perception is:

* local,
* explicitly enabled,
* read-only,
* aggregate,
* bounded,
* identity-minimized.

The immutable kernel prevents learned state from becoming executable capability.

The project does not permit a resident organism to acquire:

* arbitrary filesystem access,
* credentials,
* user content,
* remote host discovery,
* network scanning,
* exploitation,
* privilege escalation,
* stealth or evasion,
* operating-system modification,
* autonomous real-world action,
* self-propagation,
* autonomous reproduction.

Persistence is limited to owner-installed state.

Networked cooperation, when researched, remains a separate future milestone and does not imply propagation: any future exchange between organisms (see "Research direction" below) would still be explicit, consent-bound, and mediated by the same laboratory apparatus that already governs reproduction — never a capability a resident organism grants itself.

These constraints are part of the experimental definition of Symbiont, not temporary limitations waiting to be bypassed.

---

## What Symbiont is not

Symbiont is not:

**a security scanner**
It does not search a machine for vulnerabilities.

**an autonomous remediation agent**
It does not change the host in response to its observations.

**a self-modifying program**
Its learned phenotype changes; its executable kernel does not.

**a self-replicating system**
Reproduction exists only as an explicit laboratory operation.

**a simulation of a known animal**
Its architecture borrows biological principles without trying to recreate biological anatomy.

**a claim of consciousness**
Terms such as organism, perception, belief, attention and memory describe computational functions within the research model.

---

## Research principles

### Development before intelligence

Complex behavior should arise from accumulated development where possible rather than from increasingly elaborate hand-authored rules.

### Experience changes phenotype

An organism's history should matter.

Two genetically equivalent organisms living through different environments should be capable of becoming structurally different.

### No hidden teacher

Evaluator knowledge, experimental labels and synthetic ground truth must remain outside cognition.

### Boundedness is part of the organism

Memory, attention, sensing and plasticity operate under finite budgets.

Unlimited accumulation is not development.

### Forgetting matters

Removing obsolete structure is as important as creating new structure.

A system that can only accumulate eventually stops developing.

### Observation must not become control

The project may inspect the organism in detail without silently giving the observer authority over it.

### Claims must be weaker than evidence

A correlation is not causation.

A useful predictor is not understanding.

A self-model is not consciousness.

A persistent process is not automatically life.

---

## Research direction

The current focus is the development of a robust individual organism.

The next major research stage is **cooperative species**:

```text
individual development
        │
        ▼
safe knowledge exchange
        │
        ▼
evidence-aware trust
        │
        ▼
collective revision
        │
        ▼
consent-bound communication
        │
        ▼
adversarial resilience
```

The objective is not to create a swarm that spreads.

It is to investigate whether independently developed organisms can exchange abstract knowledge while preserving uncertainty, provenance, consent and individual epistemic independence.

---

## Documentation

Start here:

* [`ORGANISM.md`](ORGANISM.md) — complete developmental history and current status
* [`docs/artificial-life-model.md`](docs/artificial-life-model.md) — biological-analogy table and endogenous cognition architecture
* [`docs/roadmap.md`](docs/roadmap.md) — research roadmap and milestone exit conditions
* [`docs/design/endogenous-plasticity.md`](docs/design/endogenous-plasticity.md) — cognitive plasticity architecture
* [`docs/design/biological-memory-consolidation.md`](docs/design/biological-memory-consolidation.md) — consolidation and restart semantics
* [`docs/adr/`](docs/adr/) — architectural decision records
* [`research/`](research/) — experimental and research records

---

## The long-term question

Symbiont begins with software, not biology.

But software gives us something unusual: an environment in which development, memory, mutation, perception, inheritance, selection and ecology can all be instrumented precisely.

That makes it possible to ask a different question from conventional AI:

> **Instead of designing an intelligent system directly, how much organized behavior can emerge if we design the conditions under which a digital organism is allowed to develop?**

Symbiont Lab exists to investigate that question.
