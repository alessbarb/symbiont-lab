---
id: explanation.math.05-creencias-bayesianas-y-disidencia
title: "05 Bayesian Beliefs And Dissent"
document_type: explanation
domain: math
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Belief Dynamics, Epistemic Surprise, and Dissent Registration

> **Status:** IMPLEMENTED  
> **Type:** ADAPTIVE FILTER WITH BAYESIAN MOTIVATION  
> **Related modules:** [`symbiont.core.beliefs`](../../src/symbiont/core/cognition/beliefs.py), [`symbiont.core.evidence`](../../src/symbiont/core/cognition/evidence.py)

---

## 1. The Nature of Beliefs in Symbiont

In Symbiont, a belief is not a deterministic label, but a subjective distribution that evolves in the face of noisy local perceptions ([`symbiont.core.beliefs`](../../src/symbiont/core/cognition/beliefs.py)).

The model pursues four operational properties:

1. **Smooth Accumulation:** As consistent evidence is observed, subjective certainty increases.
2. **Reversibility:** If the host's behavior changes, the belief can cross the decision boundary ($p \ge 0.5 \leftrightarrow p < 0.5$).
3. **Conflict Sensitivity:** If successive observations conflict with each other, certainty decays.
4. **Dissent Preservation:** If a batch of evidence strongly disagrees with the established baseline, the disagreement is recorded immutably as an explicit historical event ([`symbiont.core.evidence`](../../src/symbiont/core/cognition/evidence.py)).

---

## 2. The Update Model with Pseudo-Observations

Each pattern or abstract signature $\text{fp}$ maps to a state [`BeliefState`](../../src/symbiont/core/cognition/beliefs.py):

$$\mathbf{b} = (p, E, C) \in [0, 1] \times [0, E_{\max}] \times [0, 1]$$

where $p$ is the estimated posterior probability, $E$ is the accumulated evidence mass ($E_{\max} = 32.0$), and $C$ is the exponential memory of accumulated conflict.

### 2.1 Update Equation

When observing a probability $P_{\text{obs}} \in [0, 1]$ with confidence $c_{\text{obs}} \in [0, 1]$:

$$w = \max(0.05, c_{\text{obs}})$$

$$P_{\text{posterior}} = \frac{P_{\text{prior}} \cdot E + P_{\text{obs}} \cdot w}{E + w}$$

### 2.2 Bayesian Interpretation and Saturation Limit

During the **unsaturated** phase ($E + w \le E_{\max}$), this rule is mathematically isomorphic to updating the mean of a conjugate Beta distribution $\text{Beta}(\alpha, \beta)$ with $E = \alpha + \beta$.

> **Bayesian Inference Nuance:**  
> When the accumulated evidence reaches the configured cap $E_{\max} = 32.0$, the update applies:
>
> $$E_{t} = \min(32.0, \; E_{t-1} + w) = 32.0$$
>
> The probability $P_{\text{posterior}}$ is temporarily computed with denominator $E + w$, but in the next step the state is stored with mass 32.0. Therefore, after saturation, the system **ceases to be an exact conjugate Bayesian estimator** and operates as a **finite-mass adaptive filter**, designed to prevent epistemic paralysis and allow for belief reversals in the face of sustained new evidence.

---

## 3. Conflict Dynamics and Surprise

Surprise measures the instantaneous absolute discrepancy:

$$S_t = |P_{\text{obs}} - P_{\text{prior}}| \in [0, 1]$$

### 3.1 Accumulated Conflict Filter

The conflict $C_t$ integrates surprise over time as a low-pass filter:

$$C_t = \min\Big( 1.0, \; 0.75 \cdot C_{t-1} + 0.25 \cdot S_t \Big)$$

- If observations confirm the expectation ($S_t \approx 0$), the conflict decays toward zero with a half-life of $\approx 2.4$ steps.
- If observations continuously oscillate between extremes ($S_t \approx 1$), $C_t$ saturates at $1.0$.

### 3.2 Belief Reversals

A reversal is recorded when the probability crosses the decision boundary ($0.5$) relative to the previous step, given that prior revisions existed:

$$\text{Reversal}_t = \mathbb{I}\Big( (P_{\text{prior}} \ge 0.5) \neq (P_{\text{posterior}} \ge 0.5) \land \text{revisions} > 0 \Big)$$

---

