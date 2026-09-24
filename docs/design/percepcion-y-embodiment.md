# Diseño técnico: significado emergente de señales en Symbiont

<!-- markdownlint-disable MD025 -->

> Consolidated from: diseno-descubrimiento-senales-symbiont.md, digital-body-schema-and-emergent-morphology.md, recurrent-restoration-contract.md
>
> Note: the first absorbed document ("Diseño técnico:
> significado emergente de señales en Symbiont") uses `## 1.` … `## 12.`
> plus an unnumbered "Fuentes del repositorio" section. The second absorbed
> document (further down, "Digital Body Schema & Emergent Morphology")
> independently numbers `# 1. Motivation` … `# 36. Recommended
> implementation sequence` at heading level `#`, not `##`. These are NOT a
> single continuous sequence with the first document's numbering. The third
> absorbed document ("Contrato de restauración recurrente de Symbiont",
> further below still) does not use numbered headings and is unaffected.

**Estado:** diseño cerrado; implementación del kernel, runtime, persistencia, estudio y contrato Observatory completada; verificados por la suite completa, contratos SSE/replay y smoke visual desktop/móvil en navegador, 15 de septiembre de 2026. **Referencia inicial:** `770f683ab273468b3290a0e988b3d69ce3d2314a`. **Reconciliación del inventario:** checkout local `main` de `alessbarb/symbiont-lab`, commit `a7712550724e3d22571730297af1f72eecd32acb`. Este documento especifica cambios y su estado se verifica mediante pruebas ejecutadas; la reconciliación inicial fue una inspección de código, no una validación funcional.

## 1. Objetivo y frontera epistemológica

Symbiont debe poder formular y revisar afirmaciones verificables sobre una señal opaca: comportamiento, cambios de régimen, relaciones predictivas con otras señales y utilidad para anticipar estados propios observables. El resultado será conocimiento estructurado suyo, presentado por Observatory con lenguaje preciso. La identidad estable permanece opaca. Las decisiones concretas de §12 resuelven las alternativas exploratorias de las secciones anteriores y son normativas. «Temperatura», «CPU», «disco» y otros significados de plataforma no se infieren de la forma de una serie sin evidencia discriminante. El código del proveedor, manifiestos, alias semánticos, nombres del operador y verdad del evaluador no son entradas del motor de descubrimiento.

El nombrado o definición por el operador queda **fuera del contrato, interfaz, persistencia y pruebas de esta versión**. En el futuro se podría estudiar de forma independiente; ningún campo reservado para etiquetas enseñadas es necesario hoy. Los identificadores sintéticos o ordinales de interfaz son referencias visuales, nunca conocimiento del organismo.

La unidad básica es una **afirmación con predicción falsable**. Tres estados distintos deben conservarse: `insufficient` (faltan observaciones comparables), `hypothesis` (evidencia inicial), `supported` (contraste favorable repetido fuera de muestra; ventaja incremental para claims predictivos, cumplimiento del criterio falsable para los descriptivos). `contested` describe contradicción reciente y `stale` describe evidencia caducada; ninguno equivale a certeza absoluta. Una relación observacional no autoriza el verbo «causar». En el host local real, las lecturas son de solo lectura, así que el primer diseño no atribuye efectos causales a acciones del organismo.

## 2. Inventario del sistema actual

| Ruta | Hecho verificado | Modificación propuesta |
| --- | --- | --- |
| `src/symbiont/core/foundation/narrative.py` | `NarrativeEntry` expresa baseline, incertidumbre, atención, evidencia y dissent; el `summary` reproduce el ID. | Añadir proyección de afirmaciones con plantillas cerradas; mantener la narrativa existente por compatibilidad. |
| `src/symbiont/core/orchestration/runtime.py` | `tick()` observa lecturas en `AdaptiveSenseModel`, sintetiza perceptos, actualiza aclimatación, drift, bridge y memoria; la narración se forma al final. | Inyectar un motor independiente después de adquirir las lecturas del tick y antes de construir el resultado; incluir su vista y eventos en `RuntimeTickResult`. |
| `src/symbiont/host/adaptive.py` | `PairAccumulator` calcula correlación síncrona y desfase de un tick en ambas direcciones; `SensoryRelation` no es causal. La selección usa una ventana de relaciones y muestreo selectivo. | Reutilizarlo como fuente de candidatos; no convertir correlación en conocimiento validado. Añadir acceso explícito a conteos por dirección si se usa como filtro. |
| `src/symbiont/host/drift.py` | Clasifica observaciones en `none`, `isolated`, `gradual`, `creep`, `regime_shift`. | Usar clases como evidencia contextual, sin atribuir estabilidad retrospectiva a un baseline recién reajustado. |
| `src/symbiont/core/cognition/consolidation.py` | Hay memoria estadística y trazas categóricas acotadas, sin telemetría cruda durable. | Integrar la madurez de afirmaciones, sin guardar secuencias de muestras en checkpoint ni confundir traza destacada con relación predictiva. |
| `observatory/adapter.py` | Une resúmenes en `organism.narrative` limitado a 600 caracteres y memoria a 32 cadenas. | Publicar fichas estructuradas acotadas y eventos de revisión; las narraciones generales serán resúmenes, no el único canal. |
| `observatory/snapshot.schema.json`, `projection/snapshot.js` | Hay v1, v2 y v3, con cognition y body schema según versión; `beliefs` solo contiene etiquetas de 120 caracteres. | Extensión aditiva validada de v3 o v4 explícita si se exige el campo. Mantener consumidores antiguos. |
| `observatory/render/senses.js`, `render/inspector.js` | El click busca creencia con `includes` y, si falla, selecciona por índice; el inspector tiene explicación fija que presume consistencia. | Selección exacta por ID de sentido y ficha propia; renderizar hechos estructurados sin afirmaciones fijas falsas. |

El bootstrap de sentidos semánticos (`bootstrap_semantic_senses`) añade nombres predefinidos en el runtime. Además, `SensorReading.capability_id` **no garantiza opacidad**: los proveedores stdlib usan, por ejemplo, `compute.logical_cpu`; LinuxSurfaceProvider usa hashes. Una frontera de identidad anterior al motor convertirá todos los IDs en tokens locales al organismo, sin pasar `source`, `unit`, timestamps, `DEFAULT_PERCEPT_NAMES`, `percept_names`, `cognitive_aliases`, nombres de proveedor ni `manifest` semántico. Las pruebas centrales desactivarán ese bootstrap. Si la representación en el grafo cognitivo requiere alias, un mapeo privado de referencia puede unir identidad de señal y nodo; el mapeo no aporta el significado del alias ni se exporta como inferencia.

La frontera usará HMAC-SHA256 con una clave aleatoria durable de 32 bytes y dominio `signal-knowledge-v1`, produciendo `signal.<64 hex>` a partir del ID exacto de capacidad. La clave pertenece al checkpoint privado del runtime, nunca a la vista pública ni al motor estadístico. Los IDs de proveedor se usan únicamente para detectar grupos de adquisición compartida en esa frontera, no para construir conocimiento. La correspondencia reversible para clicks vive en la proyección de Phenotype; Self recibe exclusivamente tokens. Un cambio del ID de capacidad abre una identidad nueva, aunque sus valores coincidan; no se infiere continuidad por parecido estadístico. Los claims usan SHA256 completo sobre la tupla canónica JSON `[subject_id, kind, object_id, horizon]`, con validación de unicidad y rechazo de colisiones, nunca reasignación silenciosa.

### 2.1 Cambios incorporados al inventario tras la referencia inicial

- [`cognitive_self.py`](../../src/symbiont/core/cognition/self_model.py) proyecta activaciones internas en canales opacos y clases de actividad acotadas, excluyendo los IDs sensoriales conocidos antes de producir los tokens. [`body_schema.py`](../../src/symbiont/core/embodiment/body_schema.py) aprende y exporta regiones cognitivas y dependencias; Self ya no debe describirse como carente de toda organización cognitiva propia. Estos canales no constituyen por sí mismos claims de predicción entre señales host, ni prueban relevancia independiente: cualquier objetivo de `self_relevance` necesita todavía la auditoría de circularidad de §5.4.
- [`predictive_utility.py`](../../src/symbiont_lab/studies/learning/predictive_utility.py) contiene un ensayo de una serie con autocorrelación negativa, horizonte de un tick, referencias cero/media histórica/persistencia y ablaciones de plasticidad y arista. Sus [pruebas](../../tests/unit/lab/test_predictive_utility.py) incluyen las semillas 101, 127 y 149. Es infraestructura y evidencia potencial para el diseño, **no** el estudio de descubrimiento exigido por §10: no implementa perfiles o revisión de claims, selección entre múltiples señales, entornos negativos diversos ni integración de `SignalKnowledgeEngine` en runtime. Tampoco se sustituye sin evaluación la media reciente propuesta por la media de toda la historia usada en ese ensayo.
- El [contrato de restauración recurrente](percepcion-y-embodiment.md) distingue estado durable, reinicio dinámico y reconstrucción discreta de parámetros. El [estudio de continuidad](../../src/symbiont_lab/studies/continuity/recurrent_restoration.py) es un punto de integración para §7 y §11, no una prueba de continuidad de claims aún inexistentes. Conservar una afirmación madura no garantiza que el predictor reiniciado mantenga su ventaja; deberán medirse de nuevo oportunidades y validación posteriores al corte sin puntuar trials cuyo estado transitorio se perdió.

La implementación ya añade el contrato `signal_knowledge` al runtime, la selección `selectedSignalId` al estado de Observatory, un predictor ridge fuera de muestra acotado y la migración durable host v6→v7 con conocimiento vacío para checkpoints antiguos. La aceptación completa y la cobertura de los entornos definidos en §10 están implementadas en el estudio determinista y cubiertas por pruebas unitarias e integradas; la suite conserva la verdad exclusivamente en `symbiont_lab`. La reconciliación de inventario no fijó umbrales; las decisiones posteriores y el piloto que los fundamenta constan en §12.

## 3. Contrato de datos interno

Crear `src/symbiont/core/signal_knowledge.py` con `SignalKnowledgeEngine`, `SignalProfile`, `Claim`, `EvidenceWindow`, `PredictionTrial` y `KnowledgeEvent`. Todo modelo es acotado por límites del kernel y JSON-safe. Los nombres de tipos y campos son orientativos, pero el significado y las invariantes sí son normativos.

```text
SignalProfile {
  signal_id: organism-local opaque signal token,
  observed_opportunities: int, valid_observations: int,
  last_observed_tick: int | null,
  claims: bounded list[Claim]
}
Claim {
  claim_id: stable opaque ID,
  subject_id: signal ID,
  kind: stability | change | synchronous_association |
        lead_prediction | self_relevance,
  object_id: signal ID | bounded organism-owned outcome | null,
  horizon: positive tick count | null,
  direction: same | opposite | unspecified,
  status: insufficient | hypothesis | supported | contested | stale,
  strength_class: discrete class | null,
  validation: trials, comparable_trials, baseline_loss_class,
              candidate_loss_class, improvement_class,
              successful_epochs, failed_epochs,
  context: regime_class, reliability_class, last_tested_tick,
  revision: monotonic integer, reason_class
}
KnowledgeEvent {claim_id, tick, from_status, to_status, reason_class}
```

`valid_observations` y `observed_opportunities` cuentan cosas distintas. Una oportunidad de comparar dos señales requiere **ambas disponibles, válidas y observadas con sincronía conocida**; una ausencia de muestreo no es un cero ni una prueba de ausencia de relación. No se compararán soportes brutos de perfiles con edades y tasas de muestreo distintas. Los IDs de afirmación son persistentes, derivados de una clave canónica de sujeto, objeto, tipo y horizonte con control de colisión; al recuperar o retirar nodos, nunca se enlaza silenciosamente una afirmación vieja a otra señal.

Las afirmaciones tienen procedencia exclusivamente endógena: observaciones válidas, error predictivo, drift, atención y estado propio ya observable por el organismo. No admiten cadenas arbitrarias de texto, citas de plataforma ni etiquetas semánticas. La vista exportada retiene `evidence_count` y clases discretas, no valores exactos de lectura, medias basadas en pocas muestras, marcas temporales reales o ventanas crudas.

## 4. Adquisición, sincronía y estado transitorio

En `OrganismRuntime.tick()`, construir una `SignalObservationBatch` al completar `snapshot.readings`: `tick`, ID, valor numérico finito cuando exista, calidad, disponibilidad y fiabilidad agregada propia. Entregarlo al motor una sola vez por tick. La señal permanece identificable aunque no haya valor este tick. Separar claramente `manifest available`, `selected for sampling`, `reading obtained` y `value valid`. El motor no interpreta capacidad disponible como señal medida. `observed_opportunities` cuenta intentos explícitos de muestreo de esa señal; `valid_observations` cuenta sus lecturas nominales finitas. La disponibilidad sin selección no incrementa ninguno. La cobertura de claims se calcula por época en ticks reales, no dividiendo soportes históricos de perfiles.

El motor conserva solo en RAM el mínimo transitorio para predicciones de horizontes definidos, como el último valor o clase normalizada por señal y predicciones pendientes. Un objetivo ausente o inválido deja el trial **sin resolver**; no cuenta como éxito ni fracaso. Los contadores de oportunidad registran ese censurado. Los retardos se expresan en ticks reales y se evalúan solo si la continuidad de observación satisface el contrato; si el muestreo selectivo dejó huecos, no se imputan valores. Limitar horizontes inicialmente a 1 tick; horizonte mayor requiere buffers acotados y pruebas propias.

Resolver el trial pendiente antes de actualizar el predictor con la lectura del objetivo del tick actual. Conservar el orden: `predict(t)` con estado hasta `t`, `observe(t+1)` para puntuar, y luego `learn(t+1)`. Evita fuga del objetivo al entrenamiento o al informe fuera de muestra. El `AdaptiveSenseModel` puede seleccionar pares para explorar, pero el motor no considerará esa selección una prueba de la relación; los sesgos de selección deben registrarse por cobertura.

## 5. Generación y contraste de hipótesis

### 5.1 Afirmaciones univariantes

Después de un mínimo de observaciones comparables en bloques no solapados, estimar clases de estabilidad, variabilidad y cambios de régimen desde estadísticas robustas y `DriftObservation`. La afirmación «estable» se evalúa sobre una ventana reciente acotada o épocas comparables, no sobre toda la historia acumulada. Una secuencia con cambio de régimen invalida o contextualiza la afirmación antigua, incrementa su revisión y abre una nueva hipótesis; no se declara estable por el mero reajuste del baseline. Datos constantes, rampas, valores faltantes, contadores crecientes y entradas no finitas tienen casos específicos.

### 5.2 Asociaciones entre señales

`AdaptiveSenseModel.strongest_relations()` propone pares; es filtro económico, no veredicto. El motor registra simultaneidad, dirección, conteos comparables, variabilidad efectiva y cobertura. Una correlación fuerte solo autoriza «cambian juntas en las oportunidades observadas». Exigir varias épocas no solapadas, soporte reciente y cobertura mínima. Descontar asociación trivial por tendencia común, autocorrelación o cambios compartidos de régimen mediante diferencias/clases normalizadas y controles temporales apropiados. No seleccionar solo el coeficiente mayor entre numerosos pares sin corrección o evaluación independiente.

### 5.3 Utilidad predictiva fuera de muestra

Para `A(t) → B(t+1)` usar comparación progresiva temporal: entrenar con pasado, emitir predicción antes del objetivo, puntuar la predicción preemitida al tick siguiente y solo entonces actualizar. Comparar con referencias por objetivo (`persistencia`, `media reciente` y `cero` cuando la escala lo permita). Elegir o predefinir referencia según la serie, sin elegir retrospectivamente la peor. La pérdida y el mínimo de mejora se fijan antes del experimento; reportar pérdidas agregadas discretizadas y oportunidad comparable. El claim pasa a `supported` solo tras ventaja material en varias épocas separadas y con un número mínimo de trials válidos; un único resultado favorable queda `hypothesis`.

Si `A` predice `B` tanto como `B(t)` ya lo hace, la señal A no aporta descubrimiento predictivo incremental. Incluir siempre la referencia condicional con la historia disponible de B definida en §12; sin historia suficiente no hay trial comparable. En presencia de alta autocorrelación o de acoplamiento negativo, probar ambos regímenes; «persistencia» no es una referencia universalmente buena. Un predictor que converge a cero no se acredita por bajar su pérdida inicial: debe superar las referencias relevantes sobre nuevos ticks.

### 5.4 Relevancia para el propio organismo

Relacionar la señal con resultados que Symbiont ya percibe como propios y que constan en su contrato (`SelfModel`/`BodySchema` o calidad de muestreo), sin importar etiquetas externas. Distinguir predicción de resultados propios de cambio causado por acciones. Si el resultado propio depende matemáticamente de la señal, declarar esa dependencia como circular y excluirla de la prueba de relevancia independiente. No usar loss o atención del mismo predictor como objetivo si eso crea una ventaja tautológica.

## 6. Revisión, caducidad y presupuesto

Reevaluar continuamente las afirmaciones `supported` frente a nuevos trials. Si pierde la ventaja en épocas suficientes, pasar a `contested` con razón y evidencia contradictoria; si no hay oportunidades recientes, pasar a `stale`. Una nueva ventaja sostenida puede devolverla a `supported` conservando historial y aumentando `revision`. No reutilizar `DissentRecord` de baseline como prueba de falsedad de una relación distinta.

Aplicar los límites del kernel fijados en §12: `max_signal_profiles=64`, `max_claims_total=192`, `max_claims_per_signal=4`, `max_pair_candidates=64`, `max_pending_trials=128`, `max_horizon=1`, `min_validation_trials=144` y `max_knowledge_checkpoint_bytes` dentro del presupuesto global existente. Los valores se fijan en §12 y se verificarán contra el motor integrado; no se introducen como genética aprendible. Evicción: primero claims `insufficient` o `stale`, luego perfiles inactivos; proteger afirmaciones validadas y garantizar que los perfiles jóvenes no pierdan memoria solo por tener menor soporte acumulado. Las decisiones de evicción son observables y deterministas.

## 7. Persistencia y restauración

Incluir `signal_knowledge` en `OrganismRuntime.checkpoint()` y restaurarlo con migración explícita del esquema del host checkpoint actual (v6). Checkpoints previos migran a conocimiento vacío; no se reconstruye conocimiento avanzado desde strings de narrativa o correlaciones incompletas. Validar tipos, cotas, IDs, índices, conteos, clases, revisiones y tamaño antes de comprometer la restauración. Reiniciar todos los trials pendientes y marcar el intervalo de restauración como no comparable, conservando claims maduros y estadísticas discretas. Medir cuánto cambia la validación por esa decisión.

El bloque nuevo `signal_knowledge` del checkpoint guarda únicamente contadores suficientes, clases cuantizadas y soporte por épocas; esta afirmación no describe los agregados heredados del checkpoint host completo. Prohibir muestras individuales, buffers exactos de retardos, último valor, sumas que permitan reconstruir una muestra con conteo bajo, etiquetas de proveedor y series cortas reversibles. La cuantización debe ser específica de pérdidas, fuerza y fiabilidad: no reutilizar bins de pesos por comodidad. Revisar `AdaptiveSenseModel.export()` porque sus acumuladores de relación y gating por `min_samples` tienen que seguir siendo coherentes con la privacidad de esta nueva persistencia. La decisión de publicar clases de conocimiento y la de checkpoint durable se auditan por separado.

## 8. Contrato de observación

Publicar `organism.signal_knowledge` como colección completa acotada de perfiles con ID y claims estructurados, una vez por tick. No se implementan deltas en esta versión: la colección completa simplifica SSE/replay y reconstrucción tras reconexión. El máximo es 256 KiB incluyendo eventos, a verificar con el productor real. Campos de vista: `signal_id`, `observed_opportunities`, `last_seen_age_class`, `claims[]` con `claim_id`, `kind`, `related_signal_id`, `status`, `strength_class`, `evidence_count`, `validation_opportunities`, `improvement_class`, `revision`, `reason_class`. No incluir texto libre. `KnowledgeEvent` se publica acotado en eventos del tick con IDs estables; un consumidor retrasado puede reconstruir la situación desde el estado completo.

Versionado decidido: mantener v1 y v2 exactamente como son y añadir `signal_knowledge` **opcional únicamente en v3**, sin crear v4. El productor nuevo emite `[]` cuando tiene la interfaz nueva pero aún no conocimiento; un productor antiguo puede omitir el campo. El normalizador distingue ausencia de interfaz de colección vacía, sin inventar claims. Los snapshots v1/v2 no llevan el campo, aunque el adaptador reciba conocimiento; la exportación integrada nueva conserva BodySchema y produce v3. Las pruebas deben rechazar v1/v2 con el campo nuevo y aceptar v3 antiguo sin él. Actualizar `snapshot.schema.json`, `adapter.py`, `schema_validate.py`, `projection/snapshot.js`, selectores, demo fixtures, replay y resident/transport donde corresponda. No exponer el checkpoint privado a Observatory.

La narración se genera con plantillas deterministas desde claims estructurados: «observaciones insuficientes», «se mueven juntas en X oportunidades», «A ha anticipado B con mejora de clase M en varias épocas» y «la hipótesis dejó de sostenerse». Lenguaje de hipótesis y apoyo refleja el estado. Nunca convertir `strength_class` en «sé lo que es». Evitar unir centenares de summaries hasta truncar a 600 caracteres; la narrativa general selecciona pocas novedades y el inspector muestra la ficha completa. `beliefs` actuales pueden permanecer para compatibilidad, pero no introducir claims en ellos sin un vínculo exacto de ID y semántica de certeza.

## 9. Interfaz Observatory y frontera Phenotype/Self

Crear componente de ficha `render/signal-knowledge.js` y selección `selectedSignalId` persistente. El click de `render/senses.js` selecciona el sentido por igualdad exacta `sense.id` y resuelve su perfil por igualdad exacta `sense.knowledge_signal_id === profile.signal_id`, sin `includes` ni fallback basado en índice. Si no hay perfil: «Symbiont todavía no ha reunido evidencia suficiente»; si está ausente este tick, indicar la edad de la observación sin afirmar que está olvidada. Mostrar claims, evidencia comparable, estado, contradicciones y revisión, con el ID completo en detalles. Usar DOM `textContent` para campos externos; las plantillas no interpolan IDs en `innerHTML`. Las afirmaciones estáticas del inspector actual sobre «repeated platform-neutral percepts», «consistent with recent context» y «why it matters» se sustituyen por proyección real.

En Phenotype, Observatory puede mostrar instrumentación propia etiquetada como tal y la ficha de conocimiento del organismo como capa diferenciada. En Self, mostrar solo afirmaciones que consten en el conocimiento del organismo y su BodySchema; ni manifest, ni topology externa, ni nombres semánticos de proveedor, ni heading de estado derivado del observador. El nuevo panel no debe convertir un alias de UI en dato `Self`. Si el Self existente no tiene aún conocimiento de señales, indicar ese estado sin inventar una capacidad introspectiva. La ubicación visual exacta se ajusta con la revisión actual de Self, sin filtrar información privilegiada al área central.

## 10. Evaluación y pruebas de aceptación

Un estudio determinista de laboratorio alimentará el motor con **solo observaciones opacas** y conservará la verdad en el evaluador. Entornos mínimos: constante/ruido; serie autocorrelacionada positiva; autocorrelación negativa; A que anticipa B con retardo conocido; A y B correlacionadas por causa común sin ventaja incremental; cambio de régimen; ruido con pares múltiples; observaciones selectivas, huecos y calidades invalidas; señales con escala, desplazamiento y tendencia; cambio de ID. Al menos tres semillas por entorno, con soporte observado, falsos positivos y comparación con referencias. No mezclar las semillas con problemas distintos. La ventaja se mide en horizonte posterior, sin entrenamiento con futuro.

| Caso | Condición de cierre |
| --- | --- |
| Señal sin observaciones comparables | `insufficient`, sin media cruda persistente ni inferencia. |
| Correlación simultánea sin mejora futura | Asociación descriptiva posible; ningún claim predictivo `supported`. |
| Relación con ventaja fuera de muestra | Claim `supported` solo tras trials y épocas definidos; pérdidas y referencia registradas. |
| Relación espuria por tendencia o causa común | No prometer causalidad ni ventaja incremental inexistente. |
| Régimen cambia o predicción falla | Revisión de afirmación, status `contested` o `stale` y razón observable. |
| Muestreo ausente o inválido | Trial censurado y cobertura actualizada, nunca tratado como cero. |
| Múltiples señales y presupuesto lleno | Límites estrictos, evicción determinista y memoria estable. |
| Guardado/restauración | Claims y revisiones continúan; trials pendientes reiniciados o restaurados conforme al contrato; esquema viejo migra. |
| Bootstrap semántico desactivado | Descubrimientos idénticos para cualquier renombrado de proveedor que deje los valores y IDs opacos equivalentes. |
| Observatory Self | Ningún nombre, manifest o estado privilegiado entra en el panel de conocimiento propio. |
| Sense click, SSE y replay | ID exacto, ficha correcta tras cambio de tick/reconexión; v1/v2/v3 siguen cargando. |

El informe publicará tasa de hipótesis emitidas, precisión de claims `supported`, coste de observación, cobertura, tiempo hasta descubrimiento, ventaja predictiva respecto a cada referencia, frecuencia de revisiones y tamaño de checkpoint. No declarar que «descubre CPU» por acertar una etiqueta humana que nunca recibió. El evaluador puede verificar si una relación funcional corresponde a la señal generadora sin compartir esa verdad con el organismo.

## 11. Orden de implementación y dependencias

El plan de referencia contiene la matriz de requisitos y tareas. No está en ejecución: el alcance vigente solicitado es revisar y cerrar este diseño.

1. **Contrato y estudio:** fijar clases de claims, límites, pérdida, referencias, condiciones de promoción y ensayos opacos. Una baseline nula o trivial debe ser difícil de superar en los negativos.
2. **Motor univariante:** perfiles, oportunidades, clases de estabilidad/cambio y revisión; `RuntimeTickResult` propio. Sin narrativa de plataforma. Validar límites y privacidad.
3. **Relaciones:** usar candidatos de `AdaptiveSenseModel`, trials preemitidos, evaluación progresiva, control por autocorrelación/causa común, costes y cobertura. Una relación síncrona no entra como anticipación.
4. **Durabilidad:** checkpoint, migraciones, invariantes y discontinuidad del transitorio, con pruebas de restauración durante un horizonte de predicción y cerca de un cambio de régimen.
5. **Observatory:** schema, adapter, normalizer/store, vista de ficha, selección exacta, replays/SSE y frontera Self/Phenotype. Publicar el resultado de la revisión de claims, no solo un contador interno.
6. **Estudio integrado:** mismo flujo en motor aislado y runtime con proveedores controlados; revisar regresiones de percepción, atención, consolidación, plasticidad estructural y tamaño de checkpoint.

La integración del conocimiento puede avanzar mientras se investiga la continuidad de checkpoint y reciclaje del grafo. **No se deduce significado de la topología cognitiva por sí sola**: un concepto recurrente necesita trazabilidad de entradas, predicciones y validación antes de convertirse en una afirmación legible. Si el grafo continúa degenerado o sin readouts, el motor de conocimiento aún puede describir estadística básica, pero no debe adjudicar descubrimiento estructural al grafo.

## 12. Registro de decisiones y puertas de cierre

### Decisiones resueltas por inspección

1. **Identidad:** la frontera de tokens de §2 es obligatoria también con proveedores semánticos. La igualdad exacta del click se resuelve con una referencia `knowledge_signal_id` de Phenotype, no comparando tokens con nombres ni pasando nombres a Self. Un rename de proveedor que conserva el ID de capacidad conserva el token; un cambio de ID crea otra identidad.
2. **Compatibilidad pública:** extensión v3 opcional conforme a §8. El formato de BodySchema no se altera para almacenar claims; se preserva la separación entre ambas vistas de conocimiento.
3. **Privacidad durable:** `AdaptiveSenseModel.export()` guarda medias y momentos exactos tras gates de soporte independientes; **no** existe una cuantización de relaciones que pueda reutilizarse. Esos campos heredados no entran en el bloque `signal_knowledge`, ni en sus vistas o restore. El bloque nuevo conserva únicamente contadores, clases discretas y épocas cerradas; predictores, medias, covarianzas, pérdidas continuas y trials pendientes se reinician. La migración host será v6 → v7, conocimiento vacío para versiones previas y rechazo de contenido nuevo mal formado. Esta decisión no afirma que el checkpoint host completo carezca de estadísticas exactas: el contrato de privacidad nuevo y la auditoría de los agregados heredados son separados.
4. **Objetivos propios iniciales:** se admite únicamente éxito de adquisición de otra capacidad en el tick siguiente, observable mediante `CapabilitySamplingOutcome`. El objetivo binario vale 1 para `SUCCEEDED` con calidad `NOMINAL` y 0 para fallo/ausencia o calidad no nominal después de un intento explícito; sin intento es censurado. La frontera descarta fuente igual al objetivo y grupos de adquisición con el mismo proveedor; entrega al motor tokens y elegibilidad, no nombres de proveedor. No se usan coste exacto, atención, loss del predictor ni activaciones derivadas de la misma entrada. Las regiones BodySchema no son objetivos de esta versión mientras no exista trazabilidad que descarte dependencia matemática circular. La relación con otro resultado de muestreo sigue siendo predictiva, no causal. Si no hay pares elegibles, no se fabrica relevancia propia.

### Protocolo predictivo fijado por piloto

El [piloto reproducible](../../experiments/learning/signal-knowledge-pilot/README.md) ensayó 126 ejecuciones con semillas 17, 29 y 43. Sus resultados justifican adoptar el siguiente protocolo inicial, sin convertir el piloto en aceptación de producción. Las semillas de aceptación serán 101, 127 y 149; no se ajustarán umbrales a sus resultados. Un fallo de aceptación obliga a revisar explícitamente la versión del protocolo y volver a separar calibración y evaluación.

- Predictor: ridge lineal con intercepto, regularización `1e-6`, últimas 64 transiciones resueltas en RAM. Predice `ΔB(t+1)` usando `ΔB(t)`, `ΔB(t-1)` y `ΔA(t)`; suma `B(t)` para producir el objetivo. La referencia condicional omite `ΔA(t)`. Las otras referencias son cero, media de últimas 64 lecturas de B y persistencia. Las 32 primeras transiciones válidas solo entrenan. No se aprende con targets inventados, ni se normaliza una predicción con el objetivo futuro.
- Escala de pérdida: desviación estándar de las últimas 64 lecturas de B disponibles al emitir, con suelo `1e-12`; pérdida `min(4, abs(error / scale))²`, rango `[0,16]`. Se comparan las cinco pérdidas en exactamente los mismos trials; ventaja material exige reducir pérdida contra **cada** referencia en al menos 15% y 0.01 unidades por trial. Si todas son cero, no hay mejora incremental.
- Épocas: bloques no solapados de 64 ticks reales, al menos 48 trials comparables por época (75% de cobertura). Tres épocas consecutivas favorables permiten `supported` (mínimo 144 trials comparables); dos épocas comparables desfavorables pasan a `contested`. Una época sin cobertura suficiente rompe la racha de promoción pero no cuenta como fallo. Sin prueba comparable durante 192 ticks después de haber reunido evidencia, `stale`; un claim que nunca tuvo oportunidades suficientes conserva `insufficient`. Una nueva racha de tres épocas puede restablecer apoyo. Cada cambio de estado incrementa revisión y emite razón tipada.
- Un candidato propuesto por AdaptiveSenseModel comienza su contraste en la época siguiente: las observaciones que lo seleccionaron no cuentan como confirmación. Se fijan como máximo 64 pares candidatos por época y no se reemplazan dentro de ella por el coeficiente ganador. Los negativos con múltiples pares y la confirmación prospectiva son controles empíricos; no se anuncia una garantía formal de tasa de descubrimientos falsos.
- Solo lecturas `NOMINAL`, finitas y con continuidad de ticks conocida entrenan o puntúan. `DEGRADED`, `STALE`, `UNAVAILABLE`, valores booleanos/no finitos y ausencias son inválidos para el motor. Los trials vencidos sin objetivo se contabilizan como censurados y se retiran sin pérdida; no esperan una muestra tardía como si fuera del tick debido. Las diferencias requieren tres observaciones consecutivas propias y dos de la fuente; un hueco reinicia esa continuidad. El piloto confirma sensibilidad reducida con huecos: solo 1/3 de sus ejecuciones dispersas llegó a apoyo. No se rebaja cobertura para ocultarlo.
- Para el objetivo binario propio de §12.4 se usan referencias probabilísticas cero, frecuencia reciente, persistencia y predictor condicional; las salidas de regresión se limitan a `[0,1]`, escala fija 1 y pérdida cuadrática (Brier). Solo los intentos explícitos tienen target. Se conservan los mismos umbrales y épocas; este caso requiere validación propia en el estudio de aceptación y no se atribuye al piloto continuo.

### Contraste descriptivo, memoria y cotas

- Univariante: RAM de 64 observaciones consecutivas; estadísticos robustos mediana y MAD, sin exportarlos. `stability` predice que el siguiente cambio absoluto no supera `max(1e-12, 0.1 * MAD)` de la ventana pasada. Una época favorable requiere al menos 90% de aciertos entre 48 comparables; tres épocas sostienen, dos contradicen. Una serie constante puede sostener estabilidad, no asociación ni ventaja predictiva. Una rampa no es estable por tener incrementos predecibles.
- `change`: comparar medianas de dos bloques consecutivos de 32 lecturas válidas; separación mayor que `max(1e-12, 3 * MAD_anterior)` abre hipótesis de cambio y contradice estabilidad anterior. Su predicción es permanencia del desplazamiento fuera de esa banda en la época posterior; comparte requisitos de apoyo/revisión. El reajuste del baseline no vuelve a sostener automáticamente estabilidad.
- Asociación síncrona: correlación de diferencias consecutivas, no de niveles con tendencia. Época favorable con 48 comparables, variabilidad no nula en ambos lados, `abs(r) >= 0.75` y ventaja de magnitud ≥0.15 sobre el control con desfase de ocho ticks de la misma época. Tres épocas de confirmación prospectiva; sin continuidad para el control no hay época favorable. La dirección procede del signo y debe mantenerse durante la racha. Estos controles son descriptivos, no causales.
- Límites finales: 64 perfiles, 192 claims globales, 4 por señal, 64 pares candidatos, 128 trials pendientes, horizonte 1, 64 eventos por tick, cuatro resúmenes de época por claim, 64 transiciones de entrenamiento por predictor y 64 observaciones por señal. Resultados propios: como máximo 64 canales de outcome adicionales, sin perfiles host artificiales. Los valores transitorios exactos permanecen solo en RAM. Los límites son del kernel, no del genoma.
- Contadores públicos y durables saturan en `2**31-1`; revisión saturada no se recicla: se rechazan nuevas revisiones del claim con evento `revision_limit`. Tick interno no se satura; se valida entero no negativo y continuidad estricta. El límite de bytes sigue comprobándose para ticks grandes. Edad pública: `current` (0), `recent` (1–63), `aging` (64–191), `long_absent` (≥192), `never` (sin observación).
- Evicción determinista: claims `insufficient`, después `stale`, después `hypothesis`, ordenados por antigüedad de última prueba y finalmente ID; luego perfiles inactivos sin claims protegidos. No se expulsan `supported`/`contested` para admitir nuevos candidatos. Si solo queda memoria protegida, se rechaza la admisión y se emite `budget_rejected`. Se reserva un evento agregado de desbordamiento cuando las decisiones excedan los 64 eventos; nunca hay crecimiento ilimitado de la cola.
- Clases de pérdidas: 16 intervalos uniformes de anchura 1 en `[0,16]`, último inclusivo de 16; clases de mejora `none` (<15%), `material` (15–<30%), `substantial` (≥30%), siempre condicionadas al margen absoluto. Fuerza descriptiva `weak` (<0.5), `moderate` (0.5–<0.75), `strong` (≥0.75). Fiabilidad `insufficient` o `nominal` según cobertura. Solo épocas cerradas con 48 comparables exportan clases de pérdidas; no exportar momentos, coeficientes ni pérdidas parciales reversibles.
- Subpresupuestos de 256 KiB para bloque de conocimiento durable y 256 KiB para proyección con eventos, JSON compacto UTF-8 `allow_nan=False`. La [fixture de presupuesto](../../experiments/learning/signal-knowledge-pilot/budget.py) ocupa 215577 bytes con 64 perfiles, 192 claims y 64 eventos; no mide RSS ni el resto del host. El techo host existente sigue siendo 2 MiB. Se rechaza un guardado que supere el límite combinado antes de sustituir el archivo anterior; no se descarta memoria de otros subsistemas para hacerlo caber. El estudio integrado medirá bloque real, RAM, host completo y journal con su retención existente.

### Semántica cerrada de estados y errores

Un perfil nace sin observaciones y puede contener claims `insufficient`. Un claim admitido pasa a `hypothesis` al cerrar su primera época comparable, sin que ello afirme ventaja; solo la racha favorable permite apoyo. El render distingue explícitamente «hipótesis sin ventaja demostrada» de «apoyada». Una contradicción de un claim antes apoyado conserva identidad; una nueva evaluación no borra su revisión histórica. Al restaurar se conservan identidad, revisión y épocas cerradas, pero no se puntúa hasta recuperar continuidad y entrenamiento. Una hipótesis de cambio cuyo ancla transitoria se perdió se marca `stale` con razón `restored_discontinuity` y abre nueva revisión al establecer un ancla futura; no se finge continuidad exacta de ese contraste.

Razones permitidas: `insufficient_observations`, `insufficient_coverage`, `initial_evidence`, `prospective_advantage`, `no_incremental_advantage`, `recent_contradiction`, `regime_changed`, `no_recent_trials`, `restored_discontinuity`, `invalid_observation`, `censored_target`, `evicted`, `budget_rejected`, `revision_limit`, `event_overflow`. No se aceptan razones/textos arbitrarios. Eventos globales de presupuesto/desbordamiento llevan `claim_id=null`; los demás referencian un claim exacto. El estado completo permite reconectar aunque se haya omitido un evento por límite.

IDs de señal y claim: longitud fija conforme a §2; capacidad de entrada al límite privado, token no vacío de hasta 512 caracteres sin espacios. Clave privada: 32 bytes, representada en checkpoint por 64 dígitos hex. Rechazar duplicados, booleanos usados como enteros, clases desconocidas y referencias no existentes antes de aplicar un batch o restore. Un valor de lectura inválido se censura; una estructura mal formada rechaza la operación completa. Si una operación numérica produce overflow/no finito, se censura ese trial y no se actualiza el predictor con el resultado corrupto. La restauración rechaza campos inesperados y estados contradictorios; no intenta repararlos silenciosamente.

### Condición de entrega

Estas decisiones fijan el comportamiento a implementar, no certifican su funcionamiento. El cierre de implementación requiere todos los casos de §10, matriz de cobertura del plan, pruebas de migración adversarial y privacidad, comparación motor/runtime, QA visual desktop/móvil y SSE/replay. El piloto, sus cinco pruebas y la fixture de bytes no sustituyen esas puertas de aceptación. No se reducirá el alcance para acomodar lo que resulte fácil de demostrar.

## Fuentes del repositorio

[`AGENTS.md`](https://github.com/alessbarb/symbiont-lab/blob/main/AGENTS.md) · [`runtime.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/core/orchestration/runtime.py) · [`narrative.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/core/foundation/narrative.py) · [`adaptive.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/host/adaptive.py) · [`drift.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/host/drift.py) · [`consolidation.py`](https://github.com/alessbarb/symbiont-lab/blob/main/src/symbiont/core/cognition/consolidation.py) · [`adapter.py`](https://github.com/alessbarb/symbiont-lab/blob/main/observatory/adapter.py) · [`snapshot.schema.json`](https://github.com/alessbarb/symbiont-lab/blob/main/observatory/snapshot.schema.json) · [`senses.js`](https://github.com/alessbarb/symbiont-lab/blob/main/observatory/render/senses.js) · [`inspector.js`](https://github.com/alessbarb/symbiont-lab/blob/main/observatory/render/inspector.js).

---

# Digital Body Schema & Emergent Morphology

## Status

Proposed design.

This document defines the architecture for giving Symbiont a substrate-native form of self-perception and replacing Observatory's fixed cell metaphor with an emergent digital morphology.

The design deliberately separates three different things:

1. **the organism as it actually exists**;
2. **the organism's learned representation of itself**;
3. **the human-facing visualization produced by Observatory**.

These must never be silently collapsed into the same representation.

---

# 1. Motivation

Observatory currently represents an individual Symbiont using a fixed SVG cell-like outline.

That shape is a visualization metaphor chosen by the interface. It is not produced by the organism and does not represent anything Symbiont knows about itself.

The current organism already maintains a limited `SelfModel`, but that model describes only properties of its sensory apparatus such as:

- health,
- confidence,
- cost,
- maturity,
- recency.

It does not yet contain an explicit concept of:

- organism identity,
- body boundary,
- internal parts,
- functional dependencies,
- cognitive regions,
- global viability,
- organism continuity.

The next step is therefore not to decide whether Symbiont is a cell, sphere, graph or blob.

The next step is to introduce a **Digital Body Schema**.

The central idea is:

> A Symbiont has no intrinsic Euclidean shape. It has an organization.

Observatory may translate that organization into geometry, but the geometry is a projection.

---

# 2. Core distinction

The architecture defines three epistemic layers.

```text
ACTUAL ORGANISM
    │
    │ observable state
    ▼
PHENOTYPE PROJECTION
    │
    │ human visualization
    ▼
OBSERVATORY
```

and independently:

```text
ACTUAL ORGANISM
    │
    │ internal evidence
    ▼
BODY SCHEMA LEARNING
    │
    ▼
SELF MODEL
    │
    │ exported representation
    ▼
OBSERVATORY SELF VIEW
```

The Observatory therefore exposes two distinct views:

```text
[ Phenotype ] [ Self ]
```

## Phenotype View

Represents what the scientific apparatus can legitimately observe about the organism.

It may use:

- genome identity,
- current cognitive topology,
- sensory development,
- memory state,
- safety state,
- runtime state,
- health summaries,
- topology revision.

It is the external scientific view.

## Self View

Represents only what the organism currently knows or believes about itself.

It must use only the organism's exported self-representation.

Observatory must not fill missing knowledge using privileged runtime information.

This creates a meaningful distinction between:

```text
what I am
```

and:

```text
what I think I am
```

---

# 3. Design principle: no perfect introspection

The Body Schema must not simply expose the runtime's internal structures to cognition.

This would be invalid:

```python
body_schema.parts = cognitive_graph.nodes
body_schema.dependencies = cognitive_graph.edges
```

because it gives the organism perfect administrative introspection.

Instead, self-perception must be evidence-based.

```text
experience
   │
   ▼
evidence about own functioning
   │
   ▼
self hypotheses
   │
   ▼
consolidation
   │
   ▼
BodySchema
```

The organism should be able to be:

- incomplete about itself,
- uncertain about itself,
- temporarily wrong about itself,
- more knowledgeable about some regions than others.

That is not a defect.

It is part of the research model.

---

# 4. Digital body

A digital body is defined as the bounded organization whose continued operation constitutes the individual Symbiont.

It is not identical to the host computer.

It is not identical to the operating-system process.

It is not identical to the checkpoint.

Conceptually:

```text
HOST
  │
  ▼
computational substrate

RUNTIME
  │
  ▼
execution of organism

ORGANISM
  │
  ▼
persistent developmental individual

BODY SCHEMA
  │
  ▼
organism's representation of itself
```

The body boundary is therefore functional rather than geometric.

---

# 5. Initial body domains

The Body Schema is divided into five domains.

## 5.1 Identity

Represents continuity of the individual.

```text
identity
├── organism_id
├── genome_id
├── lineage_id
├── developmental_age_class
└── continuity_state
```

The organism does not need access to implementation-specific identifiers unless they form part of its explicit identity model.

---

## 5.2 Boundary

Represents the organism's current distinction between self and environment.

```text
boundary
├── known_self
├── known_environment
├── uncertain
└── future: other_organism
```

Membership should be learned or derived from bounded evidence.

Possible states:

```text
SELF
NON_SELF
UNCERTAIN
```

Future ecology adds:

```text
OTHER_SELF
```

---

## 5.3 Parts

A body part is a stable functional component represented by the organism.

Initial kinds:

```text
SENSE
COGNITIVE_REGION
MEMORY_REGION
READOUT_REGION
```

Future physiology may add:

```text
METABOLIC_REGION
MAINTENANCE_REGION
REPRODUCTIVE_REGION
```

Suggested internal model:

```python
@dataclass(slots=True)
class BodyPartState:
    part_id: str
    kind: BodyPartKind
    existence_confidence: float
    health: float
    functional_importance: float
    activity_class: ActivityClass
    recency_class: RecencyClass
    uncertainty: float
```

No geometry is stored.

Geometry belongs to Observatory.

---

# 6. Functional dependencies

A list of parts is not enough to form a body schema.

The organism must gradually learn relationships such as:

```text
part A contributes to part B
part C degrades when part D fails
part E is usually active before part F
part G supports organism viability
```

The self-model therefore includes bounded dependencies.

```python
@dataclass(slots=True)
class BodyDependency:
    source_id: str
    target_id: str
    relation: DependencyKind
    confidence_class: int
    support_class: int
```

Initial relation kinds should remain intentionally weak:

```text
SUPPORTS
CO_ACTS_WITH
PRECEDES
DEGRADES_WITH
UNKNOWN_DEPENDENCE
```

Avoid prematurely encoding causal semantics.

---

# 7. Global organism state

The schema also represents organism-level internal state.

Initial fields:

```text
global_state
├── self_model_confidence
├── integrity
├── stress
├── maintenance_load
├── dormancy_pressure
└── viability
```

Future physiology can add:

```text
metabolic_balance
resource_deficit
waste_pressure
repair_pressure
reproductive_readiness
```

These values should be:

- bounded,
- coarse,
- learned or computed from permitted internal evidence,
- checkpoint-safe,
- non-identifying.

---

# 8. Relationship with current SelfModel

The existing `SelfModel` should not be deleted.

It becomes one evidence source feeding the broader Body Schema.

```text
SelfModel
   │
   │ sensory health / cost / confidence
   ▼
BodySchemaEngine
```

The responsibilities remain distinct:

```text
SelfModel
→ how individual senses are doing

BodySchema
→ what parts of myself I believe exist and how they relate
```

This prevents a large, monolithic self-model.

---

# 9. BodySchemaEngine

Introduce:

```text
src/symbiont/core/embodiment/body_schema.py
```

Suggested architecture:

```text
AdaptiveSenseModel ───────┐
SelfModel ────────────────┤
CognitiveBridge ──────────┤
MemoryConsolidator ───────┤
Runtime outcomes ─────────┤
SafetyState ──────────────┤
                           ▼
                    BodySchemaEngine
                           │
                           ▼
                       BodySchema
```

The engine receives bounded observations about the organism.

It must not receive arbitrary references to runtime internals.

---

# 10. First learning scope

The first implementation should be intentionally narrow.

## Phase A — Sensory body

The organism may learn:

```text
these senses belong to me
this sense is reliable
this sense is unhealthy
this sense is costly
this sense appears persistent
```

This can be built almost entirely from the existing `SelfModel`.

## Phase B — Cognitive regions

The organism begins learning coarse internal regions.

It should not be told:

```text
concept_0000000000000003
```

Instead, stable topology may be grouped into opaque regions:

```text
region.01
region.02
region.03
```

Region identity must remain persistent enough for longitudinal learning.

## Phase C — Dependencies

The organism learns that internal regions appear functionally related.

## Phase D — Global integrity

The organism forms a coarse model of:

```text
healthy
strained
unstable
recovering
dormant
```

---

# 11. Checkpoint representation

The Body Schema is persistent learned state.

Suggested checkpoint namespace:

```json
{
  "body_schema": {
    "schema_version": 1,
    "identity": {},
    "parts": [],
    "dependencies": [],
    "global_state": {}
  }
}
```

Requirements:

- bounded number of parts,
- bounded number of dependencies,
- quantized values,
- no raw activation history,
- no exact host readings,
- no runtime object names unless intentionally exposed,
- no implementation paths,
- no arbitrary strings originating from host resources.

---

# 12. Observatory projection architecture

Observatory must never directly convert `BodySchema` into internal cognition.

Its role remains passive.

The new individual visualization becomes:

```text
                 Observable organism state
                          │
                          ▼
                 MorphologyProjection
                          │
               ┌──────────┴──────────┐
               ▼                     ▼
          Phenotype View         Self View
```

The projection is visual only.

It is not persisted back into Symbiont.

---

# 13. Emergent morphology

The current fixed cell boundary is replaced by a deterministic morphology generator.

No `cellPath` constant should remain.

Suggested input:

```typescript
interface PhenotypeMorphologyInput {
  identitySeed: string
  senseCount: number
  conceptCount: number
  readoutCount: number
  edgeCount: number
  topologyRevision: number
  health: number | null
  confidence: number | null
  frozen: boolean
}
```

The output remains geometry:

```typescript
interface MorphologyGeometry {
  boundaryPath: string
  senseAnchors: Point[]
  internalAnchors: Point[]
  coreAnchor: Point
}
```

---

# 14. Stable morphology identity

The organism should not change visual identity on every frame.

The basal contour must derive from a stable seed.

Preferred order:

```text
genome hash
+
organism identity
```

The genome defines inherited morphology characteristics.

The organism identity prevents genetically identical siblings from becoming visually indistinguishable.

Conceptually:

```text
genome
  │
  ├── inherited base morphology
  │
organism identity
  │
  └── individual variation
            │
            ▼
     stable basal shape
```

Developmental state produces small changes around that baseline.

---

# 15. Morphology semantics

Possible projection mapping:

| Organism property    | Visual representation         |
| -------------------- | ----------------------------- |
| Genome / identity    | stable base contour           |
| Sense                | peripheral receptor           |
| Active sense         | open / luminous receptor      |
| Probing sense        | intermittent receptor         |
| Dormant sense        | contracted receptor           |
| Concept              | internal region               |
| Readout              | integrative core              |
| Cognitive edge       | internal fibre                |
| Edge weight          | fibre intensity               |
| Health               | boundary integrity            |
| Confidence           | visual clarity                |
| Stress               | contour tension / contraction |
| Frozen state         | reduced motion / desaturation |
| Topology change      | slow structural rearrangement |
| Memory consolidation | persistent internal texture   |
| Pruning              | gradual disappearance         |
| New structure        | controlled growth             |

No biological organ names should be used in the data model.

---

# 16. Phenotype View

This view is allowed to display the actual observable phenotype.

Example for the historical worker-3 checkpoint:

```text
Phenotype

58 SENSE
5 CONCEPT
1 READOUT
0 EDGES
topology revision 29
```

The resulting morphology should visibly show:

- many peripheral receptors,
- five disconnected internal regions,
- a central readout region,
- no fabricated connectivity.

A graph with zero edges must look disconnected.

The visualization must never invent structure for aesthetics.

---

# 17. Self View

The Self View must be driven exclusively by:

```text
body_schema
```

During the transition period, before `BodySchema` exists, it may use only the current exported `SelfModel`.

It should explicitly indicate:

```text
BODY SCHEMA
not yet developed
```

rather than reconstructing the missing schema from topology.

This is especially important for organisms such as worker-3, where actual graph structure and self-modelled sensory state diverge.

---

# 18. Self/Phenotype divergence

Observatory should eventually distinguish four cases:

```text
REAL + KNOWN
REAL + UNKNOWN
BELIEVED + UNCONFIRMED
BELIEVED + CONTRADICTED
```

Suggested visual language:

```text
solid          = known
faint          = real but not self-modelled
dashed         = uncertain
fragmented     = contradicted
```

This is one of the scientifically valuable outputs of the design.

---

# 19. Refactoring Observatory

The current `observatory/app.js` has accumulated too many responsibilities.

Before implementing the complete Body Schema visualization, it should be decomposed.

Current responsibilities include:

- demo state,
- application state,
- SVG helpers,
- senses rendering,
- organism rendering,
- population rendering,
- inspector,
- timeline,
- replay,
- snapshot normalization,
- snapshot bounds checking,
- cognition rendering,
- SSE fleet connection,
- event history,
- UI actions.

This makes morphological evolution risky.

The refactor should happen as part of this work, not afterwards.

---

# 20. Proposed Observatory structure

```text
observatory/
│
├── app.js
│
├── state/
│   ├── store.js
│   ├── demo-state.js
│   └── selectors.js
│
├── transport/
│   ├── fleet-stream.js
│   ├── instance-stream.js
│   └── replay.js
│
├── projection/
│   ├── snapshot.js
│   ├── cognition.js
│   ├── morphology.js
│   └── self-schema.js
│
├── render/
│   ├── svg.js
│   ├── organism.js
│   ├── phenotype.js
│   ├── self.js
│   ├── senses.js
│   ├── population.js
│   ├── inspector.js
│   ├── timeline.js
│   └── cognition.js
│
├── ui/
│   ├── controls.js
│   ├── profiles.js
│   ├── drawers.js
│   └── dialogs.js
│
└── ...
```

`app.js` becomes composition only.

---

# 21. Target app.js

After refactor, `app.js` should be approximately orchestration code:

```javascript
import { createStore } from "./state/store.js";
import { createDemoState } from "./state/demo-state.js";
import { connectFleet } from "./transport/fleet-stream.js";
import { bindControls } from "./ui/controls.js";
import { renderApp } from "./render/app.js";

const store = createStore(createDemoState());

store.subscribe(state => {
  renderApp(state);
});

bindControls(store);
connectFleet(store);
```

The goal is not a specific line count.

The goal is that `app.js` no longer contains domain logic.

---

# 22. Pure morphology module

Create:

```text
observatory/projection/morphology.js
```

It must be deterministic and side-effect free.

Example API:

```javascript
export function projectPhenotypeMorphology(input) {
  return {
    boundary,
    receptors,
    regions,
    core,
  };
}
```

Tests must verify:

```text
same input → same morphology
same identity → stable base morphology
topology revision change → bounded shape evolution
frozen state → no structural invention
0 edges → no rendered fibres
```

---

# 23. Separate rendering from projection

Do not calculate organism structure inside SVG rendering code.

Bad:

```javascript
function renderOrganism() {
  // infer biology
  // create geometry
  // inspect cognition
  // manipulate DOM
}
```

Preferred:

```text
raw state
   │
   ▼
projection
   │
   ▼
geometry model
   │
   ▼
renderer
```

Example:

```javascript
const model = projectPhenotype(state);
renderPhenotype(canvas, model);
```

The renderer receives already-resolved semantics.

---

# 24. New morphology mode state

Add:

```javascript
state.organismView = "phenotype";
```

Allowed values:

```text
phenotype
self
```

UI:

```html
<div class="organism-view-toggle">
  <button data-organism-view="phenotype">Phenotype</button>
  <button data-organism-view="self">Self</button>
</div>
```

This toggle belongs inside the individual view, not in the global `Individual / Population` selector.

Hierarchy:

```text
Individual
    ├── Phenotype
    └── Self

Population
```

---

# 25. Observatory self projection

Create:

```text
observatory/projection/self-schema.js
```

It receives only exported self-model data.

No topology fallback.

Example:

```javascript
export function projectSelfMorphology(bodySchema) {
  if (!bodySchema) {
    return {
      state: "undeveloped",
      parts: [],
      dependencies: [],
    };
  }
}
```

The renderer must explicitly support:

```text
undeveloped
partial
developed
```

---

# 26. Topology source

The Phenotype view may use Observatory topology data.

The Self view must not.

This distinction must be tested.

Example invariant:

```text
topology.nodes = 64
body_schema.parts = 12

Phenotype view → may show 64 structural elements
Self view      → may show only 12 represented parts
```

No implicit merge.

---

# 27. SVG vocabulary cleanup

Rename existing cell-specific concepts.

```text
cellPath
→ phenotypeBoundary

cell-fill
→ organism-fill

membrane
→ phenotype-boundary

membrane-inner
→ phenotype-boundary-inner
```

The word `membrane` should only remain if used explicitly as a visual metaphor, not as a domain concept.

---

# 28. Accessibility

The visual distinction must have a textual equivalent.

Accessible table should eventually include:

```text
Perspective
Part
Type
Known to organism?
Confidence
Health
Relation
```

Example:

```text
Phenotype | sense_123 | sense | no | — | healthy
Self      | part.07   | sense | yes | high | healthy
```

Color must not be the only carrier of meaning.

---

# 29. Observatory schema evolution

The snapshot contract should eventually add an optional self-model section.

Possible v3:

```json
{
  "schema_version": 3,
  "organism": {
    "cognition": {},
    "self": {
      "body_schema": {}
    }
  }
}
```

Do not force this into v2 if doing so weakens version semantics.

Preferred rule:

```text
v1 → no cognition
v2 → cognition
v3 → cognition + optional/required body schema according to contract
```

The exact compatibility rule should be made explicit in JSON Schema.

---

# 30. Research invariants

The implementation must preserve the following invariants.

## I1 — No false self-knowledge

Observatory must never synthesize body-schema knowledge from privileged topology.

## I2 — Visualization is one-way

Morphology never feeds back into cognition.

## I3 — Stable identity

The same organism should not appear as a completely different morphology between adjacent ticks without a corresponding developmental event.

## I4 — Developmental change is bounded

Morphological change must reflect real state changes and remain temporally smooth.

## I5 — No fabricated connectivity

If the graph has zero edges, no apparent cognitive connections are drawn.

## I6 — Self can be incomplete

Missing BodySchema data is valid.

## I7 — Self can disagree with phenotype

Divergence is preserved rather than corrected by the Observatory.

## I8 — Human geometry is not organism knowledge

SVG coordinates are never exposed back to Symbiont.

---

# 31. Development phases

## Phase 1 — Observatory refactor

No behavioral change.

Tasks:

- split `app.js`,
- isolate store,
- isolate snapshot projection,
- isolate SVG helpers,
- isolate render modules,
- maintain existing UI behavior,
- preserve replay/SSE semantics.

Exit condition:

> Observatory behaves identically to the current version with the old visual model, but rendering and projection are modular.

---

## Phase 2 — Phenotype morphology

Replace fixed cell.

Tasks:

- deterministic morphology seed,
- generated phenotype boundary,
- peripheral sensory layout,
- internal concept/readout layout,
- topology-derived fibres,
- health/safety visual modulation.

Exit condition:

> Two organisms with different phenotype/identity can visibly differ without invented structure.

---

## Phase 3 — Individual perspective toggle

Introduce:

```text
Phenotype | Self
```

Self initially displays:

```text
Body schema not yet developed
```

where no body schema is exported.

Exit condition:

> Observatory explicitly distinguishes scientific view from organism self-view.

---

## Phase 4 — Sensory BodySchema

Implement in organism:

```text
src/symbiont/core/embodiment/body_schema.py
```

Initial scope:

- sensory parts only,
- membership,
- health,
- confidence,
- recency,
- global schema confidence.

Exit condition:

> The organism can represent a subset of its own sensory apparatus without being handed the complete runtime topology.

---

## Phase 5 — Cognitive regions

Introduce coarse learned internal regions.

Exit condition:

> Symbiont can represent internal cognitive organization using opaque region identities.

---

## Phase 6 — Functional dependencies

Add learned relationships between body parts.

Exit condition:

> Self View can show organism-inferred internal structure rather than only parts.

---

## Phase 7 — Physiology integration

Connect BodySchema to Milestone F.

Add:

- stress,
- maintenance,
- dormancy,
- viability,
- metabolic state.

At this point the Body Schema becomes the organism's functional digital body model.

---

# 32. Testing strategy

## Unit tests

### Morphology

```text
same seed = same boundary
different identity = distinguishable boundary
health does not change identity
edge count controls fibres
no edge means no fibre
```

### BodySchema

```text
bounded parts
bounded dependencies
unknown part remains unknown
self membership does not come from evaluator
confidence evolves with evidence
checkpoint round-trip preserves consolidated schema
```

## Contract tests

Validate:

```text
v1
v2
v3
```

and reject illegal cross-version combinations.

## Integration tests

Example protocol:

```text
organism develops senses
→ SelfModel stabilizes
→ BodySchema discovers sensory parts
→ Observatory receives body_schema
→ Self View renders only known parts
```

## Adversarial tests

Ensure Observatory cannot:

```text
read phenotype topology
and silently insert it into Self View
```

---

# 33. Worker-3 validation protocol

Use the existing worker-3 checkpoint as the first reference case.

Expected phenotype:

```text
58 senses
5 concepts
1 readout
0 edges
```

Expected initial self view:

```text
partial sensory self-model
no complete cognitive body schema
```

The visualization should therefore show a visible mismatch.

This becomes a regression fixture for the core principle:

> Phenotype truth and self-perception are not the same data source.

---

# 34. Future extensions

The design intentionally supports later milestones.

## Digital physiology

Body Schema can represent:

```text
metabolism
maintenance
stress
waste pressure
viability
```

## Reproduction

Body Schema can later represent:

```text
lineage
reproductive maturity
offspring relation
continuity before/after fission
```

## Ecology

The boundary model gains:

```text
SELF
ENVIRONMENT
OTHER_SELF
```

This enables studying whether Symbiont distinguishes:

```text
me
world
other organism
```

without hand-coding social identity directly into cognition.

---

# 35. Long-term research question

The final objective is not to create a prettier visualization.

The objective is to make this measurable:

```text
actual organism
       │
       ├───────────────┐
       ▼               ▼
what it is       what it believes it is
       │               │
       └───────┬───────┘
               ▼
          divergence
```

That divergence may itself become a scientific observable.

A mature Symbiont should not necessarily have perfect self-knowledge.

It should have a developed, revisable and bounded model of itself.

---

# 36. Recommended implementation sequence

The recommended PR sequence is:

```text
PR 1
refactor(observatory): split state, projection and render layers

PR 2
feat(observatory): replace fixed cell with deterministic phenotype morphology

PR 3
feat(observatory): add phenotype/self perspective

PR 4
feat(self): introduce sensory digital body schema

PR 5
feat(observatory): render organism-owned body schema

PR 6
feat(self): learn coarse cognitive regions and dependencies
```

Do not combine all six into one PR.

The main architectural rule is:

> **The Observatory may know more about a Symbiont than the Symbiont knows about itself, but it must never pretend that privileged knowledge belongs to the organism.**

And the corresponding visual rule is:

> **Morphology represents organization. Geometry is a projection, not the organism's ontology.**

---

# Contrato de restauración recurrente de Symbiont

**Estado:** propuesta arquitectónica para revisión e incorporación al repositorio. **Alcance:** checkpoint actual de `CognitiveGraph` y continuación de `OrganismRuntime`. **Procedencia:** resultados de `continuity.recurrent-restoration` comunicados el 15 de septiembre de 2026 (tres semillas: 42, 123, 777) y observaciones de los dos ZIP de ejecución analizados antes.

## Decisión de contrato

Un checkpoint actual es una **continuación del organismo desde estado persistido con reinicio de la dinámica recurrente y reconstrucción discreta de parámetros**. Preserva los campos que el esquema de checkpoint exporta y restaura, pero **no promete continuación idéntica al proceso que nunca se detuvo**. La salida puede mostrar una discontinuidad inicial. Si hay aprendizaje o consolidación activa, el estado posterior puede seguir una trayectoria de pesos o topología distinta de la ejecución continua aun cuando ambos estados sean válidos.

La expresión «arranque en frío» se refiere a activaciones/buffers/trazas no persistidos. «Aproximación discreta de parámetros» se refiere a pesos guardados mediante `weight_class`. Esos dos efectos son conceptualmente distintos y deben declararse por separado. El checkpoint no equivale a una copia bit a bit del estado del proceso.

Este contrato no convierte las mediciones de un laboratorio de tres semillas en garantías universales de tiempo de estabilización, error estacionario o cambio de linaje. El rendimiento cuantitativo depende del grafo, estímulos, parámetros, punto de corte y versión del kernel. Las garantías universalmente documentables se limitan a qué estado se conserva, qué se reinicializa, cómo se reconstruyen parámetros y cuál es la identidad/procedencia de la ejecución reanudada.

## Dos modos de uso

| Uso | Qué puede esperar el operador | Qué debe observar |
| --- | --- | --- |
| Residente: reanudar tras parada/reinicio | Persistencia de los campos declarados; arranque dinámico en frío; evolución posterior válida bajo las reglas del organismo | Nuevo `run_id`, checkpoint de origen, versión y revisión; inicio de readouts y cambios de trayectoria |
| Laboratorio: estudiar continuidad | Comparación controlada entre ejecución continua y restaurada a partir del mismo corte y estímulos futuros | Error temporal de readout, estado dinámico, deriva de parámetros, mutaciones/topología y límites de observación |

El laboratorio puede usar una copia completa en memoria para comprobar paridad exacta y aislar causas; **ese control no cambia las garantías del checkpoint residente**. Una futura opción de restauración exacta, si se implementa, debe especificarse como formato/modo diferente y demostrar que conserva todo el estado que afecta a la evolución futura.

## Frontera temporal

Un checkpoint declara un punto de corte **después de completar el tick T**. Al reanudar, el siguiente estímulo se consume en T+1. Deben registrarse el tick T, la identidad durable del organismo, el `run_id` y `sequence` del último evento confirmado si existen, revisión topológica, versión del esquema, identidad efectiva del kernel y procedencia del checkpoint. Un `run_id` nuevo identifica el flujo de transporte reanudado; `display_id` por sí solo no demuestra que dos runs sean una misma vida.

Si el formato actual no puede registrar todos esos campos, constituyen requisitos de trazabilidad de la Prioridad 4, no garantías ya implementadas. No debe inferirse el punto de corte de fechas ZIP, heartbeat o nombre del archivo. Para comparar trayectorias, ambas ramas deben recibir exactamente los mismos estímulos a partir de T+1.

## Estado conservado y estado reinicializado

La lista exacta de campos es la definida por los esquemas de checkpoint de la versión instalada y la implementación `export_checkpoint/restore`. En los ZIP previamente analizados, `cognitive_bridge` conserva grafo/topología, linajes, tiempos de algunos ciclos de vida, normalizadores, leases sensoriales y estado de seguridad; el genoma conserva parámetros de plasticidad. Los archivos no muestran activaciones, `previous_frame`, buffers de retardos ni valores dinámicos de elegibilidad por arista. Las aristas del checkpoint muestran clases de peso, no pesos exactos.

| Categoría | Contrato para el formato observado | Efecto al reanudar |
| --- | --- | --- |
| Estructura y conocimiento exportados | Se reconstruyen conforme al esquema y validación de la versión compatible | Permanecen disponibles, sujetos a la fidelidad de sus campos |
| Pesos guardados como clases | Se reconstruyen mediante el cuantizador de la versión (`WEIGHT_CLASSES=16`, `WEIGHT_RANGE=(-2.0, 2.0)`) | Puede variar la función de transferencia incluso con topología idéntica |
| Activaciones y frame anterior | No están en los checkpoints inspeccionados | Se inicializan según el kernel (`previous_frame={}`); puede haber un salto de readout |
| Buffers de retardo | No están en los checkpoints inspeccionados | Se inicializan según el kernel; se pierde el contenido temporal anterior |
| Valores actuales de trazas de elegibilidad | No están en los checkpoints inspeccionados | Se inicializan a cero (`eligibility=0.0`) según el kernel y cambian las actualizaciones futuras si había trazas no nulas |
| Coeficiente de decaimiento de elegibilidad | Forma parte del genoma (`plasticity.eligibility_decay`) | Mantiene su valor configurado; **no debe describirse como `λ=0`** |
| Estado aleatorio, acumuladores y datos de runtime adicionales | Requieren inventario en el código vigente | No se promete paridad exacta hasta comprobar todo estado que afecta a los siguientes ticks |

La frase precisa para elegibilidad es: «**el valor de las trazas no persistidas se inicializa al restaurar (`eligibility=0.0`)**». El valor inicial procede de la implementación verificada y no debe confundirse con el coeficiente `eligibility_decay` del genoma. Tampoco se deben declarar perdidas trazas o variables de otros subsistemas sin inspeccionar sus esquemas.

## Evidencia experimental disponible

El estudio de laboratorio `continuity.recurrent-restoration` compara A (continuo), B (copia completa en memoria), C (checkpoint real) y D (restauración experimental con pesos exactos y dinámica reiniciada). La comparación B/A presenta paridad en los tres niveles evaluados. D conserva los pesos exactos para aislar el efecto de reiniciar dinámica; C añade el efecto del checkpoint discreto **si C y D reconstruyen idénticamente todos los demás campos**.

| Nivel medido, tres semillas | B frente a A | D frente a A | C frente a A |
| --- | --- | --- | --- |
| Dinámica fija, aprendizaje congelado | Divergencia reportada 0 | Máxima diferencia inicial ~0,23; umbral <10⁻⁴ alcanzado en promedio en 8,67 ticks; error final ~10⁻¹⁵ | Error residual reportado ~0,0627; no alcanza el umbral 10⁻⁴ en el horizonte evaluado |
| Plasticidad activa, topología fija | `Δw=0`, `Δq=0` reportados | Deriva residual de peso ~0,00104 atribuida al periodo de activaciones distintas | Deriva reportada de peso ~0,06255 y de elegibilidad ~0,1634 |
| Desarrollo estructural activo | Misma trayectoria y revisiones reportadas | Coincide en las primeras consolidaciones del experimento; se comunica deriva tardía en horizontes largos | Primera consolidación posterior al corte, tick 48, divergente en las tres semillas evaluadas |

La pérdida de `previous_frame` produce, en D y en los tres grafos/estímulos ensayados, un transitorio que se reduce. De ello **no se infiere que todo `CognitiveGraph` sea contractivo**. En C, el residual y la bifurcación observados son compatibles con cambios paramétricos por cuantización; la causalidad «100% pesos» requiere demostrar identidad de C y D en todo el resto del estado restaurado o realizar ablaciones adicionales.

«Tres de tres semillas difieren en la primera consolidación» es la formulación respaldada por esos datos. «La bifurcación es inevitable para cualquier checkpoint» no lo es. Con topología fija y plasticidad activa, la deriva puede persistir aunque el error de salida vuelva a disminuir: convergencia de readout y paridad de aprendizaje son propiedades separadas.

## Límites de cualquier garantía numérica

No se declara como garantía general «transitorio disipado en ≤12 ticks». La media observada de 8,67 ticks para un umbral 10⁻⁴ en tres semillas **no es una cota superior**, ni incluye todos los grafos recurrentes admisibles. Una cota válida debe declarar norma, horizonte, estados iniciales, estímulos, topologías y parámetros permitidos, y demostrar o verificar suficientemente su condición de estabilidad.

Si, para un dominio acotado, la transición con pesos fijos satisface

$$
\|F_W(x,u)-F_W(y,u)\|\le L\|x-y\|,\quad 0\le L<1,
$$

entonces dos trayectorias con **los mismos pesos y estímulos** cumplen

$$
\|x_t-y_t\|\le L^t\|x_0-y_0\|.
$$

Este razonamiento sólo aplica mientras topología y parámetros relevantes permanezcan fijos y el estado comparable incluya buffers, activaciones y cualquier otra variable recurrente. La aparición de ciclos retardados no demuestra ni refuta por sí sola la condición ($L<1$). Un ensayo empírico que alcanza un umbral no prueba la desigualdad para todos los estados.

Con pesos aproximados $\widehat W$, si además existe una perturbación por paso uniformemente acotada $\delta$ tal que

$$
\|F_W(x,u)-F_{\widehat W}(x,u)\|\le\delta,
$$

la comparación puede acotarse condicionalmente por

$$
\|x_t-y_t\|\le L^t\|x_0-y_0\|+\delta\frac{1-L^t}{1-L}.
$$

El residual de estado se limita entonces por $\delta/(1-L)$; el error de readout necesita **otra** cota de sensibilidad de la salida.

En la implementación actual (`symbiont.cognition.checkpoint`), el cuantizador usa `WEIGHT_CLASSES = 16` sobre `WEIGHT_RANGE = (-2.0, 2.0)`. La discretización asigna:

$$
\text{class\_id} = \text{round}\left(\frac{\text{clipped} - \text{low}}{\text{high} - \text{low}} \cdot (N - 1)\right) = \text{round}\left(\frac{w - (-2.0)}{4.0} \cdot 15\right)
$$

El paso uniforme entre niveles es $\Delta w = 4.0 / 15 \approx 0.266667$. El cero exacto no es un punto de la rejilla (las clases 7 y 8 corresponden respectivamente a $-0.133333$ y $+0.133333$). Por ello, cualquier peso cercano a 0 se desplaza al menos $0.133333$ en magnitud al cuantizarse.

## Compatibilidad, fallo y observabilidad

Un checkpoint debe validar versión de esquema, compatibilidad de kernel/genoma, integridad numérica, identidad de nodos/aristas y estados temporales persistidos antes de reanudar. Si falla la validación o la aplicación, debe conservar intacto el checkpoint original y emitir un fallo observable.

Los consumidores —incluido Observatory— deben poder distinguir: ejecución continua, ejecución reanudada desde checkpoint y experimento de laboratorio. Una primera salida cero al empezar un nuevo run no debe atribuirse automáticamente a lesión cognitiva: en topologías con retardos $\ge 1$ entre sentidos y readouts, la primera salida tras un arranque dinámico en frío es estructuralmente 0 mientras la señal transita por las capas latentes. La vista Self sólo puede mostrar lo que se haya incorporado al conocimiento propio del organismo; la advertencia de restauración y el origen técnico del checkpoint pertenecen a la instrumentación externa.

La telemetría mínima necesaria para la Prioridad 4 es: `organism_id`, `run_id`, `sequence`, tick y revisión del punto de corte, hash/version del checkpoint, `kernel_version`/build efectivo, modo de restauración, campos reiniciados y primer evento confirmado tras reanudar. Una captura coherente debe enlazar registry, journal, topology y checkpoint sin tratarlos como una transacción global si no hubo barrera de exportación.

## Criterio para cerrar la Prioridad 3

1. Incorporar en la documentación del repositorio el contrato de continuación aproximada/arranque dinámico en frío, señalando expresamente que no se garantiza replay exacto de salida, peso o topología.
2. Verificar en el código que C y D sólo difieren en la precisión de peso si se afirma causalidad exclusiva, y revisar los números, normas, umbrales y horizontes comunicados contra el artefacto reproducible del estudio.
3. Inventariar el estado no persistido que determina los próximos ticks y especificar sus valores iniciales al restaurar (`previous_frame={}`, `eligibility=0.0`).
4. Validar guardado/restauración en cortes con buffers ocupados, elegibilidad no nula y antes/después de consolidación. Declarar divergencia de trayectoria donde corresponda, aunque el readout se vuelva a activar.
5. Reservar la cota empírica observada y el supuesto carácter contractivo global para una demostración matemática con dominio explícito o una promesa empírica limitada y validada por separado; no incluirlos como garantía general en este contrato.
