# Cognición y plasticidad

<a id="que-es"></a>

## Qué es

La cognición de un Symbiont es un grafo neuronal recurrente que cambia su
propia estructura y pesos con la experiencia, sin que ningún proceso
externo genere, edite o inyecte código. El organismo no aprende "qué hacer"
frente a una etiqueta externa de verdad: aprende a predecir su propio flujo
sensorial, y esa capacidad predictiva es la señal de aprendizaje.

<a id="mecanismo"></a>

## Mecanismo

El grafo opera sobre un catálogo cerrado de tipos de nodo — `SENSE`,
`CONCEPT`, `STATE`, `PREDICTOR`, `GATE`, `READOUT` — y de arista —
`EXCITATORY`, `INHIBITORY`, `PREDICTIVE`, `GATING`. Deliberadamente no
existe un nodo `ACTION`: las lecturas de `READOUT` alimentan circuitos
externos, pero el grafo nunca ejecuta una acción de sistema por sí mismo.
Pesos, plasticidad y escalas temporales están acotados por rango fijo
(`w ∈ [-2.0, 2.0]`, por ejemplo), y `KernelLimits` impone topes duros de
nodos, conceptos y aristas — ya descritos en el capítulo 1 como el kernel
inmutable bajo el que se desarrolla cualquier fenotipo.

La activación es síncrona y de doble búfer: cada nodo lee solo del tick
actual o del marco previo ya congelado, nunca de un estado a medio
calcular en el mismo tick — esto elimina dependencias circulares y hace que
el resultado no dependa del orden en que se construyeron nodos y aristas.

El aprendizaje es libre de etiquetas. Los nodos `PREDICTOR` se entrenan
contra pérdida de Huber (cuadrática cerca de cero, lineal lejos, para no
dejar que un error grande domine la actualización). Los pesos se ajustan
con una regla de Oja modulada por disponibilidad y salud sensorial, que
evita la explosión de pesos hebbianos sin necesitar una normalización
global explícita. Antes de que un candidato predictivo entre al grafo
activo, se evalúa en modo sombra (*shadow*) comparando su pérdida contra
una línea base trivial de persistencia — solo se promueve tras acumular
evidencia de ganancia sostenida, nunca automáticamente.

La metaplasticidad decide si una adaptación estructural se consolida
evaluando un vector de cinco objetivos (error de predicción, coste de
representación, inestabilidad, información retenida, calibración) bajo
dominancia de Pareto. Tres fallos consecutivos activan un modo seguro que
congela cualquier cambio de hiperparámetro hasta que alguien lo reconozca
explícitamente.

<a id="implementado"></a>

## Qué hay implementado

- Catálogo cerrado de nodos/aristas y límites de kernel — **[implementado]**.
- Activación determinista de doble búfer, independiente del orden de
  construcción — **[implementado]**.
- Aprendizaje libre de etiquetas vía pérdida de Huber y regla de Oja
  modulada — **[implementado]**.
- Ciclo de vida de predictores en modo sombra (`candidate` → `supported` /
  `retired`) con promoción explícita, nunca automática por el evaluador —
  **[implementado] [evaluator-only]** en su verificación longitudinal (los
  estudios que ejercitan el ciclo completo viven en el laboratorio, fuera
  de la cognición del organismo).
- Metaplasticidad con objetivo de Pareto y modo seguro tras fallos
  consecutivos — **[implementado]**.

<a id="evidencia"></a>

## Evidencia

La independencia respecto al orden de construcción del grafo está
verificada por prueba directa. La regla de Oja modulada está probada en
ambos sentidos: no se mueve cuando está congelada, no es elegible, o la
modulación es cero, y sí mueve el peso hacia la actividad correlacionada
cuando las tres condiciones se cumplen. El modo seguro de metaplasticidad
está probado explícitamente: tres fallos consecutivos lo activan, y una vez
activo no se libera sin una acción de reinicio explícita — no hay
recuperación silenciosa.

<a id="abierto"></a>

## Qué sigue abierto (de este mecanismo)

- La promoción de un predictor de `candidate` a `supported` en el runtime
  real permanece como una operación explícita y acotada; su generalización
  fuera de los regímenes sintéticos estudiados en el laboratorio no está
  demostrada — el propio roadmap lo declara abierto.
- Los cinco objetivos de la metaplasticidad son un diseño de ingeniería
  (heurística de Pareto), no una propiedad matemática demostrada como
  óptima frente a otras posibles combinaciones de objetivos.

<a id="respaldo-formal"></a>

## Respaldo formal

La dinámica de activación de retardo causal, la regla de Oja discretizada,
las trazas de elegibilidad y el invariante de acotamiento en `[-1, 1]` están
formalizados en
[`docs/math/09-plasticidad-endogena-y-redes-recurrentes.md`](../math/09-plasticidad-endogena-y-redes-recurrentes.md).
El automodelo del organismo y la cuantización no lineal de costes están en
[`docs/math/08-automodelo-y-sensores-adaptativos.md`](../math/08-automodelo-y-sensores-adaptativos.md),
y la cognición de agentes y metacognición en
[`docs/math/07-cognicion-agentes-y-metacognicion.md`](../math/07-cognicion-agentes-y-metacognicion.md).
