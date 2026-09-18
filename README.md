# Symbiont Lab

**Experimental Artificial Life & Digital Organism Research**

> What happens if software is not told what its world means, but is instead
> given bounded ways to sense, learn, remember, maintain itself, reproduce,
> interact and develop its own internal conventions?

**Symbiont Lab** is an experimental Artificial Life project for studying
persistent digital organisms.

A Symbiont is not a monitoring agent with biological vocabulary layered on top.
The organism itself is the experimental subject. The project asks which
life-like functions can be implemented as real computational processes, how
those processes interact over a lifetime, and which higher-order phenomena can
emerge without being supplied as final behavior by the evaluator.

The central research question is:

> **Can increasingly organism-like organization emerge from bounded
> developmental processes rather than being explicitly programmed as the final
> behavior?**

---

## Project status

The latest published software cut is **`v0.80.16`**.

The current `main` branch contains the post-cut integration, validation and
Observatory work for **Symbiont Experimental Organism v1**. The final adversarial
re-audit classifies the canonical integrated runtime as **class A — integrated**
and the release is **`FROZEN`** in the `1.0.0` release state.

The semantic `1.0.0` freeze is complete; final tag and GitHub publication are
being finalized as administrative release operations.

The intended `1.0.0` cut does not add another organism capability. It freezes a
reproducible experimental subject whose existing capabilities can be studied
together through one canonical population runtime.

Current high-level state:

| Area | State |
| --- | --- |
| Real bounded perception | implemented |
| Developmental sensing | implemented |
| Attention, inquiry and belief revision | implemented |
| Endogenous cognitive plasticity | implemented |
| Consolidated biological memory | implemented |
| Digital physiology and viability | implemented |
| Reproduction and heredity | implemented |
| Bounded digital ecology | implemented |
| Predictive development | implemented in declared scope |
| Local social development | implemented in declared scope |
| Biological Closure v1 | closed in declared scope |
| Per-organism Private SLM v1 | closed in preregistered scope |
| Cultural Foundation v1 | closed in preregistered scope |
| Cumulative Culture v1 | closed in preregistered scope |
| Autonomous Cultural Agency v1 | closed in preregistered scope |
| Opaque symbol grounding | implemented in frozen subject |
| Structured opaque communication | implemented in frozen subject |
| Integrated Habitat Runtime v1 | implemented and validated |
| Passive Observatory | implemented and browser-validated |
| Experimental Organism v1 freeze | published and frozen in 1.0.0 |

A capability being implemented does not imply universal generalization.
Experimental claims are deliberately narrower than implementation claims.

For the exact evidence status, including negative and partial results, see
[`research/STATUS.md`](research/STATUS.md).

---

## The idea

Most software starts with a model of what its environment means.

A conventional monitoring system might be given concepts such as:

```text
CPU usage
memory usage
disk pressure
network activity
```

and then receive rules explaining how those concepts should be interpreted.

Symbiont starts from the opposite direction.

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
          │
          ▼
relations + rhythms
          │
          ▼
attention + inquiry
          │
          ▼
beliefs + self-model
          │
          ▼
plastic cognition
          │
          ▼
prediction + structural change
          │
          ▼
consolidated memory
          │
          ▼
physiology + viability
          │
          ▼
reproduction + heredity
          │
          ▼
ecology + social interaction
          │
          ▼
private learned models
          │
          ▼
culture
          │
          ▼
grounded opaque symbols
          │
          ▼
