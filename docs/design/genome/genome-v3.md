---
id: design.genome.genome-v3
title: "Genome V3"
document_type: design
domain: genome
status: proposed
canonical: false
implementation_status: not_started
migrated_on: 2026-10-03
last_reviewed: 2026-10-03
language: en
---

# Genome v3 — Specification and Candidate Genetic Architecture

- **Status:** Proposed
- **Implementation status:** Not started
- **Governing ADR:** [ADR-0064](../../adr/ADR-0064-phenotype-expression-and-genome-decoupling.md)
- **Companion Design:** [Phenotype Expression v1](phenotype-expression-v1.md)
- **Predecessor:** [Genome v2](genome-v2.md)
- **Domain:** Genetics, Evolutionary Search, Ontogeny

---

## 1. Abstract & Purpose

Genome v3 is the proposed successor to [Genome v2](genome-v2.md). While Genome v2 successfully decoupled the genome from bodily anatomy (`ActuatorSurface`) and external computational limits (`KernelLimits`), it retained two critical architectural shortcomings:

1. **Simulation Timestep Coupling:** Loci such as `consolidation_interval_ticks` and `tentative_lifetime_ticks` coupled heritability directly to simulation tick frequencies.
2. **Mechanistic Overlap and Unconstrained Simplex Spaces:** Algorithmic convergence parameters (e.g. `minimum_support`) were represented as heritable genes, and multi-component trade-offs lacked latent space guarantees against neutral genetic drift.

Genome v3 completes the separation established in [ADR-0064](../../adr/ADR-0064-phenotype-expression-and-genome-decoupling.md) and [Phenotype Expression v1](phenotype-expression-v1.md):

- **Pure Dimensionless Representation:** Every locus in Genome v3 is unitless and normalized ($\in [0, 1]$ or latent coordinates in $\mathbb{R}$).
- **Simplex Coordinates in $\mathbb{R}^{K-1}$:** Multi-component resource or salience allocations are stored in unconstrained latent coordinates via reference-gauge logistic coordinates (additive log-ratio parameterization), guaranteeing non-redundant degrees of freedom.
- **Sole Consumer Contract:** Genome v3 is consumed *exclusively* by `ExpressionProgram`. It never directly initializes Python runtime configuration classes (`PhysiologyConfig`, `ForwardModelConfig`, etc.).
- **Demarcated Candidate Inventory:** Purges all epistemic, numerical, and mechanistic parameters, classifying candidate loci by developmental validation status (`ACCEPTED_CANDIDATE`, `UNRESOLVED`, `DEFERRED`).

---

## 2. Invariants of Genome v3

1. **Constitutive Primacy:** The genome encodes only heritable biological potentials, basal metabolic costs, developmental ceilings, and allocation biases. Acquired empirical state, episodic memories, and learned skills are strictly non-heritable.
2. **Timestep Agnosticism:** No locus in Genome v3 may be denominated in, or scaled by, simulation "ticks", steps, or wall-clock seconds.
3. **Dimensionless Normalization:** Every scalar locus $g_i$ satisfies $g_i \in [0, 1]$ or represents an unconstrained real latent parameter $z_i \in \mathbb{R}$.
4. **Non-Redundant Simplex Geometry:** For any $K$-alternative biological trade-off, Genome v3 encodes exactly $K-1$ real latent parameters $\boldsymbol{z} \in \mathbb{R}^{K-1}$, projecting onto $\Delta^{K-1}$ via canonical reference-gauge softmax.
5. **Consumer Isolation:** No class in `symbiont.core` or `symbiont.sensorimotor` may take `Genome` as a direct constructor argument; all runtime configuration flows through `MechanismBinding(BiologicalPhenotype)`.
6. **Content Addressing:** `genotype_hash` is computed strictly over canonical normalized genetic loci; genealogy, lineage metadata, and individual identifiers live outside the genome payload.
7. **Morphological Independence:** The genome contains no anatomy, sensor modalities, actuator counts, joint structures, or bodily health indicators.
8. **Evolvability Preservation:** Mutation and recombination operators act on dimensionless loci and latent vectors without altering algorithmic invariants or violating simplex constraints.
9. **Independent Provenance Contract:** Expression semantics (`expression_program_version`, `phenotype_schema_version`, `mechanism_binding_version`) are versioned and persisted independently from `genome_schema_version` to guarantee reproducible phenotype reconstruction.
10. **Single Operative Representation:** `symbiont.genetics.Genome` remains the sole operative genotype across all experimental launchers and runtime profiles.
11. **Constitutional Golden Invariant:** No locus shall be added, removed, or scaled merely to force an experiment or benchmark to pass.

