# Consenso Colectivo, Dinámica de Confianza y Destilación Epigenética

## 1. La Problemática del Consenso sin Verdad Fundamental

En una población de agentes descentralizados o en una federación de anfitriones que intercambian cápsulas de conocimiento:

- Ningún nodo actúa como oráculo central de verdad.
- Algunos agentes pueden estar comprometidos o reportar observaciones invertidas (*poisoned reporters*).
- Las correlaciones y creencias son ruidosas y locales.

El sistema debe resolver dos problemas matemáticos simultáneos:

1. **Agregación de Evidencias:** ¿Cómo combinar los votos discretos o continuos de múltiples fuentes heterogéneas para inferir una creencia colectiva robusta?
2. **Evaluación de Confianza Endógena (*Trust Modeling*):** ¿Cómo evaluar si una fuente es fiable sin disponer jamás de etiquetas de verdad externa para contrastar sus afirmaciones?

Symbiont resuelve esto a través de [`SourceTrustModel`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/trust.py), [`CollectiveMemory`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/collective.py) y [`SpeciesHeritage`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/heritage.py).

---

## 2. Función Continua de Concordancia Estadística

Cuando un anfitrión recibe una cápsula de conocimiento ([`KnowledgeCapsule`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/capsule.py)) firmada criptográficamente con Ed25519, extrae la media remota afirmada $\mu_{\text{remote}}$ para una capacidad $c_k$.

