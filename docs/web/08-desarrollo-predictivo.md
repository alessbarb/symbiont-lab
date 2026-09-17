# Desarrollo predictivo

<a id="que-es"></a>

## Qué es

Más allá de reaccionar a lo que percibe, un Symbiont puede desarrollar
hipótesis predictivas sobre su propio flujo sensorial: candidatos que
intentan anticipar un valor futuro y se someten a prueba antes de contar
para algo. Ninguna métrica de laboratorio se filtra al organismo como
semántica privilegiada — la promoción de un candidato depende solo de su
desempeño frente a sí mismo.

<a id="mecanismo"></a>

## Mecanismo

Un candidato predictivo se evalúa en modo sombra, fuera del grafo activo:
compara su pérdida contra una línea base trivial de persistencia (predecir
que el próximo valor será igual al anterior). Si acumula ocho muestras con
ganancia estrictamente positiva, pasa a `supported`; si en dieciséis
muestras su desempeño sigue por debajo de la persistencia, pasa a
`retired`. Un candidato `retired` no se reactiva silenciosamente tras un
reinicio — su estado de fracaso persiste. La promoción de `supported` a
predictor activo en el grafo es siempre una operación explícita del
runtime, nunca una decisión automática disparada por el propio evaluador
del laboratorio.

La plasticidad estructural (creación y poda de nodos y aristas) está
acotada: el uso de memoria del organismo se mantiene bajo control incluso
tras procesar muchos pares distintos a lo largo de una vida larga, en vez
de crecer sin límite con el tiempo de residencia.

Cuando el laboratorio necesita seleccionar candidatos en flujo continuo sin
conocer de antemano el horizonte completo de observaciones, usa una
estructura de Treap (árbol binario aleatorizado con prioridades) para
mantener una selección en línea con complejidad logarítmica esperada — esto
vive exclusivamente en `symbiont_lab`, nunca en la cognición del organismo.

<a id="implementado"></a>

## Qué hay implementado

- Ciclo de vida de candidatos predictivos (`candidate → supported /
  contradicted → retired`) en modo sombra — **[implementado]**.
- Bloqueo de reactivación silenciosa de un candidato `retired` tras
  reinicio — **[implementado]**.
- Plasticidad estructural con uso de memoria acotado independientemente de
  la duración del residente — **[implementado]**.
- Selección causal en streaming mediante Treap para evaluación estadística
  de laboratorio — **[implementado] [evaluator-only]**: existe solo como
  herramienta de `symbiont_lab`, nunca como mecanismo cognitivo del
  organismo.

<a id="evidencia"></a>

## Evidencia

Está probado directamente que un candidato predictivo sin ganancia
sostenida no se promueve — la prueba construye un candidato con desempeño
igual o peor que la persistencia trivial y confirma que nunca alcanza el
estado promovible. Está probado también que el mecanismo de reconciliación
estructural mantiene el crecimiento de memoria acotado incluso al procesar
un número grande de pares distintos, en vez de crecer proporcionalmente sin
límite.

<a id="abierto"></a>

## Qué sigue abierto (de este mecanismo)

- La promoción real de un predictor en el runtime de producción, más allá
  de los estudios longitudinales de laboratorio, sigue siendo una operación
  opt-in y acotada — no hay evidencia de generalización automática fuera de
  los regímenes sintéticos estudiados.
- Los umbrales exactos de muestras (8 para soporte, 16 para retiro) son
  parámetros de ingeniería documentados como heurísticos, no derivados de
  una teoría de detención óptima.

<a id="respaldo-formal"></a>

## Respaldo formal

El diseño normativo de atención anti-captura, persistencia cuantizada con
cero exacto, conceptos varados (*stranded*) y predicción en modo sombra
está en
[`docs/design/sociabilidad-y-desarrollo-predictivo.md`](../design/sociabilidad-y-desarrollo-predictivo.md).
La selección causal en streaming mediante Treaps, el Brier Score y la
descomposición de Murphy están formalizados en
[`docs/math/10-seleccion-causal-y-evaluacion-estadistica.md`](../math/10-seleccion-causal-y-evaluacion-estadistica.md).
