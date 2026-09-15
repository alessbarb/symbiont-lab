# Symbiont Lab

**Experimental Artificial Life & Digital Organism Research**

> What happens if software is not told what its world means, but is instead given bounded ways to sense it, remember it, adapt to it, maintain itself, reproduce and eventually participate in an ecology?

**Symbiont Lab** is an experimental Artificial Life project exploring the development of persistent digital organisms.

A Symbiont is not intended to remain a fixed monitoring agent with biological terminology layered on top. The organism itself is the subject of the project: each stage asks which additional life-like functions can be implemented as genuine computational processes rather than as metaphors or hand-authored behavior.

The central research question is:

> **Can increasingly organism-like organization emerge from developmental processes rather than being explicitly programmed as final behavior?**

The current organism already develops senses, learns relationships and rhythms, allocates attention, maintains a model of its own perceptual health, forms and revises beliefs, changes a bounded cognitive structure through experience, and consolidates memory across restarts.

The next research direction is broader: give the organism a **digital physiology**, then **reproduction and heredity**, and only then place multiple independently developing organisms inside a true **digital ecology**.

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

Symbiont moves in the opposite direction.

On a supported host, its current developmental path is closer to:

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

The longer-term developmental loop is larger:

```text
environment
    │
    ▼
perception / intake
    │
    ▼
assimilation
    │
    ├──► activity
    ├──► beliefs
    ├──► structure
    └──► consolidated memory
    │
    ▼
maintenance / homeostasis
    │
    ▼
degradation
    │
    ▼
waste / excretion
    │
    ▼
continued viability
    │
    ├──► dormancy / recovery
    ├──► death
    └──► reproductive readiness
             │
             ▼
      habitat-authorized birth
             │
             ▼
           ecology
```

That loop is a research direction, not a claim about the current release.

---

## Artificial life, not simulated biology

Symbiont does not attempt to reproduce a biological organism literally in software. There is no simulated cell, stomach, nervous system or DNA chemistry that the implementation tries to imitate.

Instead, the project asks whether principles associated with living systems can have useful **functional digital counterparts**.

The analogy is therefore operational:

| Life function | Digital counterpart in Symbiont | State |
| --- | --- | --- |
| Perception | Developed opaque senses | implemented |
| Response | Attention, investigation and belief revision | implemented |
| Development | Lifetime sensory and cognitive change | implemented |
| Memory | Consolidated learned state | implemented |
| Self-monitoring | Perceptual health, cost and confidence | implemented |
| Homeostasis | Resource governance, rollback and safe mode | implemented |
| Nutrition | Acquisition of potentially useful information | implemented |
| Metabolism | Transformation of information under computational budgets | implemented |
| Waste / excretion | Active degradation and irreversible disposal of low-value state | implemented |
| Dormancy / viability | Organism-level stress, recovery and life-state semantics | implemented |
| Death | Irreversible closure of organism continuity | implemented |
| Reproduction | Habitat-authorized clonal budding and paired genome recombination | implemented |
| Heredity | Genome transmission, recombination and bounded variation | implemented |
| Ecology | Shared habitats, finite resources and organism interaction | implemented |

These are functional analogies, not claims of biological equivalence.

For the broader biological-analogy model and endogenous cognition architecture, see [`docs/artificial-life-model.md`](docs/artificial-life-model.md).

---

## What makes a Symbiont different today

### It develops senses

A resident Symbiont is not required to begin with a semantic sensor list.

On Linux, the host layer can discover a bounded set of explicitly vetted, aggregate, read-only numeric surfaces and expose them to development under opaque identities.

The organism learns which signals are available, variable, informative, redundant, costly, or unreliable.

Some senses become active. Others remain exploratory. Others become dormant.

Dormant senses retain a bounded possibility of being revisited so early developmental mistakes do not have to become permanent blindness.

### It learns relationships

Signals are not treated only as independent measurements.

Symbiont can learn bounded same-time and lagged associations between its senses and use those relationships when deciding how to allocate its limited perceptual resources.

Association does not automatically become causation.

### It has limited attention

Observation is not free.

Symbiont operates under explicit resource budgets and must decide where additional sensing effort is useful. Uncertainty, information, cost, health and developmental state can influence where observation effort goes next.

### It can investigate

The organism can temporarily perform a higher-resolution **second look** at something it already has permission to observe.

The process is local, bounded, read-only, cancellable and restricted to already-authorized perception.

Evidence gathered during investigation can revise an existing belief without erasing disagreement with prior evidence.

Contradiction is information.

### It models itself

Symbiont maintains a limited model of its own perceptual apparatus.

It can learn sensory availability, observation cost, perceptual health, maturity, confidence and recency. This allows the organism to reason not only about what it perceives, but about the reliability of the process doing the perceiving.

