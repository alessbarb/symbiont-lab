---
canonical_id: "explanation.math.08-automodelo-y-sensores-adaptativos"
document_type: "explanation"
diataxis_kind: "explanation"
domain: "math"
migrated_on: 2026-09-25
language: en
last_reviewed: null
---
# Organism Self-Model, Costs and Discrete Quantization

> **Status:** IMPLEMENTED  
> **Type:** ENDOGENOUS ESTIMATION AND QUANTIZED PERSISTENCE SPECIFICATION  
> **Related modules:** [`symbiont.core.selfmodel`](../../src/symbiont/core/cognition/self_model.py)

---

## 1. Self-Model Justification and Objectives

An adaptive organism interacting with a real host cannot assume that all its sensors are permanently functional or that all readings carry the same CPU cost.

- Devices with slow drivers or interfaces with timeouts can degrade the entire cognitive cycle.
- If the organism lacks an endogenous model of its own sensors, it will continue to assign attention to dead or excessively burdensome channels.

[`SelfModel`](../../src/symbiont/core/cognition/self_model.py) formalizes a **bounded and non-semantic self-model** that continuously evaluates:

1. **Attributed Computational Cost:** Sampling latency measured in seconds.
2. **Health and Operational Quality:** Success in collecting readings.
3. **Sensor Confidence:** Function of historical maturity and health.

---

## 2. Temporal Dynamics: EWMA and Decay with Grace Zone

