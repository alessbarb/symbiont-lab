# Detección de Deriva, Ruptura de Régimen y Modelado Rítmico

## 1. El Problema de la No-Estacionariedad en Sistemas Operativos y Entornos Complejos

En un anfitrión real o simulado, las señales físicas o estadísticas no provienen de distribuciones estacionarias independientes e idénticamente distribuidas (i.i.d.). Se presentan tres fenómenos no estacionarios fundamentales:

1. **Picos Aislados (*Isolated Spikes*):** Una ráfaga transitoria (ej. un hilo compilando durante 500 ms) que se desvía drásticamente de la media pero cesa de inmediato. El modelo no debe reaccionar desplazando permanentemente su nivel de base hacia el pico.
2. **Cambio Brusco de Régimen (*Regime Shift*):** Una modificación estructural permanente del entorno (ej. el anfitrión pasa a alojar una base de datos activa o el simulador entra en fase de cambio de régimen). El modelo debe olvidar rápidamente la historia previa y re-centrarse en el nuevo equilibrio.
3. **Arrastre Lento (*Slow Creep*):** Una variación infinitesimal paso a paso (ej. una fuga de memoria o un calentamiento progresivo) que en ningún tick individual supera el umbral de anomalía brusca, pero cuya acumulación temporal altera profundamente el estado del sistema.

[`DriftAwareBaseline`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/drift.py) y [`RhythmModel`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/rhythms.py) formalizan el aparato matemático necesario para resolver estos tres fenómenos sin incurrir en bucles de auto-corrupción de la varianza.

---

## 2. Filtro EWMA Estocástico para Media y Varianza Móvil

Cuando el sistema opera en condiciones de variación normal (sin desviaciones extremas activas), el estado de base se actualiza mediante un filtro de media móvil ponderada exponencialmente (EWMA) de primer orden con factor de olvido $\lambda \in (0, 1]$ (por defecto $\lambda = 0.10$):

$$\Delta_t = x_t - \mu_{t-1}$$
$$\mu_t = \mu_{t-1} + \lambda \Delta_t$$

### 2.1 Ecuación en Diferencias de la Varianza Ponderada

A diferencia de los filtros EWMA estándar que rastrean únicamente el primer momento, Symbiont rastrea recursivamente el segundo momento central $\sigma_t^2$:

$$\sigma_t^2 = (1 - \lambda) \cdot \left( \sigma_{t-1}^2 + \lambda \cdot \Delta_t^2 \right)$$

### 2.2 Derivación de la Ecuación de Varianza

Consideremos la definición teórica de la varianza exponencial con ponderaciones normalizadas:

$$\sigma_t^2 = \sum_{k=0}^\infty w_k (x_{t-k} - \mu_t)^2, \quad \text{donde } w_k = \lambda (1-\lambda)^k$$

Dado que $\mu_t - \mu_{t-1} = \lambda (x_t - \mu_{t-1}) = \lambda \Delta_t$, podemos aproximar recursivamente la evolución del error cuadrático:

$$\begin{aligned}
\sigma_t^2 &\approx (1-\lambda)\sigma_{t-1}^2 + \lambda(x_t - \mu_{t-1})(x_t - \mu_t) \\
&= (1-\lambda)\sigma_{t-1}^2 + \lambda \Delta_t \left( \Delta_t - \lambda \Delta_t \right) \\
&= (1-\lambda)\sigma_{t-1}^2 + \lambda(1-\lambda) \Delta_t^2 \\
&= (1-\lambda) \left( \sigma_{t-1}^2 + \lambda \Delta_t^2 \right) \quad \blacksquare
\end{aligned}$$

Esta formulación garantiza que $\sigma_t^2 \ge 0$ en todo instante y converge a la varianza real si la señal es estacionaria con varianza $\sigma^2$:

$$\mathbb{E}[\sigma_t^2] = (1-\lambda) \mathbb{E}[\sigma_{t-1}^2] + \lambda(1-\lambda) \mathbb{E}[\Delta_t^2] \xrightarrow{t \to \infty} \sigma^2$$