---

## 3. Causal Developmental Flow

```text
┌──────────────────────────────────────────────┐
│                  Genome v3                   │
│   (Dimensionless Loci & Latent Coordinates)  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              ExpressionProgram               │
│   Inputs: Genome v3 + DevelopmentalContext   │
│   Outputs: BiologicalPhenotype               │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│             BiologicalPhenotype              │
│   (Expressed traits at ontogenic stage t)    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│               MechanismBinding               │
│   (Discretizes physical traits to configs)   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│            Runtime Configuration             │
│   PhysiologyConfig, ForwardModelConfig, etc. │
└──────────────────────────────────────────────┘
```

---

## 4. Candidate Genetic Architecture for Genome v3

The loci below represent the proposed candidate architecture. In accordance with the governance sequence, loci retain explicit validation tags until Genome v3 is formally approved:

- `ACCEPTED_CANDIDATE`: Demarcated trait with an identified consumer and proven phenotypic mapping.
- `UNRESOLVED`: Borderline biological trait requiring preregistered Lab empirical study.
- `DEFERRED`: Structural or evolvability mechanism requiring a separate constitutional decision or ADR.

---

### 4.1 Metabolism & Somatic Maintenance (`metabolism.*`)

| Locus Name | Range | Status | Interpretation in Phenotype |
| --- | --- | --- | --- |
| `metabolism.basal_efficiency` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Inherent energetic efficiency of baseline somatic maintenance. |
| `metabolism.repair_potency` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Efficacy of somatic self-repair per unit of surplus energy. |
| `metabolism.fatigue_susceptibility` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Susceptibility to somatic fatigue accumulation under continuous work. |
| `metabolism.fatigue_recovery` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Speed of fatigue dissipation during quiescence/rest. |
| `metabolism.reproduction_investment` | $[0, 1]$ | `UNRESOLVED` | Fraction of somatic energy reserve committed to reproductive gametogenesis. |

### 4.2 Thermoregulation (`thermoregulation.*`)

| Locus Name | Range | Status | Interpretation in Phenotype |
| --- | --- | --- | --- |
| `thermoregulation.neutral_point` | $[0, 1]$ | `UNRESOLVED` | Normalized thermal setpoint. Requires Lab protocol validating heritable temperature preference. |
| `thermoregulation.tolerance_breadth` | $[0, 1]$ | `UNRESOLVED` | Width of thermal operating window before homeostatic stress triggers. |

### 4.3 Ontogeny & Development (`development.*`)

| Locus Name | Range | Status | Interpretation in Phenotype |
| --- | --- | --- | --- |
| `development.somatic_growth_rate` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Maximal rate of somatic expansion during juvenile ontogeny. |
| `development.senescence_onset` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Fraction of total expected lifespan before senescent wear accelerates. |
| `development.senescence_rate` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Slope of metabolic and somatic decay in post-reproductive life. |
| `development.cognitive_growth_potential` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Developable soft graph capacity ceiling ($\text{soft} \le \text{host\_limit}$). |

### 4.4 Plasticity & Learning (`plasticity.*`)

| Locus Name | Range | Status | Interpretation in Phenotype |
| --- | --- | --- | --- |
| `plasticity.sensorimotor_rate` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Forward-model adaptation speed (maps to continuous adaptation rate $s^{-1}$). |
| `plasticity.receptive_breadth` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Representational breadth of sensory receptive field adaptation. |
| `plasticity.habituation_rate` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Rate of decay in cognitive responsiveness to recurring stimuli. |
| `plasticity.metaplastic_sensitivity` | $[0, 1]$ | `UNRESOLVED` | Neuromodulation gain in response to persistent prediction errors. |

