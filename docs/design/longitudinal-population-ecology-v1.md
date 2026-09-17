# Longitudinal Population Ecology v1

> Do not build the phenomenon. Let the existing organism run and observe what emerges.

Esta fase es una campaña de descubrimiento evaluator-side. No añade capacidades
a `symbiont`: no cambia aprendizaje, fitness, reproducción, política cultural,
comunicación, modelos privados ni acciones. Reutiliza el simulador canónico para
ejecuciones largas y el estudio de lifecycle social ya existente para un sondeo
multigeneracional separado.

## Alcance honesto

El simulador canónico (`run_simulation`) mantiene una población fija de agentes y
no contiene un bucle de nacimiento/muerte. El runtime social sí dispone de un
protocolo bounded de budding, muerte, liberación y replay (`social_runtime_generations`).
Por eso esta versión no presenta como una única ejecución integrada lo que el
repositorio todavía expone como dos superficies distintas. La integración
multigeneracional de comunicación y Private SLM queda como limitación técnica,
no se resuelve añadiendo una feature experimental.

## Preregistro y protocolo

El preregistro está en
`experiments/learning/longitudinal-population-ecology/experiment.toml`.
Usa seeds `101, 127, 149`, población de cuatro agentes y stages `1,000` y
`10,000` ticks. Los stages posteriores de `50,000` y `100,000` están diferidos:
solo se ejecutan después de revisar estabilidad y coste. Cada stage se ejecuta
dos veces con el mismo seed como control de determinismo; no se comparan los
macro-resultados entre seeds como si debieran coincidir.

Se registra finitud numérica, límites de contadores, pasos monotónicos, RSS
máximo observado, tamaño de snapshots y equivalencia de replay. El estudio
multigeneracional existente se reporta en un bloque separado con ocho
generaciones. La muerte por reglas válidas se distingue de un crash técnico.

## Discovery, no confirmación

Los artefactos de resultados solo describen observaciones del protocolo. Los
fenómenos candidatos se registran con estado `OBSERVED` o `NEEDS_REPLICATION`;
ningún patrón descubierto se convierte en claim confirmado usando estos mismos
datos. La confirmación requiere un nuevo preregistro con semillas independientes,
controles y análisis congelados antes de ejecutarse.

## Boundedness y seguridad

Los límites son `MAX_STAGE_TICKS=100000`, `MAX_HOSTS=32`, `MAX_GENERATIONS=50`.
No se guardan trazas raw largas en Git. No se abren sockets, descubrimiento de
peers, acciones host ni canales Observatory→runtime. Las vistas Observatory
consumen snapshots/telemetría existentes de forma pasiva.
