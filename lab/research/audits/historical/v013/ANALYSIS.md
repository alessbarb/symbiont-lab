# Auditoría experimental de Symbiont Lab

## Alcance y evidencia

Estudio exploratorio sobre v0.13.0, commit `6edb4c2`. No se modifica el motor.
Primera ronda: 10 condiciones × 5 semillas × 100 hosts × 300 pasos.
La primera ronda contiene 50 simulaciones y 1.500.000 observaciones.
**Corrección de procedencia:** `replication.jsonl` registra ya el commit
`b85b7fb` (v0.14), no v0.13. Sus 15 simulaciones de una sola generación
se conservan por separado y no se agregan a la tabla de esta auditoría.
La evaluación específica de herencia está en `V014-ANALYSIS.md`.
Las semillas, parámetros, conteos individuales y hashes están en
`results.jsonl` y `replication.jsonl`; no son datos de endpoints reales.

## Resultados de la primera ronda

Promedios entre cinco semillas. “Atención” es la proporción de amenazas
investigadas. “Precisión atención” es la fracción de investigaciones que recae
sobre amenazas. “FPR atención” usa todos los eventos benignos como denominador.
“Recall clasificación” usa la decisión `believes_threat`, no la investigación.

| Condición | Atención | Precisión atención | FPR atención | Recall clasificación |
|---|---:|---:|---:|---:|
| baseline | 52.80% | 59.28% | 0.54% | 23.26% |
| fixed_trust | 55.51% | 59.02% | 0.58% | 23.27% |
| homogeneous | 47.10% | 66.93% | 0.35% | 15.38% |
| neutral_collective | 73.71% | 26.97% | 2.99% | 15.12% |
| no_curiosity | 45.81% | 67.95% | 0.32% | 24.81% |
| no_drift | 51.51% | 65.47% | 0.43% | 22.09% |
| no_poison | 47.98% | 60.30% | 0.50% | 19.72% |
| no_threats | N/A | N/A | 0.56% | N/A |
| poison_30 | 51.08% | 55.16% | 0.64% | 19.76% |
| strong_drift | 53.75% | 46.21% | 0.94% | 24.12% |

### Desglose base por tipo de evento

Conteos agrupados de las cinco semillas, no promedios de porcentajes.

| Tipo | Eventos | Investigados | Clasificados como amenaza |
|---|---:|---:|---:|
| benign:backup | 2232 | 107 | 3 |
| benign:build | 1736 | 417 | 38 |
| benign:normal | 140138 | 0 | 0 |
| benign:update | 3682 | 278 | 28 |
| pathogen:bot_sim | 733 | 474 | 163 |
| pathogen:ransom_sim | 899 | 694 | 353 |
| pathogen:stealth_sim | 580 | 1 | 0 |

## Interpretación y límites

### 1. El punto ciego principal es `stealth_sim`

Baseline investiga 1/580 eventos stealth y clasifica 0/580 como amenaza.
Incluso sin creencia colectiva solo investiga 11/580. No basta con atribuir
el problema a una población que “reprime la curiosidad”: las observaciones y
la función local de atención apenas distinguen ese generador sintético.
Es una limitación de este escenario, no evidencia sobre amenazas reales.

### 2. Curiosidad y conocimiento colectivo tienen costes y beneficios distintos

Retirar curiosidad reduce el recall de atención de 52.80% a 45.81%, pero eleva
su precisión de 59.28% a 67.95%. El recall de clasificación aumenta ligeramente,
de 23.26% a 24.81%. Por tanto, “investigar más” no demuestra “comprender mejor”.

Neutralizar probabilidad y certeza colectivas eleva la atención a 73.71%, pero
reduce su precisión a 26.97% y aumenta FPR de 0.54% a 2.99%. Esta ablación modifica
también incertidumbre y curiosidad; no identifica el efecto aislado de cada término.
No recomiendo eliminar ni el colectivo ni la curiosidad basándome en esto.

### 3. La reputación discrimina reporteros, pero eso no prueba utilidad defensiva

Con reputación fija el recall de atención sube de 52.80% a 55.50%; el recall de
clasificación prácticamente no cambia. Un `trust_gap` positivo no basta para
concluir que recalibrar confianza mejora la tarea.

Diagnóstico sintético reproducible en `diagnose_trust.py`: cinco reporteros,
cuatro votos positivos y uno negativo, sin nueva información. Tras 50 llamadas,
la confianza de la mayoría pasa de 0.75 a 0.949 y la del disidente a 0.203.
El código vuelve a asimilar el mismo consenso en cada paso, sin evidencia nueva.
Además, una única fuente con cuatro reportes obtiene certeza 0.6475 y ninguna
pregunta abierta. Esto muestra dependencia de consenso/frecuencia, no veracidad.

### 4. La prueba de deriva no demuestra adaptación explícita

