# Cumulative Culture v1

## Alcance

Cumulative Culture v1 añade composición cultural bounded sobre el DAG de
`SocialClaim` de Cultural Foundation v1. Un `CulturalComposite` es una versión
inmutable, content-addressed y serializable de una construcción cultural; no es
una observación, no crea una root y no puede convertirse automáticamente en
experiencia privada o target de Private SLM.

La superficie implementada vive en `symbiont.modeling.culture`. El transporte
sigue siendo `SocialChannel`, en memoria y autorizado explícitamente por el
laboratorio. No hay sockets, peers, almacén global, pesos, adapters, corpus ni
telemetría raw.

## Contrato e invariantes

Un composite conserva:

- `component_claim_ids`, con límite de 32;
- `parent_composite_ids`, con DAG y límite de 8;
- `contributing_organism_ids`, bounded y derivados de `source_organism_id`;
- `root_evidence_ids`, unión de las roots de sus claims y padres;
- `generation`, calculada como sucesor de sus padres;
- operación bounded (`combine`, `extend`, `refine`, `replace`, `contradict`, `retire`);
- tick de creación y estado de retirada.

La identidad se deriva del payload canónico. Duplicados, colisiones, padres
inexistentes, ciclos, componentes desconocidos, generaciones inválidas y
excesos de capacidad fallan cerrado. Componer nunca añade una evidencia nueva:
el composite es un artefacto cultural, no una raíz epistemológica.

`replace` conserva el composite erróneo como ancestro y crea una nueva versión
que excluye explícitamente el componente sustituido. `retire` crea una versión
terminal retirada; la genealogía permanece disponible y el constructo actual
puede quedar vacío. La descendencia clonal materializa un ledger social vacío:
la adquisición cultural ocurre solo por claims/composites transmitidos.

## Transmisión y costes

Un composite puede transportarse a través de un par autorizado. El receptor
adquiere únicamente los claims bounded referenciados y sus ancestros causales,
y valida que el composite coincide byte a byte con el ledger emisor. No puede
leer el estado privado completo del emisor. El ledger cobra recepción,
storage y composición; el canal cobra entregas y conserva sus ceilings.

El Observatory expone pasivamente counts, contributors, generations, roots y
lineage. Nunca edita, confirma, borra, compone ni retransmite cultura.

## Diseño científico

`learning.cumulative-culture` fue preregistrado antes de ejecutar con seeds
`101, 127, 149` y 128 ticks. El protocolo compara:

1. sin transmisión;
2. claims atómicas transmitidas sin composición;
3. composición bounded;
4. ablaciones evaluator-side sin romper invariantes internas.

La condición acumulativa usa tres superficies de experiencia distintas: una
claim X, una claim Y y una claim Z. Ningún ledger fundador recibe el producto
final antes del intercambio. La secuencia observada es `X -> X+Y -> X+Y+Z`;
después los fundadores desaparecen, un ledger nacido posteriormente recibe el
composite y añade W. La utilidad se mide como capacidad operacional del
constructo de tres componentes frente al control de transmisión atómica sin
composición. El laboratorio no entrega labels de roles, truth ni éxito al
organismo.

## Límites de interpretación

El estudio cierra el mecanismo de composición y sus propiedades causales en el
alcance autorizado. La selección de qué claims componer y cuándo transmitir
está controlada por el arnés del estudio; no se presenta como cooperación
autónoma emergente. No se implementan lenguaje, símbolos, prestigio,
conformidad, selección cultural ni entrenamiento SLM con claims sociales.

La persistencia, complejidad, utilidad y apoyo epistemológico siguen siendo
variables distintas. Una versión más compleja o más persistente puede contener
error; el protocolo incluye contradicción, replacement, retirement y replay para
hacer visible esa posibilidad.
