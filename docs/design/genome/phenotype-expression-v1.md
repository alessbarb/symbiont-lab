---
id: design.genome.phenotype-expression-v1
title: "Phenotype Expression v1"
document_type: design
domain: genome
status: proposed
canonical: false
implementation_status: not_started
migrated_on: 2026-10-03
last_reviewed: 2026-10-03
language: en
---

# Phenotype Expression v1 — Specification and Demarcation

- **Status:** Proposed
- **Implementation status:** Not started
- **Governing ADR:** [ADR-0064](../../adr/ADR-0064-phenotype-expression-and-genome-decoupling.md)
- **Relates to:** [Genome v2](genome-v2.md), [Genome v3](genome-v3.md), [Canonical Organism Profile v1](../core/canonical-organism-profile-v1.md), [Longitudinal Integrity v1](../core/longitudinal-integrity-v1.md)
- **Domain:** Genetics, Ontogeny, Developmental Phenomics

---

## 1. Abstract & Motivation

This specification formalizes the architectural separation between **Genotype**, **Developmental Expression**, **Biological Phenotype**, and **Runtime Mechanism Configuration**.

Prior to this design, configuration constants across the organism (`src/symbiont`)—ranging from basal metabolic recovery to Kalman-filter-style adaptation thresholds and memory consolidation cadences—were either hardcoded as class-level magic numbers or threatened to become direct fields on `GenomeSchema`. Directly exposing implementation constants to the genome commits four critical architectural errors:

1. **Genome as software configuration:** The genome ceases to represent an evolvable biological recipe and becomes a brittle reflection of Python class constructors.
2. **Coupling to simulation timestep:** Constants denominated in simulation "ticks" bind heritability to simulator frequency.
3. **Loss of ontogenic and morphological plasticity:** An organism cannot alter its expressed capacities during development or upon re-embodiment in bodies with different physical affordances.
4. **Genetic drift and redundant degrees of freedom:** Encoding multi-component resource partitions as unconstrained vectors introduces neutral genetic drift in evolutionary search.

Phenotype Expression v1 solves these problems by establishing a deterministic 4-stage developmental pipeline, an ontological demarcation rule for all constants in the organism, and an explicit implementation bridge matrix over current code.

---

## 2. Canonical Invariants

1. **Constitutive Primacy:** The genome encodes exclusively heritable potentials, developmental ceilings, metabolic baseline rates, and trade-off biases. It never encodes acquired knowledge, empirical facts, or learned skills.
2. **Deterministic Expression:** For any tuple $(G, C)$ where $G$ is a `Genome` and $C$ is a `DevelopmentalContext`, the developmental function $\mathcal{D}(G, C)$ evaluates to a bitwise identical `BiologicalPhenotype`.
3. **Simulation Timestep Independence:** All genetic loci are simulation-unit independent. Phenotypic traits may express canonical biological/physical units ($s^{-1}$, seconds, Joules, Celsius) but never scheduler-dependent discrete units (`ticks`, loop cadences). Discretization to scheduler frequencies occurs exclusively inside `MechanismBinding` given the environment's $\Delta t$.
4. **Structural Context Purity:** `DevelopmentalContext` contains only physical, structural, and somatic affordances. It is strictly agnostic to external semantic labels (e.g., no "humanoid", "left_arm", or named modality strings) and strictly excludes dynamic World properties (gravity, ambient temperature, external medium properties), maintaining $\text{World} \neq \text{Body} \neq \text{Organism}$.
5. **Full Simplex Non-Redundancy:** Any $K$-element allocation simplex $\Delta^{K-1}$ is represented in the genotype by exactly $K-1$ unconstrained latent variables in $\mathbb{R}^{K-1}$ via reference-gauge logistic coordinates (additive log-ratio parameterization), eliminating neutral mutational drift.
6. **Decoupled Mechanism Binding:** Runtime classes (`PhysiologyConfig`, `SensoryLimits`, `ForwardModelConfig`) must not be imported or referenced by `GenomeSchema` or `BiologicalPhenotype`.
7. **Identity Invariance under Re-embodiment:** Re-embodiment into a body with different structural constraints alters the expressed `BiologicalPhenotype` via `DevelopmentalContext`, but leaves `genotype_hash` and organism lineage unchanged ($\text{OrganismIdentity} \neq \text{BiologicalPhenotype}$).
8. **Algorithmic Invariance:** Convergence criteria, statistical testing thresholds, and numerical safety guards are universally mechanistic and must never be parameterized by the genome.
9. **Independent Expression Versioning:** Expression semantics (`expression_program_version`, `phenotype_schema_version`, `mechanism_binding_version`) are versioned independently from `genome_schema_version`. Complete provenance captures all versions to guarantee reproducible phenotypic reconstruction.
10. **Two-Phase Evolution:** Introduction proceeds in two phases: Phase 1 implements `PhenotypeExpression` as an adapter layer over `Genome v2`; Phase 2 formalizes `Genome v3` after empirical Lab validation of unresolved candidate traits.
11. **Constitutional Golden Invariant Preservation:** No parameter shall be promoted to the genome or modified in expression merely to satisfy a test or make a benchmark pass.