---

## 3. Puntuación de Desviación Tipificada ($Z$-Score) y Categorización

Para cada nueva observación $x_t$, antes de actualizar la línea base, se calcula la puntuación $Z$:

$$z(x_t) = \begin{cases}
0.0 & \text{si } \sigma_{t-1} = 0 \land x_t = \mu_{t-1} \\
+\infty & \text{si } \sigma_{t-1} = 0 \land x_t > \mu_{t-1} \\
-\infty & \text{si } \sigma_{t-1} = 0 \land x_t < \mu_{t-1} \\
\frac{x_t - \mu_{t-1}}{\sigma_{t-1}} & \text{si } \sigma_{t-1} > 0
\end{cases}$$

Se definen los umbrales canónicos de decisión:
- $z_{\text{regime}} = 2.0$ (desviación estadísticamente significativa a nivel bilateral $\alpha \approx 0.0455$).
- $z_{\text{isolated}} = 3.0$ (desviación extrema a nivel $\alpha \approx 0.0027$).
- $K_{\text{regime}} = 3$ (longitud de racha para confirmar ruptura).

```mermaid
flowchart TD
    Obs["Lectura x_t"] --> CalcZ["Calcular z = (x_t - μ) / σ"]
    CalcZ --> CheckDev{"|z| >= z_regime (2.0)?"}

    CheckDev -- "Sí" --> CheckDir{"Misma dirección que racha previa?"}
    CheckDir -- "Sí" --> IncStreak["Racha = Racha + 1; Buffer.append(x_t)"]
    CheckDir -- "No" --> ResetStreak["Racha = 1; Dirección = sgn(z); Buffer = [x_t]"]

    IncStreak --> CheckConf{"Racha >= K_regime (3)?"}
    CheckConf -- "Sí" --> Recompute["REGIME_SHIFT: μ, σ² recomputados de Buffer; Reset Racha"]
    CheckConf -- "No" --> BufferPending["Retener línea base; Buffer pendiente"]

    BufferPending --> CheckIso{"|z| >= z_isolated (3.0)?"}
    CheckIso -- "Sí" --> RetIso["Retornar ISOLATED"]
    CheckIso -- "No" --> RetGrad["Retornar GRADUAL"]

    CheckDev -- "No" --> ClearBuffer["Racha = 0; Buffer = []"]
    ClearBuffer --> UpdateDirect["Actualizar μ, σ² directo con x_t"]
    UpdateDirect --> CheckCreep["Evaluar Deriva Lenta (Creep)"]
    CheckCreep --> RetNoneOrCreep["Retornar CREEP o NONE"]
```

---

## 4. Teorema de Aislamiento de Buffer y No-Contaminación de la Línea Base

### 4.1 El Problema de la Auto-Corrupción de la Varianza
Supongamos un modelo ingenuo que actualiza $(\mu, \sigma^2)$ continuamente en cada tick incluso durante una racha de desviación.

**Teorema del Bloqueo por Auto-Corrupción:**
Si una perturbación por salto $\Delta$ ocurre en $t=1$:
$$x_1 = \mu_0 + \Delta, \quad \text{con } \Delta \ge z_{\text{regime}} \sigma_0$$

En el paso $t=1$, el término de error es $\Delta$. La nueva varianza estimada es:
$$\sigma_1^2 = (1-\lambda)(\sigma_0^2 + \lambda \Delta^2)$$

Si $\Delta = 3\sigma_0$ y $\lambda = 0.1$:
$$\sigma_1^2 = 0.9 \cdot (\sigma_0^2 + 0.1 \cdot 9 \sigma_0^2) = 0.9 \cdot (1.9 \sigma_0^2) = 1.71 \sigma_0^2 \implies \sigma_1 \approx 1.308 \sigma_0$$