The self-model is operational. It is not a claim of consciousness or subjective self-awareness.

---

## Genome and phenotype

A Symbiont has two conceptually different forms of state.

### Genome

The genome contains inherited developmental parameters and limits.

It defines what kinds of development are possible for an organism. It does not encode the final learned mind.

### Phenotype

The phenotype is what actually develops during a lifetime:

- selected senses,
- sensory relationships,
- learned baselines,
- self-model state,
- cognitive weights,
- cognitive topology,
- consolidated memory.

Two organisms beginning from the same genome can therefore diverge when exposed to different environments.

That divergence is one of the central experimental subjects of the project.

---

## Memory is not serialization

A restart should not be equivalent to freezing every microscopic variable and restoring it exactly.

Symbiont therefore distinguishes **persistent memory** from **runtime state**.

Stable learned information can be consolidated into durable representations, while transient activation and exact recent measurements are deliberately allowed to disappear.

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

This makes persistence part of the life model rather than merely an implementation convenience.

---

## The next step: digital physiology

Perception and learning are not enough to make an organism-like system.

A viable organism must regulate flows through itself: what it takes in, what it transforms, what it retains, what it spends resources maintaining, and what it eventually removes.

Symbiont's next milestone therefore treats information and computation as a bounded internal economy.

```text
information intake
       │
       ▼
   evaluation
    ┌──┴──────────────┐
    │                 │
    ▼                 ▼
assimilation       low value
    │                 │
    ▼                 ▼
learning          degradation
memory                │
structure              ▼
    │               waste
    │                 │
    └──────┬──────────┘
           ▼
       homeostasis
```

The intent is not to pretend that CPU cycles are literal biological energy or that deleted objects are literal excrement.

The research question is functional: **can the organism maintain viability by regulating acquisition, transformation, retention and disposal under finite computational resources?**

This gives existing mechanisms such as pruning, forgetting, memory consolidation, safe mode and resource budgets a common physiological interpretation instead of leaving them as unrelated implementation features.

---

## Reproduction and heredity

Reproduction is a future organism capability, not a permanent prohibition.

Symbiont will investigate at least two forms.

### Clonal budding

A viable parent remains alive while a new descendant is born with a new organism identity and the same genome.

The descendant does **not** copy the parent's developed CognitiveGraph, learned weights, sensory baselines, beliefs or lifetime memory. It begins from the canonical empty germinal phenotype and develops independently.

```text
               parent A
                  │
      persistent developmental pressure
                  │
                  ├───────────────┐
                  │               │
                  ▼               ▼
             parent A          child B
             continues         same genome
             same phenotype    new identity
                               empty phenotype
```

Saturation alone is not a reproduction command. The intended readiness signal is persistent valid developmental evidence that cannot be expressed because the current individual has exhausted relevant bounded phenotype capacity.

A successful birth consumes the reproductive pressure that justified it so the same historical saturation event cannot generate descendants repeatedly.

### Paired reproduction

Two organisms contribute heritable genome material to a new Symbiont.

```text
Symbiont A               Symbiont B
 genome A                 genome B
     │                        │
     └──────────┐  ┌──────────┘
                ▼  ▼
             recombination
                  │
                  ▼
               genome C
                  │
                  ▼
             Symbiont C
```

Genome recombination must operate on defined heritable units and the resulting genome must satisfy the same immutable kernel and validation rules as every other organism.

Learned lifetime state is not automatically genetic. Future experiments may separately study genetic inheritance, bounded epigenetic carry-over and post-birth cultural knowledge transfer rather than collapsing them into one mechanism.

### Reproduction is not propagation

An organism may eventually become reproductively ready or request reproduction, but **materializing a new resident process belongs to an authorized habitat**, not to an unrestricted self-copy mechanism.

Birth remains subject to explicit consent, hard carrying capacity, resource limits and organism-lineage accounting. A full habitat blocks birth rather than automatically killing another organism to make room.

A reproductive Symbiont is not a worm.

### Death is not process exit

A stopped process may later resume the same viable organism. Death is different: it irreversibly closes one organism identity's continuity.

A dead checkpoint may remain as a historical artifact, but normal restore must reject it. Any later reconstruction from historical material creates a new identity rather than silently resurrecting the dead organism.