---

## 3. The 4-Stage Developmental Pipeline

```text
┌──────────────────────────────────────────────┐
│                    Genome                    │  Heritable genetic loci (normalized potentials, biases)
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│       ExpressionProgram(G, DevContext)       │  Pure deterministic developmental function
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│             BiologicalPhenotype              │  Expressed biological traits (resilience, physical units)
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│               MechanismBinding               │  Discretizes physical rates to algorithm steps (ticks, dt)
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│            RuntimeConfiguration             │  PhysiologyConfig, ForwardModelConfig, ArbitrationPolicy
└──────────────────────────────────────────────┘
```

### 3.1 Type Contracts (Conceptual Signatures)

```python
@dataclass(frozen=True)
class OntogenicState:
    """Quantitative somatic development. Zero discrete semantic stage labels."""
    biological_age: float                 # Continuous biological time elapsed (seconds or normalized lifecycle fraction)
    developmental_progress: float         # [0.0 = birth/initiation, 1.0 = adult maturity, >1.0 = post-maturity]
    accumulated_somatic_load: float       # Cumulative normalized work/stress exposure (independent of scheduler ticks)
    inherited_epigenetic_state: EpigeneticState # Heritable chromatin state (if protocol enabled)

@dataclass(frozen=True)
class EmbodimentConstraints:
    """Structural affordances of the physical body chassis."""
    available_receptor_slots: int         # Physical sensor channels available on body
    available_effector_slots: int         # Physical actuator channels available on body
    mechanical_dof: int                   # Kinematic degrees of freedom

@dataclass(frozen=True)
class SomaticResourceEnvelope:
    """Somatic biomass and tissue physical properties."""
    structural_mass: float                # Somatic mass (kg)
    energy_storage_capacity: float        # Chemical/battery energy capacity (Joules)
    tissue_thermal_conductivity: float    # Somatic heat dissipation coefficient

@dataclass(frozen=True)
class DevelopmentalContext:
    """Pure structural, somatic context. Strictly excludes dynamic World properties."""
    ontogenic: OntogenicState
    embodiment: EmbodimentConstraints
    somatic_envelope: SomaticResourceEnvelope

@dataclass(frozen=True)
class BiologicalPhenotype:
    """Expressed biological capacities, biases, and trade-offs."""
    # Metabolic & Somatic Traits (continuous biological quantities)
    basal_metabolic_rate_w: float               # Expressed energy expenditure (Watts / Joules/s)
    fatigue_resilience: float                   # [0.0, 1.0] unitless tolerance
    tissue_repair_potency: float                # [0.0, 1.0] repair efficiency
    thermal_neutral_celsius: float              # Expressed optimum (°C)
    thermal_tolerance_breadth_celsius: float    # Operating window width (°C)
    somatic_growth_rate: float                  # Developmental growth ceiling
    senescence_wear_rate: float                 # Slope of senescent degradation

    # Cognitive & Plasticity Traits
    sensorimotor_plasticity_rate: float         # Continuous forward-model adaptation rate (s^-1)
    sensory_receptive_breadth: float            # Exploration vs exploitation in receptive fields
    working_memory_half_life_s: float           # Memory retention half-life in biological seconds
    memory_consolidation_drive: float           # Propensity for offline structural consolidation
    candidate_salience_simplex: tuple[float, ...] # 5-way allocation: sum = 1.0

    # Executive & Motivational Biases
    novelty_seeking_drive: float                # Intrinsic curiosity bias
    competence_seeking_drive: float             # Mastery progress bias
    executive_persistence: float                # Resistance to goal switching under stagnation
```

