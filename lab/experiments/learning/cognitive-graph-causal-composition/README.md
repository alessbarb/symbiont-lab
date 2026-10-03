# CognitiveGraph: composición temporal y revisión causal

Este experimento presenta canales escalares opacos. El aparato conoce la
estructura latente sólo para evaluar el resultado; el organismo no recibe
objetivos, recompensa, semántica, marcadores de fase ni ground truth.

Se evalúan cuatro capacidades separadas:

1. descubrir `x → m` y `m → y` como relaciones de un paso;
2. formar una relación directa `x → y` a dos pasos, que requiere composición;
3. distinguir una correlación observacional `a ~ y` cuando `a` se interviene
   sin cambiar `y`;
4. revisar `m → y` cuando la consecuencia se contradice.

Ejecución:

```bash
symbiont-lab experiment run experiments/learning/cognitive-graph-causal-composition/experiment.toml
```

El resultado actual pasa la capacidad local, pero no las tres capacidades
fuertes. Eso invalida la afirmación amplia para el CognitiveGraph actual; no
invalida que una futura arquitectura pueda aprenderlas.


## Purpose

This README defines this location's scope within the experiment hierarchy.

## Belongs here

Protocols, configuration, documentation, and identifiable results from reproducible runs.

## Does not belong here

No pytest-collectable tests, production code, or final scientific interpretation.

## Criterion for creating a file

Add only a file that records a reproducible protocol element, an execution, or a result; mechanical contracts belong in `tests/experiments/`.

## Execution

Use the explicit command documented by the protocol or CLI; do not execute this folder through pytest.

## Limits

The contents are evidence bounded by the protocol and do not demonstrate generalization by themselves.