El organismo local compara dicha afirmación con su propia distribución aclimatada $\mathcal{N}(\mu_{\text{local}}, \sigma_{\text{local}}^2)$ mediante la función en [`agreement_score`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/trust.py#L31-L45):

Si la capacidad no está aclimatada localmente o $\sigma_{\text{local}} = 0.0$, el sistema retorna `None` (silencio epistémico). En caso contrario:

$$z = \frac{|\mu_{\text{remote}} - \mu_{\text{local}}|}{\sigma_{\text{local}}}$$

$$\operatorname{Agreement}(z) = \frac{1}{1 + z} \in (0, 1]$$

```text
Agreement
   ▲
1.0│  .
   │   ╲
0.8│    ╲
   │     ╲
0.5│───────● (z = 1: discrepancia de 1 desvío estándar)
   │        ╲
0.2│         `─.
   │            `───.
0.0└────────┬────────┬────────► Discrepancia Estandarizada z
   0        1        4
```

### 2.1 Propiedades Analíticas

1. **Concordancia Exacta:** $\lim_{z \to 0^+} \operatorname{Agreement}(z) = 1.0$.
2. **Monotonía Decreciente Estricta:** $\frac{d}{dz} \operatorname{Agreement}(z) = -\frac{1}{(1+z)^2} < 0 \quad \forall z \ge 0$.
3. **Comportamiento Asintótico:** $\lim_{z \to \infty} \operatorname{Agreement}(z) = 0$.
4. **Resistencia a Puntos Atípicos Extremos:** A diferencia de las funciones de base radial gaussianas ($\exp(-z^2)$), que colapsan exponencialmente a cero ante discrepancias moderadas ($e^{-16} \approx 10^{-7}$ para $z=4$), la curva hiperbólica $\frac{1}{1+z}$ es de cola pesada ($1/5 = 0.20$ para $z=4$), evitando la aniquilación numérica del gradiente de confianza.

---

## 3. Fusión de Evidencias en Memoria Colectiva

En el simulador poblacional ([`symbiont.core.collective.CollectiveMemory`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/collective.py)), cada agente $s \in \mathcal{S}$ emite para una firma $\text{fp}$ un voto que contiene su veredicto $\text{threat}_s \in \{0, 1\}$ y su confianza $C_s \in [0.05, 1.0]$.

El peso informacional de cada informante se modula por su reputación acumulada $T(s) \in [0.15, 0.98]$:

$$w_s = T(s) \cdot C_s$$

### 3.1 Probabilidad Colectiva en Vivo

La probabilidad colectiva contemporánea $P_{\text{live}} \in [0, 1]$ es el promedio ponderado de los votos:

$$P_{\text{live}} = \frac{\sum_{s \in \text{Votes}} w_s \cdot \text{threat}_s}{\sum_{s \in \text{Votes}} w_s}$$

### 3.2 Descomposición de la Certeza Colectiva

La certeza del consenso $c_{\text{live}} \in [0, 1]$ no depende únicamente del número de votos, sino de cuatro dimensiones ortogonales:

$$c_{\text{live}} = \min\Big( 1.0, \; 0.35 \cdot D + 0.25 \cdot \bar{C} + 0.25 \cdot A + 0.15 \cdot \bar{T} \Big)$$

1. **Diversidad de Fuentes ($D$):**
   Satura con 10 informantes independientes:
   $$D = \min\left( \frac{|\text{Votes}|}{10.0}, \; 1.0 \right)$$
2. **Confianza Media Declarada ($\bar{C}$):**
   $$\bar{C} = \frac{1}{|\text{Votes}|} \sum_{s} C_s$$
3. **Acuerdo Poblacional / Polarización ($A$):**
   Mide la distancia de la probabilidad respecto a la ambigüedad máxima ($0.5$):
   $$A = 2.0 \cdot |P_{\text{live}} - 0.5| \in [0, 1]$$
   Si la población está dividida $50/50$, $A = 0.0$. Si existe unanimidad, $A = 1.0$.
4. **Reputación Media de las Fuentes ($\bar{T}$):**
   $$\bar{T} = \frac{1}{|\text{Votes}|} \sum_{s} T(s)$$

---

## 4. Recalibración de Confianza por Consenso Leave-One-Out (Jackknife)

El reto central de la reputación en Symbiont es: **¿cómo castigar a los agentes envenenados y premiar a los honestos sin conocer la verdad fundamental?**

En [`CollectiveMemory.recalibrate_sources`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/collective.py#L166-L218), el sistema aplica una técnica inspirada en el estimador de Jackknife:

Para evaluar la legitimidad del voto de un informante $s$ sobre un patrón $\text{fp}$, se calcula el consenso del resto de la población **excluyendo explícitamente a $s$**:

$$W_{-s} = \sum_{p \in \text{Votes} \setminus \{s\}} T(p) \cdot C_p$$

$$P_{-s} = \frac{1}{W_{-s}} \sum_{p \in \text{Votes} \setminus \{s\}} T(p) \cdot C_p \cdot \text{threat}_p$$

La creencia dominante de los pares es:

$$\text{PeerBelief}_{-s} = \mathbb{I}\left( P_{-s} \ge 0.5 \right)$$

### 4.1 Objetivo de Ajuste y Filtro EWMA

Se define el indicador de concordancia binaria:

$$\operatorname{Agreement}(s) = \mathbb{I}\Big( \text{threat}_s == \text{PeerBelief}_{-s} \Big)$$

El objetivo de confianza instantáneo se mapea a un rango no degenerado $[0.20, 0.95]$:

$$\text{Target} = 0.20 + 0.75 \cdot \operatorname{Agreement}(s) = \begin{cases} 0.95 & \text{si concuerda con sus pares} \\ 0.20 & \text{si discrepa de sus pares} \end{cases}$$

La reputación $T(s)$ se actualiza suavemente mediante un filtro EWMA acotado:

$$T_{t+1}(s) = \operatorname{clip}\Big( 0.90 \cdot T_t(s) + 0.10 \cdot \text{Target}, \; 0.15, \; 0.98 \Big)$$

### 4.2 Dinámica de la Brecha de Confianza (*Trust Gap*)

Bajo una fracción de envenenamiento $\rho \in [0, 0.5)$ donde los agentes maliciosos invierten sus reportes ($\text{threat}_{\text{poisoned}} = \neg \text{threat}_{\text{honest}}$):

Dado que los agentes honestos representan la mayoría ponderada ($1 - \rho > \rho$), el consenso de pares $P_{-s}$ coincide casi siempre con la realidad observada por la mayoría honesta.
Por tanto:

- Para un agente honesto: $\mathbb{E}[\text{Target}] \approx 0.95 \implies T^*_{\text{honest}} \approx 0.95$.
- Para un agente envenenado: $\mathbb{E}[\text{Target}] \approx 0.20 \implies T^*_{\text{poisoned}} \approx 0.20$.

Se define la **Brecha de Confianza** (*Trust Gap*):

$$\Delta_{\text{trust}} = \bar{T}_{\text{honest}} - \bar{T}_{\text{poisoned}} \xrightarrow{t \to \infty} 0.95 - 0.20 = 0.75$$

El sistema aísla automáticamente las fuentes no fidedignas reduciendo su peso relativo en un factor superior a $4.75\times$, sin haber recibido una sola etiqueta externa.

---

## 5. Destilación Epigenética y Fusión Intergeneracional

Entre generaciones sucesivas de agentes, el conocimiento adquirido no se transfiere como una base de datos estática completa, sino como una **destilación epigenética comprimida** ([`symbiont.core.heritage`](file:///home/alessbarb/workspace/repos/incubating/symbiont-lab/src/symbiont/core/heritage.py)).

### 5.1 Criterios de Selección Cuádruple

Un patrón $\text{fp}$ califica para ser destilado en el genoma/patrimonio de la especie si y solo si supera cuatro compuertas estadísticas:

1. **Masa Crítica de Reportes:** $\text{reports} \ge 6$.
2. **Diversidad de Fuentes:** $|\text{votes}| \ge 4$ (evita que un solo agente sesgado cree un prior).
3. **Certeza Mínima:** $c_{\text{live}} \ge 0.68$.
4. **Separación de Indiferencia:** $|P_{\text{live}} - 0.5| \ge 0.20$ (patrones con ambigüedad intrínseca no se fijan como dogmas).

### 5.2 Atenuación de Certeza Epigenética

Un prior heredado no debe dominar ciegamente a la evidencia empírica que la nueva generación recopilará. Por ello, la certeza transmitida $c_{\text{inh}}$ se somete a una contracción matemática:

$$c_{\text{inh}} = \min\Big( 0.55, \; 0.25 + 0.35 \cdot c_{\text{live}} \Big)$$

Incluso si la generación previa poseía certeza absoluta ($c_{\text{live}} = 1.0$), la nueva generación hereda como máximo una certeza de $0.55$.

### 5.3 Función de Fusión Bayesiana Prior-Live

Cuando la nueva generación combina su evidencia en vivo con el prior heredado:

$$w_{\text{prior}} = 0.65 \cdot c_{\text{prior}}$$
$$w_{\text{live}} = \max(c_{\text{live}}, 0.15)$$

$$P_{\text{combined}} = \frac{P_{\text{live}} w_{\text{live}} + P_{\text{prior}} w_{\text{prior}}}{w_{\text{live}} + w_{\text{prior}}}$$

La certeza combinada incorpora una sinergia no lineal acotada:

$$c_{\text{combined}} = \min\Big( 1.0, \; c_{\text{live}} + 0.18 \cdot c_{\text{prior}} \cdot (1.0 - c_{\text{live}}) \Big)$$

El término $0.18 \cdot c_{\text{prior}} \cdot (1.0 - c_{\text{live}})$ asegura que el prior aumente la certeza cuando la evidencia local es escasa ($c_{\text{live}} \approx 0$), pero ceda completamente el control a medida que la evidencia local madura ($c_{\text{live}} \to 1$).
