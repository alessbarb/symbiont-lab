---
id: explanation.math.07-cognicion-agentes-y-metacognicion
title: "07 Agent Cognition And Metacognition"
document_type: explanation
domain: math
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Agent Cognition, Counterfactual Curiosity and Metacognition

> **Status:** IMPLEMENTED  
> **Type:** HEURISTIC DECISION RULES AND MULTIVARIATE METASCORE  
> **Related modules:** [`symbiont.core.model`](../../src/symbiont/core/foundation/model.py), [`symbiont.core.agent`](../../src/symbiont/core/cognition/agent.py), [`symbiont.core.curiosity`](../../src/symbiont/core/cognition/curiosity.py), [`symbiont.core.metacognition`](../../src/symbiont/core/cognition/metacognition.py)

---

## 1. Introduction to the Agent Cognitive Cycle

In Symbiont, each autonomous agent synthesizes continuous observations, builds local normality models, formulates causal hypotheses, explores counterfactual questions via intrinsic curiosity, and issues evaluations on the state of its beliefs.

The design is structured in three levels:

1. **Sensorimotor and Representational Level:** Discretization into ternary Hamming signatures and multivariate novelty detection ([`symbiont.core.model`](../../src/symbiont/core/foundation/model.py)).
2. **Inference and Decision Level:** Calculation of apparent risk, combined suspicion, curiosity, and drift adaptation via hysteresis ([`symbiont.core.agent`](../../src/symbiont/core/cognition/agent.py)).
3. **Metacognitive Level:** Aggregation of epistemic pressures in the population and classification of qualitative certainty regimes ([`symbiont.core.metacognition`](../../src/symbiont/core/cognition/metacognition.py)).

> **Epistemological Note:**  
> The equations in this chapter constitute **multilinear heuristic scoring models** empirically calibrated to balance exploration and stability in the simulation environment, not analytical deductions from formal statistical decision theory.

---

## 2. Ternary Signature Algebra and Multivariate Novelty

> **Classification:** CODE IDENTITY / INFORMATION COMPRESSION

