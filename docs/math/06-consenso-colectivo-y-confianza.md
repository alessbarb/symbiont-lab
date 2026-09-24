# Consenso Colectivo, Dinámica de Confianza y Destilación Epigenética

> **Estado:** IMPLEMENTADO  
> **Tipo:** PROTOCOLO COOPERATIVO Y DINÁMICA DE REPUTACIÓN  
> **Módulos relacionados:** [`symbiont.core.trust`](../../src/symbiont/core/social/trust.py), [`symbiont.core.collective`](../../src/symbiont/core/social/collective.py), [`symbiont.core.heritage`](../../src/symbiont/core/lineage/heritage.py)

---

## 1. La Problemática del Consenso sin Verdad Fundamental

En una población de agentes descentralizados o en una federación de anfitriones que intercambian cápsulas firmadas:

- Ningún nodo actúa como oráculo central de verdad.
- Algunos agentes pueden emitir reportes invertidos o maliciosos (*poisoned reporters*).
- Las señales observadas son ruidosas y locales.

El sistema aborda dos problemas matemáticos simultáneos:

1. **Agregación de Evidencias:** ¿Cómo combinar los votos discretos de múltiples fuentes para inferir una creencia colectiva coherente?
2. **Evaluación de Confianza Endógena (*Trust Modeling*):** ¿Cómo evaluar si una fuente es fiable sin disponer de etiquetas de verdad externa para contrastar sus afirmaciones?

Symbiont implementa estos mecanismos en [`SourceTrustModel`](../../src/symbiont/core/social/trust.py), [`CollectiveMemory`](../../src/symbiont/core/social/collective.py) y [`SpeciesHeritage`](../../src/symbiont/core/lineage/heritage.py).

---

## 2. Función Continua de Concordancia Estadística

> **Clasificación:** IDENTIDAD DEL CÓDIGO / MÉTRICA DE SIMILITUD DE COLA PESADA

Cuando un anfitrión recibe una cápsula de conocimiento ([`KnowledgeCapsule`](../../src/symbiont/core/social/capsule.py)) firmada criptográficamente con Ed25519, extrae la media remota afirmada $\mu_{\text{remote}}$ para una capacidad $c_k$.