The self-model metrics are smoothed using an EWMA filter with constant $\alpha = 0.06$ ([`SELF_MODEL_EWMA_ALPHA`](../../src/symbiont/core/cognition/self_model.py#L10)):

$$\mu_t = \alpha \cdot x_t + (1 - \alpha) \cdot \mu_{t-1}$$

### 2.1 Idle Decay Equation

When a sensor stops being sampled for $\Delta t = t_{\text{actual}} - t_{\text{último}}$ ticks:

- In brief pauses, the learned state must persist intact.
- In prolonged absences, the state must decay towards a neutral value $x_{\text{neutral}}$ (health towards $0.5$, confidence towards $0.0$).

A **grace zone** of $\tau_{\text{grace}} = 20$ ticks is defined ([`IDLE_GRACE_TICKS`](../../src/symbiont/core/cognition/self_model.py#L13)):

$$\text{steps} = \max\Big(0, \; \Delta t - \tau_{\text{grace}}\Big)$$

$$x_{\text{decayed}}(\Delta t) = x_{\text{neutral}} + \big( x_{\text{last}} - x_{\text{neutral}} \big) \cdot (1 - \alpha)^{\text{steps}}$$

```text
Valor del Estado
   ▲
1.0│  x_last
   │  ─────────────┐ (Zona de gracia: primeros 20 ticks sin cambio)
   │               ╲
   │                ╲  Decaimiento suave: (1 - α)^steps
0.5│─────────────────●───────────────────────────  x_neutral (Salud = 0.5)
   │                  `─.
   │                     `───.
0.0└────────┬──────────────┬──────────────► Ticks Inactivos Δt
   0        20 (τ_grace)   50             100
```

---

## 3. Normalized Logarithmic Maturity Function

To determine when a sensor has sufficient sampling support ([`_maturity`](../../src/symbiont/core/cognition/self_model.py#L61-L65)):

$$\operatorname{Maturity}(s) = \begin{cases}
0.0 & \text{si } s \le 0 \\
\min\left( 1.0, \; \frac{\ln(1 + s)}{\ln(1 + N_{\min})} \right) & \text{si } s > 0 \quad (\text{con } N_{\min} = 5)
\end{cases}$$

### 3.1 Properties of the Logarithmic Profile
1. **Decreasing derivative:** The first success raises maturity to $\frac{\ln(2)}{\ln(6)} \approx 0.387$, while subsequent successes provide diminishing marginal returns until reaching $1.0$ at $s = 5$.
2. **Early Inhibition:** Modulates sensor confidence, preventing a single lucky sampling from granting full credibility.

### 3.2 The Health and Quality Axis in the Current Implementation
The composite confidence is formally calculated as:

$$\operatorname{Target}_{\text{conf}} = \operatorname{clip}\Big( 0.70 \cdot H + 0.30 \cdot Q, \; 0.0, \; 1.0 \Big) \cdot \operatorname{Maturity}(s)$$

> **Implementation Note (Effective Axis Collapse):**  
> In the current codebase (`v0.53`), both $H$ (`health_ewma`) and $Q$ (`quality_ewma`) are updated from the same health value `health_obs`, and in checkpoint deserialization `quality_ewma` is restored directly from `health_class`. Consequently, in current practice:
> $$H_t = Q_t \implies 0.70 \cdot H_t + 0.30 \cdot Q_t \equiv H_t$$
> Both variables currently represent a single effective operational axis. The mathematical separation anticipates the planned specialization:
> - *Health:* Probe availability and invocation success.
> - *Quality:* Precision and fidelity of the delivered payload.

---

## 4. Relative Cost Normalization with Respect to the Median

For the cost weighting to be agnostic to the absolute speed of the host machine ([`relative_cost`](../../src/symbiont/core/cognition/self_model.py#L129-L142)):

Given a set of already consolidated reference sensors $\mathcal{R}_{\text{est}}$:

$$C_{\text{ref}} = \operatorname{median}\Big( \big\{ \text{cost\_ewma}_j \;\big|\; j \in \mathcal{R}_{\text{est}} \big\} \Big)$$

$$r_{\text{cost}}(i) = \operatorname{clip}\left( \frac{\text{cost\_ewma}_i}{C_{\text{ref}}}, \; 0.25, \; 4.0 \right)$$

The use of the median offers a $50\%$ breakdown point against atypical blocked calls. The bounded range $[0.25, 4.0]$ limits the influence of cost on priority to a maximum factor of $16\times$.

---

## 5. Quantization and Reconstructibility Reduction in Checkpoints

To mitigate telemetry reconstruction and bound the payload to 4 bits per metric, the self-model projects the continuous states into closed classes.

### 5.1 Uniform Health and Confidence Quantization
For variables in $[0, 1]$ with $K$ classes ($K=16$ for health and confidence; $K=8$ for maturity):

$$\operatorname{Quantize}(v, K) = \operatorname{round}\Big( \operatorname{clip}(v, 0.0, 1.0) \cdot (K - 1) \Big) \in \{0, \dots, K-1\}$$

The **reconstructed representative value** upon restoration is:

$$\hat{v} = \frac{\operatorname{Quantize}(v, K)}{K - 1}$$

### 5.2 Logarithmic Cost Quantization
For the execution cost in seconds with reference $S_{\text{ref}} = 1.0 \text{ s}$ and $K_{\text{cost}} = 16$ classes ([`_quantize_cost`](../../src/symbiont/core/cognition/self_model.py#L221-L229)):

$$\rho(c) = \min\left( 1.0, \; \frac{\ln\big(1 + \max(0, c)\big)}{\ln(2)} \right) = \min\big( 1.0, \; \log_2(1 + \max(0, c)) \big)$$

$$\operatorname{Class}_{\text{cost}}(c) = \operatorname{round}\Big( 15 \cdot \rho(c) \Big) \in \{0, 1, \dots, 15\}$$

The reconstructed representative value upon deserializing the checkpoint is obtained through the exponential inverse:

$$\hat{c}(q) = \operatorname{expm1}\left( \frac{q}{15} \cdot \ln(2) \right) = 2^{q / 15} - 1$$

### 5.3 Analytical Analysis of Quantization Cells
Explicitly calculating the partition intervals and representative values:

1. **Upper Bound of Cell Zero ($q=0$):**  
   Because Python implements the round-half-to-even rule (IEEE 754), the exact midpoint $0.5$ rounds to $0$ (`round(0.5) == 0`). Therefore, the assignment condition to class 0 includes the boundary:
   $$15 \cdot \log_2(1 + c) \le 0.5 \iff \log_2(1 + c) \le \frac{1}{30} \iff c \le 2^{1/30} - 1$$
   $$c_{\text{boundary}, 0} = 2^{1/30} - 1 \approx \mathbf{23.374 \text{ ms}}$$
   The exact mathematical boundary is $2^{1/30} - 1$ ($\approx 23.374\text{ ms}$ as a decimal approximation). Any continuous latency in the closed interval $[0.0, \; 2^{1/30} - 1]$ is assigned to class $q = 0$, whose reconstructed representative value is $\hat{c}(0) = 0.0 \text{ ms}$.

2. **First Positive Reconstruction ($q=1$):**  
   For class $q=1$, the reconstructed representative value is:
   $$\hat{c}(1) = 2^{1/15} - 1 \approx \mathbf{47.294 \text{ ms}}$$
   This class covers the interval $(2^{1/30} - 1, \; 2^{1.5/15} - 1) \approx (23.374 \text{ ms}, \; 71.773 \text{ ms})$.

> **Practical Engineering Implications:**  
> - **Micro-Latency Collapse:** Typical execution latencies in memory polling or `/proc` reading (50 µs, 1 ms, 10 ms, 20 ms) all fall within $[0.0, \; 2^{1/30} - 1]$, identically collapsing into class 0 and being reconstructed as 0.0 ms when restoring a checkpoint.
> - **Effective Discrimination Range:** The logarithmic function begins to resolve differences starting from the boundary $2^{1/30} - 1 \approx 23.374$ ms, allowing heavy I/O or periodic disk inspection operations to be discriminated from lightweight checks.
> - **Irreversibility and Scale Loss at Low Costs:** The quantization function $c \mapsto q$ (and thus the composition $c \mapsto \hat{c}$) is a non-injective transformation that compresses infinitely many values into 16 discrete classes, even though the reconstruction function $\hat{c}: \{0, \dots, 15\} \to \mathbb{R}^+$ is strictly injective over the classes. Above $2^{1/30} - 1 \approx 23.374$ ms an approximate geometric progression is retained between successive classes; however, for any latency $c \le 2^{1/30} - 1$, the scale collapses to zero, eliminating any internal differentiation between lightweight operations.
