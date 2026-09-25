---
id: explanation.math.09-plasticidad-endogena-y-redes-recurrentes
title: Endogenous Plasticity, Recurrent Cognitive Graphs and Activation Dynamics
document_type: explanation
domain: math
status: unclassified
canonical: false
implementation_status: unknown
supersedes: []
extends: []
implements: []
depends_on: []
related_adrs: []
migrated_on: 2026-09-25
last_reviewed: null
review_required: true
language: en
---
# Endogenous Plasticity, Recurrent Cognitive Graphs and Activation Dynamics

> **Status:** PARTIALLY IMPLEMENTED (v0.55/v0.56) / SPECIFIED (v0.57/v0.58)  
> **Type:** RECURRENT NETWORK ARCHITECTURE AND LEARNING SPECIFICATION  
> **Related modules:** [`symbiont.cognition.activation`](../../src/symbiont/cognition/activation.py), [`symbiont.cognition.graph`](../../src/symbiont/cognition/graph.py), [`symbiont.cognition.genome`](../../src/symbiont/cognition/genome.py)

---

## 1. The Data Plasticity Paradigm under Immutable Kernel

Symbiont's plastic cognition subsystem implements a sparse, interpretable recurrent network without requiring metaprogramming or modification of the resident Python source code.

The model is organized into four abstraction layers:

```text
  ┌──────────────────────────────────────────────────────────┐
  │                 IMMUTABLE KERNEL [IMPLEMENTED]           │
  │  Hard limits: N_max=128, C_max=32, E_max=1024, etc.      │
  │  Closed catalog of node and edge types                   │
  │  Safe mode and non-learnable execution quotas            │
  └────────────────────────────┬─────────────────────────────┘
                               │ Defines ranges and limits
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 DECLARATIVE GENOME [IMPLEMENTED]         │
  │  Heritable JSON configuration validated against schema   │
  │  Soft budgets, base rates, latency windows               │
  └────────────────────────────┬─────────────────────────────┘
                               │ Configures birth
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 PLASTIC PHENOTYPE [IN PROGRESS]          │
  │  Active recurrent graph: nodes, edges, weights w_ij      │
  │  Eligibility traces, latent concepts                     │
  └────────────────────────────┬─────────────────────────────┘
                               │ Processes each tick
                               ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 DYNAMIC STATE (EPHEMERAL) [IMPLEMENTED]  │
  │  Activations a(t), net inputs u(t), readouts             │
  └──────────────────────────────────────────────────────────┘
```

---

## 2. Non-Linear Sensory Normalization [IMPLEMENTED]

> **Classification:** CODE IDENTITY

Before entering the CognitiveGraph, system readings pass through the normalizer [`SensoryNormalizer`](../../src/symbiont/cognition/activation.py).

For a continuous reading $x_t \in \mathbb{R}$, the deviation from the local moving average $\mu_{t-1}$ and its variance $\sigma_{t-1}^2$ is evaluated:

$$\sigma_t = \sqrt{\max\big(\sigma_{t-1}^2, \; 10^{-6}\big)}$$

$$z_t = \frac{x_t - \mu_{t-1}}{\sigma_t}$$

A symmetric clipping in $[-z_{\max}, z_{\max}]$ is applied (default $z_{\max} = 4.0$):

$$z_{\text{clip}} = \operatorname{clip}(z_t, -z_{\max}, z_{\max})$$

Sensory activation $a_i(t) \in (-1, 1)$ is obtained via hyperbolic tangential compression with smoothness factor $s = 2.0$:

$$a_i(t) = \tanh\left( \frac{z_{\text{clip}}}{s} \right)$$

---

## 3. Recurrent Graph Activation Dynamics [IMPLEMENTED]

> **Classification:** CODE IDENTITY / PROPAGATION DETERMINISM

The [`CognitiveGraph`](../../src/symbiont/cognition/graph.py) operates on a closed catalog of types:

- **Nodes:** `SENSE`, `CONCEPT`, `STATE`, `PREDICTOR`, `GATE`, `READOUT`.
- **Edges:** `EXCITATORY`, `INHIBITORY`, `PREDICTIVE`, `GATING`.

### 3.1 Strict Causality and Instantaneous Cycle Elimination

Let $d_{ij} \in \{0, 1\}$ be the discrete delay of the edge connecting source node $i$ to destination node $j$.

