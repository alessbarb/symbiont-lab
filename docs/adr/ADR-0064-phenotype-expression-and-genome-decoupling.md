# ADR-0064 — Phenotype Expression and Genome Decoupling

- **Status:** Accepted
- **Date:** 2026-10-03
- **Decision owner:** project owner
- **Relates to:** Constitution (Golden Invariant), ADR-0043, ADR-0056, ADR-0062, `docs/design/genome/genome-v2.md`, `docs/design/genome/phenotype-expression-v1.md`, `docs/design/genome/genome-v3.md`
- **Scope:** Architecture of genetic representation, developmental expression, biological phenotype, and runtime mechanism configuration. This ADR defines the boundary between heritable traits and algorithmic parameters; it modifies no organism code directly.

---

## Context

An exhaustive audit of internal parameters and constants across `src/symbiont` (physiology, homeostasis, sensorimotor dynamics, body schema, cognitive arbitration, memory consolidation, and metacognition) revealed a recurring design tension: the temptation to expose any constant that influences biological behavior directly as a locus in `GenomeSchema`.

Directly mapping internal algorithmic thresholds (e.g., `learning_rate = 0.08`, `min_samples = 5`, `consolidation_cadence = 50`, `tenacity_ticks = 12`) to genetic loci produces severe architectural failure modes:

1. **Genome as a configuration dump:** The genome ceases to represent an evolved biological blueprint and degenerates into an unmaintainable mirror of Python constructor keyword arguments.
2. **Coupling to simulation mechanics:** Loci denominated directly in "ticks" or discrete step counts tie heritable genetics to the simulation's update rate, integration step, and embodiment physics.
3. **Loss of developmental plasticity:** When the genome directly supplies runtime configuration, the organism cannot express different phenotypes across ontogenic stages (juvenile, adult, senescent) or across different physical embodiments (re-embodiment) without altering its genotype.
4. **Genetic drift and redundant degrees of freedom:** Encoding simplex allocations (e.g., attention weights or resource divisions summing to 1.0) as unconstrained vectors in $\mathbb{R}^K$ introduces redundant neutral drift where fitness cannot distinguish between identical normalized distributions.
5. **Erosion of algorithmic invariants:** Treating mathematical criteria of convergence, statistical stability, or numerical precision as heritable traits destroys the epistemological guarantee that two organisms are evaluated against the same mechanistic standard.

---

## Decision

We establish the canonical four-stage developmental architecture for Symbiont:

$$\text{Genome} \xrightarrow{\text{ExpressionProgram}} \text{BiologicalPhenotype} \xrightarrow{\text{MechanismBinding}} \text{RuntimeConfiguration}$$

```text
Genome (G)
  │  [Heritable, normalized biological potentials and biases]
  ▼
ExpressionProgram(G, DevelopmentalContext)
  │  [Pure deterministic developmental function]
  ▼
BiologicalPhenotype (P)
  │  [Expressed biological traits, capacities, resilience, and trade-offs]
  ▼
MechanismBinding (B)
  │  [Adapter mapping biological traits to concrete algorithmic parameters]
  ▼
RuntimeConfiguration (C)
     [PhysiologyConfig, SensoryLimits, ForwardModelConfig, ArbitrationPolicy]
```

### 1. The Demarcation Rule

To classify any candidate parameter, the following golden question must be answered:
> *Can two organisms differ heritably in this property without altering the algorithmic meaning, contract, or mathematical correctness of the mechanism?*

- If differing changes the validity, convergence definition, or epistemological contract of the algorithm, the parameter is **MECHANISTIC** and MUST NOT be a genetic locus.
- If differing represents an heritable trade-off, adaptive bias, metabolic cost, or developmental ceiling within a valid mechanism, the property is **GENETIC** or **PHENOTYPIC**.

### 2. Ontological Demarcation Matrix

Every constant in the codebase belongs to one of five mutually exclusive categories:

- **`GENETIC`**: Heritable potentials, developmental ceilings, metabolic baseline costs, and trade-off biases encoded in the genome. Unitless, normalized ($\in [0, 1]$ or latent coordinates in $\mathbb{R}$), invariant across the organism's lifespan.
- **`PHENOTYPIC`**: Biological traits actively expressed at tick $t$ given the genome and ontogenic state (e.g., `fatigue_resilience = 0.71`, `sensory_receptive_breadth = 0.45`, `memory_half_life_s = 4.3`). May express continuous biological/physical quantities ($s^{-1}$, Joules, Celsius), but NEVER scheduler-dependent discrete units (`ticks`).
- **`MECHANISTIC`**: Parameters required for the numerical, physical, epistemic, or semantic correctness of an algorithm. Subdivided into:
  - *PHYSICAL*: Physical laws and properties of the modeled simulation environment (e.g., integration timestep $\Delta t$, medium drag). Distinct from host infrastructure.
  - *EPISTEMIC*: Truth conditions and convergence definitions (e.g., convergence threshold, minimum support for hypothesis promotion).
  - *NUMERICAL*: Numerical stability and conditioning (e.g., epsilon $\epsilon = 10^{-7}$, matrix regularization).
  - *SEMANTIC*: Discrete cognitive state thresholds and discrete state machine contracts.
- **`INFRASTRUCTURE`**: Host OS, memory ceilings, hardware protections, telemetry formats, checkpoint serialization, and lab harness limits (e.g., maximum buffer sizes for OS memory protection).
- **`UNRESOLVED`**: Borderline traits requiring empirical lab preregistration before deciding promotion to genetics or retention as mechanistic constants.

### 3. Structural Developmental Context

Phenotypic expression is a pure, deterministic function:
$$\text{Phenotype} = \text{Expression}(\text{Genome}, \text{DevelopmentalContext})$$

`DevelopmentalContext` MUST contain strictly **structural, somatic affordances and physical bounds**:

- `ontogenic_state`: Continuous biological age, developmental progress, accumulated somatic load, and inherited epigenetic marks.
- `embodiment_constraints`: Observable physical capacity of the body chassis (`available_receptor_slots`, `available_effectors`, `mechanical_dof`, `structural_mass`).
- `inherited_epigenetic_state`: Stable chromatin/metaplastic markers transmitted under explicit protocol.
- `somatic_resource_envelope`: Somatic mass, tissue energy storage capacity, and tissue thermal conductivity.

**Boundary Guarantees:**

- `DevelopmentalContext` MUST NEVER contain semantic labels or external taxonomies (e.g., `body_type = "humanoid"`, "left_arm", or named sensory modalities).
- `DevelopmentalContext` MUST NEVER contain dynamic properties of the World (gravity, ambient temperature, external medium properties). Maintaining $\text{World} \neq \text{Body} \neq \text{Organism}$ ensures expression does not conflate ontogeny with environmental reaction norms in v1.

### 4. Simplex Geometry in Latent Space (Reference-Gauge Logistic Coordinates)

Any genetic trade-off representing a point on a probability or resource simplex $\Delta^{K-1}$ (where $\sum_{i=1}^K w_i = 1$ and $w_i > 0$) MUST be encoded as an unconstrained latent vector in $\mathbb{R}^{K-1}$ using reference-gauge logistic coordinates (additive log-ratio parameterization):
$$\boldsymbol{z} \in \mathbb{R}^{K-1} \xrightarrow{\Pi} \boldsymbol{w} \in \Delta^{K-1}$$
This prevents redundant degrees of freedom, avoids neutral genetic drift during evolutionary search, and guarantees that distinct genetic vectors map to distinct phenotypic allocations.

### 5. Separation of MechanismBinding

`MechanismBinding` is an interchangeable layer mapping `BiologicalPhenotype` to concrete runtime configurations (`PhysiologyConfig`, `ForwardModelConfig`, etc.).
Discretization of continuous physical rates ($s^{-1}$) to simulation-frequency parameters (`ticks`, filter alphas, buffer lengths) is performed exclusively inside `MechanismBinding` given the active $\Delta t$.
If an internal machine-learning or estimation algorithm is updated or replaced (e.g., replacing an EMA forward model with an ensemble or neural estimator), the genome and biological phenotype remain unchanged; only the `MechanismBinding` is adapted.

### 6. Invariant of Organism Identity

