# Auditoría adversaria del monorepo — 2026-09-29

## Estado y alcance

**Resultado: seis hallazgos anteriores corregidos y los seis nuevos hallazgos de esta revisión (A01-A06) corregidos y verificados en los escenarios cubiertos con pruebas específicas y de regresión en commits atómicos dedicados. No se declara el monorepo libre de defectos.**

Base de las correcciones: `d3dac186`. Durante el trabajo entró el commit documental externo `36b3eb21`; se preservó. Código corregido de la primera ronda: `5304304a`, con narrowing tipado en `e52478c3` y referencias documentales en `035942a5`. Resoluciones de la segunda ronda (A01-A06): `eb827a94`, `498ab854`, `9a7ee2c9`, `1643b6f7`, `4ab38690`, `f2530793`. Esta sesión no ejecutó push. Las referencias locales y remotas avanzaron por trabajo concurrente, incluyendo `4331f500` y posteriormente `adf5021a`; por ello la publicación no se atribuye a esta ejecución.

La revisión cubre límites arquitectónicos, continuidad, persistencia, reproducción, observación, estudios y configuración de pruebas. Combina lectura dirigida, análisis AST, diagnósticos estáticos, pruebas existentes y reproducciones adversarias pequeñas. No equivale a revisión manual de cada línea ni certificación de seguridad. No se ejecutaron campañas científicas completas, pruebas en otros sistemas operativos, ataques a servicios reales ni análisis de vulnerabilidades de dependencias publicado en Internet. Los escenarios destructivos se simularon con dobles o directorios temporales.

## Correcciones de la primera auditoría

| Hallazgo anterior | Cambio | Commit | Estado |
| --- | --- | --- | --- |
| Organismo crea descendientes y conserva autoridad poblacional | Construcción, registros y autoridad trasladados a `symbiont_lab.reproduction`; Lab registra nacimientos y observa muertes; migración de consumidores y pruebas | `5304304a` | Corregido |
| Restauración convierte silenciosamente ticks incompatibles en reembodiment | Rechazo de cuerpo ausente/incompatible; `fresh_body` explícito conserva el camino autorizado | `328b6bf7` | Corregido |
| Cargador de bundle no verifica manifiesto/hash | Verificación del runtime y coherencia antes de publicar artefactos | `cf850430` | Corregido |
| Extracción altera archivos antes de encontrar una entrada inválida | Validación completa previa, publicación sin sobrescritura y rollback de archivos nuevos ante excepción | `cf850430` | Corregido con límite de crash indicado abajo |
| Exportación omite silenciosamente modelos activos/shadow incompletos | Rechazo de artefactos requeridos ausentes; inventario SHA-256 en bundle 1.1 | `cf850430` | Corregido |
| Excepciones del hilo de checkpoint no llegan al caller | Resultado `Future`, consumo de errores y propagación del fallo final tras cleanup en el camino de error de checkpoint | `328b6bf7` | Corregido; no implica tolerancia a errores de observación, véase A01 |

Límites deliberados: los bundles históricos sin manifiesto/1.0 carecen de hashes de artefactos; se comprueban estructura y completitud, no una integridad criptográfica que nunca registraron. El rollback de extracción cubre excepciones capturadas, no atomicidad de varios archivos frente a apagado abrupto. Los archivos existentes idénticos se reutilizan y los conflictivos se rechazan. No se añade autenticidad/firma a los hashes. La migración de reproducción todavía lee configuración constitucional privada del runtime desde Lab; eliminar ese acoplamiento requiere una interfaz constitucional explícita, no devolver la reproducción al sujeto.

## Hallazgos confirmados y resueltos (A01—A06)

### A01 — Alta: un fallo del observador impide guardar y limpiar el organismo