### 4.5 Memory & Consolidation (`memory.*`)

| Locus Name | Range | Status | Interpretation in Phenotype |
| --- | --- | --- | --- |
| `memory.working_retention` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Retention half-life in short-term working memory buffers. |
| `memory.consolidation_drive` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Propensity to trigger offline replay and structural network consolidation. |
| `memory.encoding_selectivity` | $[0, 1]$ | `UNRESOLVED` | Disposition governing experience filtering; MechanismBinding derives recording threshold. |

### 4.6 Candidate Salience & Arbitration Simplex (`arbitration.candidate_salience_latent`)

Arbitration over motivational drives is represented as a **candidate latent vector in $\mathbb{R}^4$** with status `ACCEPTED_CANDIDATE`:
$$\boldsymbol{z}_{\text{salience}} = (z_1, z_2, z_3, z_4) \in \mathbb{R}^4$$

Projected deterministically via reference-gauge logistic coordinates ($z_5 = 0$):
$$w_i = \frac{\exp(\tilde{z}_i)}{\sum_{j=1}^5 \exp(\tilde{z}_j)}$$

| Component | Target Drive in Phenotype | Status | Meaning |
| --- | --- | --- | --- |
| $w_1$ | `survival_preservation` | `ACCEPTED_CANDIDATE` | Urgency to escape immediate somatic damage or acute fatigue. |
| $w_2$ | `novelty_curiosity` | `ACCEPTED_CANDIDATE` | Intrinsic motivation to explore unpredicted states. |
| $w_3$ | `competence_mastery` | `ACCEPTED_CANDIDATE` | Intrinsic motivation to practice and refine emerging motor skills. |
| $w_4$ | `social_cohesion` | `UNRESOLVED` | Bias towards epistemic alignment; subject to ongoing social architecture studies. |
| $w_5$ | `metabolic_maintenance` | `ACCEPTED_CANDIDATE` | Bias towards energy harvesting and somatic repair. |

> **Taxonomic Note on Motivational Axes:** While the mathematical manifold ($\mathbb{R}^4 \to \Delta^4$) is `ACCEPTED_CANDIDATE`, the 5-component drive taxonomy is explicitly provisional. Component $w_4$ (`social_cohesion`) is `UNRESOLVED` and subject to active social epistemology research; the vector dimension and component semantics remain candidate until empirical closure.

### 4.7 Executive Policy & Tenacity (`executive.*`)

| Locus Name | Range | Status | Interpretation in Phenotype |
| --- | --- | --- | --- |
| `executive.persistence` | $[0, 1]$ | `ACCEPTED_CANDIDATE` | Resistance to abandoning current goal under stagnation (tenacity bias). |
| `executive.deliberation_budget` | $[0, 1]$ | `UNRESOLVED` | Computational energy partition: reflex actions vs prospective rollout. |
| `executive.risk_tolerance` | $[0, 1]$ | `UNRESOLVED` | Propensity to select high-variance actions under uncertainty. |

### 4.8 Evolvability & Recombination (`evolvability.*`)

| Locus Name | Range | Status | Governance Rationale |
| --- | --- | --- | --- |
| `evolvability.family_mutation_scales` | Mapping | `DEFERRED` | Heritable mutability alters lineage mutation distributions; requires dedicated constitutional ADR. |
| `evolvability.recombination_linkage` | $[0, 1]$ | `DEFERRED` | Crossover suppression between gene clusters; deferred pending reproductive model consolidation. |

---

## 5. Deliberately Purged Loci (from Genome v2)

The following loci from Genome v2 are **purged** in Genome v3:

1. **`consolidation_interval_ticks`:** Purged because ticks are simulation artifacts. Replaced by dimensionless `memory.consolidation_drive`.
2. **`tentative_lifetime_ticks`:** Purged because ticks are simulation artifacts. Replaced by `plasticity.habituation_rate` and `structural_retention`.
3. **`minimum_support`:** Purged because statistical support threshold is an epistemic property of the hypothesis testing algorithm (`MECHANISTIC(EPISTEMIC)`).
4. **`growth_threshold` and `pruning_threshold` (discrete values):** Purged; algorithmic thresholds are `MECHANISTIC(NUMERICAL)`. Replaced by continuous growth potentials.
5. **Raw 5-way vector weights:** Purged; replaced by reference-gauge logistic coordinates in $\mathbb{R}^4$.

