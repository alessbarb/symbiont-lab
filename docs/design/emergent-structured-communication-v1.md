# Emergent Structured Communication v1

> Give Symbionts capabilities and constraints, not linguistic answers.

Esta fase sustituye el diseño prescriptivo de Proto-language v1 antes de su
ejecución científica. Conserva únicamente el sustrato general de mensajes,
grounding local, costes, límites y replay; no conserva slots, roles, gramática,
pares objetivo ni objetivos de composicionalidad.

## Principio operacional

**WE PROVIDE:** channel, symbols, memory, cost, limits, experience.

**WE DO NOT PROVIDE:** meaning, grammar, roles, composition, syntax, optimal
messages.

El canal permite `SILENCE`, un símbolo o una secuencia de longitud variable
bounded (máximo 4 en el baseline). Los símbolos son IDs opacos y el receptor
solo crea asociaciones tras exposición y experiencia local. La política vive en
`symbiont.modeling`; el laboratorio fija únicamente contactos, recursos,
condiciones y métricas evaluator-side.

## Contratos y fronteras

`SymbolSequence`, `SequenceMessage`, `SequenceDecisionRecord` y
`SequenceGroundingLedger` son serializables y no contienen labels de mundo,
roles ni traducciones. La asociación es exacta al mensaje recibido: no existe
un camino privilegiado que factorice posiciones o premie reutilización. El
ledger de secuencias es separado del ledger privado del SLM y no transfiere
pesos, corpus ni adapters. La descendencia empieza sin asociaciones.

Las decisiones conservan digest de candidatos, estado local, receptor elegido,
coste y tick. Las oportunidades de contacto son control experimental; el
contenido no lo selecciona el harness. Observatory expone solo estado pasivo.

## Estudio preregistrado

`learning.emergent-structured-communication` compara `NO SIGNAL`, `RANDOM
SIGNAL` y `AUTONOMOUS UNSTRUCTURED CHANNEL` en seeds `101, 127, 149`, con
vocabulario opaco, longitud variable y coste bounded. El análisis de estructura
(holístico, parcialmente estructurado o productivo) se realiza después sobre
trazas y nunca entra en la política. No se fuerza un holdout ni una solución
factorial: si el código es holístico o no funciona, ese resultado se conserva.

La condición autónoma no recibe mapping de significado, secuencia objetivo,
roles, slots, etiquetas latentes ni ground truth. La permutación de IDs es un
control de arbitrariedad, no una ruta de entrenamiento privilegiada.

## Estado

La capacidad está implementada y el estudio base fue ejecutado localmente en
las tres semillas preregistradas. El cierre es funcional y acotado: la
comunicación autónoma fue útil, no trivial y replay-safe. No se observó ni se
afirma productividad composicional; esa propiedad no es un requisito
arquitectónico y queda fuera del cierre.