structured communication
```

The organism does not need to know that an opaque signal corresponds to a
particular Linux file, metric, device or subsystem in order to learn from its
behavior.

That separation is deliberate.

**Access to the host is semantic at the safety boundary and opaque at the
developmental boundary.**

The host layer knows enough to decide what may safely be observed. The organism
does not automatically inherit those human meanings.

---

## Artificial life, not simulated biology

Symbiont does not attempt to reproduce biological anatomy or chemistry in
software.

There is no simulated stomach, cell membrane, neuron, chromosome molecule or
endocrine system that the implementation claims to reproduce literally.

Instead, the project asks whether functions associated with living systems can
have useful **digital operational counterparts**.

| Life-like function | Digital counterpart in Symbiont |
| --- | --- |
| Perception | Developed opaque senses |
| Response | Attention, inquiry and belief revision |
| Development | Lifetime sensory and cognitive change |
| Memory | Consolidated durable learned state |
| Self-monitoring | Perceptual cost, health, maturity and confidence |
| Homeostasis | Bounded resource regulation and recovery |
| Intake | Acquisition of usable information/resources |
| Metabolism | Transformation under finite computational budgets |
| Degradation | Loss and active disposal of low-value state |
| Dormancy | Reduced activity under physiological pressure |
| Viability | Explicit organism-level life state |
| Death | Irreversible closure of one organism identity |
| Reproduction | Habitat-authorized birth |
| Heredity | Genome transmission and bounded variation |
| Ecology | Finite shared habitats and resource interaction |
| Social development | Local evidence-driven interaction |
| Individual modeling | Per-organism Private SLM |
| Culture | Provenance-preserving social knowledge |
| Symbol grounding | Opaque conventions grounded in experience |
| Communication | Bounded opaque structured sequences |

These are functional analogies, not claims of biological equivalence.

The project does not claim that a Symbiont is biologically alive, conscious,
sentient or generally intelligent.

---

## What makes a Symbiont different

### It develops senses

A resident Symbiont is not required to begin with a semantic catalogue of host
metrics.

The host layer discovers a bounded set of vetted, aggregate, read-only surfaces
and exposes them to development through opaque identities.

The organism can learn which signals are:

- available;
- variable;
- informative;
- redundant;
- costly;
- unreliable;
- worth revisiting.

Some senses become active. Some remain exploratory. Others become dormant.

Dormancy is not permanent blindness: bounded revisitation allows early
developmental choices to be revised.

---

### It learns relationships without being given their meaning

Signals are not treated only as independent measurements.

Symbiont can learn bounded same-time and lagged relationships and can use those
relationships when allocating scarce perceptual resources.

The organism may learn that two opaque signals move together without being told
what either signal represents.

Association remains association. It is not silently promoted to causation.

---

### Attention is a finite resource

Observation is not free.

Attention is allocated under explicit budgets. Uncertainty, information,
observation cost, sensory health, maturity and diminishing returns can influence
where additional observation is spent.

A capability that has never been acclimated may receive high initial priority,
while repeated low-information observations become progressively less valuable.

The attention mechanism is a resource allocator, not a threat classifier.

---

### It can investigate

A Symbiont can temporarily perform a higher-resolution **second look** at
something it already has permission to observe.

Investigation remains:

- local;
- read-only;
- bounded;
- cancellable;
- limited to authorized perception.

Evidence collected during investigation can revise an existing belief without
erasing disagreement with prior evidence.

Contradiction is preserved as information.

---

### It models its own perceptual apparatus

`SelfModel` gives the organism a limited operational model of its own sensing
process.

It can learn:

- sensory availability;
- observation cost;
- perceptual health;
- maturity;
- confidence;
- recency.

This lets the organism reason about the reliability of its own perception
without turning the self-model into a claim of subjective awareness.

---

## Cognition develops under an immutable kernel

Symbiont can change its cognitive structure during life, but it does not rewrite
its source code.

Its self-modification model is:

> **plasticity of data and structure under an immutable kernel**

The cognitive substrate uses a declarative genome, a bounded
`CognitiveGraph`, explicit node and edge kinds, structural budgets and
transactional mutation rules.

Learning includes:

- prediction error;
- bounded weight updates;
- eligibility traces;
- metaplastic adaptation;
- structural proposal and pruning;
- lifecycle-aware safety freezing.

The kernel defines what kinds of changes are legal. Learning decides which legal
changes occur.

The organism does **not** generate, edit or execute arbitrary program code as a
learning mechanism.

---

## Genome, phenotype and individual history

A Symbiont has at least two conceptually different classes of state.

### Genome

The genome contains inherited developmental parameters, structural limits and
other heritable configuration.

It defines the space in which development can occur.

It does not encode the final learned mind.

### Phenotype

The phenotype is what develops during a lifetime.

It includes state such as:

- developed senses;
- sensory relationships;
- learned baselines;
- self-model state;
- cognitive weights;
- cognitive topology;
- predictive state;
- consolidated memory;
- physiological state;
- local relational evidence;
- private learned-model lineage;
- cultural experience.

Two organisms beginning with compatible or identical genomes can therefore
diverge through different histories.

That divergence is one of the central experimental subjects of the project.

---

## Memory is not serialization

A restart is not treated as a perfect freeze-frame of every microscopic runtime
variable.

Symbiont distinguishes **durable memory** from **transient state**.

```text
experience
    │
    ├── transient activation ─────────── discarded
    │
    ├── unstable adaptation ─────────── not yet memory
    │
    ├── stable learned structure ───── consolidated
    │
    └── exceptional salient event ─── bounded fast path
                                         │
                                         ▼
                                      checkpoint
