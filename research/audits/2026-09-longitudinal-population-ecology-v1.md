# Adversarial audit — Longitudinal Population Ecology v1

## Scope

Auditoría de la campaña de larga duración, no auditoría de una capacidad nueva.

## Checks

- El diff no modifica `src/symbiont` ni las políticas de aprendizaje,
  comunicación, cultura, fitness o reproducción.
- El estudio usa callbacks de snapshot del simulador existente y el protocolo
  social-runtime existente; no introduce mensajes, labels, rewards ni planner.
- Cada stage tiene ceilings explícitos y detecta valores no finitos, contadores
  inválidos, ticks no monotónicos y divergencia de replay.
- La telemetría existente sigue siendo bounded y su truncamiento no se presenta
  como historia absoluta.
- Observatory permanece consumidor pasivo; no hay ruta de feedback.
- La ausencia de integración real entre simulador canónico, generaciones,
  comunicación y Private SLM está documentada como limitación.
- Un crash de proceso no se registra como extinción poblacional.

## Resultado

No se ejecuta ninguna afirmación científica confirmatoria desde la campaña de
discovery. La lista de fenómenos candidatos permanece vacía hasta que un
análisis de resultados real justifique registrar uno con sus alternativas.
