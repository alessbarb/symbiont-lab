---
id: explanation.math.06-consenso-colectivo-y-confianza
title: "06 Collective Consensus And Trust"
document_type: explanation
domain: math
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Collective Consensus, Trust Dynamics and Epigenetic Distillation

> **Status:** IMPLEMENTED  
> **Type:** COOPERATIVE PROTOCOL AND REPUTATION DYNAMICS  
> **Related modules:** [`symbiont.core.trust`](../../src/symbiont/core/social/trust.py), [`symbiont.core.collective`](../../src/symbiont/core/social/collective.py), [`symbiont.core.heritage`](../../src/symbiont/core/lineage/heritage.py)

---

## 1. The Problem of Consensus without Ground Truth

In a population of decentralized agents or a federation of hosts exchanging signed capsules:

- No node acts as a central oracle of truth.
- Some agents may emit inverted or malicious reports (*poisoned reporters*).
- Observed signals are noisy and local.

The system addresses two simultaneous mathematical problems:

1. **Evidence Aggregation:** How to combine the discrete votes of multiple sources to infer a coherent collective belief?
2. **Endogenous Trust Evaluation (*Trust Modeling*):** How to evaluate if a source is reliable without having external truth labels to contrast their claims?

Symbiont implements these mechanisms in [`SourceTrustModel`](../../src/symbiont/core/social/trust.py), [`CollectiveMemory`](../../src/symbiont/core/social/collective.py) and [`SpeciesHeritage`](../../src/symbiont/core/lineage/heritage.py).

---

## 2. Continuous Statistical Agreement Function

> **Classification:** CODE IDENTITY / HEAVY-TAILED SIMILARITY METRIC

When a host receives a knowledge capsule ([`KnowledgeCapsule`](../../src/symbiont/core/social/capsule.py)) cryptographically signed with Ed25519, it extracts the claimed remote mean $\mu_{\text{remote}}$ for a capability $c_k$.

