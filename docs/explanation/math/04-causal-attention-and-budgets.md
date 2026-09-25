---
canonical_id: "explanation.math.04-atencion-causal-y-presupuestos"
document_type: "explanation"
diataxis_kind: "explanation"
domain: "math"
migrated_on: 2026-09-25
language: en
last_reviewed: null
---
# Causal Attention Allocation and Finite Budget Optimization

> **Status:** IMPLEMENTED  
> **Type:** HEURISTIC POLICY AND RESOURCE ALLOCATION  
> **Related modules:** [`symbiont.core.attention`](../../src/symbiont/core/cognition/attention.py)

---

## 1. The Bounded Attention Problem

In any biological or computational system that interacts with a high-dimensional environment, perceptual bandwidth is a strictly limited resource. An organism cannot sample all observation surfaces at every tick with high resolution.

The Symbiont attention subsystem ([`symbiont.core.attention`](../../src/symbiont/core/cognition/attention.py)) formalizes capability selection under four guiding principles:

1. **Strict Causality:** Attention selection at tick $t$ is performed using exclusively the information known before making any new observation at $t$. There is no lookahead, threat labels, or future rewards.
2. **Hard and Inviolable Budget:** There is a scalar budget $B > 0$ per tick. The sum of the costs of the selected observations cannot exceed $B$.
3. **Non-Classification (ADR-0003):** Attention is an informational optimization mechanism, not a threat judgment. A capability that receives attention is not declared "anomalous"; it is simply a capability over which there is greater relative dispersion or lack of acclimation.
4. **Determinism and Bounded Complexity:** The selection algorithm operates in time $O(n \log n)$ and memory $O(n)$, with deterministic tie-breaking by lexicographical order.

---

## 2. Mathematical Formulation: From 0/1 Knapsack to Decoupled Greedy Heuristic

Let there be a set of $N$ candidate capabilities $\mathcal{C} = \{c_1, c_2, \dots, c_N\}$.
For each candidate $c_i$, the following are defined:

- $u_i \in [0, +\infty]$: The baseline dispersion or uncertainty.
- $k_i \in (0, +\infty)$: The intrinsic physical cost of budget consumption.
- $r_i \in (0, +\infty)$: The ranking cost or bias assigned by the self-model.

The idealized combinatorial optimization problem corresponds to the 0/1 knapsack problem:

$$\max_{\mathbf{z} \in \{0, 1\}^N} \sum_{i=1}^N z_i u_i \quad \text{subject to} \quad \sum_{i=1}^N z_i k_i \le B$$

### 2.1 Greedy Heuristic vs. Exact 0/1 Knapsack

The 0/1 knapsack problem is NP-hard. Standard dynamic programming algorithms require pseudo-polynomial time and memory dependent on the discretization of the budget $B$. If the budget is continuous or changes between ticks, dynamic programming introduces variable latencies (*computational jitter*), which are inadmissible for the resident cycle.

Therefore, Symbiont adopts a **single-pass greedy heuristic policy** in $O(N \log N)$ time.

> **Theoretical Nuance on Dantzig (1957):**  
> Sorting by value density is optimal for the **continuous relaxation (fractional knapsack)**. For the implemented integer 0/1 knapsack, the simple greedy heuristic possesses no general optimality guarantees and can, in ad-hoc constructed extreme cases, deviate significantly from the optimum if branching phases are not added. Symbiont consciously assumes this compromise to guarantee determinism, strict single-pass execution, and temporal predictability.

---

## 3. Quantification of Relative Dispersion: Coefficient of Variation

The statistical dispersion $u(c_i)$ is calculated in [`uncertainty_from_baseline`](../../src/symbiont/core/cognition/attention.py#L86-L104) from $(\mu_i, \sigma_i, n_i)$:

$$u(c_i) = \begin{cases}
+\infty & \text{if the capability is not acclimated } (n_i < N_{\text{min}}) \\
\sigma_i & \text{if } n_i \ge N_{\text{min}} \land \mu_i = 0.0 \\
\frac{\sigma_i}{|\mu_i|} & \text{if } n_i \ge N_{\text{min}} \land \mu_i \neq 0.0
\end{cases}$$

### 3.1 Properties and Limitations of the Coefficient of Variation ($c_v$)
1. **Epistemic Priority of the Unknown:**
   A signal without sufficient samples receives $u = +\infty$, surpassing any already established signal and guaranteeing the initial exploration of new capabilities.
2. **Scale Invariance:**
   For positive signals with ratio scale, if $Y = \alpha X$ with $\alpha > 0$, then $c_v(Y) = c_v(X)$, which allows comparing disparate magnitudes without manual rescaling.

> **Warning on Entropy and Scale:**  
> The coefficient of variation $c_v = \frac{\sigma}{|\mu|}$ is a measure of **relative dispersion**, not of entropy. Gaussian differential entropy depends solely on the variance: $h(X) = \frac{1}{2}\ln(2\pi e \sigma^2)$, not on $\mu$.  
> It also presents two theoretical limitations:
> - If $\mu \approx 0$, $c_v$ diverges independently of how small and concentrated the variance $\sigma^2$ is.
> - When $\mu = 0$, the code switches to the standard deviation $\sigma_i$, which ceases to be dimensionless.  
> Its use in Symbiont is justified as an engineering heuristic rule to prioritize noisy signals relative to their operating mean.

---

## 4. Formal Decoupling Between Consumption Cost and Ranking Cost

> **Classification:** PROPOSITION / SAFETY INVARIANT

A common weakness in systems with learned budgets is that an internal component learns that an action "costs zero" to deceive the scheduler and consume excessive resources.

Symbiont resolves this by decoupling the physical consumption from the sorting criterion:

```text
Candidate c_i:
  ├── Uncertainty: u_i
  ├── Ranking Cost: r_i   ──► Modulates PRIORITY (greedy order)
  └── Physical Cost:  k_i   ──► Discounts the HARD BUDGET B
```

### 4.1 Deterministic Sorting Function
The candidates are sorted lexicographically by the tuple:

$$\operatorname{Key}(c_i) = \left( -\frac{u_i}{k_i \cdot r_i}, \;\; \operatorname{name}(c_i) \right)$$

The priority ratio is:

$$\rho_i = \frac{u_i}{k_i \cdot r_i}$$

The `name` term resolves any tie strictly deterministically, eliminating dependence on the internal order of hash tables.

### 4.2 Hard Budget Invariance
**Proposition (Budget Inviolability):**  
No learned bias in $r_i$ can cause the sum of the costs of the selected capabilities to exceed the configured budget $B$.

*Proof:*  
Let $\mathcal{A} \subseteq \mathcal{C}$ be the subset of candidates chosen by the greedy loop:
```python
selected = []
remaining = B
for candidate in ranked:
    if candidate.cost <= remaining:
        selected.append(candidate)
        remaining -= candidate.cost
```
Each element $c \in \mathcal{A}$ is incorporated if and only if $k_c \le \text{remaining}$. The update strictly decrements $\text{remaining} \leftarrow \text{remaining} - k_c$, where $k_c$ is the governed and immutable physical cost. By induction over the added elements:

$$\sum_{c \in \mathcal{A}} k_c \le B \quad \blacksquare$$

The learned parameter $r_i$ exclusively alters which capabilities compete first for the budget, but never alters the physical amount of quota they consume.
