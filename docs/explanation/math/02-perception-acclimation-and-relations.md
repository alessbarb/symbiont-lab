---
canonical_id: "explanation.math.02-percepcion-aclimatacion-y-relaciones"
document_type: "explanation"
diataxis_kind: "explanation"
domain: "math"
migrated_on: 2026-09-25
language: en
last_reviewed: null
---
# Perception, Sensory Acclimation and Algebra of Relations

> **Status:** IMPLEMENTED  
> **Type:** CODE IDENTITY AND SELECTION HEURISTIC  
> **Related modules:** [`symbiont.host.acclimation`](../../src/symbiont/host/acclimation.py), [`symbiont.host.adaptive`](../../src/symbiont/host/adaptive.py)

---

## 1. Motivation and Design Principles

In Symbiont, the perceptual apparatus does not assume a closed or preconfigured catalog of sensors, nor does it know a priori the scale, mean or variance of the host's signals. To interact with a real or synthetic system without violating privacy and without storing raw telemetry (which would violate memory quotas and security guidelines), online operators are designed capable of:

1. Learning order 1 (mean) and order 2 (variance) descriptive statistics with spatial complexity $O(1)$.
2. Measuring synchronous linear correlation and lagged statistical association between pairs of unknown signals.
3. Assigning a dynamic utility value to each signal based on its heuristic information content (variability and motion) weighted by its availability.
4. Pruning collinear redundancies without resorting to costly matrix inversions ($O(N^3)$).

---

## 2. The Univariate Welford's Algorithm

> **Classification:** PROPOSITION / EXACT ALGEBRAIC IDENTITY

To estimate the sample mean $\bar{x}_n$ and the unbiased sample variance $s_n^2$ of an infinite sequence of observations $x_1, x_2, \dots, x_n \in \mathbb{R}$, the naive two-pass formulation:

$$\bar{x}_n = \frac{1}{n} \sum_{i=1}^n x_i, \quad s_n^2 = \frac{1}{n-1} \left( \sum_{i=1}^n x_i^2 - n \bar{x}_n^2 \right)$$

suffers from **catastrophic cancellation** in single or double precision floating-point arithmetic (IEEE 754). When the variance is small compared to the square of the mean ($\sigma^2 \ll \mu^2$), the terms $\sum x_i^2$ and $n \bar{x}_n^2$ have almost identical magnitudes in the most significant bits, causing a total loss of precision and sometimes yielding spurious negative values ($\sigma^2 < 0$), which produces runtime crashes (`math domain error` when calculating $\sqrt{\sigma^2}$).

### 2.1 Recurrence Equations

Symbiont implements Welford's (1962) online algorithm in [`RunningStats`](../../src/symbiont/host/acclimation.py) and [`SenseState`](../../src/symbiont/host/adaptive.py):

Let $M_{2, n} = \sum_{i=1}^n (x_i - \bar{x}_n)^2$ be the sum of squared deviations from the accumulated mean up to step $n$.

Upon receiving the observation $x_n$:

$$\begin{aligned}
n &\leftarrow n + 1 \\
\delta_n &= x_n - \mu_{n-1} \\
\mu_n &= \mu_{n-1} + \frac{\delta_n}{n} \\
M_{2, n} &= M_{2, n-1} + \delta_n \cdot (x_n - \mu_n)
\end{aligned}$$

### 2.2 Proof of Algebraic Consistency
**Lemma:** $x_n - \mu_n = \delta_n \left( 1 - \frac{1}{n} \right) = \delta_n \frac{n-1}{n}$.

*Proof:*
$$x_n - \mu_n = x_n - \left( \mu_{n-1} + \frac{x_n - \mu_{n-1}}{n} \right) = (x_n - \mu_{n-1}) - \frac{x_n - \mu_{n-1}}{n} = \delta_n \left( 1 - \frac{1}{n} \right)$$

We expand the definition of $M_{2, n}$:
$$M_{2, n} = \sum_{i=1}^n (x_i - \mu_n)^2 = \sum_{i=1}^{n-1} (x_i - \mu_n)^2 + (x_n - \mu_n)^2$$