The local organism compares this claim with its own acclimated distribution $\mathcal{N}(\mu_{\text{local}}, \sigma_{\text{local}}^2)$ via [`agreement_score`](../../src/symbiont/core/social/trust.py#L31-L45):

If the capability is not locally acclimated or $\sigma_{\text{local}} = 0.0$, the system returns `None` (epistemic silence given the lack of comparative baseline). Otherwise:

$$z = \frac{|\mu_{\text{remote}} - \mu_{\text{local}}|}{\sigma_{\text{local}}}$$

$$\operatorname{Agreement}(z) = \frac{1}{1 + z} \in (0, 1]$$

```text
Agreement
   ▲
1.0│  .
   │   ╲
0.8│    ╲
   │     ╲
0.5│───────● (z = 1: discrepancia de 1 desvío típico)
   │        ╲
0.2│         `─.
   │            `───.
0.0└────────┬────────┬────────► Discrepancia Estandarizada z
   0        1        4
```

### 2.1 Analytical Properties

1. **Exact Agreement:** $\lim_{z \to 0^+} \operatorname{Agreement}(z) = 1.0$.
2. **Decreasing Monotonicity:** $\frac{d}{dz} \operatorname{Agreement}(z) = -\frac{1}{(1+z)^2} < 0 \quad \forall z \ge 0$.
3. **Heavy Tail:** Unlike radial basis Gaussian functions ($\exp(-z^2)$), which numerically collapse to zero given moderate discrepancies ($e^{-16} \approx 10^{-7}$ for $z=4$), the hyperbolic curve $\frac{1}{1+z}$ assigns $0.20$ for $z=4$, avoiding the premature annihilation of the reputation gradient.

---

## 3. Evidence Fusion in Collective Memory

In the population simulator ([`CollectiveMemory`](../../src/symbiont/core/social/collective.py)), each agent $s$ emits for a signature $\text{fp}$ a vote containing its verdict $\text{threat}_s \in \{0, 1\}$ and its declared confidence $C_s \in [0.05, 1.0]$.

The informational weight assigned to each informant is modulated by its accumulated reputation $T(s) \in [0.15, 0.98]$:

$$w_s = T(s) \cdot C_s$$

### 3.1 Live Collective Probability

The contemporary collective probability $P_{\text{live}} \in [0, 1]$ is the weighted average:

$$P_{\text{live}} = \frac{\sum_{s \in \text{Votes}} w_s \cdot \text{threat}_s}{\sum_{s \in \text{Votes}} w_s}$$

### 3.2 Decomposition of Collective Certainty

The consensus certainty $c_{\text{live}} \in [0, 1]$ combines four orthogonal dimensions:

$$c_{\text{live}} = \min\Big( 1.0, \; 0.35 \cdot D + 0.25 \cdot \bar{C} + 0.25 \cdot A + 0.15 \cdot \bar{T} \Big)$$

1. **Source Diversity ($D$):** Saturates upon reaching 10 independent informants:
   $$D = \min\left( \frac{|\text{Votes}|}{10.0}, \; 1.0 \right)$$
2. **Mean Declared Confidence ($\bar{C}$):**
   $$\bar{C} = \frac{1}{|\text{Votes}|} \sum_{s} C_s$$
3. **Population Polarization / Agreement ($A$):**
   $$A = 2.0 \cdot |P_{\text{live}} - 0.5| \in [0, 1]$$
4. **Mean Source Reputation ($\bar{T}$):**
   $$\bar{T} = \frac{1}{|\text{Votes}|} \sum_{s} T(s)$$

---

## 4. Trust Recalibration via Leave-One-Out Consensus

> **Classification:** RECALIBRATION HEURISTIC / LIMIT CASE ANALYSIS

In [`CollectiveMemory.recalibrate_sources`](../../src/symbiont/core/social/collective.py#L166-L218), the system evaluates the legitimacy of an informant $s$ by comparing its vote with the consensus of the rest of the population **explicitly excluding $s$**:

$$W_{-s} = \sum_{p \in \text{Votes} \setminus \{s\}} T(p) \cdot C_p$$

$$P_{-s} = \frac{1}{W_{-s}} \sum_{p \in \text{Votes} \setminus \{s\}} T(p) \cdot C_p \cdot \text{threat}_p$$

The belief of the peers is:

$$\text{PeerBelief}_{-s} = \mathbb{I}\left( P_{-s} \ge 0.5 \right)$$

### 4.1 Adjustment Target and EWMA Filter

The binary agreement indicator is defined:

$$\operatorname{Agreement}(s) = \mathbb{I}\Big( \text{threat}_s == \text{PeerBelief}_{-s} \Big)$$

The reputation target is set to:

$$\text{Target} = 0.20 + 0.75 \cdot \operatorname{Agreement}(s) = \begin{cases} 0.95 & \text{si concuerda con sus pares} \\ 0.20 & \text{si discrepa de sus pares} \end{cases}$$

The reputation $T(s)$ is smoothly updated via an EWMA filter with hard bounds:

$$T_{t+1}(s) = \operatorname{clip}\Big( 0.90 \cdot T_t(s) + 0.10 \cdot \text{Target}, \; 0.15, \; 0.98 \Big)$$

### 4.2 Critical Analysis and Trust Model Limits
>
> **Warning regarding Leave-One-Out Consensus:**  
> This scheme is **inspired by Leave-One-Out cross-validation**, but it does not constitute a formal Jackknife statistical estimator (it does not generate pseudovalues or estimate variances of estimators).  
> Its theoretical limitations are:
>
> 1. **No Absolute Isolation:** The minimum trust value is bounded at $T_{\min} = 0.15$. A hostile informant is never mathematically silenced; its weight is strongly attenuated, but persists in the weighted mixture.
> 2. **Vulnerability to Coordinated Majorities (*Sybil / Echo Chamber*):** If malicious agents exceed $50\%$ of the active weight on a pattern, the Leave-One-Out consensus will systematically punish the minority honest agents, reducing their trust towards $0.20$.
> 3. **Unmodeled Correlation:** Treating multiple agents as independent votes assumes uncorrelated sources. If several agents share an identical upstream, their joint vote artificially amplifies the apparent weight.

**Idealized Limit Case ($\Delta_{\text{trust}} \to 0.75$):**  
Under the strict assumption of a stable and uncorrelated honest majority, honest agents asymptotically converge to $T^* \approx 0.95$ and poisoned ones to $T^* \approx 0.20$, producing a limit trust gap of $\Delta_{\text{trust}} \approx 0.75$. This value must be interpreted as an idealized laboratory case, not as a universal Byzantine security guarantee.

---

## 5. Epigenetic Distillation and Intergenerational Fusion

> **Classification:** COMPRESSION POLICY AND PRIORS ATTENUATION

Between generations of agents, accumulated knowledge is transferred as a **compressed epigenetic distillation** ([`SpeciesHeritage`](../../src/symbiont/core/lineage/heritage.py)).

### 5.1 Quadruple Selection Criteria

A pattern $\text{fp}$ qualifies to be distilled into the hereditary heritage if it passes four filters:

1. **Sample Support:** $\text{reports} \ge 6$.
2. **Source Diversity:** $|\text{votes}| \ge 4$.
3. **Minimum Certainty:** $c_{\text{live}} \ge 0.68$.
4. **Indifference Separation:** $|P_{\text{live}} - 0.5| \ge 0.20$.

### 5.2 Epigenetic Certainty Attenuation

So that an inherited prior does not stifle the empirical learning capability of the new generation, the transmitted certainty $c_{\text{inh}}$ is deliberately attenuated:

$$c_{\text{inh}} = \min\Big( 0.55, \; 0.25 + 0.35 \cdot c_{\text{live}} \Big)$$

Even given absolute prior certainty ($c_{\text{live}} = 1.0$), the new generation inherits at most a certainty of $0.55$.

### 5.3 Bayesian Prior-Live Fusion Function

The new generation combines its live evidence with the inherited prior:

$$w_{\text{prior}} = 0.65 \cdot c_{\text{prior}}, \qquad w_{\text{live}} = \max(c_{\text{live}}, 0.15)$$

$$P_{\text{combined}} = \frac{P_{\text{live}} w_{\text{live}} + P_{\text{prior}} w_{\text{prior}}}{w_{\text{live}} + w_{\text{prior}}}$$

$$c_{\text{combined}} = \min\Big( 1.0, \; c_{\text{live}} + 0.18 \cdot c_{\text{prior}} \cdot (1.0 - c_{\text{live}}) \Big)$$

The factor $0.18 \cdot c_{\text{prior}} \cdot (1.0 - c_{\text{live}})$ provides an orienting informational bias in the initial phases ($c_{\text{live}} \approx 0$), but smoothly fades as direct empirical evidence matures ($c_{\text{live}} \to 1$).