```

Stable learning can be consolidated into durable representations. Exact recent
activation and other transient microstate may deliberately disappear.

After restart, the organism reacclimates instead of fabricating a reconstructed
microstate that never actually occurred.

Persistence is therefore part of the life model, not merely an implementation
convenience.

---

## Physiology is now part of the runtime

Symbiont no longer treats resource budgets as unrelated implementation details.

Digital physiology provides an explicit internal economy:

```text
intake
  │
  ▼
assimilation
  │
  ├──► activity
  ├──► learning
  ├──► maintenance
  └──► memory / structure
  │
  ▼
degradation
  │
  ▼
disposal
  │
  ▼
continued viability
  │
  ├──► recovery
  ├──► dormancy
  ├──► reproduction pressure
  └──► irreversible death
```

The system does not claim that CPU cycles are literal biological energy or that
deleted objects are literal biological waste.

The functional question is narrower:

> **Can a persistent digital organism regulate intake, transformation,
> maintenance, degradation, recovery and continued viability under finite
> resources?**

`MetabolicLedger`, `InformationAssimilator`, `DegradationQueue`,
`HomeostaticController` and `ViabilityController` provide the corresponding
bounded mechanisms.

---

## Reproduction and heredity are implemented

Reproduction is not unrestricted self-copying.

Actual birth is mediated by an authorized habitat.

### Clonal budding

A viable parent can produce a descendant with a new organism identity while
remaining alive.

The descendant inherits declared germinal material but does not silently receive
the parent's acquired lifetime phenotype.

In particular, clonal birth does not copy the parent's complete learned graph,
physiology, sensory history, Private SLM corpus or acquired model as germinal
state.

### Paired reproduction

Two compatible parents may contribute heritable genome material to a new
organism.

The recombined genome must satisfy the same immutable validation and kernel
boundaries as every other genome.

### Birth remains bounded

A birth requires:

- explicit habitat authority;
- carrying-capacity availability;
- valid lineage identity;
- finite resource allocation;
- valid germinal material.

A full habitat blocks birth.

### Death is irreversible

Process shutdown and organism death are different events.

A viable process may stop and later continue the same organism.

Death closes continuity for that organism identity. Normal restoration cannot
silently erase the death event.

---

## Ecology and social development

Symbionts can inhabit finite shared environments.

`SharedHabitat`, `EcologicalResourcePool` and the bounded social runtime provide
mechanisms for:

- finite carrying capacity;
- shared resource pressure;
- local exchange;
- competition;
- local relation evidence;
- directional rejection;
- channel suspension and resumption;
- contextual resource adaptation;
- bounded exploration and re-exploration;
- lineage-aware population studies.

No central planner assigns organisms social roles, friends, enemies, niches or a
goal of cooperation.

Evaluator-side studies may measure interaction diversity, reciprocity,
competition, isolation or niche differentiation. Those labels remain outside
organism cognition.

**Cooperation is an observable outcome, not a hard-coded objective.**

---

## Private SLM: a learned model owned by one organism

Each organism can maintain a bounded private experience record from which a
small learned sequence model may be trained in the laboratory apparatus.

Private SLM v1 deliberately excludes pretrained human knowledge from the
scientific baseline.

The system supports:

- organism-isolated experience ledgers;
- explicit provenance and epistemic state;
- deterministic native tokenization;
- isolated train/validation/test corpora;
- bounded GRU and causal Transformer configurations;
- held-out evaluation;
- candidate → shadow → active/degraded/retired lifecycle;
- evidence-gated promotion;
- incremental model adaptation;
- explicit model lineage;
- content-addressed artifacts.

The learned model may influence the organism only through typed bounded
interfaces.

It cannot directly write arbitrary facts into cognition or execute host actions.

Private model state remains private to the organism that learned it.

A descendant inherits the **capacity** to learn a Private SLM, not its parent's
acquired corpus or model weights.

Negative experimental results remain part of the scientific record and are not
rewritten when a later protocol demonstrates a different capability.

---

## Culture preserves provenance

Culture begins with bounded social evidence, not with model transfer.

The cultural substrate preserves distinctions between:

- direct experience;
- organism inference;
- socially received evidence;
- independent corroboration;
- copied transmission;
- contradiction;
- composite cultural artifacts.

A copied claim does not become independent evidence simply because another
organism repeated it.

### Cultural Foundation v1

Validated bounded claim transport, provenance, contradiction, replay and
persistence across organism turnover.

### Cumulative Culture v1

Added versioned cultural composition while retaining contributors, evidence
roots and derivation history.

### Autonomous Cultural Agency v1

Moved the decision about what to retain, validate, transmit, compose or ignore
into the organism-side cultural policy.

The laboratory still supplies authorized topology, budgets and transport
conditions. It does not choose cultural content for the organism.

Private SLM weights, adapters and corpora do not cross the cultural channel.

---

## Opaque symbol grounding

The project deliberately separates **discovering a convention** from
**assigning it a human-readable name**.

A Symbiont can ground opaque symbols through its own experience and interaction
without receiving an operator-supplied semantic label as part of the learning
loop.

The relevant scientific question is whether stable internal or shared
conventions emerge and remain useful under bounded conditions.

Human naming may be added as an observer-facing convenience in the future. It
is not required for organism-side grounding.

---

## Structured communication without a hidden grammar

The communication substrate supports bounded variable-length opaque sequences.

It includes:

- silence;
- transmission cost;
- bounded memory;
- forgetting;
- replay;
- cultural transmission.

It does not hard-code:

- semantic slots;
- grammatical roles;
- syntax;
- compositional targets;
- evaluator-selected message content.

Structured Communication Characterization studies the codes that arise from the
generic channel. The evaluator may measure functional, holistic or structured
patterns without rewarding the organisms for matching the evaluator's preferred
description.

---

## One organism, two epistemic worlds

The repository deliberately separates the organism from the apparatus studying
it.

```text
┌──────────────────────────────────────────────┐
│                  symbiont                    │
│                                              │
│             experimental subject             │
│                                              │
│ perception · cognition · memory              │
│ physiology · prediction · culture            │
│ communication · lifecycle                    │
└──────────────────────┬───────────────────────┘
                       │
             outbound evidence only
                       │