> **Note on Developmental Stages:** Discrete labels such as `juvenile`, `adult`, or `senescent` are **derived evaluations** on `developmental_progress`, never raw inputs to `DevelopmentalContext`.

---

## 4. Ontological Demarcation Matrix

The repository-wide constant audit established five mutually exclusive categories based on the canonical rule:
> *Can two organisms differ heritably in this property without altering the algorithmic meaning, contract, or mathematical correctness of the mechanism?*

### 4.1 Taxonomy of Categories

- **`GENETIC`**: Heritable unitless locus in `Genome` ($\in [0, 1]$ or latent coordinates in $\mathbb{R}$).
- **`PHENOTYPIC`**: Expressed biological trait in `BiologicalPhenotype` (unitless or physical biological units: seconds, $s^{-1}$, Joules).
- **`MECHANISTIC`**: Implementation parameter preserving algorithmic contract:
  - `MECHANISTIC(PHYSICAL)`: Physical laws of the modeled simulation environment (e.g., $\Delta t$, medium drag).
  - `MECHANISTIC(EPISTEMIC)`: Truth, convergence, and statistical validity criteria.
  - `MECHANISTIC(NUMERICAL)`: Floating point precision, regularizers, numerical conditioning.
  - `MECHANISTIC(SEMANTIC)`: State machine definitions and discrete structural contracts.
- **`INFRASTRUCTURE`**: Host OS, memory ceilings, telemetry formats, and serialization buffers.
- **`UNRESOLVED`**: Borderline traits requiring empirical Lab study before resolution.

---

### 4.2 Full Audit Classification Table