La deriva fuerte reduce precisión de atención a 46.21%, con FPR 0.94%.
En las cinco ejecuciones base y las cinco de deriva fuerte, `drift_adaptations`
es cero. Esto se refiere a la rama explícita de adaptación; el baseline puede
seguir aprendiendo por sus actualizaciones normales. No debe presentarse el
contador como evidencia de recuperación. La ventana “recent” contiene 200
observaciones benignas de hosts afectados, no 200 pasos por host.

### 5. Misma semilla no siempre equivale al mismo mundo

Las ablaciones y la condición homogénea conservan el hash completo de eventos
para las cinco semillas iniciales. Cambiar `poison_fraction` altera el consumo
del RNG en `_make_agents`, antes de generar eventos: la comparación cambia
reporteros y también realizaciones de la ecología. Eliminar deriva modifica
el muestreo de hosts y desplaza el RNG posterior.

Cambiar magnitud de deriva también cambia el hash, pero ahí cambiar las
observaciones es parte de la intervención y no cambia el número de extracciones
aleatorias. No todos los hashes diferentes implican el mismo problema.
Se necesitan RNG separados y/o reproducción explícita para aislar efectos.

### 6. Hay mecanismos sin retorno hacia la decisión

`Agent.observe` almacena episodios y conceptos, pero `assess` no los consulta.
Investigar registra y reporta la creencia ya calculada; no obtiene una nueva
medición que pueda refutarla. Reasoning, probes y metacognición producen salidas
observacionales, no acciones de aprendizaje. Esta separación es segura, pero
no permite afirmar todavía que exista aprendizaje activo o memoria útil para
resolver ambigüedad. Ampliar esos módulos sin una prueba causal añadiría
complejidad sin evidencia de mejora.

### 7. Calibración y confianza requieren una definición consistente

`calibration_error` es la diferencia absoluta entre exactitud agregada y media
de `1 - uncertainty`: no agrupa predicciones por intervalos y puede ocultar
compensaciones entre subpoblaciones. Brier usa una probabilidad construida con
`0.5 ± 0.5 * confidence`, mientras esa diferencia compara directamente
`confidence` contra acierto; no usan la misma confianza de clase predicha.

`blind_spot_rate` solo cuenta fallos con confianza >= 0.65: neutralizar el
colectivo lo lleva a cero pese a seguir perdiendo amenazas stealth. “Cero puntos
ciegos” sería una lectura falsa. La confianza que produce `interpretation.py`
es heurística, no un intervalo estadístico ni una probabilidad de replicación.

## Mejoras priorizadas: propuestas, no cambios implementados

1. **P0 — Corregir el contrato de evaluación.** Separar atención, clasificación
   y adquisición de evidencia. Mostrar matrices de confusión por familia,
   fase temporal y estado de deriva; tasas sin denominador como N/A. Mantener
   compatibilidad de nombres existentes mediante etiquetas explícitas.
2. **P0 — Comparaciones controladas.** Separar RNG de ecología, perfiles,
   reporteros y diversidad. Guardar secuencias o hashes de etiquetas/observaciones
   por separado. Exigir igualdad del mundo para ablaciones de agentes.
3. **P1 — Comparar a presupuesto de atención equivalente.** Curvas de recall
   y precisión frente a investigaciones por 1.000 eventos; medir recall stealth
   y gasto en builds/updates. Congelar parámetros antes de evaluar semillas
   reservadas. No optimizar únicamente el promedio global.
4. **P1 — Dar contenido a investigar, solo dentro del simulador.** Probar una
   medición sintética adicional, ruidosa y con coste, accesible por una interfaz
   perceptiva, nunca entregando `truth_label` o `is_threat` al agente. Comparar
   contra selección aleatoria y por riesgo al mismo coste. Esta es la prueba
   mínima de si la curiosidad adquiere información útil.
5. **P1 — Reputación basada en evidencia nueva.** Evitar reutilización ilimitada
   del mismo voto; exigir diversidad mínima para cerrar preguntas. Comparar
   confianza fija, consenso actual y versión incremental ante mayoría honesta,
   disidencia correcta y colusión sintética. No usar verdad del evaluador para
   entrenar reputación dentro del agente.
6. **P2 — Memoria y deriva con prueba causal.** Primero incorporar escenarios
   temporales de recurrencia y cambios sostenidos; luego comparar memoria
   consultada/no consultada y adaptación habilitada/deshabilitada. Medir tiempo
   de recuperación y contaminación por anomalías, no solo número de episodios.

La siguiente implementación mínima recomendada es P0 (evaluación y RNG), antes
de nuevos módulos “cognitivos”. Después, P1 de presupuesto y percepción adicional.
Los experimentos de esta carpeta no han modificado umbrales ni comportamiento
persistente del motor, y no validan ninguna de estas propuestas como mejora aplicada.
