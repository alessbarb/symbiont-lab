# Estado de investigación

Corte: `v0.76.9`.

Este registro clasifica el estado de la evidencia; no sustituye al roadmap ni
convierte un resultado exploratorio en una afirmación de capacidad.

## Implementado y validado

- Contratos y límites de `symbiont` y Observatory cubiertos por sus suites de
  pruebas correspondientes.
- Estudios de aceptación de conocimiento de señales: límites del kernel,
  proyección acotada y separación organismo/evaluador verificadas en la partición
  sintética descrita en [`signal-knowledge-study.md`](signal-knowledge-study.md).
- Auditorías históricas v0.13–v0.24 reproducibles desde sus commits congelados,
  con procedencia y restricciones documentadas individualmente.

## Implementado con validación parcial

- Capacidades de fisiología, herencia y ecología de `v0.60–v0.76`: el contrato y
  las pruebas del repositorio están implementados; la evidencia científica no
  equivale a una caracterización exhaustiva de todos los regímenes.
- Observatory: la suite de contratos e integración pasa, pero no constituye QA
  visual exhaustivo ni medición de RSS en producción.
- Intercambio ecológico: transporte local en memoria validado; sockets, red y
  descubrimiento de pares siguen fuera de alcance.

## Diseñado pero no implementado

- Cualquier frontera posterior al Milestone H.
- Nuevas capacidades de comunicación real o acciones sobre el host.
- Estudios congelados bajo `research/studies/`: el directorio conserva el formato,
  pero todavía no contiene una carpeta cerrada con manifest, resultados y hashes.

## Diferido o requiere nuevo consentimiento

- Escrituras del host, remediación, ejecución de comandos, inspección de procesos,
  credenciales, escaneo de red, propagación y auto-instanciación.
- Toda ampliación del residente que cambie de observación pasiva a control activo.

## Regla de cierre

Una tarea de investigación solo se puede mover a **implementado y validado** si
conserva procedencia, separa evaluación de cognición, declara su matriz y tiene
una validación reproducible. Una suite verde aislada no basta para cerrar un
estudio.