The detailed life-cycle design is in [`docs/design/reproduction-death-population.md`](docs/design/reproduction-death-population.md).

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
│ evolution · archives · selection     │
└──────────────────────────────────────┘
```

The organism does not import the laboratory.

Synthetic ground truth belongs to the evaluator. Experimental labels do not leak back into cognition.

This boundary exists to prevent a particularly dangerous experimental mistake: believing that an organism discovered something which the experiment itself secretly told it.

---

## Evolution and reproduction are different

Symbiont already has **laboratory evolution**. Genome mutation and Pareto selection happen in the scientific apparatus during explicit experiments.

The current resident organism does **not yet** reproduce.

Future biological reproduction will be different: it will become part of the organism's life cycle while actual birth remains mediated by an authorized habitat.

Organism lineage and genome lineage are also different. Exact clonal descendants may share one `genome_id` while having distinct `organism_id` values and independent life histories. A new genome identity is required only when the heritable genome changes.

That distinction gives the project three different inheritance processes to study independently:

```text
lifetime development     organism changes during life
          │
          ▼
biological reproduction  organism creates descendants
          │
          ▼
laboratory evolution     experiment selects across generations
```

Conflating those three processes would make experimental conclusions much weaker.

---

## Current state

Current release: **v0.77.1** — Milestones A through H are complete. Milestone I enters implementation with bounded runtime physiology, explicit metabolic intake, irreversible habitat release and a hard post-death execution boundary. J and K remain partial implementation tracks with their respective gates open. v0.76.1-v0.76.46 remain historical hardening releases.

| Milestone | Capability | Status |
| --- | --- | --- |
| A | Safe real perception | ✓ |
| B | Adaptive host model | ✓ |
| C | Autonomous inquiry and explanation | ✓ |
| D | Operational embodiment | ✓ |
| E | Developmental embodiment | ✓ |
| E2 | Endogenous plasticity + memory consolidation | ✓ |
| F | Digital physiology | ✓ |
| G | Reproduction & heredity | ✓ |
| H | Digital ecology | ✓ |

Today, a Symbiont can develop on an unfamiliar consenting host, regulate bounded physiological state, maintain explicit viability and lineage semantics, participate in finite habitats, exchange bounded knowledge through authorized local channels and expose ecological/population outcomes for laboratory study.

Those are developmental frontiers, not definitions of what Symbiont must never become.

The current system should not be interpreted as evidence of consciousness, sentience or biological life. It is an experimental digital organism architecture designed to make those distinctions measurable rather than rhetorical.

For the complete developmental history, see [`ORGANISM.md`](ORGANISM.md).

For the complete roadmap history and the defined-but-unimplemented Milestones I and J, see [`docs/roadmap.md`](docs/roadmap.md).

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

```text
Symbiont ─────► Observatory
          state

Observatory ─X─► Symbiont
            commands
```

The Observatory may display what is happening. It does not become part of cognition and does not control development.

See [`observatory/`](observatory/) for the visualization application.

---

## Experiments

The same repository contains a synthetic research environment for controlled studies.

```bash
# Run a synthetic simulation
symbiont-lab simulate --hosts 100 --steps 300 --seed 7

# Run a declarative experiment
symbiont-lab experiment run path/to/experiment.toml

# Run a registered study
symbiont-lab study run attention.replicated --seeds 101,127,149

# Reproduce an archived execution
symbiont-lab reproduce .symbiont/runs/<run_id>/manifest.json