$$\text{OrganismIdentity} \neq \text{BiologicalPhenotype}$$
An organism's genetic identity (`genotype_hash`) and individual continuity remain invariant across ontogenic development (juvenile $\to$ adult $\to$ senescent) and across re-embodiment in distinct bodies. The expressed phenotype varies deterministically with the body's structural affordances, but the genome remains untouched.

---

## Canonical Invariants of Phenotype Expression v1

1. **Constitutive Primacy:** The genome encodes only heritable potential, metabolic costs, developmental ceilings, and allocation biases; it never encodes acquired knowledge, memories, or learned policies.
2. **Deterministic Expression:** Given identical `Genome` and identical `DevelopmentalContext`, `ExpressionProgram` yields bitwise identical `BiologicalPhenotype`.
3. **Simulation Timestep Independence:** All genetic loci are simulation-unit independent. Phenotypic traits may express canonical biological/physical units ($s^{-1}$, Joules) but never scheduler-dependent units (`ticks`). Discretization to scheduler steps occurs exclusively inside `MechanismBinding`.
4. **Structural Context Purity:** `DevelopmentalContext` contains only structural, somatic affordances and quantitative boundaries; it is strictly agnostic to semantic body labels and excludes dynamic World properties.
5. **Full Simplex Non-Redundancy:** Every $K$-component simplex locus has exactly $K-1$ heritable degrees of freedom in $\mathbb{R}^{K-1}$ via reference-gauge logistic coordinates.
6. **Decoupled Mechanism Binding:** Algorithmic parameter definitions (`PhysiologyConfig`, `ForwardModelConfig`) must not be referenced by `GenomeSchema`.
7. **Identity Invariance under Re-embodiment:** Re-embodiment into a body with different structural constraints alters the expressed `BiologicalPhenotype` via `DevelopmentalContext`, but leaves `genotype_hash` and organism lineage unchanged.
8. **Algorithmic Invariance:** Convergence criteria, statistical significance thresholds, and numerical guards are universally mechanistic and must never be parameterized by the genome.
9. **Independent Expression Versioning:** Expression semantics (`expression_program_version`, `phenotype_schema_version`, `mechanism_binding_version`) are versioned independently from `genome_schema_version`. Complete provenance requires capturing all versions to guarantee reproducible phenotypic reconstruction.
10. **Two-Phase Evolution:** Introduction of phenotypic expression proceeds in two phases:
    - *Phase 1:* Implement `PhenotypeExpression` and `MechanismBinding` bridging existing `Genome v2` to runtime configs.
    - *Phase 2:* Formalize `Genome v3` after empirical Lab testing of `UNRESOLVED` candidate loci.
11. **Constitutional Golden Invariant Preservation:** No parameter shall be promoted to the genome or modified in expression merely to make an experiment or benchmark pass.

---

## Consequences

- **Positive:**
  - Prevents the genome from bloating into a fragile mirror of internal implementation classes.
  - Decouples evolutionary algorithms in Lab from internal engine changes.
  - Allows clean ontogenic maturation and principled re-embodiment where the same genome expresses appropriately adapted phenotypes in differing physical bodies.
  - Eliminates evolutionary search waste caused by simplex over-parameterization.
- **Negative / Costs:**
  - Introduces two explicit intermediate representations (`BiologicalPhenotype` and `MechanismBinding`) between genome and runtime configs.
  - Requires maintaining the deterministic projection logic between latent spaces and runtime parameters.
- **Migration & Phasing:**
  - Does not invalidate current `Genome v2` checkpoints. Phase 1 will operate as a deterministic adapter layer over `Genome v2`.
  - Empirical resolution of `UNRESOLVED` traits will be executed in preregistered Lab protocols before minting `Genome v3`.

---

## Alternatives Rejected

1. **Direct Parameter Exposure:** Exposing all ~70 audited constants directly in `GenomeSchema`. Rejected because it turns the genome into a software configuration file, breaks simulation timestep independence, and destroys algorithmic invariance.
2. **Direct Genome-to-Config Translation (`Genome -> Config`):** A single monolithic translation class without an explicit `BiologicalPhenotype` intermediate. Rejected because it tightly couples the genome to specific Python configuration classes, preventing mechanism replacement without changing the genetic definition.
3. **Semantic Body Context:** Passing body type strings or joint names into the expression function. Rejected because it violates morphological open-endedness and injects host-level semantics into biological expression.