Given the synthetic observation vector $\mathbf{x} = (x_1, x_2, x_3, x_4, x_5) \in [0, 1]^5$, a discrete signature is extracted via ternary partitioning ([`fingerprint`](../../src/symbiont/core/foundation/model.py#L108-L119)):

$$\phi_{\text{bin}}(v) = \begin{cases}
\text{"L"} & \text{si } v < 0.25 \quad (\text{Bajo / Low}) \\
\text{"M"} & \text{si } 0.25 \le v < 0.60 \quad (\text{Medio / Medium}) \\
\text{"H"} & \text{si } v \ge 0.60 \quad (\text{Alto / High})
\end{cases}$$

The resulting pattern space has a finite cardinality:

$$|\Sigma_{\text{patterns}}| = 3^5 = 243 \text{ estados}$$

This coarse discretization acts as a deliberate *information bottleneck*, facilitating consensus and memory matching across multiple hosts with disparate noise profiles.

### 2.1 Multidimensional Novelty Heuristic Metric
Each agent maintains a local [`HostModel`](../../src/symbiont/core/foundation/model.py) with EWMA statistics for each of the 5 dimensions $(\mu_i, \sigma_i)$.

Model maturity saturates at 24 observations:

$$\operatorname{Maturity}(n) = \min\left( \frac{\min_i n_i}{24.0}, \; 1.0 \right)$$

If $\operatorname{Maturity} < 0.25$, novelty is identically 0.0 (judgment inhibition during initial warmup).
Otherwise:

$$z_i = \frac{|x_i - \mu_i|}{\max(\sigma_i, 0.12)}$$

$$\bar{z} = \frac{1}{5} \sum_{i=1}^5 \min(z_i, 8.0)$$

$$\operatorname{Novelty}(\mathbf{x}) = \min\left( \frac{\bar{z}}{4.0}, \; 1.0 \right) \in [0, 1]$$

The clipping at $z_{\max} = 8.0$ prevents an extreme one-dimensional perturbation from dominating the full score, requiring consistent displacement across several features to approximate the novelty to $1.0$.

---

## 3. Intrinsic Curiosity and Counterfactuals in the Shadow Space

> **Classification:** INFORMATIONAL RANKING HEURISTIC

The organism generates counterfactual questions in a shadow space (*shadow world*) without acting on the real host ([`CuriosityPlanner`](../../src/symbiont/core/cognition/curiosity.py)).

For an active hypothesis with signature $\text{fp} = (b_1, \dots, b_5)$, the planner explores adjacent neighbors in the ternary hypercube:

$$\operatorname{Adj}(b_i) = \begin{cases} \{\text{"M"}\} & \text{si } b_i \in \{\text{"L"}, \text{"H"}\} \\ \{\text{"L"}, \text{"H"}\} & \text{si } b_i = \text{"M"} \end{cases}$$

For each neighbor $\text{fp}'$, the previous collective beliefs $(P_{\text{base}}, c_{\text{base}})$ and $(P_{\text{neighbor}}, c_{\text{neighbor}})$ are queried.

### 3.1 Heuristic Expected Information Gain ($IG$)
It calculates:
1. **Counterfactual Discrimination:**
   $$d = \begin{cases} |P_{\text{base}} - P_{\text{neighbor}}| & \text{si el vecino es conocido} \\ 0.25 & \text{si el vecino es nuevo} \end{cases}$$
2. **Evidence Gap:**
   $$g = \begin{cases} 1.0 - c_{\text{neighbor}} & \text{si el vecino es conocido} \\ 1.0 & \text{si el vecino es nuevo} \end{cases}$$
3. **Base Uncertainty:**
   $$u = 1.0 - c_{\text{base}}$$

The expected information gain is formalized as:

$$IG = \min\Big( 1.0, \; u \cdot \big( 0.45 + 0.35 \cdot d + 0.20 \cdot g \big) \cdot \big( 0.65 + 0.35 \cdot \text{priority} \big) \Big)$$

### 3.2 Exploration Cost and Utility
Assuming an ordinal synthetic cost according to the position of the feature $i \in \{0, \dots, 4\}$:

$$\operatorname{Cost}(i) = 0.10 + 0.04 \cdot \frac{i}{4} \in [0.10, 0.14]$$

The utility of the probe is the regularized quotient:

$$\operatorname{Utility} = \min\left( 1.0, \; \frac{IG}{0.55 + \operatorname{Cost}} \right)$$

---

## 4. The Agent Decision Engine

> **Classification:** MULTILINEAR DECISION RULE WITH HYSTERESIS

On each tick, the agent integrates signals from multiple sources to decide whether to investigate and whether to classify the event as a threat ([`Agent.assess`](../../src/symbiont/core/cognition/agent.py#L25-L101)).

### 4.1 Apparent Risk Function
$$R_{\text{raw}} = \min\Big( 1.0, \; 0.12\,x_{\text{cpu}} + 0.18\,x_{\text{net}} + 0.28\,x_{\text{file}} + 0.16\,x_{\text{proc}} + 0.26\,x_{\text{persist}} \Big)$$

$$R = \min\big( 1.0, \; R_{\text{raw}} \cdot \text{risk\_scale} \big)$$

### 4.2 Composite Agent Uncertainty
$$U_{\text{agent}} = \min\Big( 1.0, \; 0.38(1 - \operatorname{Maturity}) + 0.42(1 - c_{\text{coll}}) + 0.20\big(1 - 2|R - 0.5|\big) \Big)$$

### 4.3 Combined Suspicion
$$w_{\text{local}} = 0.12 \cdot c_{\text{local}}$$

$$S_{\text{comb}} = \operatorname{clip}\left( \frac{0.72 \cdot R + 0.18 \cdot \operatorname{Novelty} + 0.10 \cdot P_{\text{coll}} c_{\text{coll}} + w_{\text{local}} \cdot P_{\text{local}}}{1.0 + w_{\text{local}}}, \; 0.0, \; 1.0 \right)$$

### 4.4 Decision Logic with Double Threshold and Hysteresis
Let $b$ be the agent's individual bias ($\text{investigation\_bias}$).
The agent makes two separate decisions:

1. **Attention / Active Investigation (`should_investigate`):**
   $$\text{Investigate} \iff \operatorname{Maturity} \ge 0.5 \land \Big( S_{\text{comb}} \ge 0.43 + b \;\lor\; \operatorname{Curiosity} \ge \max(0.012, \; 0.025 - 0.25 b) \Big)$$

2. **Threat Classification (`believes_threat`):**
   $$\text{Threat} \iff S_{\text{comb}} \ge 0.48 + 0.5 b$$

### 4.5 Drift Adaptation via Streak Hysteresis
To prevent a hostile anomaly from forcing the re-adaptation of the normality model, a state machine with a streak is implemented:

$$\text{DriftCandidate} \iff \Big( \operatorname{Maturity} \ge 0.5 \land \operatorname{Novelty} \ge 0.45 \land R < 0.45 \land P_{\text{coll}} < 0.65 \Big)$$

$$\text{Streak}_t = \begin{cases} \text{Streak}_{t-1} + 1 & \text{si DriftCandidate es Verdadero} \\ \max(0, \text{Streak}_{t-1} - 1) & \text{en otro caso} \end{cases}$$

- If $\text{Streak} \ge 5$: It is assumed that the sustained novelty is not an acute attack (low apparent risk and non-hostile consensus). The agent incorporates the observation into its baseline and resets $\text{Streak} \leftarrow 2$.
- If the streak does not reach 5, the host's baseline remains intact.

---

## 5. Population Metacognition

> **Classification:** GLOBAL EPISTEMIC AGGREGATION

[`MetacognitionEngine`](../../src/symbiont/core/cognition/metacognition.py) synthesizes a global indicator of the population's epistemic state:

$$\begin{aligned}
\bar{u} &= \frac{1}{N} \sum_i U_i, \qquad \bar{\nu} = \frac{1}{N} \sum_i \operatorname{Novelty}_i, \qquad \bar{c} = \frac{1}{N} \sum_i \operatorname{Curiosity}_i \\
P_{\text{disagreement}} &= \frac{1}{N} \sum_i \Big( 1.0 - 2|P_{\text{coll}, i} - 0.5| \Big) \\
P_{\text{questions}} &= \min\left( 1.0, \; \frac{|\text{OpenQuestions}|}{\max(|\text{Patterns}|, 1)} \right)
\end{aligned}$$

The total **Epistemic Pressure** is:

$$P_{\text{epistemic}} = \min\Big( 1.0, \; 0.42\,\bar{u} + 0.24\,\bar{\nu} + 0.20\,P_{\text{disagreement}} + 0.10\,P_{\text{questions}} + 0.04\,\min(8.0\,\bar{c}, 1.0) \Big)$$

The **Metacognitive Self-Confidence** is:

$$C_{\text{self}} = 1.0 - P_{\text{epistemic}} \in [0, 1]$$

### 5.1 Qualitative Regime Classification
- `uncertain`: $C_{\text{self}} < 0.40$.
- `novel`: $\bar{\nu} > 0.30$.
- `contested`: $P_{\text{disagreement}} > 0.62 \land P_{\text{questions}} > 0.08$.
- `stable`: $C_{\text{self}} > 0.72 \land P_{\text{questions}} < 0.10$.
- `watchful`: default regime in intermediate transitions.
