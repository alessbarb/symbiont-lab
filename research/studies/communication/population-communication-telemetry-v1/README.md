# Population Communication Telemetry v1

## Estado

Implementada y validada localmente en la rama posterior a `v0.80.16`.
Esta fase no modifica la selección de símbolos, los mensajes, los receptores,
el grounding ni la política cultural. `v0.80.16` permanece congelada.

## Pregunta y alcance

La línea comprueba si el Observatory puede reconstruir hechos comunicativos
poblacionales reales a partir de una fuente explícita, bounded y outbound-only.
No reconstruye relaciones históricas desde snapshots individuales ni atribuye
significado a IDs opacos.

Se mantienen separadas tres capas:

1. **Organism state**: conocimiento y grounding local del Symbiont.
2. **Population telemetry**: eventos factuales de entrega y actualización de
   grounding.
3. **Evaluator analytics**: agregados y análisis científicos derivados fuera
   del organismo.

## Implementación

`CommunicationTelemetry` conserva eventos y grounding events en buffers
bounded, con deduplicación, pruning por edad/capacidad, exportación y
checkpoint/replay deterministas. El canal registra una entrega solamente
después de que el receptor real la acepta; el ledger de grounding registra el
cambio local observado. Los errores del sink observacional no cambian la
entrega ni el aprendizaje.

El agregador del Observatory usa únicamente eventos exportados. Las aristas
se construyen desde `DELIVER`, `RECEIVE` y `RETRANSMIT`; no se infieren aristas
por proximidad temporal, identidad o presencia de un snapshot. La truncación
se conserva y se muestra como límite de historia disponible.

Las vistas son pasivas: Communication Live, Population Communication Graph,
Convention Explorer, Emergence Timeline, grounding y perfiles de recién
nacidos. Los mensajes siguen siendo IDs opacos o aliases visuales reversibles.

## Estudio observacional

`observability.population-communication` usa el canal real en una cadena
autorizada `A → B → C → D`, con retransmisiones posteriores y actualizaciones
de grounding locales. Para cada seed (`101`, `127`, `149`) se registran tres
eventos de entrega, tres eventos de grounding, las tres aristas observadas y
la restauración determinista del buffer. El escenario no pretende demostrar
una capacidad cognitiva nueva; valida reconstrucción y límites de telemetría.

## Validación y límites

La batería específica pasa y el estudio reproduce exactamente la cadena
exportada. La suite completa debe ejecutarse en el checkout final antes de
publicar un cierre del milestone. La QA visual requiere servidor y navegador
locales; si no están disponibles, debe registrarse como limitación de
infraestructura y no como evidencia funcional.

La telemetría solo garantiza historia dentro del buffer disponible. Por ello
`first_seen` se interpreta como primer evento disponible cuando el historial
está truncado, no como origen absoluto. No se afirma intención, enseñanza,
liderazgo, significado o causalidad más allá de los eventos exportados.
