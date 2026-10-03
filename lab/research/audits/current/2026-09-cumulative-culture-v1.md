# Auditoría adversaria — Cumulative Culture v1

Fecha: 2026-09-17  
Protocolo: `learning.cumulative-culture` v1  
Seeds: `101, 127, 149`  
Estado: cerrada en alcance preregistrado

## Pregunta

Se auditó si la secuencia `X -> X+Y -> X+Y+Z` podía ser un artefacto del
laboratorio en vez de composición causal entre individuos.

## Controles ejecutados

- Sin transmisión: el ledger no obtiene ningún composite.
- Transmisión atómica sin composición: el ledger puede conservar tres claims,
  pero no tiene un constructo compuesto.
- Composición bounded: cada contribución procede de una claim originada en un
  ledger distinto; los composites se transmiten solo por `SocialChannel`.
- Retirement/replacement: se conservan versiones anteriores y no se reescribe
  la historia.

## Hallazgos

- **Evaluator leakage:** no se encontró. El estudio no entrega labels de roles,
  ground truth ni métricas de éxito al ledger.
- **Planificador central oculto:** no se encontró almacén cultural global. La
  composición se ejecuta sobre estado local y la recepción importa únicamente
  claims bounded referenciadas.
- **Acumulación falsa:** no se encontró. El composite final tiene tres claims,
  tres contributors y tres roots; ningún fundador empieza con las tres.
- **Inflación de roots:** no se encontró. Un composite no crea evidencia; sus
  roots son la unión de claims/padres.
- **Restore inflation:** no se encontró. Checkpoint/restore conserva exactamente
  composites, parents, costs y claims sin duplicar IDs.
- **Lineage loss:** no se encontró en `extend`, `replace`, `retire` ni en la
  entrega al recién nacido.
- **Comunicación gratuita:** no se encontró. Claims, composites, storage,
  composición y deliveries tienen contadores y ceilings bounded.
- **Herencia genética accidental:** no se encontró. El ledger del recién nacido
  se crea vacío; su composite llega solo por entrega explícita.
- **Private SLM contamination:** no se encontró. Los composites permanecen en
  `SocialEvidenceLedger`; no tienen corpus, pesos ni targets de entrenamiento.

## Resultado

El estudio obtuvo CC1–CC8 y replay `3/3` en las tres seeds. La evidencia cierra
la capacidad de composición/provenance multi-contributor bounded. La decisión
sobre qué componer y cuándo transmitir sigue siendo evaluator-side en este
protocolo; por tanto no se afirma cooperación autónoma, lenguaje o selección
cultural.