| Subsystem / File | Original Parameter / Magic Number | Value / Default | Classification | Rationale & Architectural Target |
| --- | --- | --- | --- | --- |
| **Physiology** (`physiology_config.py`) | `basal_metabolism` | `0.001` | `GENETIC` $\to$ `PHENOTYPIC` | Inherent metabolic cost of maintenance. Locus: `metabolism.basal_efficiency`. |
| | `repair_rate` | `0.005` | `GENETIC` $\to$ `PHENOTYPIC` | Somatic repair potency. Locus: `metabolism.repair_potency`. |
| | `fatigue_gain` | `0.02` | `GENETIC` $\to$ `PHENOTYPIC` | Work-induced fatigue rate. Locus: `metabolism.fatigue_susceptibility`. |
| | `fatigue_recovery` | `0.01` | `GENETIC` $\to$ `PHENOTYPIC` | Rest recovery rate. Locus: `metabolism.fatigue_recovery`. |
| | `temp_neutral` | `37.0` | `GENETIC` $\to$ `PHENOTYPIC` | Thermal setpoint. Locus: `thermoregulation.neutral_point`. |
| | `temp_tolerance` | `2.0` | `GENETIC` $\to$ `PHENOTYPIC` | Thermal comfort width. Locus: `thermoregulation.tolerance_breadth`. |
| | `growth_rate_per_tick` | `0.0005` | `GENETIC` $\to$ `PHENOTYPIC` | Expressed somatic expansion rate scaled by `ontogenic_state`. |
| | `senescence_start_ticks` | `10000` | `GENETIC` $\to$ `PHENOTYPIC` | Unitless ontogenic fraction: `development.senescence_onset`. |
| | `senescence_wear_rate` | `0.001` | `GENETIC` $\to$ `PHENOTYPIC` | Heritable senescent degradation slope: `development.senescence_rate`. |
| | `repro_energy_cost` | `50.0` | `GENETIC` $\to$ `PHENOTYPIC` | Fraction of somatic energy required for gametogenesis. |
| | `repro_structural_cost` | `20.0` | `GENETIC` $\to$ `PHENOTYPIC` | Somatic biomass contribution to offspring. |
| **Homeostasis** (`homeostasis.py`) | `min_energy_reserve` | `10.0` | `MECHANISTIC(SEMANTIC)` | Contract defining acute physiological starvation crash. |
| | `thermal_inertia` | `0.95` | `MECHANISTIC(PHYSICAL)` | Physical heat capacity of the body tissue. |
| **Dynamics** (`dynamics.py`) | `learning_rate` | `0.08` | `MECHANISTIC` $\leftarrow$ `PHENOTYPIC` | Biological trait is `plasticity.sensorimotor_rate`; binding projects it to EMA $\alpha$. |
| | `state_dim` | `16` | `MECHANISTIC(SEMANTIC)` | Algorithmic state vector dimension of the forward estimator. |
| | `regularization_lambda` | `1e-4` | `MECHANISTIC(NUMERICAL)` | Matrix conditioning parameter to prevent ill-conditioned inversion. |
| **Adaptation** (`adaptation.py`) | `adaptation_ticks` | `100` | `MECHANISTIC(EPISTEMIC)` | Window size required for empirical convergence estimation. |
| | `convergence_threshold` | `0.01` | `MECHANISTIC(EPISTEMIC)` | Mathematical definition of stability. MUST NOT vary across organisms. |
| | `perturbation_resilience` | `0.70` | `GENETIC` $\to$ `PHENOTYPIC` | Physiological resistance to shock. DOES NOT alter convergence definition. |
| **Body Schema** (`body_schema.py`) | `max_receptor_slots` | `64` | `EMBODIMENT_CONSTRAINTS` | Structural constraint set by body chassis affordances. |
| | `max_effector_slots` | `32` | `EMBODIMENT_CONSTRAINTS` | Structural constraint set by body chassis affordances. |
| | `schema_retention_rate` | `0.98` | `GENETIC` $\to$ `PHENOTYPIC` | Locus: `body.schema_plasticity`. |
| **Kernel Limits** (`limits.py`) | `max_graph_nodes` | `1024` | `INFRASTRUCTURE` | Memory ceiling preventing host OOM. Non-heritable computational boundary. |
| | `max_active_edges` | `4096` | `INFRASTRUCTURE` | Computational graph ceiling. |
| **Fitness** (`fitness.py`) | `survival_weight` | `0.5` | `INFRASTRUCTURE` / `LAB` | Objective function defined by Lab experiment protocol, not organism trait. |
| | `efficiency_weight` | `0.5` | `INFRASTRUCTURE` / `LAB` | Evaluator metric defined outside the organism. |
| **Predictive Credit** (`predictive_credit.py`) | `min_samples` | `5` | `MECHANISTIC(EPISTEMIC)` | Minimum statistical support to assert causal credit. |
| | `discount_factor` | `0.9` | `UNRESOLVED` | Candidate for temporal discount trait vs algorithmic contract. |
| **Cognitive Arbitration** (`arbitration.py`) | `salience_weights` (5-way) | `[0.2]*5` | `GENETIC` $\to$ `PHENOTYPIC` | Encoded as $\boldsymbol{z} \in \mathbb{R}^4 \xrightarrow{\Pi} \boldsymbol{w} \in \Delta^4$. |
| | `decision_margin` | `0.05` | `MECHANISTIC(NUMERICAL)` | Epsilon guard against numerical tie-breaking jitter. |
| **Competence** (`competence.py`) | `established_min_support` | `10` | `MECHANISTIC(EPISTEMIC)` | Algorithmic definition of skill establishment. |
| | `novelty_decay` | `0.95` | `GENETIC` $\to$ `PHENOTYPIC` | Locus: `cognition.novelty_habituation_rate`. |
| **Memory Consolidation** (`consolidation.py`) | `replay_cadence` | `50` | `MECHANISTIC` $\leftarrow$ `PHENOTYPIC` | Phenotype `memory_consolidation_drive` mapped to execution cadence ticks. |
| | `pruning_threshold` | `0.02` | `MECHANISTIC(EPISTEMIC)` | Minimum informational entropy for edge retention. |
| **Metacognition** (`metacognition.py`) | `confidence_bounds` | `(0.1, 0.9)` | `MECHANISTIC(NUMERICAL)` | Clamping guards to prevent log-odds overflow. |
| | `metacognitive_sensitivity` | `0.85` | `UNRESOLVED` | Candidate for cognitive monitoring bias; pending Lab preregistration. |
| **Intention & Policy** (`intention.py`, `policy.py`) | `tenacity_ticks` | `12` | `MECHANISTIC` $\leftarrow$ `PHENOTYPIC` | Biological trait `executive_persistence` mapped by binding to persistence ticks. |
| | `stagnation_threshold` | `0.001` | `MECHANISTIC(NUMERICAL)` | Derivative threshold detecting lack of task progress. |
| | `budget_allocation` | `0.6` | `GENETIC` $\to$ `PHENOTYPIC` | Ratio of computational energy allocated to deliberation vs reflex. |