In [`CognitiveGraph`](../../src/symbiont/cognition/graph.py#L115-L124), the kernel imposes two fundamental topological constraints:

1. **Origin Constraint for Zero Delay:**
   $$d_{ij} = 0 \implies \operatorname{Kind}(i) = \text{SENSE}$$
   Zero delay is permitted only if the source is a SENSE node. For any internal node, it is strictly required that $d_{ij} = 1$:
   $$\operatorname{Kind}(i) \neq \text{SENSE} \implies d_{ij} = 1$$

2. **Prohibition of Incoming Edges to Sensors:**
   For any node $j$ such that $\operatorname{Kind}(j) = \text{SENSE}$, the kernel explicitly prohibits incoming edges ([`graph.py` L122-L123](../../src/symbiont/cognition/graph.py#L122-L123)):
   $$\operatorname{deg}^-(j) = 0 \quad \forall j \text{ with } \operatorname{Kind}(j) = \text{SENSE}$$
   Sensor activations are strictly exogenously set from environment readings at each tick and do not depend on any network edge.

**Proof of Instantaneous Acyclicity:**  
Since every zero-delay edge ($d = 0$) originates from a SENSE node ($\operatorname{Kind}(i) = \text{SENSE}$) and ends at a non-sensory node ($\operatorname{Kind}(j) \neq \text{SENSE}$), the subgraph induced by zero-delay edges $\mathcal{G}_0 = (\mathcal{V}, \mathcal{E}_0)$ is strictly a **directed bipartite graph** from $\text{SENSE}$ to $\mathcal{V} \setminus \text{SENSE}$.  
As no SENSE node allows incoming edges, no directed zero-delay path of length $\ge 2$ can exist (which excludes both connections between sensors and cycles among internal nodes). Thus, **the graph lacks instantaneous algebraic dependencies or zero-delay cycles**.

*Algorithmic Consequence:*  
Since SENSE nodes can emit both direct edges ($d=0$) and unit-delay edges ($d=1$), the activation of internal nodes at time $t$ depends on current tick sensory inputs and the complete activation vector of the previous step $t-1$:

$$\mathbf{a}_{\text{internal}}(t) = \mathbf{f}\Big( \mathbf{a}_{\text{sense}}(t), \; \mathbf{a}(t-1) \Big)$$

where $\mathbf{a}(t-1) = \big(\mathbf{a}_{\text{sense}}(t-1), \; \mathbf{a}_{\text{internal}}(t-1)\big)$.

This eliminates instantaneous circular dependencies and makes activation invariant to the node traversal order in memory.

### 3.2 Multiplicative Gates (*Gating Factor*)

For a node $j$, let $\mathcal{E}_{\text{gate}}(j)$ be the set of incoming `GATING` type edges.
The gating factor $G_j(t) \in [0, 1]$ multiplicatively modulates the input:

$$G_j(t) = \begin{cases}
1.0 & \text{if } \mathcal{E}_{\text{gate}}(j) = \emptyset \\
\prod_{e \in \mathcal{E}_{\text{gate}}(j)} \operatorname{clip}\Big( w_e \cdot a_{\text{source}(e)}(t - d_e), \; 0.0, \; 1.0 \Big) & \text{otherwise}
\end{cases}$$

### 3.3 Net Input and Activation
Let $\mathcal{E}_{\text{signal}}(j)$ be the set of non-gating incoming edges.
The net input $u_j(t)$ integrates the self bias $b_j \in \mathbb{R}$ (validated as finite upon initialization) and the modulated weighted sum:

$$u_j(t) = b_j + G_j(t) \cdot \sum_{e \in \mathcal{E}_{\text{signal}}(j)} w_e \cdot a_{\text{source}(e)}(t - d_e)$$

The final activation utilizes the **activation scale parameter** $\tau_j \in [0.1, 10.0]$:

$$a_j(t) = \tanh\left( \frac{u_j(t)}{\tau_j} \right)$$

> **Terminological Precision:**  
> $\tau_j$ operates here as a scale parameter or smoothing/temperature factor that modulates the saturation slope at the origin ($\left.\frac{da_j}{du_j}\right|_{0} = \frac{1}{\tau_j}$). It must not be confused with a "time scale constant", as the static formulation $a = \tanh(u / \tau)$ does not include continuous derivatives nor its own autoregressive terms.

---

## 4. Boundedness Analysis: Mathematical Model, Numerical Implementation and Dynamics [IMPLEMENTED]

> **Classification:** PROPOSITION / ALGORITHM IDENTITY

To evaluate recurrent graph stability, it is imperative to rigorously separate three dimensions: the continuous analytical model, floating-point arithmetic, and recurrent dynamics.

### 4.1 Mathematical Model (Real Numbers)
Under algebra over $\mathbb{R}$:
1. For each SENSE node: $a_i(t) = \tanh(z_{\text{clip}} / s)$. Since $z_{\text{clip}}$ is finite and $s = 2.0 > 0$, the analytical property of the hyperbolic tangent establishes:
   $$\tanh(x) \in (-1, 1) \quad \forall x \in \mathbb{R}$$
2. For each internal node $j$, weights satisfy $w \in [-2.0, 2.0]$ and the incoming degree meets $\deg^-(j) \le E_{\max} = 1024$. Assuming finite $b_j \in \mathbb{R}$:
   $$|u_j(t)| \le |b_j| + 1.0 \cdot \deg^-(j) \cdot 2.0 < +\infty$$
3. Since $\tau_j \ge 0.1 > 0$, the argument $u_j(t) / \tau_j$ is strictly finite. Consequently, over real numbers:
   $$a_j(t) \in (-1, 1) \implies |a_j(t)| < 1.0 \quad \forall t \ge 0$$

### 4.2 Numerical Implementation (IEEE 754 Floating Point)
In practical 64-bit floating point computing (Python `float` / IEEE 754 double precision):
- For arguments with magnitude $|x| \gtrsim 20$, `math.tanh(x)` numerically saturates at $\pm 1.0$ (for example, `math.tanh(100) == 1.0`). The observable bound in memory is therefore **the closed interval $[-1.0, 1.0]$**, that is, $|a| \le 1.0$.
- **On the Absence of Overflows in Intermediate Operations:**  
  The validations described (verifying that initial biases are finite with `math.isfinite` and that $\tau_j \ge 0.1$) **do not guarantee by themselves finite intermediate operations**. That guarantee requires sufficient magnitude bounds or explicit handling of overflows.  
  *Demonstrative counterexample:* A node without incoming edges with bias $b_j = 10^{308}$ satisfies `math.isfinite(1e308) == True` and $\tau_j = 0.1 \ge 0.1$, but the intermediate division $10^{308} / 0.1$ overflows to `inf`. Even though in Python `math.tanh(float("inf"))` returns `1.0`, the intermediate operation produced a floating point overflow without raising an exception. Therefore, the absence of intermediate overflows in the implementation is conditioned to the practical orders of magnitude of inputs and biases or to the detection and handling of non-finite results.

### 4.3 Nuance on Dynamic Stability
Bounding activations in $[-1, 1]^N$ demonstrates **confinement of the trajectory in a compact set**, but:
> **It does not demonstrate Lyapunov stability nor convergence.**  
> A non-linear system in discrete time $\mathbf{a}(t) = \tanh\left(\frac{1}{\tau} \mathbf{W} \mathbf{a}(t-1)\right)$ with activations confined in $[-1, 1]^N$ can present periodic attractors (limit cycles), period bifurcations, or chaotic behavior dependent on initial conditions if the eigenvalues of the weight matrix $\mathbf{W}$ have a modulus significantly greater than the scale $\tau$.

---

## 5. Local Learning Rules and Plasticity [SPECIFIED]

> **Classification:** LEARNING SPECIFICATION (ROADMAP v0.57)

### 5.1 Stabilized Oja's Rule
For associative edges between plastic nodes, the specification incorporates Oja's normalizing rule (1982):

$$\Delta w_{ij}(t) = \eta_{ij} \cdot m(t) \cdot \Big[ a_i(t - d_{ij}) \cdot a_j(t) - a_j(t)^2 \cdot w_{ij}(t) \Big]$$

where:
- $\eta_{ij}$ is the learning rate modulated by edge plasticity.
- $m(t) \in [0, 1]$ is the local modulator (attention, perceptual health, and stability).

> **Rigor Nuance on Oja's Rule:**  
> The discrete Oja's rule introduces a **quadratic decay pressure** that, under stationary continuous conditions and infinitesimal iterations, limits growth and orients weights towards principal eigenvectors.  
> However, in a recurrent network with finite discrete steps, multiplicative gates, and clipping, it does not mathematically guarantee that $\|\mathbf{w}\|_2 \le 1$ at every tick. The hard bound of weights in Symbiont comes from the kernel guard:
> $$w_{ij} \in [-2.0, 2.0]$$

### 5.2 Temporal Eligibility Traces [SPECIFIED]
To associate previous activations with deferred consequences:

$$q_{ij}(t) = \lambda_{\text{elig}} \cdot q_{ij}(t-1) + a_i(t - d_{ij}) \cdot a_j(t)$$

with $\lambda_{\text{elig}} \in [0.80, 0.98]$ governed by the declarative genome ([`symbiont.cognition.genome`](../../src/symbiont/cognition/genome.py)).
