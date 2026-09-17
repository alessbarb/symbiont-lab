# Atención y decisión

<a id="que-es"></a>

## Qué es

Un Symbiont tiene un presupuesto de observación finito por tick: no puede
muestrear todos sus sentidos a la vez con resolución máxima. La atención
decide a qué prestar observación limitada, y las creencias deciden cómo
esa observación revisa lo que el organismo ya sostiene como probable — sin
que ninguna de las dos capas reciba jamás la etiqueta de verdad del
evaluador.

<a id="mecanismo"></a>

## Mecanismo

Según ADR-0003, la atención es un mecanismo de optimización de recursos
limitados, explícitamente **no** un juicio de clasificación ni una
detección de amenazas. Cada candidato sensorial recibe una incertidumbre
adimensional (coeficiente de variación); si el sensor todavía no completó
su aclimatación mínima, su incertidumbre se fija en infinito, lo que
garantiza que explorar señales desconocidas siempre gane frente a refinar
señales ya establecidas. La puntuación de cada candidato combina esa
incertidumbre con una ponderación de retornos decrecientes (cuantas más
observaciones ya tiene un sensor, menos urgente es seguir insistiendo) y se
divide por el coste físico de muestrearlo y por un coste de ranking
separado —desacoplados deliberadamente, para que penalizar la posición de
un sensor en el ranking no altere cuánto presupuesto físico real consume.
La asignación final resuelve una heurística voraz de mochila 0/1 sobre un
presupuesto máximo fijo.

Las creencias se actualizan de forma bayesiana con pseudo-observaciones: la
evidencia acumulada tiene un tope superior explícito que impide la
parálisis epistémica — el organismo siempre conserva capacidad de revisar
una creencia si la evidencia cambia drásticamente, por muchas
confirmaciones previas que tuviera. Cuando un lote de lecturas discrepa
significativamente de la línea base, no se suaviza la contradicción: se
genera un registro de disidencia inmutable. En los checkpoints persistentes
solo se guardan contadores acotados de esos conflictos, nunca los valores
numéricos crudos que los originaron — el hecho epistémico de que una
creencia fue refutada sobrevive al reinicio; el dato de host que la refutó,
no.

<a id="implementado"></a>

## Qué hay implementado

- Cálculo de incertidumbre por coeficiente de variación con prioridad
  infinita para sensores no aclimatados — **[implementado]**.
- Asignación de atención por mochila voraz con presupuesto fijo y
  desacoplamiento coste-de-ranking / coste físico — **[implementado]**.
- Revisión bayesiana de creencias con tope de evidencia acotado —
  **[implementado]**.
- Preservación explícita de disidencia (`DissentRecord`) sin suavizado —
  **[implementado]**.

<a id="evidencia"></a>

## Evidencia

Está probado directamente que una incertidumbre infinita siempre gana
sobre cualquier incertidumbre finita en la asignación de atención. La
revisión de creencias fortalece la certeza con evidencia repetida sin
recibir jamás una etiqueta de verdad externa — la prueba construye el
modelo de creencias y lo alimenta solo con observaciones, no con verdad de
evaluador. Y la evidencia conflictiva efectivamente revisa la creencia
mientras registra el conflicto, en vez de descartarlo silenciosamente.

<a id="abierto"></a>

## Qué sigue abierto (de este mecanismo)

- Los pesos concretos de la función de puntuación (0.65/0.35, el exponente
  de retornos decrecientes) son elecciones de ingeniería documentadas como
  heurísticas en el compendio matemático, no derivaciones óptimas
  demostradas.
- El consenso colectivo entre múltiples organismos que comparten evidencia
  (capítulo 6 del compendio matemático) se trata en el capítulo 7 de esta
  serie (ecología y sociabilidad), no aquí.

<a id="respaldo-formal"></a>

## Respaldo formal

La heurística voraz de Dantzig para la mochila 0/1, el coeficiente de
variación como medida de dispersión adimensional, y el desacoplamiento
formal entre coste de ranking y coste físico están en
[`docs/math/04-atencion-causal-y-presupuestos.md`](../math/04-atencion-causal-y-presupuestos.md).
La actualización bayesiana con pseudo-observaciones, la saturación de
evidencia acotada y el test Z de disidencia están en
[`docs/math/05-creencias-bayesianas-y-disidencia.md`](../math/05-creencias-bayesianas-y-disidencia.md).
El consenso colectivo sin oráculo externo está en
[`docs/math/06-consenso-colectivo-y-confianza.md`](../math/06-consenso-colectivo-y-confianza.md).
