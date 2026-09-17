# Metodología y límites

<a id="que-es"></a>

Este capítulo es transversal: no sigue el espinazo fijo de los capítulos
1-8. Aquí se documenta cómo se genera la evidencia citada en el resto de la
serie, y qué límites de generalización aplican a través de todos los
mecanismos, en vez de repetir la misma advertencia ocho veces.

<a id="metodologia"></a>

## Metodología experimental

La experimentación sintética del proyecto sigue cinco principios fijos:

1. **Aislamiento determinista de flujos de RNG** — la aleatoriedad no
   relacionada nunca debe interferir entre sí; los flujos se derivan vía
   SHA-256 con espacios de nombres separados.
2. **Integridad de prefijo causal en atención** — los selectores de
   atención procesan eventos secuencialmente y nunca pueden mirar
   puntuaciones futuras ni resultados globales.
3. **Observación solo-sombra** — los ganchos experimentales del
   observador (presupuestos retrospectivos, sensores contrafactuales)
   operan estrictamente en modo sombra: nunca perturban las acciones del
   agente, la memoria colectiva ni el estado del mundo.
4. **Diseños replicados pareados** — los estudios multisemilla preservan el
   emparejamiento por mundo/semilla entre intervenciones comparadas, para
   maximizar poder estadístico y eliminar sesgo de varianza inter-mundo.
5. **Razonamiento explicativo, no operacional** — las hipótesis generadas
   internamente cumplen una función interpretativa de búsqueda de
   información, nunca disparan acciones operacionales externas.

<a id="preregistro"></a>

## Pre-registro y auditorías

Los protocolos se declaran formalmente antes de la recolección de datos
(`research/protocols/`), y los estudios de replicación se especifican de
forma declarativa (`research/studies/`) antes de ejecutarse. Las auditorías
adversariales (`research/audits/`) verifican la integridad experimental del
propio simulador y aparato de laboratorio — no solo miden al organismo,
sino que también intentan encontrar fallos metodológicos en cómo se mide.

Por ejemplo, la auditoría de la versión v0.13.0 documenta explícitamente
una corrección de procedencia descubierta durante el propio análisis: un
archivo de replicación resultó pertenecer a un commit distinto del
declarado, y esa discrepancia se registra y se separa de la tabla principal
en vez de mezclarse silenciosamente. Esto es deliberado: el proyecto trata
los errores de procedencia de datos como hallazgos que se documentan, no
como ruido que se descarta.

<a id="limites-transversales"></a>

## Límites transversales de generalización

Estos límites aplican a través de todos los mecanismos descritos en los
capítulos 1-8, no a uno solo:

- **La emergencia autónoma multi-organismo** (ecología, sociabilidad) está
  medida únicamente en arneses evaluator-only del laboratorio, bajo
  regímenes sintéticos controlados. No hay evidencia de que ese
  comportamiento se generalice a producción sin supervisión de laboratorio.
- **La promoción de predictores** en el ciclo de desarrollo predictivo es
  una operación explícita y acotada; su generalización fuera de los
  regímenes estudiados permanece abierta.
- **La cobertura multiplataforma** más allá de Linux conserva una salvedad
  histórica de verificación cruzada, documentada como limitación de
  verificación, no como bloqueante de desarrollo.
- **Ningún estudio de laboratorio retroalimenta la cognición del
  organismo**: las métricas del evaluador, incluidas las de este mismo
  capítulo, existen para medir desde fuera, nunca para enseñar desde
  dentro — es la misma frontera epistemológica del capítulo 1, aplicada
  ahora a la metodología que produce la evidencia citada en toda la serie.

<a id="respaldo-formal"></a>

## Respaldo formal

Los cinco principios metodológicos están en
[`docs/methodology/README.md`](../methodology/README.md). Los protocolos
pre-registrados viven en `research/protocols/`, los estudios declarativos
en `research/studies/`, y las auditorías adversariales en
`research/audits/`.