┌──────────────────────▼───────────────────────┐
│                symbiont_lab                  │
│                                              │
│              scientific apparatus            │
│                                              │
│ experiments · evaluation · training          │
│ studies · evolution · audits · archives      │
└──────────────────────────────────────────────┘
```

The organism does not import evaluator ground truth.

Synthetic labels, experiment outcomes, scientific classifications and external
fitness judgments belong to the apparatus.

This boundary prevents one of the most damaging errors in artificial-life
research: concluding that the organism discovered something that the experiment
secretly taught it.

The architectural rule is simple:

> **`symbiont` is the subject. `symbiont_lab` is the scientist.**

The subject must not secretly become the scientist.

---

## Integrated Habitat Runtime

The final major pre-freeze step was integration rather than another new
capability.

`IntegratedHabitatRuntime` provides the canonical joint population lifecycle for
the APIs that had previously been validated in separate layers.

One bounded habitat can now exercise together:

```text
population lifecycle
        │
        ├── birth / death / lineage
        ├── physiology
        ├── sensing and cognition
        ├── prediction
        ├── Private SLM state
        ├── culture
        ├── symbol grounding
        ├── structured communication
        ├── social/resource interaction
        ├── checkpoint / replay
        └── outbound telemetry
```

The integrated runtime does not add a new cognitive, social, cultural or
linguistic policy.

It provides one reproducible experimental subject in which the existing
capabilities coexist.

The final audit validates integrated smoke behavior, replay, boundedness and
telemetry observer equivalence in the declared test scope.

---

## The Observatory

Symbiont includes a passive Observatory for inspecting organisms and
populations.

```text
Symbiont ───────► Observatory
          state

Observatory ─X─► Symbiont
            control
