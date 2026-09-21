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