---

### 4.3 Cognitive Capacity Binding Boundaries

`MechanismBinding` must distinguish three distinct layers of cognitive graph sizing:

1. **Expressed Genetic Potential:** $\text{potential} = \text{cognitive\_growth\_potential} \times \text{developmental\_progress}$.
2. **Somatic Affordance Capacity:** Scaled and constrained by somatic biomass (`structural_mass`) and physical sensor/actuator channel envelope.
3. **Host Hard Ceiling:** Non-negotiable computational limit enforced by `KernelLimits` to protect host memory. Expressed capacity is always clamped: $\text{capacity} \le \text{host\_limit}$.

---

## 5. Simplex Parameterization: Reference-Gauge Logistic Coordinates (ALR)

When a biological trade-off represents a distribution over $K$ alternatives (e.g., candidate salience arbitration), the values lie on the standard simplex:
$$\Delta^{K-1} = \left\{ \boldsymbol{w} \in \mathbb{R}^K \;\middle|\; \sum_{i=1}^K w_i = 1, \; w_i > 0 \right\}$$

> **Taxonomic Note:** While the latent geometry in $\mathbb{R}^{K-1}$ and the ALR projection are `ACCEPTED_CANDIDATE`, the specific 5-drive motivational partition (survival, novelty, competence, social cohesion, maintenance) is a provisional candidate model because `social_cohesion` remains `UNRESOLVED`. The mathematical manifold is fixed; the axis semantics remain open to empirical revision.

### 5.1 Additive Log-Ratio (ALR) Latent Space $\mathbb{R}^{K-1}$

To prevent neutral mutational drift caused by the gauge symmetry $\operatorname{softmax}(\boldsymbol{g} + c \cdot \mathbf{1}) = \operatorname{softmax}(\boldsymbol{g})$, the genotype stores an unconstrained vector $\boldsymbol{z} \in \mathbb{R}^{K-1}$.

The forward projection $\Pi: \mathbb{R}^{K-1} \to \Delta^{K-1}$ is defined by:

1. Append fixed reference gauge $z_K = 0$:
   $$\boldsymbol{\tilde{z}} = (z_1, z_2, \dots, z_{K-1}, 0)^T \in \mathbb{R}^K$$
2. Apply centered softmax:
   $$w_i = \frac{\exp(\tilde{z}_i)}{\sum_{j=1}^K \exp(\tilde{z}_j)}$$

### 5.2 Inverse Transformation and Boundary Conditions

For legacy migration or initialization from existing weights $\boldsymbol{w} \in \Delta^{K-1}$:

- **Interior points ($w_i > 0$ for all $i$):**
  $$z_i = \log(w_i) - \log(w_K) \quad \text{for } i \in \{1, \dots, K-1\}$$
- **Boundary points ($w_i = 0$ for some $i$):**
  $\log(0)$ is mathematically undefined. In accordance with longitudinal integrity and provenance invariants, **silent clamping is strictly prohibited**. An explicit declared boundary projection with a provenance audit marker (`PROVENANCE: BOUNDARY_PROJECTION_SIMPLEX_ZERO`) must be emitted.