---

## 6. Migration and Compatibility Contract (v2 $\to$ v3)

### 6.1 Locus-Specific Migration Taxonomy

Automatic migration from Genome v2 to Genome v3 is **not a blanket numerical conversion**. Each legacy locus receives an explicit, auditable disposition:

- **`EXACT`:** Dimensionless locus copied directly without modification (e.g., `uncertainty_exploration_gain` mapped to normalized curiosity bias).
- **`DERIVED`:** Re-parameterized via an explicit, documented transformation function justified by causal equivalence tests (e.g., discrete `learning_rate` $\alpha$ bounds inverted to continuous adaptation rate $s^{-1}$ via $-\ln(1-\alpha)/\Delta t_{\text{ref}}$).
- **`DEFAULTED`:** New candidate loci in v3 not present in v2 receive default values defined in the canonical organism profile.
- **`DROPPED_MECHANISTIC`:** Loci identified as algorithmic parameters (e.g., `minimum_support`) are omitted from the genome and managed by mechanism configuration.
- **`UNRESOLVED`:** Traits undergoing empirical study are not migrated automatically until positive closure of their respective Lab protocol.

### 6.2 Simplex Inverse Migration & Boundary Conditions

When migrating legacy 5-way salience vectors $(w_1, \dots, w_5)$:

- **If all $w_i > 0$:** Exact additive log-ratio (ALR) transform:
  $$z_i = \log(w_i) - \log(w_5) \quad \text{for } i \in \{1, 2, 3, 4\}$$
- **If any $w_i = 0$:** Mathematical $\log(0)$ boundary condition. Silent clamping is strictly forbidden. The migration engine requires a declared boundary projection accompanied by an auditable provenance marker (`PROVENANCE: BOUNDARY_PROJECTION_SIMPLEX_ZERO`).

### 6.3 Serialization Schema and Complete Provenance

```json
{
  "schema_version": 3,
  "genotype_hash": "sha256:...",
  "provenance": {
    "genome_schema_version": 3,
    "expression_program_version": 1,
    "phenotype_schema_version": 1,
    "mechanism_binding_version": 1,
    "parent_v2_genotype_hash": "sha256:... (if migrated)"
  },
  "loci": {
    "metabolism": { "basal_efficiency": 0.72, "repair_potency": 0.55, "fatigue_susceptibility": 0.30, "fatigue_recovery": 0.60 },
    "development": { "somatic_growth_rate": 0.40, "senescence_onset": 0.75, "senescence_rate": 0.20, "cognitive_growth_potential": 0.65 },
    "plasticity": { "sensorimotor_rate": 0.65, "receptive_breadth": 0.50, "habituation_rate": 0.70 },
    "memory": { "working_retention": 0.80, "consolidation_drive": 0.60 },
    "arbitration": { "candidate_salience_latent": [0.25, -0.10, 0.40, -0.30] },
    "executive": { "persistence": 0.63 }
  }
}
```

---

## 7. Acceptance Criteria for Genome v3 Promotion

Genome v3 will remain `Proposed` until the following formal sequence completes:

1. **Phase 1 Validation:** `Phenotype Expression v1` operates stably as an adapter over `Genome v2` on `main`.
2. **Empirical Preregistration:** All loci marked `UNRESOLVED` (thermoregulation preference, encoding selectivity, social drive, deliberation budget) complete preregistered characterization studies in Lab.
3. **Evolvability ADR:** If heritable mutation scales or crossover suppression are retained, an authorized constitutional ADR governs their mechanics.
4. **Equivalence & Determinism Tests:** Automated test suite confirms that identical v3 genomes produce identical phenotypes under identical contexts, with zero neutral drift on simplex manifolds.
5. **Re-embodiment Invariance:** Checkpoint save, restore, and re-embodiment tests confirm complete preservation of `genotype_hash` across differing body chassis.