El organismo local compara dicha afirmación con su propia distribución aclimatada $\mathcal{N}(\mu_{\text{local}}, \sigma_{\text{local}}^2)$ mediante [`agreement_score`](../../src/symbiont/core/social/trust.py#L31-L45):

Si la capacidad no está aclimatada localmente o $\sigma_{\text{local}} = 0.0$, el sistema retorna `None` (silencio epistémico ante falta de base comparativa). En caso contrario:

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

### 2.1 Propiedades Analíticas

1. **Concordancia Exacta:** $\lim_{z \to 0^+} \operatorname{Agreement}(z) = 1.0$.
2. **Monotonía Decreciente:** $\frac{d}{dz} \operatorname{Agreement}(z) = -\frac{1}{(1+z)^2} < 0 \quad \forall z \ge 0$.
3. **Cola Pesada:** A diferencia de funciones gaussianas de base radial ($\exp(-z^2)$), que colapsan numéricamente hacia cero ante discrepancias moderadas ($e^{-16} \approx 10^{-7}$ para $z=4$), la curva hiperbólica $\frac{1}{1+z}$ asigna $0.20$ para $z=4$, evitando la aniquilación prematura del gradiente de reputación.

---

## 3. Fusión de Evidencias en Memoria Colectiva

En el simulador poblacional ([`CollectiveMemory`](../../src/symbiont/core/social/collective.py)), cada agente $s$ emite para una firma $\text{fp}$ un voto que contiene su veredicto $\text{threat}_s \in \{0, 1\}$ y su confianza declarada $C_s \in [0.05, 1.0]$.

El peso informacional asignado a cada informante se modula por su reputación acumulada $T(s) \in [0.15, 0.98]$:

$$w_s = T(s) \cdot C_s$$

### 3.1 Probabilidad Colectiva en Vivo

La probabilidad colectiva contemporánea $P_{\text{live}} \in [0, 1]$ es el promedio ponderado:

$$P_{\text{live}} = \frac{\sum_{s \in \text{Votes}} w_s \cdot \text{threat}_s}{\sum_{s \in \text{Votes}} w_s}$$

### 3.2 Descomposición de la Certeza Colectiva

La certeza del consenso $c_{\text{live}} \in [0, 1]$ combina cuatro dimensiones ortogonales:

$$c_{\text{live}} = \min\Big( 1.0, \; 0.35 \cdot D + 0.25 \cdot \bar{C} + 0.25 \cdot A + 0.15 \cdot \bar{T} \Big)$$

1. **Diversidad de Fuentes ($D$):** Satura al alcanzar 10 informantes independientes:
   $$D = \min\left( \frac{|\text{Votes}|}{10.0}, \; 1.0 \right)$$
2. **Confianza Media Declarada ($\bar{C}$):**
   $$\bar{C} = \frac{1}{|\text{Votes}|} \sum_{s} C_s$$
3. **Polarización Poblacional / Acuerdo ($A$):**
   $$A = 2.0 \cdot |P_{\text{live}} - 0.5| \in [0, 1]$$
4. **Reputación Media de las Fuentes ($\bar{T}$):**
   $$\bar{T} = \frac{1}{|\text{Votes}|} \sum_{s} T(s)$$

---

## 4. Recalibración de Confianza por Consenso Leave-One-Out

> **Clasificación:** HEURÍSTICA DE RECALIBRACIÓN / ANÁLISIS DE CASO LÍMITE

En [`CollectiveMemory.recalibrate_sources`](../../src/symbiont/core/social/collective.py#L166-L218), el sistema evalúa la legitimidad de un informante $s$ comparando su voto con el consenso del resto de la población **excluyendo explícitamente a $s$**:

$$W_{-s} = \sum_{p \in \text{Votes} \setminus \{s\}} T(p) \cdot C_p$$

$$P_{-s} = \frac{1}{W_{-s}} \sum_{p \in \text{Votes} \setminus \{s\}} T(p) \cdot C_p \cdot \text{threat}_p$$

La creencia de los pares es:

$$\text{PeerBelief}_{-s} = \mathbb{I}\left( P_{-s} \ge 0.5 \right)$$

### 4.1 Objetivo de Ajuste y Filtro EWMA

Se define el indicador de concordancia binaria:

$$\operatorname{Agreement}(s) = \mathbb{I}\Big( \text{threat}_s == \text{PeerBelief}_{-s} \Big)$$

El objetivo de reputación se fija en:

$$\text{Target} = 0.20 + 0.75 \cdot \operatorname{Agreement}(s) = \begin{cases} 0.95 & \text{si concuerda con sus pares} \\ 0.20 & \text{si discrepa de sus pares} \end{cases}$$

La reputación $T(s)$ se actualiza suavemente mediante un filtro EWMA con cotas duras:

$$T_{t+1}(s) = \operatorname{clip}\Big( 0.90 \cdot T_t(s) + 0.10 \cdot \text{Target}, \; 0.15, \; 0.98 \Big)$$

### 4.2 Análisis Crítico y Límites del Modelo de Confianza
>
> **Advertencia sobre el Consenso Leave-One-Out:**  
> Este esquema está **inspirado en la validación cruzada Leave-One-Out**, pero no constituye un estimador de Jackknife estadístico formal (no genera pseudovalores ni estima varianzas de estimadores).  
> Sus limitaciones teóricas son:
>
> 1. **No-Aislamiento Absoluto:** El valor mínimo de confianza está acotado en $T_{\min} = 0.15$. Un informante hostil nunca es matemáticamente silenciado; su peso queda fuertemente atenuado, pero persiste en la mezcla ponderada.
> 2. **Vulnerabilidad a Mayorías Coordinadas (*Sybil / Echo Chamber*):** Si los agentes maliciosos superan el $50\%$ del peso activo en un patrón, el consenso Leave-One-Out castigará sistemáticamente a los agentes honestos minoritarios, reduciendo su confianza hacia $0.20$.
> 3. **Correlación no Modelada:** Tratar a múltiples agentes como votos independientes asume fuentes no correlacionadas. Si varios agentes comparten un upstream idéntico, su voto conjunto amplifica artificialmente el peso aparente.

**Caso Límite Idealizado ($\Delta_{\text{trust}} \to 0.75$):**  
Bajo el supuesto estricto de una mayoría honesta estable y descorrelacionada, los agentes honestos convergen asintóticamente a $T^* \approx 0.95$ y los envenenados a $T^* \approx 0.20$, produciendo una brecha límite de confianza de $\Delta_{\text{trust}} \approx 0.75$. Este valor debe interpretarse como un caso idealizado de laboratorio, no como una garantía universal de seguridad bizantina.

---

## 5. Destilación Epigenética y Fusión Intergeneracional

> **Clasificación:** POLÍTICA DE COMPRESIÓN Y ATENUACIÓN DE PRIORS

Entre generaciones de agentes, el conocimiento acumulado se transfiere como una **destilación epigenética comprimida** ([`SpeciesHeritage`](../../src/symbiont/core/lineage/heritage.py)).

### 5.1 Criterios de Selección Cuádruple

Un patrón $\text{fp}$ califica para ser destilado en el patrimonio hereditario si supera cuatro filtros:

1. **Soporte Muestral:** $\text{reports} \ge 6$.
2. **Diversidad de Fuentes:** $|\text{votes}| \ge 4$.
3. **Certeza Mínima:** $c_{\text{live}} \ge 0.68$.
4. **Separación de Indiferencia:** $|P_{\text{live}} - 0.5| \ge 0.20$.

### 5.2 Atenuación de Certeza Epigenética

Para que un prior heredado no sofoque la capacidad de aprendizaje empírico de la nueva generación, la certeza transmitida $c_{\text{inh}}$ se atenúa deliberadamente:

$$c_{\text{inh}} = \min\Big( 0.55, \; 0.25 + 0.35 \cdot c_{\text{live}} \Big)$$

Incluso ante una certeza previa absoluta ($c_{\text{live}} = 1.0$), la nueva generación hereda como máximo una certeza de $0.55$.

### 5.3 Función de Fusión Bayesiana Prior-Live

La nueva generación combina su evidencia en vivo con el prior heredado:

$$w_{\text{prior}} = 0.65 \cdot c_{\text{prior}}, \qquad w_{\text{live}} = \max(c_{\text{live}}, 0.15)$$

$$P_{\text{combined}} = \frac{P_{\text{live}} w_{\text{live}} + P_{\text{prior}} w_{\text{prior}}}{w_{\text{live}} + w_{\text{prior}}}$$

$$c_{\text{combined}} = \min\Big( 1.0, \; c_{\text{live}} + 0.18 \cdot c_{\text{prior}} \cdot (1.0 - c_{\text{live}}) \Big)$$

El factor $0.18 \cdot c_{\text{prior}} \cdot (1.0 - c_{\text{live}})$ aporta un sesgo informativo orientativo en las fases iniciales ($c_{\text{live}} \approx 0$), pero se desvanece suavemente a medida que la evidencia empírica directa madura ($c_{\text{live}} \to 1$).
