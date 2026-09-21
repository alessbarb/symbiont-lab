# Resultado

Ejecución reproducida el 2026-09-21 con diez semillas
`(101, 127, 149, 173, 211, 257, 307, 353, 401, 457)` y `ticks=200`:

| capacidad | tasa |
|---|---:|
| descubrimiento de las dos relaciones locales | 1,00 |
| composición directa a dos pasos (`x → y`) | 0,00 |
| detección en sombra de una relación con retardo fijo de dos ticks | 1,00 |
| discriminación de intervención frente a persistencia | 0,30 |
| revisión tras contradicción | 0,00 |
| reutilización en un contexto con escala y trayectoria nuevas | 1,00 |
| replay determinista | 1,00 |

Los pesos de la relación `m → y` no revisaron su signo tras invertir la
consecuencia:

```text
101: 1.000128 -> 1.011824
127: 1.000746 -> 1.006644
149: 1.000842 -> 1.009937
```

El gate global es `full_capability_supported=false`. El resultado no dice que
sea imposible construir un CognitiveGraph con esas capacidades; demuestra que
el sustrato actual, con su aprendizaje local disponible y sin información
externa, no las produce.

## Lectura conjunta

Este resultado, combinado con `learning.predictive-discovery`, separa dos
afirmaciones que no deben mezclarse:

- **Validado:** descubrimiento de predictores de un paso y selección frente a
  decoys.
- **Validado en sombra:** una memoria temporal acotada puede detectar que
  `x[t-2]` predice `y[t]`, sin mutar el `CognitiveGraph`. Esto demuestra
  representación de un retardo fijo, no composición causal ni una creencia
  revisable.
- **Invalidado para la versión actual:** salto temporal compuesto, distinguir
  correlación de intervención y revisión de una creencia predictiva ante una
  contradicción.

Por ello todavía no procede promover el CognitiveGraph actual a un modelo
causal general ni sustituirlo por una red neuronal sin diseñar antes un nuevo
experimento que aporte explícitamente esos mecanismos como hipótesis
plásticas, no como semántica precargada.