```

The Observatory may observe. It does not become part of cognition.

The current architecture exposes bounded projections of areas such as:

- individual and population state;
- cognitive topology;
- published activation classes;
- learning summaries;
- structural pressure;
- sensory relation change;
- physiological state;
- social evidence;
- resource evidence;
- communication history;
- Private SLM lifecycle;
- cultural state;
- telemetry truncation and freshness.

It explicitly distinguishes:

- **organism-observed** state;
- **organism-known** state;
- **observer-derived** interpretation.

The cognitive view uses the canonical cognitive node kinds and published state.
Synthetic demo telemetry is explicitly identified as synthetic.

The final freeze-readiness audit includes real browser QA of the Observatory.

See [`observatory/`](observatory/).

---

## Experimental Organism v1 freeze

The project has reached a point where adding another mechanism to the organism
would often make the science weaker rather than stronger.

Experimental Organism v1 is therefore intended to freeze the current subject so
that future work can study what the existing organism does under new conditions.

The frozen core includes the current bounded contracts for:

- runtime and lifecycle;
- developmental perception;
- cognitive plasticity;
- consolidated memory;
- physiology and homeostasis;
- heredity and reproduction;
- predictive development;
- social interaction;
- Private SLM state;
- provenance-preserving culture;
- autonomous cultural agency;
- opaque grounding;
- structured communication;
- checkpoint/replay.

`IntegratedHabitatRuntime` is the canonical orchestration layer for exercising
those capabilities together.

### Allowed after the freeze

The freeze does **not** end research.

It allows:

- bug and safety fixes;
- boundedness fixes;
- checkpoint and reproducibility fixes;
- integration corrections that preserve semantics;
- new habitats;
- new experiments and studies;
- passive Observatory improvements;
- telemetry improvements;
- scientific analysis;
- preservation of negative results;
- performance work that preserves causal semantics.

### Not added silently after the freeze

A new design and review gate is required for changes such as:

- new cognitive or learning mechanisms;
- new social or cultural policy;
- new language abilities;
- new inherited behavior;
- evaluator truth entering cognition;
- transfer of Private SLM weights or corpora;
- autonomous host actions;
- relaxed resource or security boundaries.

> **New phenomena should primarily be investigated through habitats and
> experiments, not by continuously adding organism capabilities.**

---

## Permanent invariants

The following boundaries are intended to remain true even if future research
eventually opens new capability lines:

- access to a real host is explicit, revocable and capability-bounded;
- learning cannot grant itself permissions outside the kernel;
- credentials and privilege-escalation mechanisms stay outside the
  developmental substrate;
- no stealth, concealment or evasion is used to preserve residence;
- no exploitation is used to acquire capabilities or resources;
- persistence remains transparent and owner-controlled;
- reproduction never means covert or uncontrolled propagation;
- materializing a descendant requires an authorized habitat;
- hard resource ceilings remain outside learned control;
- death cannot be silently undone by normal restore;
- evaluator ground truth does not become a hidden teacher;
- observation does not silently become control.

The current frozen subject also keeps network sockets, remote peer discovery and
autonomous host remediation outside its runtime.

Those are deliberate boundaries, not accidental omissions.

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

Optional model-training dependencies:

```bash
pip install -e ".[dev,modeling]"
```

---

### Explore the available host surface

```bash
symbiont-lab host discover
```

---

### Observe real host readings

```bash
symbiont-lab host sample
```

---

### Run the organism

```bash
symbiont-lab organism run \
  --ticks 20 \
  --state-file organism-state.json
```

---

### Run as a resident process

```bash
symbiont-lab organism live \
  --state-file ~/.local/state/symbiont/organism.json \
  --interval 15 \
  --stdout
