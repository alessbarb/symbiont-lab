# Milestone I — Fisiología integrada

## Estado

Diseño en implementación incremental. Ya existe estado fisiológico irreversible,
acoplamiento al runtime, liberación transaccional del hábitat e intake metabólico
explícito. El runtime también puede solicitar descanso de forma bounded y
checkpointable, sin reposición gratuita. La reparación runtime ya consume intake
de mantenimiento y queda cubierta por un estudio evaluator-only con replay. El
cierre requiere integrar recuperación sostenida, reproducción y los estudios de déficit definidos más
abajo.

## Propósito

Convertir los mecanismos existentes de metabolismo, homeostasis, degradación,
viabilidad, reproducción y hábitat en un sistema acoplado y observable. El
Symbiont debe poder sostenerse, recuperarse, entrar en déficit y morir por falta
de condiciones, sin que el evaluador satisfaga o fuerce ninguna necesidad.

## Principios

- La energía, la información, el mantenimiento, el espacio y la reproducción
  tienen recursos finitos y fuentes explícitas.
- La reposición metabólica no es gratuita: debe proceder de una asignación o de
  una adquisición ambiental declarada.
- Reparar, aprender, persistir, interactuar y reproducirse tienen costes.
- Dormir reduce consumo; no restaura reservas sin una fuente ambiental.
- La muerte es irreversible y libera la asignación del hábitat exactamente una
  vez.
- Ground truth y métricas del evaluador permanecen fuera de la cognición.

## Necesidades mínimas

1. **Intake:** obtener recursos autorizados del hábitat.
2. **Metabolismo:** transformar reservas en observación, cognición,
   persistencia y mantenimiento.
3. **Homeostasis:** reducir actividad y plasticidad bajo presión.
4. **Reparación:** recuperar integridad consumiendo recursos y dentro de límites.
5. **Descanso:** entrar en dormancia y reanudar actividad sin teletransportar
   microestado ni reservas. `request_rest()` expresa la decisión local; la
   presión metabólica sigue siendo la autoridad de la transición.
6. **Gestión de residuos:** degradar y excretar memoria o estado de bajo valor
   de forma bounded y trazable.
7. **Viabilidad:** distinguir activo, estresado, dormido, agonizante y muerto.
8. **Reproducción:** consumir reserva, capacidad y asignación del hábitat.
9. **Muerte:** finalizar continuidad, impedir restore de identidad muerta y
   liberar recursos de forma transaccional.

## Acoplamiento requerido

```text
hábitat y asignaciones
        ↓
adquisición → reserva metabólica → actividad / reparación / persistencia
        ↓                    ↓
    escasez              integridad
        ↓                    ↓
homeostasis → dormancia → muerte irreversible
        ↓
presión reproductiva y asignación de descendencia
```

Cada transición debe ser determinista, checkpointable y replayable. Ningún
componente puede crear reserva, integridad o capacidad fuera del contrato.

## Criterios de salida

- Una prueba de déficit sostenido produce dormancia y finalmente muerte sin
  intervención externa.
- La reparación consume recursos y no puede superar los límites declarados.
- La dormancia reduce consumo y no genera reservas de forma gratuita.
- La adquisición compite con otros consumidores dentro de la capacidad del
  hábitat.
- Reproducción y muerte actualizan capacidad y reservas exactamente una vez.
- Reinicio, replay y checkpoints conservan identidad, edad, reservas e
  integridad sin inventar microestado.
- El Observatory publica necesidades, costes y estados como observaciones,
  separadas de las decisiones del evaluador.
- Todos los límites de host, consentimiento, red, persistencia y autoridad
  permanecen invariantes.

## Orden de implementación

1. Auditar el acoplamiento actual de `MetabolicLedger` con `SharedHabitat`.
2. Introducir fuentes y consumo de recursos explícitos.
3. Integrar costes de reparación, persistencia y reproducción.
4. Cerrar dormancia, recuperación y muerte transaccional.
5. Añadir contratos de checkpoint/replay y métricas Observatory.
6. Ejecutar estudios de inanición, recuperación, competencia y extinción.

El intercambio y las relaciones entre Symbionts quedan fuera de I y se reservan
para **Milestone K — Sociabilidad emergente**.