Al llegar el paso $t=2$ con la misma perturbación $x_2 = \mu_0 + \Delta$:
$$\mu_1 = \mu_0 + 0.1 \Delta \implies x_2 - \mu_1 = 0.9 \Delta$$
$$z(x_2) = \frac{0.9 \Delta}{\sigma_1} = \frac{0.9 \cdot 3 \sigma_0}{1.308 \sigma_0} = \frac{2.7}{1.308} \approx 2.06$$

En $t=3$, $\sigma_2$ se infla aún más y el $z$-score cae indefectiblemente por debajo de $z_{\text{regime}} = 2.0$.
**Consecuencia:** La racha se rompe antes de alcanzar $K_{\text{regime}} = 3$. El sistema normaliza la anomalía antes de poder clasificarla como cambio de régimen y jamás confirma el shift.

### 4.2 Solución de Symbiont: Buffer de Cuarentena
Durante una racha de desviación ($|z| \ge z_{\text{regime}}$):
1. **La línea base comprometida $(\mu, \sigma^2)$ no se toca.** Permanece congelada en el estado anterior a la perturbación.
2. Los valores discrepantes se acumulan en un buffer temporal $\mathcal{B} = [x_1, \dots, x_k]$.
3. Si la racha se rompe ($|z| < z_{\text{regime}}$ o inversión de signo), el buffer se descarta íntegramente: los picos aislados jamás contaminan la línea base.
4. Si la racha alcanza $K_{\text{regime}} = 3$, se ejecuta una **recomputación cerrada instantánea**:

$$\mu_{\text{new}} = \frac{1}{|\mathcal{B}|} \sum_{x \in \mathcal{B}} x$$
$$\sigma_{\text{new}}^2 = \frac{1}{|\mathcal{B}|} \sum_{x \in \mathcal{B}} (x - \mu_{\text{new}})^2$$

El modelo pasa al nuevo estado sin inercia histórica de la fase previa.

---

## 5. Detección de Arrastre Lento (*Slow Creep*) y Suelo de Ruido Congelado

El arrastre lento ocurre cuando una señal varía según una rampa suave:

$$x_t = x_0 + c \cdot t, \quad \text{donde } c \ll z_{\text{regime}} \sigma_0$$

Para cada paso, $|z(x_t)| < z_{\text{regime}}$, por lo que el detector de saltos bruscos clasifica el evento como `NONE`.

### 5.1 Desacoplamiento de Dos Escalas Temporales
Para detectar esta acumulación progresiva, se mantiene en paralelo una media móvil rápida $\mu_{\text{fast}}$ con parámetro $\lambda_{\text{fast}} = 0.30 > \lambda = 0.10$:

$$\mu_{\text{fast}, t} = \mu_{\text{fast}, t-1} + \lambda_{\text{fast}} \big( x_t - \mu_{\text{fast}, t-1} \big)$$

La divergencia entre la media rápida y la media comprometida $\mu$ mide la pendiente acumulada:

$$D_t = \mu_{\text{fast}, t} - \mu_t$$

### 5.2 El Bucle de Falsa Estabilidad con Varianza en Vivo
¿Por qué no evaluar la significancia de $D_t$ calculando $\frac{|D_t|}{\sigma_t}$?

**Demostración del Teorema del Techo Sub-umbral:**
Bajo una rampa lineal $x_t = c \cdot t$, el retardo de un filtro EWMA respecto a la entrada es:
$$\mathbb{E}[x_t - \mu_t] = c \left( \frac{1-\lambda}{\lambda} \right)$$
$$\mathbb{E}[x_t - \mu_{\text{fast}, t}] = c \left( \frac{1-\lambda_{\text{fast}}}{\lambda_{\text{fast}}} \right)$$

Por consiguiente, la diferencia entre las dos medias es:
$$D = \mu_{\text{fast}} - \mu = c \left( \frac{1-\lambda}{\lambda} - \frac{1-\lambda_{\text{fast}}}{\lambda_{\text{fast}}} \right) = c \left( \frac{0.9}{0.1} - \frac{0.7}{0.3} \right) = c (9.0 - 2.333) = 6.667 c$$