- **Ubicación:** `src/symbiont_lab/physics3d/engine.py:824,858-860`; `src/symbiont_lab/physics3d/telemetry_v41.py:823-845,873-888`.
- **Mecanismo:** el worker de telemetría registra su excepción; `flush()` la propaga. El `finally` del motor empieza con otro `telemetry.flush()` sin aislamiento, antes del checkpoint final, cierre físico y restauración de señales. Una avería del observador toma control del ciclo vital y de su salida.
- **Reproducción ejecutada:** runtime de un tick y writer simulados, `telemetry.flush.side_effect = RuntimeError('async telemetry worker failed')`; `_save_checkpoint` instrumentado. Resultado: `checkpoint calls 0`, `runtime close 0`, `telemetry close 0`. No requiere fallo del mecanismo de checkpoint corregido.
- **Impacto:** pérdida del último estado cognitivo guardable, recursos sin cerrar y handlers sin restaurar. El worker real es no-daemon; saltarse su cierre también puede impedir la terminación del proceso. Este último efecto se deriva del código, no se provocó un bloqueo real.
- **Corrección recomendada:** aislamiento del fallo de observación; cleanup por recursos independientes y checkpoint cognitivo que no dependa de `flush`. Registrar la pérdida de evidencia sin atribuirla a muerte del sujeto. Añadir inyección de fallo en append/flush/close.
- **Certeza:** confirmación dinámica del salto de guardado/cleanup. **Estado:** Corregido (`eb827a94`). Pruebas añadidas en `lab/tests/unit/lab/physics3d/test_shutdown.py` validando aislamiento de observación, preservación de presupuesto, checkpoint y cierre independiente de recursos.

### A02 — Alta: las pruebas de integridad experimental no se ejecutan con el comando de CI

- **Ubicación:** `tests/conftest.py:10-23`, `pyproject.toml` (`addopts`), `.github/workflows/ci.yml:29,45`.
- **Mecanismo:** todos los archivos de `tests/integration/` y `tests/experimental_integrity/` se marcan `slow` por ruta, aunque sean pruebas pequeñas. El filtro predeterminado excluye `slow`; los jobs no lo reemplazan.
- **Reproducción ejecutada:** `pytest --collect-only -q tests/experimental_integrity` devuelve `no tests collected (150 deselected)`. La ejecución explícita con `-o addopts=''` sí ejecuta las 150 pruebas.
- **Impacto:** `software-tests` omite integración; el job dedicado de integridad no valida sus límites y termina sin tests seleccionados (pytest código 5), no con una garantía de integridad. También quedan ocultas en el loop predeterminado las nuevas regresiones correctamente ubicadas en esas capas.
- **Corrección recomendada:** marcar lentitud por coste real, no por pertenencia a una capa; dar al job dedicado una selección explícita y comprobar que selecciona pruebas. No trasladar pruebas al directorio equivocado para eludir el filtro.
- **Certeza:** configuración y colección reproducidas. **Estado:** Corregido (`498ab854`). Clasificación en `tests/conftest.py` acotada a costes reales, flag `-o addopts=` en CI workflow y prueba unitaria en `tests/unit/test_pytest_profile.py`. Colección completa de 150 pruebas verificada.

### A03 — Alta para evidencia: exportación asíncrona mezcla individuos/runs

- **Ubicación:** `observatory/ui/exports.js:59-68,80-105`.
- **Mecanismo:** se congela el snapshot antes del `await`, pero se consultan identidad, secuencia y topología desde el estado mutable después. Las respuestas de procedencia no se cotejan con la identidad capturada.
- **Reproducción ejecutada con Node:** iniciar exportación con A/run-A; bloquear `fetch`; cambiar el estado a B/run-B; resolver ambas respuestas de A. Resultado exportado: snapshot `run-A`, manifiesto `run-A`, procedencia `run-B`, topología `B`.
- **Impacto:** paquete aparentemente coherente atribuye evidencia a otro individuo. No es evidencia válida para una conclusión científica.
- **Corrección recomendada:** capturar contexto inmutable completo antes de cualquier await; verificar identidad/run/revisión de las respuestas, abortar o marcar explícitamente incoherencia si cambian.
- **Certeza:** reproducción dinámica del módulo JS con red/DOM simulados, no prueba de navegador real. **Estado:** Corregido (`9a7ee2c9`). Captura completa de contexto previa a llamadas async y validación estricta de artefactos en `observatory/ui/exports.js`. Suite de regresión en `tests/regression/test_observatory_export_identity.py` (9 escenarios passing).

