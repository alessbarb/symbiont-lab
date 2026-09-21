# Resultado

Ejecución reproducida el 2026-09-21 con `seeds=(101, 127, 149)` y
`ticks=200`:

| capacidad | tasa |
|---|---:|
| descubrimiento de las dos relaciones locales | 1,00 |
| composición directa a dos pasos (`x → y`) | 0,00 |
| discriminación de intervención frente a persistencia | 0,00 |
| revisión tras contradicción | 0,00 |
| reutilización en un contexto con escala y trayectoria nuevas | 1,00 |
| replay determinista | 1,00 |

Los pesos de la relación `m → y` no revisaron su signo tras invertir la
consecuencia:

```text
101: 1.006209 -> 1.016730
127: 1.006322 -> 1.016083
149: 1.006330 -> 1.016287
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
- **Invalidado para la versión actual:** salto temporal compuesto, distinguir
  correlación de intervención y revisión de una creencia predictiva ante una
  contradicción.

Por ello todavía no procede promover el CognitiveGraph actual a un modelo
causal general ni sustituirlo por una red neuronal sin diseñar antes un nuevo
experimento que aporte explícitamente esos mecanismos como hipótesis
plásticas, no como semántica precargada.