---

## 6. Structural Developmental Context & Isolation Boundaries

To maintain $\text{World} \neq \text{Body} \neq \text{Organism}$, `DevelopmentalContext` enforces strict isolation:

```text
DevelopmentalContext
├── ontogenic: OntogenicState
│   ├── biological_age: float
│   ├── developmental_progress: float
│   ├── accumulated_somatic_load: float
│   └── inherited_epigenetic_state: EpigeneticState
├── embodiment: EmbodimentConstraints
│   ├── available_receptor_slots: int
│   ├── available_effector_slots: int
│   └── mechanical_dof: int
└── somatic_envelope: SomaticResourceEnvelope
    ├── structural_mass: float
    ├── energy_storage_capacity: float
    └── tissue_thermal_conductivity: float
```

### Prohibited Content in `DevelopmentalContext`

- ❌ **Dynamic World properties:** Gravitational acceleration $g$, ambient air/fluid temperature $T_{\text{ambient}}$, external medium conductivity/viscosity.
- ❌ **Semantic body taxonomies:** `"humanoid"`, `"quadruped"`, `"drone"`, `"left_arm"`, `"vision"`.
- ❌ **Scheduler artifacts:** `cumulative_work_ticks`, loop iterations.
- ❌ **Evaluation & Task metrics:** Fitness scores, benchmark rewards, objective weights.

---

## 7. Decoupled Mechanism Binding

`MechanismBinding` is the algorithmic translation layer that transforms pure `BiologicalPhenotype` traits into concrete runtime parameters given simulation timestep $\Delta t$.

### 7.1 Forward Model Plasticity Example

- **Genotype:** `plasticity.sensorimotor_potency = 0.65` ($\in [0, 1]$).
- **Phenotype:** `sensorimotor_plasticity_rate = 1.35\text{ s}^{-1}$ (continuous physical rate).
- **Binding at $\Delta t = 0.05\text{ s}$:**
  $$\alpha = 1.0 - \exp(-\text{rate} \cdot \Delta t) = 1.0 - \exp(-1.35 \cdot 0.05) \approx 0.0653$$
  Yields `ForwardModelConfig(learning_rate=0.0653)`.
- **Binding at $\Delta t = 0.01\text{ s}$:**
  $$\alpha = 1.0 - \exp(-1.35 \cdot 0.01) \approx 0.0134$$
  Yields `ForwardModelConfig(learning_rate=0.0134)`.

The organism's biological phenotype is **timestep invariant**; only the discrete algorithmic alpha adapts to $\Delta t$.

---

## 8. Expression Provenance

To guarantee that any expressed phenotype can be audited, reproduced, and causally tracked, the runtime captures an explicit `ExpressionSnapshot`:

```python
@dataclass(frozen=True)
class ExpressionSnapshot:
    """Complete provenance tuple guaranteeing reproducible phenotype expression."""
    genotype_hash: str                  # Cryptographic hash of heritable loci
    genome_schema_version: int          # Version of genetic schema (e.g. 2 or 3)
    expression_program_version: int     # Version of ExpressionProgram logic
    phenotype_schema_version: int       # Version of BiologicalPhenotype dataclass
    mechanism_binding_version: int      # Version of MechanismBinding adapter
    developmental_context_hash: str     # Hash of the structural DevelopmentalContext
    phenotype_hash: str                 # Cryptographic hash of the resulting BiologicalPhenotype
