# Ecología y sociabilidad

<a id="que-es"></a>

## Qué es

Cuando varios Symbionts comparten un hábitat con recursos finitos, pueden
competir, coexistir, especializarse o intercambiar evidencia entre ellos —
pero ninguna de esas relaciones está impuesta de antemano. El proyecto no
codifica cooperación como objetivo; la cooperación, si aparece, es un
resultado observado, no una meta programada.

<a id="mecanismo"></a>

## Mecanismo

Cada organismo mantiene su propia memoria relacional direccional: un
registro por cada par y por cada canal opaco de interacción. La valencia de
una relación (positiva, negativa o desconocida) se deriva de la diferencia
entre soporte y daño observados — no de una etiqueta social externa. La
frescura de esa evidencia decae exponencialmente con el tiempo desde la
última observación, y la fiabilidad combina la proporción de observaciones
sin conflicto con esa frescura. Nada de esto es reputación global: es
evidencia local, propia de cada organismo, sobre cada relación concreta.

Frente a recursos finitos, `ResourceEvidenceLedger` calcula un puntaje de
utilidad local combinando disponibilidad observada, frescura y una
penalización por denegaciones consecutivas — con un límite explícito para
que ninguna cantidad de denegaciones bloquee un recurso permanentemente. Si
un token ha sido denegado repetidamente pero lleva varios ticks inactivo,
se le concede una oportunidad de reexploración: la escasez temporal no se
convierte en una lista negra permanente, y el organismo permanece adaptable
si el régimen ecológico cambia.

Un hábitat autorizado (`SocialHabitat`) impone capacidad de carga dura,
admisión explícita y liberación transaccional al morir un miembro — la
ecología hereda las mismas garantías transaccionales que ya se describieron
para el nacimiento en el capítulo 6.

<a id="implementado"></a>

## Qué hay implementado

- Memoria relacional direccional por par y por canal, con valencia basada
  en evidencia — **[implementado]**.
- Frescura exponencial y fiabilidad local ponderada por conflicto —
  **[implementado]**.
- Evidencia de disponibilidad de recursos con penalización acotada por
  denegaciones consecutivas — **[implementado]**.
- Reexploración acotada tras enfriamiento, evitando bloqueo permanente —
  **[implementado]**.
- Emergencia autónoma multi-par (interacción social sin planificador
  central, sin miembros aislados) — **[implementado] [evaluator-only]**:
  demostrada en un arnés determinista de laboratorio, no como propiedad
  auto-observada por el organismo en producción.

<a id="evidencia"></a>

## Evidencia

Está probado directamente que la valencia de una relación se deriva de la
evidencia acumulada, no de una etiqueta impuesta. Está probado que el
registro relacional conserva reciprocidad, conflicto y frescura como
dimensiones separadas, no fusionadas en un único número de reputación. Y
está probado que la evidencia de un recurso históricamente útil pero
denegado repetidamente se revisa tras el periodo de enfriamiento — el
organismo puede cambiar de opinión sobre un recurso sin necesitar una señal
externa que se lo indique.

<a id="abierto"></a>

## Qué sigue abierto (de este mecanismo)

- La emergencia autónoma multi-par y su generalización a poblaciones de
  distinto tamaño están medidas solo en estudios evaluator-only del
  laboratorio; no hay evidencia todavía de comportamiento social emergente
  fuera de esos regímenes sintéticos controlados — el propio roadmap lo
  declara así explícitamente.
- La diferenciación de nichos entre organismos bajo contención prolongada
  se ha observado en trayectorias sintéticas específicas, pero no se
  reclama como una propiedad general demostrada del sistema.

<a id="respaldo-formal"></a>

## Respaldo formal

El diseño normativo completo de percepción social, decisión local,
competencia por recursos finitos y límites adversariales está en
[`docs/design/milestone-k-sociabilidad-emergente.md`](../design/milestone-k-sociabilidad-emergente.md).
El consenso colectivo sin oráculo externo, relevante para cómo múltiples
organismos revisan evidencia compartida sin tratar la mayoría como verdad,
está en
[`docs/math/06-consenso-colectivo-y-confianza.md`](../math/06-consenso-colectivo-y-confianza.md).