### A04 — Media: overflow y reconexión dejan deltas sin su base

- **Ubicación:** `src/symbiont_lab/observation/bus.py:108-130,147-166`.
- **Mecanismo 1:** al llenar la cola se descarta el mensaje más antiguo, pero se materializa un anchor del canal entrante, que no necesariamente es el canal del mensaje perdido.
- **Reproducción ejecutada:** cola de tamaño 2; cliente ya tiene body/vitals revisión 1; publicar body2, vitals2, vitals3 sin consumir; drenar; publicar body3. El cliente recibe body3 con `base_revision=2`, aunque solo dispone de body1.
- **Mecanismo 2:** reconexión selecciona historia válida y luego la recorta a la capacidad de la cola sin reconstruir bases. Con cinco mensajes body y `after_sequence=1`, cola 2 comienza en delta4/base3.
- **Impacto:** el consumidor no puede reconstruir fielmente el canal hasta un nuevo anchor; una UI defensiva descarta y queda desactualizada, una permisiva puede mezclar estados. No se demostró contaminación del organismo.
- **Corrección recomendada:** recuperación por canal invalidado o nueva instantánea materializada de todos los canales afectados; al truncar replay comenzar por bases válidas. Añadir tests de streams intercalados, no solo un canal.
- **Certeza:** ambas secuencias reproducidas con `ObservationBus` real. **Estado:** Corregido (`1643b6f7`). Rebase por canal dependiente, drenaje defensivo y snapshot en suscripción en `src/symbiont_lab/observation/bus.py`. Pruebas en `test_live_delta.py` y `test_world_scene.py`.

### A05 — Media: checkpoint público de World pierde los cuerpos

- **Ubicación:** `src/symbiont_world/checkpoint.py:18-52`; `src/symbiont_world/state.py:24-56`.
- **Mecanismo:** `WorldState` posee `bodies`, además de occupancy. `take_checkpoint` no serializa cuerpos y `restore` crea un estado sin ellos.
- **Reproducción ejecutada:** una ocupación y un `BodyPlacement` con orientación 3; checkpoint/restore devuelve `len(bodies): 1 -> 0`, mientras occupancy permanece igual.
- **Impacto:** se pierden orientación, radio y origen de emisión; no existe continuidad equivalente de ese estado. Es una API pública exportada desde `symbiont_world.__init__`.
- **Límite de alcance:** Lab tiene un checkpoint persistente diferente. No se ha demostrado que esta omisión afecte a los guardados de población de Lab; no debe extrapolarse a esa ruta.
- **Corrección recomendada:** serializar/validar todo el estado causal propiedad de World y probar continuación, no solo ocupación y tick.
- **Certeza:** reproducción directa. **Estado:** Corregido (`4ab38690`). `WorldCheckpoint` captura `bodies` mediante copia profunda y un mapping de solo lectura y `restore` reinstancia las colocaciones corporales. Pruebas en `environment/tests/unit/world/test_checkpoint.py` y `environment/tests/integration/test_world_checkpoint_continuation.py`.

### A06 — Media: el estudio prospectivo encarnado falla en su primer tick