```

---

## 9. Implementation Bridge Matrix for Phase 1 over Current Code

The following matrix defines the exact, non-breaking Phase 1 implementation mapping existing `Genome v2` to runtime classes:

| Genome v2 Locus | Expression Trait | BiologicalPhenotype Field | MechanismBinding Target | Existing Runtime Parameter | Current Consumer Class | Migration / Default Impact | Invariant & Test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `soft_node_budget` | Developable ceiling | `cognitive_capacity_ceiling` | `KernelLimits.max_nodes` | `max_graph_nodes` | `symbiont.core.system.Mind` | Scaled by `somatic_mass` | Capped by host limit |
| `soft_edge_budget` | Developable ceiling | `cognitive_edge_ceiling` | `KernelLimits.max_edges` | `max_active_edges` | `symbiont.core.system.Mind` | Scaled by `somatic_mass` | Capped by host limit |
| `learning_rate` (adaptive range) | Sensorimotor potency | `sensorimotor_plasticity_rate` | `ForwardModelConfig.alpha` | `learning_rate = 0.08` | `symbiont.sensorimotor.dynamics` | DERIVED: Inverted from legacy $\alpha$ via $-\ln(1-\alpha)/\Delta t_{\text{ref}}$ | Timestep independence test |
| `consolidation_interval_ticks` | Consolidation cadence | `memory_consolidation_drive` | `ConsolidationConfig.interval` | `replay_cadence = 50` | `symbiont.cognition.consolidation` | Derived: $\text{ticks} = \tau_{\text{base}} / \text{drive}$ | Tick discretizer test |
| `uncertainty_exploration_gain` | Epistemic curiosity | `novelty_seeking_drive` | `ArbitrationPolicy.curiosity` | `salience_weights[1]` | `symbiont.cognition.arbitration` | Maps to salience weight | Simplex normalization test |
| `tentative_lifetime_ticks` | Structural retention | `structural_retention_bias` | `StructureConfig.lifetime` | `tentative_lifetime` | `symbiont.core.structure` | Derived: $\text{ticks} = \tau_{\text{struct}} \cdot \text{retention}$ | Step count binding test |
| `growth_threshold` (range) | Somatic expansion | `somatic_growth_rate` | `PhysiologyConfig.growth` | `growth_rate_per_tick` | `symbiont.core.physiology` | Scaled by developmental progress | Monotonic ontogeny test |
| `reacclimation_sensitivity` | Perturbation resilience | `perturbation_resilience` | `AdaptationConfig.resilience` | `disturbance_tolerance` | `symbiont.sensorimotor.adaptation` | Does NOT affect convergence criteria | Convergence invariance test |

---

## 10. Two-Phase Implementation Strategy

### Phase 1: Phenotype Expression v1 (Non-Breaking Adapter)

- Operates over current `Genome v2` without altering checkpoint schema or `genotype_hash`.
- Constructs `DevelopmentalContext` from existing runtime state and body affordances.
- Implements `PhenotypeExpressionEngine` and `MechanismBinding` following the Bridge Matrix (§9).
- Emits `ExpressionSnapshot` for provenance tracking in longitudinal checkpoints.

### Phase 2: Genome v3 Formalization

- Preregister empirical Lab protocols for all `UNRESOLVED` candidate traits.
- Formalize `Genome v3` with pure dimensionless loci and reference-gauge logistic simplex coordinates.
- Implement explicit locus-by-locus migration transformers (`EXACT`, `DERIVED`, `DEFAULTED`, `DROPPED_MECHANISTIC`).
- Formally supersede `Genome v2`.

---

## 11. Verification & Acceptance Criteria

1. **Deterministic Expression Invariance:** $\mathcal{D}(G, C) \equiv \mathcal{D}(G, C)$ for bitwise identical inputs.
2. **Timestep Independence:** Varying simulation step $\Delta t$ scales runtime ticks in `MechanismBinding` while `BiologicalPhenotype` traits remain strictly constant.
3. **Simplex Non-Redundancy:** Bijective projection between $\mathbb{R}^{K-1}$ and $\Delta^{K-1}$ with non-zero gradient across all interior points.
4. **Boundary Projection Provenance:** Non-positive simplex inputs emit explicit boundary projection provenance markers without silent clamping.
5. **Re-embodiment Phenotypic Response:** Evaluating the same `Genome` under differing `DevelopmentalContext` instances yields distinct `BiologicalPhenotype` instances while preserving identical `genotype_hash`.
6. **Architectural Isolation:** Static lint/import check ensuring `GenomeSchema` and `BiologicalPhenotype` contain zero imports of `PhysiologyConfig`, `ForwardModelConfig`, or `symbiont_lab`.
