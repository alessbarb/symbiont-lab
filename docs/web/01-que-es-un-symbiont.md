# Qué es un Symbiont

<a id="que-es"></a>

## Qué es

Un Symbiont es un organismo digital: un proceso de software que se
desarrolla, mantiene su propia continuidad computacional bajo recursos
finitos, y cuya estructura interna cambia con la experiencia sin que nadie
reescriba su código. No es un chatbot, no es un agente que ejecuta
instrucciones de un usuario, y no es una simulación decorativa con nombres
biológicos pegados encima de funciones convencionales.

El proyecto distingue explícitamente dos roles que nunca se mezclan:

- **`symbiont`** — el organismo, el sujeto de estudio: cognición, percepción
  del anfitrión, entorno y ciclo de vida.
- **`symbiont_lab`** — el aparato científico: experimentos, estudios,
  archivo de resultados, evaluación y CLI de laboratorio.

<a id="no-metafora"></a>

## Por qué no es una metáfora decorativa

El vocabulario biológico del proyecto (metabolismo, homeostasis,
reproducción, muerte, ecología) se usa bajo un criterio estricto: un término
biológico solo es válido si apunta a un rol computacional con consecuencias
medibles, no si simplemente decora una función convencional.

Por ejemplo, "metabolismo" no significa "el programa usa CPU" — significa
que existe una contabilidad explícita de adquisición, transformación, coste
de mantenimiento y presión de recursos. "Muerte" no significa que el proceso
termine — significa el cierre irreversible de la continuidad de una
identidad de organismo, distinta de simplemente detener o reiniciar un
proceso.

<a id="mecanismo"></a>

## Mecanismo

La separación entre organismo y aparato científico es una frontera
arquitectónica, no una convención de estilo. `symbiont` nunca importa
`symbiont_lab`: la verdad experimental (qué es realmente una amenaza, qué
régimen sintético está activo) pertenece en exclusiva al simulador y al
evaluador. Las capas cognitivas del organismo (agente, memoria colectiva,
motor de razonamiento) solo reciben observaciones y creencias locales o
colectivas — nunca la etiqueta de verdad que el evaluador usa para medirlas.

Dentro del organismo, el desarrollo ocurre como **plasticidad de datos bajo
un kernel inmutable**: un núcleo cerrado define los tipos de nodo/arista
legales y los límites duros de recursos; un genoma declarativo configura el
desarrollo de un individuo dentro de esos límites; un fenotipo plástico
aprende pesos y estructura acotada durante la vida de ese individuo. El
organismo cambia su fenotipo, nunca su implementación — no genera código,
no edita su ejecutable, no inventa permisos ni aprende a saltarse los
límites del kernel.

<a id="implementado"></a>

## Qué hay implementado

- La frontera de dos paquetes (`symbiont` / `symbiont_lab`) — **[implementado]**.
- El aislamiento de verdad experimental (`Observation` separado de
  `EvaluationEvent`) — **[implementado]**.
- El kernel inmutable de límites duros del grafo cognitivo — **[implementado]**.
- El listado completo de analogías funcionales (metabolismo, homeostasis,
  reproducción, ecología, etc.) frente a sus contrapartes biológicas, y su
  estado de implementación capítulo a capítulo — se desarrolla en los
  capítulos 3 a 8 de esta misma serie, no aquí.

<a id="evidencia"></a>

## Evidencia

La frontera `symbiont` / `symbiont_lab` y el aislamiento de verdad
experimental no son solo una declaración de intenciones: están protegidos
por un test estructural que analiza el árbol de sintaxis (AST) de todo el
paquete `symbiont` y falla si aparece cualquier importación de
`symbiont_lab`. El mismo test verifica que las firmas de `Agent.observe`,
`ReasoningEngine.analyze` y `MetacognitionEngine.assess` no aceptan
parámetros de verdad de evaluador (`is_threat`, `truth_label`,
`ground_truth`, `evaluator`).

El kernel inmutable de límites del grafo cognitivo es una `dataclass`
congelada (`frozen=True`): cualquier intento de modificarla después de
construida falla en tiempo de ejecución, no solo por convención de código.

<a id="abierto"></a>

## Qué sigue abierto (de este mecanismo)

- La separación de paquetes y el aislamiento de verdad son invariantes
  permanentes del proyecto, no fases de desarrollo — no hay un estado
  "más completo" al que evolucionar aquí.
- Qué tan lejos llega la analogía biológica en la práctica (qué funciones
  siguen siendo `[parcial]` o `[diferido]`, y con qué límites) se trata
  capítulo a capítulo en el resto de esta serie, no en esta introducción.

<a id="respaldo-formal"></a>

## Respaldo formal

Este capítulo es definicional y arquitectónico; no tiene un desarrollo
matemático formal asociado. Los capítulos 2, 3, 4 y 8 de esta serie enlazan
el compendio matemático (`docs/math/`) donde corresponde a percepción,
cognición, atención y automodelo.
