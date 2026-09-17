# Emergent Symbol Grounding v1

## Scope

Esta fase estudia una convención simbólica opaca y bounded, no lenguaje. El espacio
`symbol.<digest>` no contiene semántica humana ni una tabla `símbolo -> significado`.
El organismo emisor decide localmente entre silencio y una señal; el receptor solo
actualiza su `SymbolGroundingLedger` después de exposición y experiencia local.

El transporte es `SymbolChannel`, un canal autorizado en memoria. No hay red real,
descubrimiento de peers, payload ejecutable, transferencia de pesos ni corpus.
Ground truth y la relación latente evento/resultado existen únicamente en el
estudio evaluator-side para medir el efecto; nunca entran en la política.

## Contratos

- `SymbolPolicy` produce decisiones locales bounded, con coste, candidatos y digest
  del estado disponible.
- `SymbolGroundingLedger` conserva exposiciones, asociaciones, soporte,
  contradicción, freshness implícita por tick y olvido checkpointable.
- `SymbolMessage` conserva emisor, receptor, tick y profundidad; la propiedad del
  receptor y los pares autorizados se validan fail-closed.
- La descendencia recibe una ledger simbólica vacía: hereda capacidad y seed, no
  significados ni historial.
- Observatory expone solo IDs opacos, contadores y bins de soporte; no expone el
  token de outcome como traducción de significado y permanece pasivo.

## Estudio preregistrado

`learning.emergent-symbol-grounding`, seeds `101, 127, 149`, compara `none`,
`random`, `autonomous` y `permuted`. `directed_label` queda fuera del tratamiento
y, si se usa, es solo un upper-bound metodológico. Los criterios ESG1--ESG10 y
replay están fijados en `experiments/learning/emergent-symbol-grounding/experiment.toml`.

La condición permutada cambia las identidades en el canal y comprueba que el
receptor puede reaprender la asociación sin depender de la grafía del símbolo.
La condición random recibe señales sin el proceso emisor autónomo y sirve como
control de separación, no como evidencia positiva.

## Resultado

Con las semillas preregistradas `101, 127, 149`, ESG1–ESG10 y replay pasaron.
La utilidad predictiva autónoma fue `0.125`, `0.3125` y `0.4375`; el control
random fue `-0.1875`, `0.0` y `-0.1875`. La condición permutada mantuvo utilidad
de `0.125`, `0.3125` y `0.4375`. La adquisición newborn ocurrió en `2`, `2` y
`1` ticks. El resultado queda cerrado solo en este alcance y no se extiende a
lenguaje, gramática o semántica humana.

## Criterio de interpretación

Pasar los gates demostraría únicamente una convención simbólica grounded en el
alcance del protocolo: una señal opaca elegida por organismos puede adquirir
utilidad predictiva y transmitirse más allá del fundador. No demostraría lenguaje,
gramática, semántica humana ni composición de secuencias.
