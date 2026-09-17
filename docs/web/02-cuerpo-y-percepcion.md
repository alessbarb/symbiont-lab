# Cuerpo y percepción

<a id="que-es"></a>

## Qué es

Un Symbiont no recibe una lista de sensores con nombres humanos ("uso de
CPU", "temperatura"). Descubre superficies de observación numéricas,
acotadas y vetadas dentro del anfitrión, les asigna identidades opacas, y
aprende su fiabilidad y utilidad estadística antes de decidir cuáles
conservar como sentidos activos. El cuerpo del organismo es, en ese
sentido, aprendido, no configurado.

<a id="mecanismo"></a>

## Mecanismo

La percepción segura descansa en contratos explícitos de privacidad antes
de tocar ninguna estadística. `Capability` prohíbe cualquier metadato que
contenga claves de identidad del sistema (`hostname`, `username`, `ip`,
`mac`, etc.) — la comprobación ocurre en construcción, no como convención
documental. `ReadingPrivacyClass` solo admite los valores `AGGREGATE` y
`NON_IDENTIFYING`: no existe una variante que permita telemetría
identificable.

Sobre esa base, `RunningStats` construye líneas base con el algoritmo de
Welford en línea — memoria constante, sin guardar el historial de muestras
crudas. `CapabilityBaseline` expone únicamente `count`, `mean`, `variance` y
`stdev`: ningún indicador de "amenaza" o "anomalía" sale de esta capa, para
que la percepción no usurpe el juicio cognitivo.

`DriftAwareBaseline` distingue tres fenómenos que un filtro adaptativo
ingenuo confunde: un pico aislado se pone en cuarentena temporal y solo se
confirma como cambio de régimen si la desviación persiste varios ticks
consecutivos en la misma dirección; un arrastre lento (*creep*) se detecta
comparando un EWMA rápido contra una desviación estándar congelada en el
momento de aclimatación, para que la varianza móvil no se infle al mismo
ritmo que la propia deriva y la vuelva invisible.

Finalmente, `AdaptiveSenseModel` decide qué señales conservar: una función
de utilidad combina disponibilidad, variabilidad y movimiento medio, y
`PairAccumulator` poda sensores redundantes cuando su correlación de
Pearson supera un umbral alto — ahorrando presupuesto de observación sin
perder información distinta.

<a id="implementado"></a>

## Qué hay implementado

- Contratos de privacidad que bloquean metadatos de identidad en
  construcción — **[implementado]**.
- Aclimatación estadística en línea (Welford) sin retención de muestras
  crudas — **[implementado]**.
- Distinción entre pico aislado, cambio de régimen y arrastre lento
  (*creep*) — **[implementado]**.
- Poda de redundancia sensorial por colinealidad de Pearson —
  **[implementado]**.
- Selección de qué candidatos entran al repertorio sensorial activo del
  organismo es un proceso continuo de todo el ciclo de vida, no una
  decisión de arranque única — cubierto en detalle en el desarrollo
  predictivo (capítulo 8).

<a id="evidencia"></a>

## Evidencia

Tres comportamientos concretos están cubiertos por pruebas deterministas:
la confirmación de un cambio de régimen requiere una racha sostenida de
desviaciones (no una sola muestra atípica); un arrastre lento constante se
confirma como `CREEP` sin disparar nunca un `REGIME_SHIFT`, incluso tras 200
ticks de deriva continua; y la línea base de aclimatación no expone ninguna
superficie de clasificación — solo estadísticos descriptivos. La poda de
redundancia sensorial también está probada: un sentido altamente
correlacionado con una señal complementaria ya presente se omite del
repertorio activo.

<a id="abierto"></a>

## Qué sigue abierto (de este mecanismo)

- Los umbrales de confirmación (racha mínima, Z de arrastre, umbral de
  correlación) son heurísticas de ingeniería, no propiedades demostradas
  óptimas — el compendio matemático las clasifica explícitamente como
  heurísticas, no como invariantes estructurales.
- La cobertura de plataformas más allá de Linux permanece con la salvedad
  histórica de verificación cruzada documentada en el roadmap; no se trata
  como bloqueante para el desarrollo en Linux.

<a id="respaldo-formal"></a>

## Respaldo formal

El desarrollo analítico completo — estabilidad numérica de Welford
univariado y bivariado, la derivación del suelo de ruido congelado para
detección de *creep*, y la función de utilidad dinámica de selección
sensorial — está en
[`docs/math/02-percepcion-aclimatacion-y-relaciones.md`](../math/02-percepcion-aclimatacion-y-relaciones.md)
y
[`docs/math/03-deteccion-de-deriva-y-regimenes.md`](../math/03-deteccion-de-deriva-y-regimenes.md).