- **Ubicación:** `src/symbiont_lab/studies/learning/prospective_agency_embodied.py:350-362`.
- **Mecanismo:** se crea `private_model_training`, pero se llama a `slm.poll(runtime)`; `slm` no está definido.
- **Reproducción ejecutada:** invocar `run_prospective_embodied_trial(1, warmup_ticks=1, horizon_ticks=1)` con runtime y servicio de entrenamiento simulados. Resultado: `NameError: name 'slm' is not defined`. Ruff confirma F821.
- **Impacto:** el protocolo no alcanza su decisión de split ni produce el resultado previsto. No es un resultado científico negativo ni `not_testable`; es un fallo mecánico.
- **Corrección recomendada:** usar la API real del servicio con el argumento apropiado y añadir un contrato corto del primer tick; no modificar la conducta del organismo ni aumentar presupuestos para ocultarlo.
- **Certeza:** diagnóstico estático y reproducción dinámica con dobles. **Estado:** Corregido (`f2530793`). Invocación corregida a `private_model_training.poll(runtime.organism)` y test de contrato de 1 tick añadido en `lab/tests/experiments/protocols/test_prospective_embodied_warmup.py`.

## Cobertura, evidencias negativas y límites

| Área | Revisión realizada | Límite |
| --- | --- | --- |
| Sujeto / World / Lab | AST de imports directos: 250 archivos de sujeto y 12 de World, cero imports prohibidos directos; inspección de reproducción y restore | No prueba ausencia de dependencia dinámica ni de semántica privilegiada |
| Cognición / autoridad / aprendizaje | Suite completa de integridad seleccionada explícitamente; lectura dirigida de fronteras generativas y modelado | Sin campaña de aprendizaje/utility ni certificación de todos los flujos |
| Persistencia y ciclo vital | Pruebas focalizadas, bundles alterados, artefactos ausentes, fallos del writer, reembodiment explícito | No corte real de energía ni filesystem cross-platform |
| World | State/checkpoint/topología y lectura de persistencia Lab | A05 limitado a checkpoint del kernel |
| Observación / UI / servidor | Bus/deltas/export; suite Observatory; bind loopback inspeccionado | Sin navegador real ni prueba integral entre sesiones |
| Host y despliegue | Superficies Linux acotadas e IDs opacos; servicio de usuario con restricciones; búsquedas de ejecución/serialización | Sin operación sobre host real ni instalación de servicios |
| CI / tests / scripts | Ruff, Bandit, selección efectiva de pytest y suite predeterminada | No matriz CI remota ni cobertura de todas las campañas |

Bandit: dos avisos LOW (B404/B603) en `scripts/reprofile_performance.py`; no se han convertido en vulnerabilidades sin demostrar una entrada adversaria. Su configuración omite varias familias de reglas, de modo que una salida casi vacía no certifica seguridad. Ruff antes de corregir A01–A06: ocho diagnósticos, siete de imports/formato y el F821 de A06; no se corrigieron problemas ajenos automáticamente.

## Validación