```

Resident development uses the safe developmental sensing path.

Stop it with `Ctrl-C` or `SIGTERM`. Durable state is checkpointed atomically
during normal shutdown.

---

## Running the cognitive substrate

Example genome and graph files are available under:

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

The legal initial substrate is explicit.

Once durable state exists, learned phenotype state is restored from checkpoint
contracts rather than reconstructed from the original example files.

---

## Experiments and reproducibility

The same repository contains the scientific apparatus used for controlled
experiments.

Examples:

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

Execution manifests retain the information needed to inspect and reproduce
laboratory runs without exposing evaluator knowledge to the organism.

Experiment definitions live under [`experiments/`](experiments/).

Research outcomes, audits and negative results live under
[`research/`](research/).

---

## Repository architecture

At the highest level:

```text
symbiont-lab/
│
├── src/
│   ├── symbiont/          # the experimental organism
│   └── symbiont_lab/      # the scientific apparatus
│
├── observatory/           # passive visualization
├── experiments/           # declarative experiment definitions
├── examples/              # runnable examples
├── research/              # evidence, audits and scientific records
├── docs/                  # architecture, design, ADRs and roadmap
│
├── ORGANISM.md            # organism evolution and freeze record
└── README.md
```

The exact module structure evolves, but the epistemic boundary does not:

```text
organism state ─────────────► apparatus
evaluator truth ───────X────► organism cognition
```

---

## Research principles

### Development before final behavior

Where possible, complex behavior should arise from accumulated development
rather than increasingly elaborate hand-authored policies.

### No hidden teacher

Evaluator knowledge, experimental labels and synthetic ground truth remain
outside organism cognition.

### Boundedness is part of the organism

Memory, attention, sensing, learning, physiology, communication and culture all
operate under finite budgets.

Unlimited accumulation is not development.

### Experience should matter

Two organisms with the same inherited starting point should be able to diverge
through different life histories.

### Forgetting is a life function

Removing obsolete state matters as much as creating new state.

A system that can only accumulate eventually stops developing.

### Physiology precedes unconstrained ecology

Interaction is meaningful only if individual organisms have real bounded
viability and resource consequences.

### Ecology does not imply cooperation

Competition, coexistence, specialization, support, conflict and cooperation are
outcomes to observe, not roles to assign.

### Reproduction is not deployment

Organism-side reproductive state and actual process materialization are
different boundaries.

Birth remains habitat-mediated.

### Death is not shutdown

A stopped viable process may continue. A dead organism identity may not be
normally resumed as though the death event never occurred.

### Social evidence is not direct evidence

A claim does not become more independently supported merely because it has been
copied through several organisms.

### A model is not knowledge

A useful predictor is evidence of predictive utility, not proof of semantic
understanding.

### A symbol need not have a human name

An opaque convention can be meaningful to the organism without first being
translated into operator vocabulary.

### Observation must not become control

The project may inspect organisms in detail without making the observer a hidden
decision-maker.

### Claims must remain weaker than evidence

A correlation is not causation.

A predictor is not understanding.

A self-model is not consciousness.

Culture is not human culture by analogy alone.

Structured communication is not automatically language.

A persistent, adaptive and reproductive digital process is not automatically
biological life.

---

## Where to read next

Use each document for a different purpose:

- [`ORGANISM.md`](ORGANISM.md) — complete organism evolution and freeze record;
- [`research/STATUS.md`](research/STATUS.md) — current scientific evidence,
  including negative and partial results;
- [`docs/roadmap.md`](docs/roadmap.md) — active research state and experimental
  lines;
- [`docs/history/roadmap-log.md`](docs/history/roadmap-log.md) — historical
  milestone and patch tracking;
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — release-by-release implementation
  history;
- [`docs/architecture.md`](docs/architecture.md) — architecture and biological
  analogy;
- [`docs/design/`](docs/design/) — formal designs and experimental contracts;
- [`docs/adr/`](docs/adr/) — architectural decision records;
- [`research/audits/`](research/audits/) — adversarial and scientific audits;
- [`observatory/`](observatory/) — passive visualization system.

Design documents describe contracts and hypotheses. They are not, by
themselves, proof that a capability exists or that an experiment succeeded.

For implementation state, use the roadmap and organism record.

For scientific claims, use the research evidence.

---

## The long-term question

Symbiont begins with software, not biology.

Software gives us an unusually instrumentable environment in which perception,
development, learning, memory, metabolism, forgetting, heredity, reproduction,
social interaction, culture and communication can all be observed under explicit
constraints.

Experimental Organism v1 turns those mechanisms into a stable subject rather
than an indefinitely moving implementation target.

That makes the next question more interesting:

> **If the organism is held stable, what new organization appears when its
> environment, history, population and selective pressures change?**

That is the direction of Symbiont Lab after the freeze.