## 4. Subjective Certainty Function and Dimensional Analysis

Certainty $\text{Certainty} \in [0, 1]$ in [`BeliefState.certainty`](../../src/symbiont/core/cognition/beliefs.py) is defined as:

$$\text{Certainty}(E, C) = \operatorname{clip}\left( \Big( 1 - e^{-E / 4.0} \Big) \cdot \Big( 1 - 0.60 \cdot C \Big), \; 0.0, \; 1.0 \right)$$

```text
Certainty
   ▲
1.0│              C = 0.0 (Sin conflicto)
   │             .───────────────────────  1 - exp(-E/4)
0.8│          .─'
   │       .─'    C = 0.5 (Conflicto moderado)
   │     .─'─────────────────────────────  0.7 * [1 - exp(-E/4)]
0.4│ .─'          C = 1.0 (Máximo conflicto)
   │.────────────────────────────────────  0.4 * [1 - exp(-E/4)]
0.0└──────┬──────┬──────┬──────┬──────► Masa de Evidencia E
   0      4      8      16     32
```

### 4.1 Conceptual Distinction: Certainty, Polarization, and Conflict

To avoid pedagogical ambiguities, the compendium formalizes three orthogonal dimensions:

1. **Strength or Maturity of the Belief ($E$):** Accumulated mass of observations.
2. **Probability Polarization ($|p - 0.5|$):** Proximity to deterministic extremes (0 or 1).
3. **Historical Conflict ($C$):** Accumulated level of recent surprise and contradiction.

> **Clarification on $p = 0.5$:**  
> A state with $p = 0.5, E = 32.0, C = 0.0$ generates a certainty of:
> $$\text{Certainty} = 1 - e^{-32/4} = 1 - e^{-8} \approx 0.999665$$
> This indicates **high confidence in the stability of the estimation**, not an ontological demonstration that the phenomenon is a perfect coin. It reflects that, under the observed evidence, the subjective probability has stabilized consistently in the center without oscillations.

---

## 5. Standardized Batch Discrepancy and Dissent Registration

When the organism executes a high-resolution inspection (*second look*), it collects a batch of discrete readings $\mathcal{X}_{\text{batch}} = \{x_1, \dots, x_m\}$.

[`EvidenceRevisionLedger`](../../src/symbiont/core/cognition/evidence.py) evaluates whether this batch clashes with the acclimated baseline $(\mu_{\text{prior}}, \sigma_{\text{prior}})$.

### 5.1 Standardized Displacement Discrepancy

The batch mean $\bar{x}_{\text{batch}} = \frac{1}{m}\sum x_i$ is calculated, and the displacement is evaluated:

$$Z_{\text{batch}} = \frac{\bar{x}_{\text{batch}} - \mu_{\text{prior}}}{\sigma_{\text{prior}}}$$

> **Distinction from the Classic Z-Test:**  
> The $Z_{\text{batch}}$ formulation **does not divide by $\sqrt{m}$**. Therefore, it is not a statistical significance test to check if the sample mean comes from the population (whose statistic would be $\frac{\bar{x} - \mu}{\sigma / \sqrt{m}}$). In Symbiont, $Z_{\text{batch}}$ represents a **heuristic measure of the displacement size in standard deviations from the baseline**.

### 5.2 Emission and Preservation of Dissent

If the previous baseline is acclimated ($\sigma_{\text{prior}} > 0$) and the discrepancy exceeds the threshold:

$$|Z_{\text{batch}}| \ge z_{\text{conflict}} \quad (\text{by default } z_{\text{conflict}} = 2.0)$$

An immutable [`DissentRecord`](../../src/symbiont/core/cognition/evidence.py) log is generated:

$$\text{DissentRecord} = \big( \text{capability\_id}, \; \mu_{\text{prior}}, \; \sigma_{\text{prior}}, \; \bar{x}_{\text{batch}}, \; Z_{\text{batch}} \big)$$

The organism applies a deliberate double movement:

1. **Adapts the baseline:** The readings are transferred to acclimation (`acclimation.observe`), allowing the organism to assimilate the observed reality.
2. **Preserves the discord:** The disagreement record is stored in a circular queue of size 256, allowing the narrative layer ([`symbiont.core.narrative`](../../src/symbiont/core/foundation/narrative.py)) to report to the human operator that the belief was modified under conditions of statistical contestation.