# Verify experimental invariants
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
│   │   ├── host/              # safe real-world perception
│   │   ├── cognition/         # endogenous cognitive plasticity
│   │   ├── environment/       # synthetic ecology
│   │   └── simulation/        # simulation primitives
│   │
│   └── symbiont_lab/          # scientific apparatus
│       ├── experiments/
│       ├── studies/
│       ├── evolution/
│       ├── archive/
│       └── cli/
│
├── observatory/               # passive organism visualization
├── experiments/               # declarative experiment definitions
├── examples/                  # runnable examples
├── research/                  # research records
├── docs/
│   ├── adr/                   # architectural decisions
│   └── design/                # technical research designs
│
├── ORGANISM.md                # complete organism evolution
└── README.md
```

The most important architectural rule is simple:

> **`symbiont` is the subject. `symbiont_lab` is the scientist.**

The subject must never secretly become the scientist.

---

## Permanent invariants

Symbiont is expected to gain capabilities over time. Therefore the project distinguishes **permanent invariants** from **current developmental limitations**.

The following are intended to remain true even as the organism becomes more capable:

- access to a real host is explicit, revocable and capability-bounded;
- the organism does not obtain new permissions by learning around the kernel;
- credentials and privilege-escalation mechanisms are outside the organism's developmental substrate;
- no stealth, concealment or evasion is used to preserve residence;
- no exploitation is used to acquire resources or capabilities;
- persistence is transparent and owner-controlled;
- reproduction never means covert or uncontrolled propagation;
- newly materialized organisms require an authorized habitat, a carrying-capacity slot and bounded resources;
- dead organism identities cannot be normally resumed as though continuity never closed;
- hard CPU, memory, storage and communication limits remain outside learned control;
- experimental ground truth never becomes a hidden teacher for organism cognition;
- observation by the laboratory does not silently become control by the laboratory.

These are architectural constraints, not statements that Symbiont must remain permanently read-only, solitary or incapable of reproduction.

Any future capability that writes to a host, communicates over a network, performs real-world action or materializes descendants must cross an explicit design and consent gate before implementation.

---

## Current post-roadmap boundaries

The current release does not autonomously modify its host, discover remote peers, instantiate itself on other machines, open network sockets or perform remediation. These are deliberate post-roadmap boundaries, not missing implementations. Any future write, network, action or propagation capability requires a new design and consent gate.

---

## Research principles

### Development before intelligence

Complex behavior should arise from accumulated development where possible rather than from increasingly elaborate hand-authored rules.

### Physiology before ecology

Before asking organisms to coexist, each organism should have a coherent internal economy: acquisition, assimilation, maintenance, degradation, disposal and viability.

### Ecology before society

Cooperation must not be hard-coded as the inevitable endpoint of multiple organisms. Competition, coexistence, specialization, symbiosis and cooperation should be measurable ecological outcomes.

### Experience changes phenotype

An organism's history should matter. Two genetically equivalent organisms living through different environments should be capable of becoming structurally different.

### No hidden teacher

Evaluator knowledge, experimental labels and synthetic ground truth remain outside cognition.

### Boundedness is part of the organism

Memory, attention, sensing, metabolism and plasticity operate under finite budgets. Unlimited accumulation is not development.

### Forgetting is a life function

Removing obsolete state is as important as creating new state. A system that can only accumulate eventually stops developing.

### Reproduction is not deployment

Reproductive readiness may become an organism capability; creating a new process remains a habitat-mediated, consent-bound event under hard carrying capacity.

### Death is not shutdown

Stopping a viable process preserves the possibility of continuity. Death explicitly closes one organism identity and normal restore may not erase that event.

### Observation must not become control

The project may inspect the organism in detail without silently giving the observer authority over its cognition.

### Claims must be weaker than evidence

A correlation is not causation. A useful predictor is not understanding. A self-model is not consciousness. A persistent, adaptive and reproductive process is not automatically biological life.

---

## Research direction

The roadmap now follows three major stages:

```text
INDIVIDUAL DEVELOPMENT
        │
        ▼
F — DIGITAL PHYSIOLOGY
    intake
    assimilation
    metabolism
    waste / excretion
    maintenance
    dormancy / viability
    death
        │
        ▼
G — REPRODUCTION & HEREDITY
    organism identity
    organism lineage
    reproductive pressure
    clonal budding
    genome recombination
    inheritance
    bounded mutation
        │
        ▼
H — DIGITAL ECOLOGY
    habitats
    hard carrying capacity
    birth / death resource accounting
    resource competition
    knowledge exchange
    trust
    cooperation / coexistence
    population dynamics
```

The ecological stage is intentionally not called **cooperative species** anymore.

Cooperation is scientifically interesting only if it can arise as one possible relationship between organisms rather than being encoded as the required outcome.

The long-term goal is to make it possible to study digital organisms that develop independently, maintain themselves under finite resources, reproduce through explicit heredity mechanisms, die through explicit irreversible life-cycle semantics, and interact inside bounded habitats where ecological relationships can emerge and be measured.

---

## Documentation

Start here:

- [`ORGANISM.md`](ORGANISM.md) — complete developmental history and current status
- [`docs/artificial-life-model.md`](docs/artificial-life-model.md) — biological-analogy table and endogenous cognition architecture
- [`docs/roadmap.md`](docs/roadmap.md) — research roadmap and milestone exit conditions
- [`docs/design/endogenous-plasticity.md`](docs/design/endogenous-plasticity.md) — cognitive plasticity architecture
- [`docs/design/biological-memory-consolidation.md`](docs/design/biological-memory-consolidation.md) — consolidation and restart semantics
- [`docs/design/reproduction-death-population.md`](docs/design/reproduction-death-population.md) — reproductive pressure, clonal budding, death and population bounds
- [`docs/adr/`](docs/adr/) — architectural decision records
- [`research/`](research/) — experimental and research records

---

## The long-term question

Symbiont begins with software, not biology.

Software gives us something unusual: an environment in which perception, development, memory, metabolism, forgetting, reproduction, inheritance, selection and ecology can all be instrumented precisely.

That makes it possible to ask a different question from conventional AI:

> **Instead of designing an intelligent system directly, how much organized behavior can emerge if we design the conditions under which a digital organism is allowed to live and develop?**

Symbiont Lab exists to investigate that question.