Por otro lado, la varianza viva $\sigma_t^2$ absorbe continuamente el término $(x_t - \mu_{t-1})^2 \approx (9.0 c)^2 = 81 c^2$.
En el equilibrio dinámico:
$$\sigma_{\text{live}}^2 \approx 81 c^2 \implies \sigma_{\text{live}} \approx 9.0 c$$

El cociente evaluado con la varianza viva es:
$$\frac{D}{\sigma_{\text{live}}} \approx \frac{6.667 c}{9.0 c} \approx 0.741$$

Nótese que la constante $c$ (la velocidad de la deriva) se cancela completamente tanto en el numerador como en el denominador.
**Resultado:** Sin importar cuán grande sea la deriva acumulada total, la relación se estrella asintóticamente contra un techo estricto de $\approx 0.741 < z_{\text{creep}} = 1.0$. **La varianza viva se auto-infla al mismo ritmo que la divergencia**, impidiendo de por vida que el detector de creep se active.

### 5.3 Suelo de Ruido Congelado (*Frozen Noise Floor*)
Para romper este bucle de retroalimentación corruptor, Symbiont normaliza la divergencia contra el desvío estándar congelado $\sigma_{\text{creep\_stdev}}$, capturado en el momento en que la línea base se estableció o tras la última confirmación de un shift:

$$z_{\text{creep}}(t) = \frac{\mu_{\text{fast}, t} - \mu_t}{\sigma_{\text{creep\_stdev}}}$$

Dado que el denominador $\sigma_{\text{creep\_stdev}}$ permanece constante mientras la señal se desplaza:
$$\lim_{t \to \infty} |z_{\text{creep}}(t)| = \infty$$

Cuando $|z_{\text{creep}}| \ge z_{\text{creep}} = 1.0$ durante $K_{\text{creep}} = 8$ ticks consecutivos con el mismo signo:
1. Se confirma `DriftKind.CREEP`.
2. Se re-centra suavemente la media principal: $\mu \leftarrow \mu_{\text{fast}}$.
3. Se actualiza el suelo de ruido congelado al nivel actual: $\sigma_{\text{creep\_stdev}} \leftarrow \sigma_{\text{live}}$.
4. Se resetea el contador de racha.

---

## 6. Modelado Rítmico y Cuantización Temporal Cíclica

Para capturar dependencias diurnas (como que la carga de CPU o el tráfico de red son estructuralmente menores de noche que en horario laboral) sin violar el principio de privacidad diferencial ni retener marcas de tiempo absolutas del anfitrión, [`RhythmModel`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/rhythms.py) define un mapa de cuantización cíclico:

$$\psi: \{0, 1, \dots, 23\} \to \{\text{NIGHT}, \text{MORNING}, \text{AFTERNOON}, \text{EVENING}\}$$

$$\psi(h) = \begin{cases}
\text{NIGHT} & \text{si } 0 \le h < 6 \\
\text{MORNING} & \text{si } 6 \le h < 12 \\
\text{AFTERNOON} & \text{si } 12 \le h < 18 \\
\text{EVENING} & \text{si } 18 \le h \le 23
\end{cases}$$

### 6.1 Distribuciones Condicionales
Para cada tupla $(\text{percept\_name}, \text{time\_bucket})$, el sistema mantiene una instancia independiente de [`RunningStats`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/host/acclimation.py#L51-L76).

Esto descompone la densidad marginal de una señal $X$ en una mezcla de densidades condicionadas por la fase diurna:

$$\mathbb{P}(X) = \sum_{b \in \mathcal{T}} \mathbb{P}(X \mid \text{Bucket} = b) \, \mathbb{P}(\text{Bucket} = b)$$

Una señal puede ser clasificada como perfectamente normal a las 14:00 (en `AFTERNOON`, donde su media esperada es $\mu_{\text{aft}} = 0.65$), mientras que el mismo valor a las 03:00 (en `NIGHT`, donde $\mu_{\text{night}} = 0.10$) constituye una discrepancia altamente informativa, sin requerir reglas manuales ni conocimiento del calendario humano.