- Persistencia/shutdown/session/manifiestos: **56 passed**. Tras formatear para los hooks, shutdown/session: **21 passed**.
- Reproducción/autoridad/continuidad/fisiología/modelado, con filtro slow desactivado explícitamente: **58 passed**.
- Consumidores de reproducción (hábitat integrado y cuatro estudios): **12 passed**.
- Physics3D + unidades relacionadas: **310 passed, 1 skipped, 3 failed**. Los tres fallos de reembodiment se reprodujeron en el archivo de la base `d3dac186`: **14 passed, 3 failed**. No se debilitaron esas aserciones.
- Integridad experimental completa, `-o addopts='' -n 4`: **149 passed, 1 failed**. Fallo de presupuesto temporal `test_diff_cognitive_atlas_incremental_delta_meets_5ms_budget`, 6.66 ms frente a 5 ms, bajo carga concurrente. Reejecución aislada del test: **1 passed**. No se atribuye a regresión funcional ni se considera un benchmark controlado.
- Observatory: **266 passed, 1 failed**; fixture espera genome v1 y recibe v2 (`test_resident_publishes_registry_journal_and_canonical_topology`). La expectativa histórica no se modificó como parte de esta tarea.
- Pyright global: **870 errors, 104 warnings** en la primera pasada; incluía siete errores de narrowing del nuevo adaptador que se corrigieron en `e52478c3`. Pyright focalizado posterior de `src/symbiont_lab/reproduction`: **0 errors, 0 warnings**. No se ejecutó una segunda pasada global ni se clasificaron todos sus diagnósticos.
- Revalidación tras narrowing: **13 passed** (reproducción, autoridad y frontera de propiedad).
- Enlaces Markdown: inicialmente detectó una referencia rota por el traslado de autoridad; corregida en `035942a5`, reejecución **1 passed**.
- Base archivada `d3dac186`, suite predeterminada: **2839 passed, 6 failed, 10 skipped, 1 xfailed**, 974 s. Uno de los fallos es propio del método de aislamiento: la comprobación documental necesita `.git`, ausente en `git archive`. Los otros cinco corresponden a dos tests de retracción de readouts y los tres de reembodiment. Los subprocess CLI pueden resolver el ejecutable editable del checkout: esta base no es prueba de aislamiento hermético de todos los procesos.
- Suite predeterminada iniciada antes de cerrar correcciones/documentación: **2866 passed, 9 failed, 10 skipped, 1 xfailed**, 775 s. Cuatro fallos documentales por referencias trasladadas, dos de retracción y tres de reembodiment. El checkout recibió modificaciones concurrentes durante esta ejecución: no representa una validación congelada del HEAD actual. Las referencias documentales y otros fallos recibieron commits posteriores; no se declara verde la suite completa final.
- Integridad experimental revalidada sobre el estado actual, selección explícita y ejecución secuencial: **150 passed**, 58 s.
- Revalidación actual tras las seis correcciones: **145 passed** (shutdown, clasificación pytest, exportación JS, World, continuación, primer tick del estudio y enlaces/fuentes documentales).
- Seguimiento A04: dos regresiones nuevas fallaron antes del cambio y pasan después. Suite unitaria de observación: **67 passed, 9 deselected**. `b0a3603e` elimina la presuposición de que un cursor SSE garantiza todas las bases del cliente; conserva historia materializada acotada y establece bases solo para canales realmente enviados. Trade-off: más bytes por entrada histórica y por replay, sin cambiar la compresión del stream vivo ni el número máximo de entradas.
- Smoke de servidor unificado y adaptador de stream tras el seguimiento A04: **131 passed**, 6.86 s.
- El checkpoint de World protege el mapping y separa objetos mediante copia profunda; no hace inmutables los campos de cada `BodyPlacement`. No hay migración que invente los cuerpos ausentes en checkpoints antiguos.
- El primer tick de A06 también reveló un campo obsoleto: se sustituyó `cognitive_motor_competence_candidates` por `motor_competences`, campo real de `Tick3D`.

## Estado final de la intervención

Las seis intervenciones recomendadas han sido implementadas, verificadas y consolidadas en commits atómicos:

1. **A01 (`eb827a94`):** Aislamiento de fallos de telemetría/observador respecto al guardado de checkpoint y cleanup en `engine.py`. Pruebas en `test_shutdown.py` (26 passed).
2. **A02 (`498ab854`):** Corrección de filtro de lentitud en `conftest.py` y workflow de CI para ejecución explícita de `tests/experimental_integrity` (150 passed).
3. **A03 (`9a7ee2c9`):** Congelación y validación de contexto inmutable de exportación antes de llamadas asíncronas en `observatory/ui/exports.js`. Pruebas en `test_observatory_export_identity.py` (9 passed).
4. **A04 (`1643b6f7`):** Rebase defensivo de canales dependientes ante desbordamiento de cola y truncado de reconexión en `ObservationBus`. Pruebas en `test_live_delta.py` y `test_world_scene.py` (25 passed).
5. **A05 (`4ab38690`):** Inclusión de una copia independiente de `bodies` en `WorldCheckpoint` y restauración íntegra de `WorldState`. Pruebas en `test_checkpoint.py` y `test_world_checkpoint_continuation.py` (7 passed).
6. **A06 (`f2530793`):** Sustitución del identificador no definido `slm` por `private_model_training.poll(runtime.organism)` en el estudio prospectivo encarnado. Prueba de contrato de 1 tick en `test_prospective_embodied_warmup.py` (1 passed).