Given that $x_i - \mu_n = (x_i - \mu_{n-1}) + (\mu_{n-1} - \mu_n) = (x_i - \mu_{n-1}) - \frac{\delta_n}{n}$:

$$\begin{aligned}
\sum_{i=1}^{n-1} (x_i - \mu_n)^2 &= \sum_{i=1}^{n-1} \left( (x_i - \mu_{n-1}) - \frac{\delta_n}{n} \right)^2 \\
&= \sum_{i=1}^{n-1} (x_i - \mu_{n-1})^2 - \frac{2\delta_n}{n} \underbrace{\sum_{i=1}^{n-1} (x_i - \mu_{n-1})}_{= 0} + (n-1) \frac{\delta_n^2}{n^2} \\
&= M_{2, n-1} + \frac{n-1}{n^2} \delta_n^2
\end{aligned}$$

Adding the term of step $n$:
$$(x_n - \mu_n)^2 = \left( \frac{n-1}{n} \delta_n \right)^2 = \frac{(n-1)^2}{n^2} \delta_n^2$$

Therefore:
$$M_{2, n} = M_{2, n-1} + \frac{n-1}{n^2} \delta_n^2 + \frac{(n-1)^2}{n^2} \delta_n^2 = M_{2, n-1} + \frac{n(n-1)}{n^2} \delta_n^2 = M_{2, n-1} + \frac{n-1}{n} \delta_n^2$$

Since $\delta_n (x_n - \mu_n) = \delta_n \left( \frac{n-1}{n} \delta_n \right) = \frac{n-1}{n} \delta_n^2$, the recurrence is exactly proven:
$$M_{2, n} = M_{2, n-1} + \delta_n (x_n - \mu_n) \quad \blacksquare$$

### 2.3 Calculation of Variance and Standard Deviation
The sample variance is calculated as:

$$\sigma_n^2 = \begin{cases}
\frac{M_{2, n}}{n} & \text{in } \texttt{RunningStats} \text{ (maximum likelihood estimator)} \\
\frac{M_{2, n}}{n-1} & \text{in } \texttt{SenseState} \text{ (Bessel's unbiased estimator, } n > 1)
\end{cases}$$

$$\sigma_n = \sqrt{\max(0.0, \sigma_n^2)}$$

### 2.4 Exact Reconstruction Property without Raw Retention
A non-negotiable security requirement is that the checkpoint must not contain past raw samples. When serializing [`CapabilityBaseline`](../../src/symbiont/host/acclimation.py), only $(n, \mu, \sigma^2)$ are saved. When restoring, the accumulator $M_2$ is exactly regenerated by:

$$M_2 = \sigma^2 \cdot n$$

which allows resuming Welford updates without discontinuities or numerical distortion.

---

## 3. Bivariate Welford's Algorithm for Online Correlation

> **Classification:** PROPOSITION / NUMERICAL IDENTITY

To discover relations between system capabilities (for example, between CPU usage and temperature or network traffic), the system uses [`PairAccumulator`](../../src/symbiont/host/adaptive.py).

Accumulating raw sums $\sum x_i, \sum y_i, \sum x_i y_i$ fails when the signals are monotonically increasing Linux kernel counters (with magnitudes like $10^{14}$ transferred bytes), because $\sum x_i y_i$ overflows the floating-point mantissa.

### 3.1 Centered Co-moment
Symbiont maintains the centered co-moment $C_{xy, n} = \sum_{i=1}^n (x_i - \bar{x}_n)(y_i - \bar{y}_n)$.

Upon receiving the ordered pair $(x_n, y_n)$:

$$\begin{aligned}
n &\leftarrow n + 1 \\
dx_n &= x_n - \mu_{x, n-1} \\
\mu_{x, n} &= \mu_{x, n-1} + \frac{dx_n}{n} \\
dy_n &= y_n - \mu_{y, n-1} \\
\mu_{y, n} &= \mu_{y, n-1} + \frac{dy_n}{n} \\
C_{xy, n} &= C_{xy, n-1} + dx_n \cdot (y_n - \mu_{y, n}) \\
M_{2, x, n} &= M_{2, x, n-1} + dx_n \cdot (x_n - \mu_{x, n}) \\
M_{2, y, n} &= M_{2, y, n-1} + dy_n \cdot (y_n - \mu_{y, n})
\end{aligned}$$

### 3.2 Pearson Correlation Coefficient
The linear correlation coefficient $r \in [-1, 1]$ is obtained in $O(1)$:

$$r(X, Y) = \begin{cases}
\text{None (undefined)} & \text{if } n < 3 \lor M_{2, x} \le 10^{-18} \lor M_{2, y} \le 10^{-18} \\
\operatorname{clip}\left( \frac{C_{xy}}{\sqrt{M_{2, x} \cdot M_{2, y}}}, -1.0, 1.0 \right) & \text{otherwise}
\end{cases}$$

---

## 4. Temporal Dynamics: Synchronous vs. Lagged Association

> **Classification:** DESCRIPTIVE HEURISTIC (TEMPORAL ASSOCIATION, NOT CAUSALITY)

To measure temporal dependency without imposing external semantic models, each relation [`SensoryRelation`](../../src/symbiont/host/adaptive.py) maintains three independent bivariate accumulators:

```text
Tick t-1:       x(t-1)                     y(t-1)
                   │  ╲                   ╱  │
                   │   ╲    Lagged       ╱   │
                   │    ╲ association   ╱    │
                   │     ▼             ▼     │
Tick t:         x(t) ◄── Synchronous ──► y(t)
```

1. **Synchronous Association ($r_{\text{sync}}$):**
   Measures simultaneous co-variation in the same tick:
   $$r_{\text{sync}} = r\big(x(t), y(t)\big)$$

2. **Lagged Temporal Association from $A$ to $B$ ($r_{a_{t-1}, b_t}$):**
   Measures the correlation between signal $A$ in the previous step and signal $B$ in the current step:
   $$r_{a_{t-1}, b_t} = r\big(x(t-1), y(t)\big)$$

3. **Lagged Temporal Association from $B$ to $A$ ($r_{b_{t-1}, a_t}$):**
   $$r_{b_{t-1}, a_t} = r\big(y(t-1), x(t)\big)$$

> **Fundamental Methodological Warning:**  
> A lagged correlation $r(x_{t-1}, y_t) \neq 0$ **does not prove causality in a strict sense**. This statistical association can originate from common unobserved causes, internal autocorrelation of the series, shared rhythms (like day/night cycles), synchronized sampling of monotonic accumulators or feedback dynamics with different latencies. In Symbiont, these metrics are strictly descriptive and are never internally interpreted as proofs of cause and effect.

**Strength of the Relation:**  
To prioritize which pairs deserve to be kept in the bounded table of relations, it is defined:

$$\text{Strength}(A, B) = \max\Big( |r_{\text{sync}}|, |r_{a_{t-1}, b_t}|, |r_{b_{t-1}, a_t}| \Big)$$

---

## 5. Sensory Dynamic Utility Function

> **Classification:** INFORMATIONAL RANKING HEURISTIC

The organism must autonomously solve a sensory allocation problem: among hundreds of available operating system observation surfaces, which deserve routine sampling?

In [`SenseState.utility`](../../src/symbiont/host/adaptive.py), the utility $U \in [0, 1]$ is calculated using three purely statistical variables:

### 5.1 Utility Components

1. **Availability ($A$):**
   Fraction of attempts in which the sensor produced a valid and non-null numerical value:
   $$A = \frac{N_{\text{available}}}{N_{\text{samples}}} \in [0, 1]$$

2. **Invariant Scale ($S$):**
   Scaling factor that combines absolute magnitude and dispersion:
   $$S = |\mu| + \sigma + \epsilon, \quad \text{where } \epsilon = 10^{-12}$$

3. **Normalized Relative Variability ($V$):**
   A constant signal (zero variance) does not carry dynamic information about the host:
   $$V = \min\left( 1.0, \frac{\sigma}{S} \right) \in [0, 1]$$

4. **Kinematics of Change / Motion ($M$):**
   The exponential moving average (EWMA) of successive absolute increments between contiguous ticks with a reading is tracked:
   $$\Delta_{\text{raw}}(t) = |x(t) - x(t_{\text{prev}})|$$
   $$\Delta_{\text{ewma}}(t) = 0.20 \cdot \Delta_{\text{raw}}(t) + 0.80 \cdot \Delta_{\text{ewma}}(t-1)$$
   $$M = \min\left( 1.0, \frac{\Delta_{\text{ewma}}}{S} \right) \in [0, 1]$$

### 5.2 Closed Formulation of Utility
If $N_{\text{available}} < 2$, $U = 0.0$. Otherwise:

$$U(s) = A \cdot \Big( 0.65 \cdot V + 0.35 \cdot M \Big)$$

This heuristic weighting assigns $65\%$ to the amplitude of the sample range and $35\%$ to the temporal rate of change, scaled by the data acquisition success rate.

---

## 6. Selection and Collinear Redundancy Pruning

> **Classification:** SPATIAL PRUNING HEURISTIC

Given a set of candidate senses sorted by decreasing utility $U_1 \ge U_2 \ge \dots \ge U_k$:

A candidate sense $s_j$ is declared **redundant** with respect to the already selected set $\mathcal{S}_{\text{sel}}$ if there exists any $s_i \in \mathcal{S}_{\text{sel}}$ with sufficient historical support ($N_{\text{samples}} \ge 6$) such that:

$$|r_{\text{sync}}(s_i, s_j)| \ge \theta_{\text{redundancy}} \quad (\text{by default } \theta_{\text{redundancy}} = 0.97)$$

If declared redundant, $s_j$ is excluded from the main quota (active limit $K_{\text{active}} = 24$) and relegated to the reserve list, encouraging the sensory space to explore linearly independent dimensions of variation.

---

## 7. Sampling Scheduling: Deterministic Rotation and Eventual Coverage

> **Classification:** PROPOSITION (UNDER STABLE CANDIDATES) / EXPLORATION HEURISTIC

To avoid *irreversible early blindness* (where a bad initial estimate permanently discards a signal that later becomes informative), the organism classifies the senses into three strata:

1. **Active:** Routinely sampled every tick.
2. **Unknown / Latent:** Not yet observed or with $n < N_{\text{min}}$.
3. **Dormant:** Known but not selected by the utility/redundancy filter.

Let $\mathcal{P} = \text{Unknown} \cup \text{Dormant}$ be the exploration group, with size $P = |\mathcal{P}|$.
Let $B_{\text{probe}}$ be the probe budget ($B_{\text{probe}} = 4$ in regular regime, $B_{\text{probe}} = 32$ at startup).

To avoid biases from the internal memory order, candidates are sorted lexicographically by their hash key:

$$\text{order\_key}(c_k) = \operatorname{SHA-256}(\text{"symbiont-sampling:"} \parallel c_k)$$

The circular cursor $c \in \mathbb{N}_0$ selects the indices:

$$\text{Indices} = \left\{ (c + i) \pmod P \;\middle|\; i = 0, 1, \dots, \min(B_{\text{probe}}, P) - 1 \right\}$$

$$c \leftarrow (c + \min(B_{\text{probe}}, P)) \pmod P$$

**Proposition of Eventual Coverage:**  
For a finite and stationary candidate set $\mathcal{P}$ (without addition or eviction of senses), and with budget $B_{\text{probe}} \ge 1$, each element of $\mathcal{P}$ is visited with a guaranteed maximum period of:

$$T_{\text{max\_visit}} = \left\lceil \frac{P}{B_{\text{probe}}} \right\rceil \text{ ticks}$$

> **Rigor Nuance:** This property does not constitute ergodicity in a classical dynamic sense. If the candidate set dynamically changes frequently (due to continuous appearance and disappearance of virtual devices), the change of size $P$ or the lexicographical reordering can postpone the visit of certain elements. On hosts with stable hardware, the deterministic cyclic coverage is strict.
