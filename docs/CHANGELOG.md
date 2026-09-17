# Symbiont Lab Changelog

Consolidated from docs/releases/archive/ (140 individual release notes).

---

## v0.80.16 — agencia cultural autónoma bounded

Este corte consolida los avances posteriores al tag `v0.80.15` y añade
Autonomous Cultural Agency v1 en el alcance preregistrado:

- política cultural determinista y organismo-side;
- selección bounded de retención, validación, transmisión, composición y
  silencio sin IDs de contenido suministrados por el arnés;
- trazabilidad checkpointable de decisiones y coste;
- estudio `learning.autonomous-cultural-agency` con replay y auditoría
  adversaria;
- proyección pasiva del Observatory.

Biological Closure v1, Private SLM v1, Cultural Foundation v1 y Cumulative
Culture v1 conservan sus resultados históricos. No se introducen sockets,
acciones de host, transferencia de modelos/corpus ni símbolos/lenguaje.

---

## v0.80.15 — generalización bounded de emergencia K

El gate social evaluator-only amplía la verificación de emergencia autónoma:

- confirma replay determinista del estudio de runtime;
- repite el escenario con poblaciones de 3 y 5 miembros;
- exige interacción multi-par y ausencia de miembros aislados en ambas variantes.

La variación se mantiene en el evaluador. No se inyectan tamaños, etiquetas,
objetivos ni resultados del gate en los organismos.

---

## v0.80.14 — gate de emergencia autónoma K

La matriz social integrada deja de depender únicamente del arnés seeded que
suministra interacciones sintéticas. Ahora incluye una ejecución evaluator-only
de `OrganismRuntime.autonomous_social_step()` en un hábitat acotado.

El gate exige, sin devolver etiquetas al runtime:

- más de un par interactuante;
- entropía de pares positiva;
- ningún miembro aislado;
- observaciones recíprocas presentes.

Esto verifica que las capacidades sociales se ejercitan desde el runtime
autónomo y no solo desde la instrumentación del evaluador.

---

## v0.80.13 — telemetría cognitiva visible en Observatory

El panel de cognición del Observatory muestra, cuando están presentes, los
indicadores pasivos de desarrollo ya definidos por el contrato:

- presión estructural;
- error agregado de cuantización del checkpoint;
- churn de relaciones sensoriales;
- divergencia estructural de la trayectoria de sesión.

Los valores se validan como finitos antes de renderizarse. Las fracciones se
presentan como porcentajes y los valores de error conservan cuatro decimales.
La vista no expone pesos, etiquetas semánticas ni controles de intervención.

---

## v0.80.12 — cobertura social ampliada K

La matriz social integrada incorpora además límites adversariales, competencia
finita y diversidad de interacciones emergentes. Las condiciones se derivan de
estudios evaluator-only ya existentes: rechazo reversible, pérdidas locales,
recursos finitos, pares múltiples y entropía de interacción positiva.

---

## v0.80.11 — gate integrado de milestones I/J/K

Se incorpora una matriz evaluator-only que ejecuta de forma independiente los
gates de fisiología integrada (I), desarrollo predictivo (J) y sociabilidad (K),
y solo compone sus resultados booleanos. No comparte etiquetas, métricas de
verdad terreno ni estado del evaluador con el runtime del organismo.

---

## v0.80.10 — matriz integrada de desarrollo social K

Se incorpora un gate evaluator-only que compone contratos independientes de
Milestone K: límites del hábitat, replay longitudinal, continuidad de linaje,
adaptación de recursos, revisión tras denegaciones y diferenciación de nichos.

Las etiquetas y resultados del evaluador permanecen fuera del runtime; el gate
solo verifica la reproducibilidad y los invariantes de los estudios.

---

## v0.80.09 — sincronización documental de Observatory

La documentación del Observatory describe ahora sus métricas cognitivas pasivas
actuales: presión estructural, error agregado de cuantización, churn de
relaciones sensoriales y divergencia estructural de sesión. Se explicita que
ninguna de ellas controla el runtime ni representa semántica del host.

---

## v0.80.08 — divergencia estructural de desarrollo

Observatory puede publicar `developmental_divergence` cuando el residente
entrega una topología basal explícita. La métrica compara únicamente conjuntos
opacos de nodos y aristas mediante distancia simétrica normalizada en `[0, 1]`;
ignora pesos, activaciones, etiquetas y métricas del evaluador.

La referencia se fija al primer estado estructural de la sesión del residente.
Por tanto es una observación de trayectoria de esa sesión, no una afirmación de
fitness, causalidad ni equivalencia entre organismos. No entra en decisiones del
Symbiont y no se publica cuando no existe una referencia autoritativa.

---

## v0.80.07 — churn pasivo de relaciones sensoriales

Observatory publica `relation_churn` como observación bounded `[0, 1]` del
cambio estructural de relaciones sensoriales desde la última publicación.
Cuenta únicamente altas y expulsiones de pares; actualizar evidencia no altera
la métrica. El contador se drena explícitamente, no se persiste ni retroalimenta
la cognición, y no expone valores ni semántica de las señales.

---

## v0.80.06 — métricas estructurales de Observatory

El contrato cognitivo de Observatory incorpora dos observaciones agregadas y
pasivas:

- `structural_pressure`: ocupación relativa bounded frente a los presupuestos
  de nodos y aristas del genoma;
- `quantization_error`: error medio absoluto introducido por el codec de
  checkpoints sobre las aristas vivas.

Ambas métricas se calculan fuera de `symbiont`, no entran en decisiones del
organismo y no exponen pesos, elegibilidad ni contenido de host. El esquema
rechaza valores negativos y limita la presión estructural a `[0, 1]`.

---

## v0.80.05 — matriz integrada de desarrollo predictivo

Se añade un gate evaluator-only para Milestone J que compone, sin retroalimentar
resultados al organismo:

- cero exacto, zona muerta y preservación de signo del codec;
- rendimiento decreciente de la atención ante una señal ya repetida;
- continuidad de hipótesis y estado tras serialización;
- promoción shadow cuando existe ganancia fuera de muestra;
- rechazo de una señal que no supera persistencia;
- continuidad de la decisión tras checkpoint/replay del runtime.

La matriz no crea predictores directamente desde correlaciones ni introduce
semántica de plataforma.

---

## v0.80.04 — retiro de hipótesis contradichas

El lifecycle de hipótesis sensoriales ahora registra la racha de contradicción y
retira una hipótesis cuando la evidencia validada y la contradicción sostenida
superan dos umbrales bounded (`2 × min_samples` de validación y
`min_samples` actualizaciones contradictorias).

Una hipótesis retirada permanece retirada durante actualizaciones posteriores y
se conserva así en el checkpoint. Esto evita que una asociación estadística
rechazada vuelva a considerarse soportada solo porque una lectura posterior
cambió de signo; la reexploración debe crear una hipótesis nueva con identidad
de relación nueva, no mutar silenciosamente el conocimiento retirado.

---

## v0.80.03 — atención con rendimiento decreciente conectado

La selección de atención sobre capacidades del host pasa el número de muestras
agregadas del baseline al scheduler genérico. Por tanto, la penalización de
rendimiento decreciente se aplica también a señales ya conocidas, en lugar de
quedar disponible solo para callers que construyan `AttentionCandidate`
manualmente.

Las capacidades aún no aclimatadas conservan incertidumbre infinita y prioridad
inicial; cuando alcanzan un baseline bounded, sus observaciones participan en la
reducción de prioridad por repetición. No se introducen etiquetas de host ni
retroalimentación del evaluador.

---

## v0.80.02 — persistencia de hipótesis sensoriales

Las hipótesis de relaciones opacas forman parte ahora del checkpoint agregado
del desarrollo sensorial:

- se conserva el lifecycle (`candidate`, `provisional`, `supported`,
  `contradicted`, `retired`), las muestras y las métricas acotadas;
- la restauración valida identificadores, estado, contadores y valores finitos;
- las entradas duplicadas o corruptas se rechazan antes de entrar en el modelo;
- el payload sigue conteniendo únicamente identidades opacas y estadística
  agregada, nunca valores de host ni etiquetas semánticas.

Esto evita que un reinicio convierta relaciones ya contrastadas en asociaciones
jóvenes o pierda contradicciones registradas.

---

## v0.80.01 — límites de evidencia relacional

El lifecycle de hipótesis sensoriales valida sus entradas antes de actualizar
una relación:

- los dos identificadores deben ser opacos, distintos y bounded;
- `correlation` debe ser finita y pertenecer a `[-1, 1]`;
- muestras, mínimo de muestras y tick deben ser enteros no negativos, con un
  mínimo de tres observaciones para validar una relación;
- los booleanos no se aceptan como números por coerción implícita.

Los valores `None` siguen representando ausencia de una correlación disponible y
no destruyen evidencia previa. El cambio evita que checkpoints o acumuladores
corruptos alteren el estado candidate/provisional/supported/contradicted.

---

## v0.80.00 — límites numéricos de atención

El scheduler de atención valida sus fronteras numéricas antes de ordenar o
consumir presupuesto:

- `AttentionBudget` rechaza presupuestos `NaN`, infinitos, booleanos o no
  positivos.
- `AttentionCandidate` rechaza costes y `rank_cost` no finitos, booleanos o no
  positivos.
- La incertidumbre `NaN` queda excluida; `+inf` sigue siendo válido únicamente
  como señal explícita de una capacidad todavía sin baseline.
- `observations` debe ser un entero no negativo y no booleano.

El cambio evita que valores no comparables hagan que el orden de atención o el
consumo del presupuesto sean indeterministas, sin quitar al organismo la
capacidad de priorizar una señal genuinamente no conocida.

El estudio de promoción predictiva actualiza además su rango explícito de
compatibilidad del kernel para admitir esta release (`<0.81`); no se relaja la
validación de checkpoints de organismos con rangos incompatibles.

---

## v0.79.99 — codec de pesos estricto

El checkpoint cognitivo valida explícitamente la versión del codec y rechaza
versiones desconocidas en lugar de reinterpretarlas. La cuantización de pesos
rechaza valores no finitos y la des-cuantización valida el rango de clases.
Los checkpoints históricos sin versión siguen usando el codec v1; el codec v2
mantiene cero exacto y zona muerta.

---

## v0.79.98 — matriz integrada de gates sociales

Se añade `SocialBoundaryGateStudy`, un arnés evaluator-only que compone los
estudios de cooperación/contención/aislamiento, rechazo reversible, replay de
contexto y continuidad de linaje. La matriz no crea una política social: solo
verifica que los límites del hábitat, la memoria local y el replay mantienen sus
invariantes bajo escenarios sintéticos bounded.

---

## v0.79.97 — estudio adversarial social

El estudio de límites sociales del runtime incorpora una negativa direccional y
su reanudación explícita junto a cooperación, contención finita y aislamiento.
La reposición del recurso es bounded y pertenece solo al hábitat sintético; el
runtime recibe presencia y resultados, nunca la etiqueta del escenario.

---

## v0.79.96 — límites ecológicos bounded

`EcologicalResourcePool` valida ahora tokens textuales bounded y cantidades
finitas al crear recursos, asignar solicitudes y reponer inventario. Los
checkpoints siguen pasando por el mismo constructor, por lo que `NaN`, infinitos,
booleanos y solicitudes ambiguas no pueden alterar la competencia ni escapar
los límites del hábitat. La corrección no introduce política social ni señales
externas.

---

## v0.79.95 — validación estricta de evidencia relacional

La memoria social rechaza ahora identificadores no textuales o excesivamente
largos, valores de beneficio/daño no finitos y ticks ambiguos. La restauración
de checkpoints aplica las mismas restricciones y no acepta `NaN`, infinitos ni
ticks fraccionarios. Esto mantiene los agregados relacionales bounded y evita
que una entrada corrupta altere valencia, fiabilidad o selección contextual.
La validación es local y no introduce etiquetas sociales ni retroalimentación
del evaluador.

---

## v0.79.94 — UI del Observatory para relaciones contextuales

El perfil individual del Observatory muestra el canal/token opaco y la
fiabilidad bounded de cada relación social junto a soporte, daño, frescura,
conflictos y rechazos. Los valores ausentes permanecen explícitos; la vista no
rankea peers, no infiere reputación y no devuelve datos al runtime.

---

## v0.79.93 — Observatory para relaciones contextuales

El contrato pasivo del Observatory proyecta ahora `channel` y `reliability` en
cada relación social. El canal sigue siendo un token opaco local; la fiabilidad
combina observaciones, conflictos y frescura, y no es un ranking ni una señal de
control.

Los campos son opcionales en el schema para conservar compatibilidad con
snapshots históricos. La UI y la normalización bounded preservan sus límites y
no inyectan estos datos de vuelta al runtime.

---

## v0.79.92 — estado canónico I/J/K

Se sincronizan `README.md` y `ORGANISM.md` con la evidencia actual: I dispone
de una matriz longitudinal de gates, J de continuidad semántica shadow y K de
memoria relacional contextual. Las fronteras de generalización fisiológica,
predictiva y social siguen declaradas como trabajo abierto.

---

## v0.79.91 — sincronización de estado I/J

La documentación canónica refleja la evidencia disponible: Milestone I dispone
de una matriz integrada de gates longitudinales y Milestone J dispone de
continuidad semántica de hipótesis shadow a través de checkpoint.

Esto no declara resueltas la generalización fuera de régimen ni la emergencia
social abierta de Milestone K.

---

## v0.79.90 — K fiabilidad relacional bounded

`SocialRelation.reliability()` combina observaciones, conflictos y frescura en
una señal bounded para la decisión local. La selección de oportunidades usa esa
señal junto a la expectativa contextual; una contradicción reduce la confianza
sin eliminar evidencia ni crear una reputación global.

La fiabilidad es una propiedad local de memoria, no una etiqueta del hábitat,
del Observatory ni del evaluador.

---

## v0.79.89 — I matriz longitudinal integrada

`runtime_physiology_gates` compone los estudios evaluator-only de fisiología para
hacer explícita la salida de Milestone I: replay de reparación bounded, ausencia
de reparación sin intake, replay de reproducción, bloqueo de nacimientos por
capacidad y continuación social prolongada.

Cada subestudio conserva su propio checkpoint y hábitat sintético. La matriz
solo agrega observaciones; no devuelve ground truth, recompensas ni etiquetas al
runtime.

---

## v0.79.88 — K estudios con contexto explícito

Los estudios evaluator-only que agregan evidencia social declaran ahora el
canal/token opaco de cada interacción. Esto mantiene sus métricas longitudinales
compatibles con la memoria contextual introducida en v0.79.84 y evita fusionar
por accidente observaciones de recursos distintos.

---

## v0.79.87 — K competencia guiada por contexto opaco

`propose_social_competition()` ya no puede combinar una oportunidad positiva con
una relación negativa arbitraria del mismo objetivo. Busca únicamente presencia
disponible con evidencia negativa local, selecciona la relación negativa más
fresca y usa su canal opaco cuando el hábitat lo ofrece.

La competencia sigue siendo una solicitud bounded: el hábitat adjudica el lote,
el organismo no recibe etiquetas de escenario y una relación negativa no se
convierte en una lista negra permanente.

---

## v0.79.86 — K selección relacional contextual

La selección social local deja de sobrescribir relaciones del mismo par cuando
existen varios canales opacos. Agrupa la evidencia por objetivo, calcula la
expectativa de cada canal con frescura y observaciones bounded, y conserva la
mejor oportunidad local. La propuesta de competencia exige además una relación
negativa explícita.

Esto no impone afinidad ni rechazo: mantiene disponibles las alternativas para
que la evidencia futura revise la elección.

---

## v0.79.85 — K propagación de contexto en memoria local

El runtime conserva el canal/token opaco al registrar en su propia memoria los
resultados de intercambios y competencia. La separación contextual introducida
en `RelationLedger` ya no se pierde al cruzar la frontera entre el hábitat y el
organismo.

El canal solo sirve para separar evidencia local y permitir revisión. No recibe
semántica del host, no se convierte en una preferencia universal y no cambia la
autoridad del hábitat sobre las asignaciones.

---

## v0.79.84 — K relaciones contextuales por canal opaco

La memoria social ya no agrega automáticamente toda la evidencia de un par en
una única relación. Cada observación conserva un `channel` bounded, que en las
interacciones de runtime corresponde al token de recurso opaco. Intercambio,
competencia, reciprocidad, conflicto y valencia permanecen separados entre
canales.

Los checkpoints de relación v1-v3 siguen siendo válidos y migran sus entradas
al canal `default`. La contextualidad es local y descriptiva: no asigna nombres,
roles, preferencias ni etiquetas humanas, y no cambia la autoridad del hábitat
sobre admisión, suspensión o adjudicación de recursos.

---

## v0.79.83 — J replay longitudinal de predicción shadow

El estudio evaluator-only `runtime_prediction_longitudinal` mantiene una
hipótesis predictiva durante una continuación posterior a checkpoint. Comprueba
que el número de muestras, el estado de soporte y la ganancia frente a
persistencia sobreviven a la restauración antes de autorizar la promoción a
`PREDICTOR`.

La igualdad exigida es semántica, no bit a bit: el checkpoint conserva la
trayectoria de tick, mientras que el reinicio mantiene el arranque frío del
frame previo. La cuantización bounded de pesos puede producir una pérdida de
modelo ligeramente distinta. Esa divergencia se
expone como `continuation_model_loss_delta` y no alimenta las decisiones del
organismo.

---

## v0.79.82 — I/K coste metabólico de interacción

Las interacciones sociales ya no son gratuitas para un runtime con metabolismo
explícito. Cada intercambio y cada solicitud del lote de competencia consume un
coste cognitivo configurable, no negativo y persistido en checkpoint/replay.

El coste se carga después de que el hábitat autoriza la operación, de modo que
una solicitud rechazada por el límite social no inventa actividad. El valor no
es una recompensa ni una penalización social: representa únicamente trabajo
fisiológico local y no recibe etiquetas del evaluador.

---

## v0.79.81 — K revisión ecológica prolongada

Se añade `social_runtime_denial_revision`, un estudio evaluator-only que
mantiene un historial local de un token opaco, cambia la disponibilidad finita,
observa denegaciones consecutivas y verifica que el runtime revisa su elección
sin recibir una etiqueta de preferencia. La continuación posterior al cambio se
compara desde checkpoint en un hábitat independiente.

El estudio no convierte la revisión en una regla social: mide únicamente que la
memoria local sea revisable, bounded y reproducible.

---

## v0.79.80 — K revisión de recursos tras denegación

El ledger local de recursos conserva ahora una racha bounded de denegaciones
consecutivas. La selección incorpora esa presión reciente junto con la
disponibilidad agregada, de forma que un recurso que fue útil históricamente no
pueda secuestrar indefinidamente la atención cuando el régimen ecológico cambia.

La racha se reinicia al observar una concesión y se conserva en checkpoint;
los checkpoints de esquema anterior siguen siendo válidos. No se introduce una
preferencia semántica, una etiqueta del evaluador ni una exclusión permanente:
la revisión solo modifica la prioridad local de exploración entre tokens
opacos.

---

## v0.79.79 — J ciclo de vida de hipótesis shadow

Las predicciones shadow tienen ahora un estado explícito:

- `candidate`: evidencia insuficiente;
- `supported`: ganancia positiva fuera de muestra;
- `contradicted`: evidencia suficiente sin ganancia;
- `retired`: contradicción sostenida, sin derecho a promoción.

El estado se conserva junto con pérdidas y muestras en checkpoint/replay. La
retirada no borra la evidencia histórica: solo impide que un candidato
contradicho siga ocupando el camino de promoción. El runtime continúa sin
recibir etiquetas semánticas ni métricas privilegiadas del evaluador.

---

## v0.79.78 — I capacidad reproductiva

El estudio evaluator-only de población verifica la frontera de capacidad del
hábitat reproductivo: después de materializar una cría con el único hueco
disponible, una segunda solicitud queda bloqueada. La muerte de la cría libera
su asignación exactamente una vez y el segundo tick no puede repetir la
liberación.

La prueba mantiene la autoridad de capacidad fuera de la cognición y no añade
reproducción autónoma ni reposición de recursos.

---

## v0.79.77 — I intake compartido

Se añade un estudio evaluator-only que conecta dos runtimes con un
`SharedHabitat` finito. Ambos residentes reciben una asignación inicial y
compiten después por el recurso restante mediante `request_resource_intake`.

El estudio verifica que:

- la autoridad del hábitat limita el intake concedido;
- el segundo consumidor recibe solo el remanente disponible;
- la reserva metabólica no supera el intake aceptado;
- el agotamiento y la asignación se conservan tras checkpoint/replay.

No se introduce reposición gratuita ni información del evaluador en la
cognición.

---

## v0.79.76 — I reparación sostenida

Se añade un estudio evaluator-only de reparación fisiológica repetida. El
runtime recibe intake de mantenimiento explícito por ciclo y la reparación:

- permanece limitada por la reserva disponible;
- no supera el máximo de reparación por operación;
- alcanza integridad completa solo tras varios ciclos;
- no repara un control sin intake;
- conserva la trayectoria y el estado mediante checkpoint/replay.

El estudio no alimenta la cognición con métricas del evaluador ni crea recursos
de forma gratuita.

---

## v0.79.75 — K cambio de régimen ecológico

Se añade un estudio evaluator-only de revisión de nicho ante un cambio bounded
de disponibilidad. Durante la primera fase solo un token opaco puede sostener
intercambios; después el hábitat cambia la reserva del segundo token. El
runtime revisa su evidencia local y vuelve a explorar el recurso que antes no
estaba disponible.

El estudio conserva checkpoint/replay y compara la continuación en un hábitat
independiente. No asigna roles, preferencias ni objetivos sociales, y no cierra
los gates de emergencia prolongada o especialización fuera del régimen
sintético.

---

## v0.79.74 — K replay longitudinal

El estudio evaluator-only de sociabilidad prolongada compara ahora la secuencia
completa de pares autónomos posterior al checkpoint en un hábitat independiente
restaurado desde el mismo estado. La comprobación cubre la adjudicación del
hábitat y la memoria local, no solo la igualdad inmediata del ledger.

No se asignan pares, roles ni objetivos al runtime. La emergencia multi-
organismo prolongada y la especialización fuera del régimen sintético siguen
siendo gates abiertos.

---

## v0.79.73 — K replay de trayectoria social

El estudio evaluator-only de especialización social conserva ahora las
secuencias completas de elección de recursos y compara la continuación tras el
checkpoint en un hábitat independiente restaurado desde el mismo estado.

Esto verifica algo más fuerte que la igualdad inmediata del ledger: que la
asignación finita, la evidencia local y las elecciones posteriores permanecen
deterministas tras replay. No asigna roles, preferencias ni objetivos al
runtime, y no cierra los gates de emergencia multi-organismo prolongada ni de
generalización fuera del régimen sintético.

---

## v0.79.72 — I recuperación fisiológica sostenida

Se amplía el aparato científico de Milestone I con un estudio determinista de
déficit y recuperación sostenida. El estudio:

- mantiene el organismo bajo déficit repetido hasta observar dormancia;
- comprueba que el retorno a `active` requiere intake explícito;
- ejecuta un control sin intake que no se recupera;
- restaura el checkpoint tomado al final del déficit y compara la trayectoria
  de recuperación y el estado final con la ejecución original.

El estudio es evaluator-only: no introduce etiquetas, ground truth ni métricas
del evaluador en el runtime o en la cognición.

---

## v0.79.71 — I gestión de residuos integrada

La cola bounded `DegradationQueue` deja de ser un componente aislado y pasa a
formar parte del ciclo de vida de `OrganismRuntime`. Cada tick envejece el
estado retenido y excreta de forma irreversible los elementos que superan la
ventana configurada. Sus límites, edades y contador se conservan en
checkpoint/replay; checkpoints históricos sin esta sección siguen restaurando
con una cola vacía.

El Observatory publica únicamente `retained_items` y `excreted_units`, sin
exponer contenido, identificadores ni una superficie de control.

---

## v0.79.70 — K evidencia de recursos en Observatory

El contrato del Observatory incorpora la proyección bounded
`organism.social_resource_evidence`. Conserva tokens opacos, cantidades
solicitadas/concedidas, disponibilidad, observaciones, denegaciones, frescura y
último tick para inspeccionar la adaptación local sin exponer semántica del host.

La UI lo muestra como evidencia pasiva y no ofrece controles ni retroalimentación
al runtime.

---

## v0.79.69 — K reexploración ecológica bounded

El `ResourceEvidenceLedger` vuelve a probar tokens cuya evidencia local ha
quedado antigua después de una ventana bounded. Esto evita que una denegación
histórica bloquee para siempre un recurso que puede volver a estar disponible.

La reexploración es determinista, depende únicamente de ticks y evidencia local,
y no introduce preferencias, roles ni objetivos del evaluador.

---

## v0.79.68 — K paridad de proyección social

Corrige la proyección browser del Observatory para conservar el contador de
rechazos direccionales que ya publicaban el adaptador y los esquemas del
snapshot.

La corrección mantiene la evidencia social bounded entre runtime, snapshot
validado y visualización pasiva, sin convertirla en reputación global ni
retroalimentarla al organismo.

---

## v0.79.67 — K diferenciación de nicho

Añade un estudio evaluator-only de trayectoria prolongada en el que dos
runtimes reciben los mismos tokens opacos y compiten por un recurso finito. La
evidencia local de disponibilidad hace que sus elecciones posteriores se
diferencien y la memoria se verifica tras checkpoint/replay.

Esto es una señal de diferenciación bajo un régimen sintético concreto, no una
prueba de roles, sociedad ni especialización generalizada.

---

## v0.79.66 — K evidencia de competencia

Los resultados de `request_social_competition()` se incorporan ahora a la
memoria local de disponibilidad de recursos. Intercambio y competencia pueden
por tanto producir adaptación bounded sobre los mismos tokens opacos, con
checkpoint/replay y sin convertir la cantidad concedida en una recompensa
social universal.

---

## v0.79.65 — K rechazo explícito

- Añade evidencia direccional de rechazo a `SocialRelation` y su checkpoint,
  manteniendo compatibilidad con ledgers de versiones anteriores.
- Añade `OrganismRuntime.reject_social_interaction()`: una negativa suspende
  solicitudes futuras de ese canal hasta una reanudación explícita y no se
  confunde con daño ni con una valoración global del peer.
- Extiende el contrato pasivo del Observatory con `rejections`, incluyendo
  esquemas, matriz de contratos, proyección y representación de evidencia.

La negativa no crea un planificador social ni una política de exclusión. La
red, el descubrimiento de peers y las acciones sobre el host permanecen
deshabilitados.

---

## v0.79.64 — K adaptación ecológica

- Añade `ResourceEvidenceLedger`, una memoria local y bounded de resultados
  agregados para tokens de recursos opacos.
- El runtime elige recursos sociales usando disponibilidad observada, mantiene
  exploración acotada y registra solicitudes denegadas sin convertirlas en una
  etiqueta externa.
- La evidencia de recursos se serializa y restaura junto al checkpoint del
  organismo.
- Añade un estudio evaluator-only que demuestra cambio de recurso tras una
  denegación y paridad de replay.

La adaptación no asigna roles, nichos ni recompensas universales. La
especialización emergente requiere trayectorias más largas y sigue abierta.
No se habilitan red, descubrimiento de peers ni acciones sobre el host.

---

## v0.79.63 — K longitudinal runtime

- Añade `social_runtime_longitudinal`, un estudio evaluator-only que ejecuta
  pasos sociales autónomos de varios runtimes durante una trayectoria prolongada.
- Inserta un checkpoint intermedio y verifica que el ledger social restaurado
  conserva la evidencia antes de continuar la ejecución.
- Mide interacciones, diversidad de pares, entropía de pares y miembros
  aislados sin asignar roles, objetivos ni selección de peers desde el evaluador.

Esta versión demuestra continuidad y observabilidad de una ecología social
bounded, pero no demuestra especialización emergente ni una sociedad diseñada.
La red, el descubrimiento de peers y las acciones sobre el host siguen
deshabilitados.

---

## v0.79.62 — J: replay de predicción shadow

Los candidatos `ShadowPrediction` ya forman parte del checkpoint cognitivo:
se conservan sus muestras y pérdidas de modelo/persistencia, con validación y
límite de 256 candidatos. La restauración mantiene la ganancia fuera de muestra
y permite repetir una promoción explícita bajo las mismas condiciones.

La serialización no crea predictores ni activa promoción automática; solo
preserva evidencia local bounded para que el organismo pueda continuar su
contraste después de un reinicio.

---

## v0.79.61 — Observatory: distribución de atención

El Observatory publica dos métricas externas y bounded de la asignación de
atención por tick: `concentration` (participación máxima) y `entropy` (entropía
normalizada). No exponen el valor de ninguna señal, no contienen etiquetas de
plataforma y no pueden modificar el presupuesto ni la selección del runtime.

El contrato JSON, la proyección Python y la normalización browser quedan
alineados; la vista individual las muestra como instrumentación, no como una
decisión o diagnóstico.

---

## v0.79.60 — Observatory: intención de descanso

La proyección pasiva del Observatory publica `organism.physiology.resting_requested`
junto al estado fisiológico, las transiciones y el tick de muerte. El campo
queda incluido en el contrato JSON cerrado, validado en la proyección Python y
normalizado en la interfaz browser sin exponer reservas, costes ni control.

La instrumentación sigue siendo estrictamente observacional: el Observatory no
puede solicitar, cancelar ni inferir una decisión del Symbiont.

---

## v0.79.59 — I: recuperación explícita

Se añade `run_runtime_recovery_study`, un estudio evaluator-only que ejercita
el ciclo local de intake de mantenimiento, reparación acotada, descanso y
reanudación. La reparación consume exclusivamente el recurso aceptado por el
ledger y la intención de descanso sobrevive a checkpoint/replay.

Este cierre no declara completado Milestone I: siguen pendientes los estudios
de recuperación prolongada y la integración reproductiva/observacional.

---

## v0.79.58 — I: descanso explícito bounded

`OrganismRuntime` incorpora `request_rest()` y `resume_activity()`. El
Symbiont puede expresar una decisión local de descanso sin que el evaluador
inyecte reservas, integridad o recuperación. Bajo presión metabólica severa, el
pedido permite entrar en dormancia en lugar de agonía; con presión normal no
teletransporta estado ni añade recursos.

La intención queda incluida en el checkpoint y en la configuración efectiva.
La prueba de contrato verifica presión severa, replay de la decisión y ausencia
de reposición gratuita.

---

## v0.79.57 — K: propuestas de competencia local

El runtime añade `propose_social_competition()`. Cuando su propia memoria
relacional contiene evidencia negativa sobre el canal seleccionado, produce una
propuesta bounded de recurso. La propuesta no elige un adversario ni ejecuta un
resultado: el hábitat autorizado adjudica el lote de solicitudes y atribuye la
escasez únicamente a los participantes concurrentes.

El estudio evaluator-only `social_runtime_competition` verifica dos propuestas,
contención finita y atribución peer-to-peer sin roles, etiquetas globales ni
objetivos inyectados.

---

## v0.79.56 — K: paso social autónomo bounded

El runtime incorpora `autonomous_social_step()`. La operación selecciona un
canal disponible mediante presencia opaca y evidencia relacional propia, toma un
token de recurso del hábitat explícitamente autorizado y realiza una única
solicitud bounded. El caller no suministra peer, rol, valencia ni objetivo
social; la ausencia de oportunidad produce una operación nula.

El estudio evaluator-only de emergencia utiliza ahora este camino del runtime,
no un target elegido por el arnés. El resultado sigue siendo una observación
externa: no se devuelve al organismo ninguna etiqueta de cooperación,
competencia, éxito o aislamiento.

---

## v0.79.55 — K: continuidad social generacional

Se cierra una brecha del ciclo de vida social: un runtime hijo nacido mediante
`materialize_clonal_bud()` conserva una capacidad reproductiva nueva y puede
unirse explícitamente al mismo hábitat social bounded. La unión sigue siendo
una acción autorizada por el organismo y la admisión sigue estando limitada por
el hábitat; no se descubre ningún par ni se inyecta una etiqueta social.

El estudio evaluator-only `social_runtime_generations` recorre tres
nacimientos consecutivos, intercambios con un vecino opaco, checkpoints y
restauraciones, y la muerte/liberación de cada progenitor. Comprueba la
trazabilidad de parentela, la continuidad de membresía y que el último
organismo permanece vivo. La emergencia social auténtica y la promoción
predictiva siguen siendo fronteras abiertas.

---

## v0.79.54 — K: paridad live/replay social

Se añade un estudio de paridad que restaura el runtime y el hábitat social,
reaplica evidencia contradictoria y verifica que la selección multi-vecino y la
suspensión producen el mismo resultado en la rama live y la restaurada.

---

## v0.79.53 — K: contexto social multi-vecino

Se añade un estudio longitudinal bounded con varios vecinos que combina evidencia
contradictoria, suspensión y reanudación, aislamiento y competencia por un recurso
finito. El estudio verifica que las decisiones locales cambian de forma revisable
y que el mediador ecológico conserva la escasez.

---

## v0.79.52 — K: revisión longitudinal de evidencia social

Se añade un estudio evaluator-only que verifica que una contradicción agregada
puede cambiar reversiblemente la selección social local: la evidencia positiva
favorece una interacción, una observación costosa la vuelve negativa y el runtime
reabre una oportunidad desconocida. Ninguna etiqueta del estudio entra en la
decisión del organismo.

---

## v0.79.51 — K: estudio de selección social local

Se añade un estudio evaluator-only que verifica replayable la selección social
basada en evidencia local: soporte acumulado favorece un canal, daño reduce su
prioridad y los canales desconocidos siguen disponibles sin imponer una política.
Las etiquetas del estudio no entran en el runtime.

---

## v0.79.50 — K: decisión social local basada en evidencia

La selección de oportunidades sociales del runtime usa exclusivamente su ledger
local y una combinación bounded de evidencia neta, frescura y exploración. La
evidencia positiva favorece repetir un canal, el coste acumulado reduce su
prioridad y los canales desconocidos conservan una oportunidad de exploración.
No se introducen etiquetas, objetivos sociales ni métricas del evaluador.

---

## v0.79.49 — Observatory: accesibilidad de evidencia social

La tabla accesible del Observatory incluye las relaciones sociales publicadas como
evidencia agregada, con valencia, observaciones y frescura. La información sigue
siendo pasiva y bounded; no se deriva ranking ni objetivo social.

---

## v0.79.48 — Observatory: evidencia social visible

El proyector y el estado del Observatory ahora conservan relaciones sociales acotadas
como evidencia agregada: valencia, observaciones, reciprocidad, soporte, daño,
frescura y conflictos. La vista de organismo las muestra explícitamente como
evidencia — nunca como objetivos, etiquetas de peers ni ranking. Los identificadores
se mantienen opacos y los límites del contrato se aplican antes de renderizar.

---

## v0.79.47 — Observatory: evidencia relacional completa

La proyección social del Observatory publica, de forma bounded y pasiva, soporte,
daño y frescura además de valencia, observaciones, reciprocidad, conflictos y
último tick. El contrato JSON y su matriz documentan que esos campos son
agregados de evidencia, no objetivos ni ranking de peers.

---

## v0.79.46 — K: ciclo social de reinicio, linaje y muerte

Se añade un estudio evaluator-only que recorre un canal social persistido,
reinicio con identidad estable, reanudación, nacimiento clonal con trazabilidad
de parentela y muerte con liberación del progenitor. El hijo permanece vivo en
la autoridad de hábitat después de la muerte del padre. Ninguna métrica del
estudio se devuelve como objetivo cognitivo.

---

## v0.79.45 — Observatory: phenotype adaptativo

La vista de organismo del Observatory ahora representa de forma pasiva el estado
fenotípico disponible: salud topológica, estrés, recuperación, actividad de
receptores, desarrollo sensorial, utilidad, errores predictivos y rutas de
creencias. Añade marcadores visuales para conexiones excitatorias, inhibitorias,
moduladoras y predictivas, manteniendo la identidad opaca y sin introducir
estado privilegiado en el runtime.

La vista sigue siendo una proyección de datos ya publicados; no decide acciones
ni devuelve métricas al Symbiont.

---

## v0.79.44 — hardening del descubrimiento de tests

El proyecto excluye explícitamente `backups/` del descubrimiento de pytest.
Los snapshots y copias locales del Observatory siguen siendo útiles para
revisión, pero no se interpretan como suites activas ni alteran la validación
del checkout.

---

## v0.79.43 — K: escenarios sociales adversariales en runtime

Se añade un estudio evaluator-only que combina intercambio de soporte, demanda
simultánea sobre recursos finitos y aislamiento explícito de un canal. Las
métricas verifican que el hábitat limita la asignación, que el runtime conserva
evidencia unidireccional y que la selección local no fuerza una interacción con
un miembro aislado. Los escenarios son estímulos sintéticos; no se convierten
en objetivos ni etiquetas para los organismos.

---

## v0.79.42 — K: control local de canales sociales

El `OrganismRuntime` puede suspender y reanudar explícitamente su propio canal
hacia un miembro admitido del hábitat. La operación está acotada a la identidad
del runtime, respeta el estado post-muerte y sobrevive a un checkpoint del
hábitat. El estudio de replay usa ahora ese camino runtime para verificar que la
memoria local y la suspensión se restauran sin convertir al evaluador en un
planificador social.

---

## v0.79.41 — K emergencia runtime evaluator-only

Se añade un estudio determinista en el que varios `OrganismRuntime` perciben
presencia opaca, seleccionan oportunidades desde su memoria relacional local y
solicitan intercambios dentro de un `SocialHabitat` autorizado. El estudio mide
interacciones, diversidad de pares, entropía y reciprocidad sin asignar roles,
valencias ni objetivos sociales al runtime.

El estudio sigue siendo aparato científico externo; no convierte métricas del
evaluador en señales cognitivas privilegiadas.

---

## v0.79.40 — I intake metabólico competido

`SharedHabitat` ofrece consumo explícito de recursos finitos para residentes
admitidos. `OrganismRuntime.request_resource_intake()` solo incorpora al ledger
metabólico la cantidad efectivamente aceptada; la escasez no crea reserva
virtual y un organismo muerto no puede adquirir recursos.

La operación es local, bounded y checkpointable a través de los contratos de
hábitat y metabolismo existentes.

---

## v0.79.39 — I necesidades metabólicas en Observatory

El adaptador pasivo del Observatory publica la presión metabólica y clases de
reserva por función, sin exponer reservas, costes ni lecturas numéricas. Esto
separa las necesidades vitales observadas de las decisiones del evaluador y
permite revisar inanición, recuperación y dormancia en replay.

Se actualiza el esquema normativo y se añade una prueba de proyección de runtime.

---

## v0.79.38 — K selección local de oportunidades

El runtime puede seleccionar una oportunidad social a partir de su percepción
local de presencia y de su propio ledger acotado. Se prioriza un canal disponible
con menor evidencia previa; un canal suspendido no se selecciona. La operación no
mueve recursos, no descubre peers fuera del hábitat autorizado y no programa a
otros organismos: deja la decisión final de intercambiar o competir al ciclo
cognitivo del Symbiont.

---

## v0.79.37 — K percepción social autorizada

`SocialHabitat` ofrece ahora una percepción mínima de presencia: tokens opacos de
residentes admitidos y disponibilidad/suspensión del canal. `OrganismRuntime`
puede leerla sin recibir metadatos, nombres humanos ni semántica del proveedor.
La decisión de interactuar sigue siendo local y explícita; el hábitat no
planifica emparejamientos.

Se añaden pruebas de autorización, límites de identidad y exposición mínima.

---

## v0.79.36 — K Observatory social evidence

The Observatory projection now preserves directional social evidence needed to
inspect Milestone K: reciprocal-observation count, conflict count and bounded
last-observed tick. The resident and CLI producers pass the runtime-owned ledger;
no evaluator labels, social objectives or host actions are added.

The normative snapshot schema and contract tests are updated together. Existing
snapshots without social relations remain valid because the projection is
optional; snapshots containing relations must use the complete bounded record.

---

## v0.79.35 — K reciprocidad y revisión relacional

Esta release añade evidencia automática de reciprocidad en intercambios
bidireccionales y un estudio determinista que cubre reciprocidad, conducta
unilateral, conflicto de evidencia y aislamiento. El estudio es exclusivamente
del laboratorio: no introduce objetivos sociales ni devuelve etiquetas del
evaluador al runtime.

## Validación

- `tests/integration/studies/test_social_reciprocity.py`
- suite completa de tests del repositorio

La reciprocidad se conserva como contador direccional y no se convierte en una
clasificación global de "amigo" o "enemigo".

---

## v0.79.34 — social replay and death study

A deterministic evaluator study now checkpoints and restores a runtime's local
relation memory together with a social habitat's members and finite resources.
It also verifies that an admitted resident's irreversible death releases social
membership while preserving replay traceability.

---

## v0.79.33 — social membership death boundary

When an admitted runtime reaches irreversible death, it releases its social
habitat membership exactly once. This complements ecological and birth-authority
release and prevents a dead resident from occupying social capacity or issuing
later interactions.

---

## v0.79.32 — local relation memory

Each runtime now keeps an organism-owned bounded `RelationLedger` for outcomes
of its explicit social requests. The ledger is checkpointed with runtime state,
and competition requests must originate from that runtime identity. The shared
habitat remains the external authority for membership and finite resources.

---

## v0.79.31 — longitudinal runtime promotion gate

A deterministic evaluator study now drives runtime-owned cognitive bridges over
repeated opaque observations. A candidate with out-of-sample gain is promoted
only through the explicit runtime operation, while a constant/no-gain candidate
is rejected. The study does not feed evaluator truth into runtime decisions.

---

## v0.79.30 — explicit runtime predictor promotion

`OrganismRuntime.promote_shadow_prediction` provides the explicit production
boundary for promoting an eligible shadow candidate. Promotion remains bounded,
opt-in, evaluator-independent and unavailable after irreversible death.

---

## v0.79.29 — runtime shadow-prediction observability

`OrganismRuntime.shadow_predictions` exposes the bounded shadow evidence held by
its cognitive bridge as a read-only tuple. This allows longitudinal studies to
inspect candidates while promotion remains opt-in and evaluator metrics never
enter organism decisions.

---

## v0.79.28 — explicit runtime social boundary

`OrganismRuntime` can now issue explicit exchange and finite-resource competition
requests through an attached, authorized `SocialHabitat`. The runtime does not
schedule peers, discover residents, or select a social objective. Requests are
mediated by the habitat and are rejected after irreversible death.

---

## v0.79.27 — contextual pairwise competition evidence

Finite-resource competition now attributes observed scarcity to another resident
when requests contend for the same resource. A solitary request remains a cost
against the habitat. This preserves contextual negative evidence without adding
a universal social objective or evaluator-provided valence.

---

## v0.79.26 — interaction diversity instrumentation

The evaluator-only social-emergence study now records the number of unique
unordered member pairs and Shannon entropy of pair selection. These metrics make
interaction concentration and diversity explicit while remaining external to
organism decisions. No social objective, semantic label, network discovery or
autonomous runtime emergence is introduced.

---

## v0.79.25 — runtime population death/release study

Milestone I now exercises a parent/child runtime population: an authorized
clonal child is created, driven into unrecoverable metabolic pressure, and
released from `HabitatBirthAuthority` exactly once. The parent remains live and
the released allocation returns to the authority. This evaluator-only study is
deterministic and does not start processes or feed evaluator truth into runtime
decisions.

---

## v0.79.24 — runtime reproduction replay study

The laboratory now provides a deterministic evaluator-only study covering the
full runtime reproduction boundary: sustained pressure, authorized birth, a
new germinal runtime, independent ticks and checkpoint replay. The study checks
identity and generation separation and compares child metabolism after restore.
It does not inject evaluator labels or create processes.

---

## v0.79.23 — germinal runtime materialization

Authorized clonal budding can now materialize a new `OrganismRuntime` with a
new organism identity and incremented generation. The child receives the
inherited genome and a canonical empty germinal graph, while acquired graph
state, memory, metabolism, physiology and tick history remain with the parent.
Materialization is local, bounded by the existing `HabitatBirthAuthority`, and
does not start processes or discover peers.

---

## v0.79.22 — reproductive metabolic cost

A successful runtime clonal bud now charges a bounded maintenance cost after
habitat authorization and reserve consumption. Failed births do not charge the
parent. The cost is checkpointed with runtime configuration so replay preserves
the resource contract.

---

## v0.79.21 — integrity-safe reproduction imports

The runtime reproduction boundary now imports the birth authority directly and
removes the compatibility module that violated the repository's structural
integrity rule forbidding lineage/evolution modules under `symbiont/`. Existing
`core.lineage` compatibility is retained through the package import alias, while
no forbidden file is present on disk.

---

## v0.79.20 — runtime reproductive pressure and budding

Milestone I now exposes an explicit runtime reproductive boundary. A runtime
may record sustained developmental pressure and, only when configured with a
`ReproductivePressure`, genome and `HabitatBirthAuthority`, request one bounded
clonal bud. The authority registers the existing parent, enforces capacity and
resource allocation, creates a new identity and consumes reproductive reserve.

Pressure and generation are checkpointed. The mechanism never starts a process,
performs peer discovery or receives evaluator labels; offspring materialization
remains an explicit local-host/laboratory action.

---

## v0.79.19 — dormant activity scaling

Milestone I now applies a bounded 0.25 activity factor to declared observation,
cognition and persistence charges while the runtime physiology is dormant.
Dormancy therefore reduces metabolic demand without creating reserves or
changing the irreversible state machine. The factor is internal to the runtime;
host permissions and evaluator data remain unchanged.

---

## v0.79.18 — seeded social-emergence baseline

Milestone K adds an evaluator-only, deterministic social-emergence study. The
study repeatedly samples pairs in an explicitly admitted `SocialHabitat` and
mediates finite-resource exchange or competition, then reports positive,
negative and neutral relation counts together with isolated members.

This harness establishes a reproducible baseline for measuring whether social
structure emerges from bounded cellular capabilities. It does **not** inject a
social objective, platform semantics, evaluator ground truth or peer discovery
into `symbiont`; runtime interaction remains explicitly authorized and
resource-bounded.

---

## v0.79.17 — opt-in runtime predictor promotion

`OrganismRuntime` now exposes an explicitly opt-in `auto_promote_predictors`
configuration. When enabled, only promotable shadow candidates (minimum trials
and positive out-of-sample gain) can add bounded `PREDICTOR` nodes; the setting
is persisted in effective configuration and checkpoint restore. The default
remains disabled.

---

## v0.79.16 — longitudinal shadow-promotion gate

Milestone J now includes an evaluator-only study contrasting a predictable
shadow candidate with a no-gain candidate over repeated trials. Promotion is
reported only after the minimum evidence count and positive out-of-sample gain;
no predictor is created directly by the study.

---

## v0.79.15 — synthetic niche differentiation study

Milestone K includes an evaluator-only study with finite typed resources and
independent demand trajectories. It reports whether resource use differentiates
into distinct niches, without assigning roles or feeding evaluator labels into
resident cognition.

---

## v0.79.14 — longitudinal social evidence

Milestone K adds a bounded evaluator-only longitudinal study that exercises
repeated exchange, one explicit suspension, reactivation and relation evidence
accumulation. It reports rejected interactions and derived evidence freshness
without feeding evaluator labels into the organism.

---

## v0.79.13 — reversible social suspension

`SocialHabitat` now provides explicit pair-level `suspend`/`resume` controls.
Suspended interactions are rejected, suspension survives checkpoint/restart, and
release removes stale pair controls. No scheduler or social preference is
introduced; organisms choose whether to invoke these bounded capabilities.

---

## v0.79.12 — runtime physiology replay

The evaluator-only physiology studies now checkpoint a live
`OrganismRuntime`, restore it and compare the subsequent physiology trajectory.
This verifies continuity of identity-independent vital state and metabolic
reserves without synthesizing evaluator state or microstate.

---

## v0.79.11 — deterministic dormancy study

The Milestone I physiology harness accepts an explicit resting schedule and
reports dormant ticks. Dormancy is derived from severe resource pressure and
never replenishes reserves by itself; the study now covers the transition and
its terminal resource accounting.

---

## v0.79.10 — reproduction and death study

Milestone I now includes an evaluator-only reproduction contract study covering
capacity-bounded paired birth, lineage allocation and exactly-once death release.
The study verifies that duplicate death events do not release resources twice.

---

## v0.79.9 — social lifecycle replay study

The evaluator-only social study now exercises release (temporary separation)
and checkpoint/restart continuity, reporting restored members and finite-resource
state. Invalid zero-resource scenarios are rejected before issuing an impossible
allocation. No social policy is introduced into the organism.

---

## v0.79.8 — contextual relation evidence

Milestone K relation records now retain bounded reciprocal-observation and
conflict counts plus the latest observation tick. A derived exponential
freshness score makes evidence expiry explicit without deleting contradictory
history. Checkpoint schema v2 is backward-readable for schema v1 records.

---

## v0.79.7 — comparative protocol validation

The lazy comparative-study registry wrapper now rejects missing required
`base_spec` configuration with the declared `ValueError` contract instead of
leaking an internal `TypeError`.

---

## v0.79.6 — explicit physiology repair

Milestone I exposes a bounded `OrganismRuntime.repair()` action. Repair consumes
maintenance reserve, is capped per action, is checkpoint-compatible through the
existing homeostasis/metabolism state, and is rejected after irreversible death.
No evaluator state or host semantics are introduced.

---

## v0.79.5 — social habitat checkpoint continuity

Milestone K now persists and restores an explicitly authorized `SocialHabitat`
boundary as one deterministic checkpoint: admitted members, finite resource
balances and aggregate relation evidence are restored together. Invalid or
duplicate membership is rejected. This preserves replay/restart semantics
without adding social objectives or hidden peer discovery.

---

## v0.79.4 — study import boundary hardening

The experiment registry now lazily imports the comparative study implementation,
removing a package-collection circular import. This keeps milestone study
modules independently importable and does not alter evaluator or organism
semantics.

---

## v0.79.3 — social emergence study harness

Added a deterministic evaluator-only Milestone K scenario covering explicit
exchange, finite-resource competition and member release. The study records
aggregate relation valence without injecting labels or social preferences into
organism cognition.

---

## v0.79.2 — physiology study harness

Added a deterministic evaluator-only starvation/recovery study for Milestone I.
It uses zero automatic replenishment and explicit intake schedules, records
viability transitions and terminal death, and never feeds evaluator metrics back
into the organism.

---

## v0.79.1 — explicit metabolic mode

`OrganismRuntime(explicit_metabolism=True)` disables automatic reserve
replenishment. Resource recovery must then use bounded explicit intake, while
legacy callers retain the historical default until they opt into the milestone
contract. The mode is checkpointed and restored.

---

## v0.79.0 — Milestone K interaction substrate

Milestone K now includes an explicitly authorized local `SocialHabitat` with
bounded admission/release, aggregate relation memory, voluntary exchange and
finite-resource competition. The mediator does not assign social roles,
preferences or universal rewards.

Longitudinal emergence, reciprocity, isolation and exploitation studies remain
open gates. Network discovery, propagation and real-host actions remain outside
scope.

---

## v0.78.0 — Milestone J implementation track

This milestone release makes the predictive-development primitives part of the
post-I milestone lane: exact-zero weight codec, bounded anti-capture attention,
provisional signal hypotheses, stranded-concept route repair and shadow
prediction with explicit promotion gates.

Promotion remains opt-in and evidence-gated. No evaluator labels, host
semantics, network access or real-world action are introduced.

---

## v0.77.1 — irreversible runtime boundary

Execution now refuses further ticks after the physiology controller reaches
`dead`, and dead checkpoints cannot be restored as live runtime identities.
This closes the continuity boundary required by Milestone I without adding any
host-side action or evaluator feedback path.

---

## v0.77.0 — Milestone I implementation start

This is the first milestone release after the v0.76 hardening lane.

## Included

- irreversible bounded physiology states in `OrganismRuntime`;
- explicit bounded metabolic intake, including zero-replenishment ledgers;
- checkpoint/restore of physiology and one-time habitat release on death;
- Observatory projection and schema support for physiology and aggregate social
  relation evidence;
- relation ledger persistence and bounded interaction primitives remain available
  as partial Milestone K work.

## Gates still open

Full Milestone I requires repair, dormancy, reproduction coupling and sustained
deficit/recovery studies. Milestones J and K remain partial and are not claimed
as complete by this release. No network, peer discovery, host mutation or
evaluator feedback path is introduced.

---

## v0.76.41 — separación de fisiología, desarrollo predictivo y sociabilidad

Cierre documental en `main`. No se habilitan capacidades de runtime.

- Se mantiene **Milestone I — Fisiología integrada** como el cierre de las
  necesidades vitales y mortales.
- Se introduce **Milestone J — Desarrollo predictivo autónomo**, que recoge los
  hallazgos de telemetría: codec de pesos con cero exacto/deadband, atención
  anti-captura, ciclo de vida de hipótesis, conceptos `stranded`, predicción en
  shadow mode y métricas externas del Observatory.
- La sociabilidad se desplaza a **Milestone K — Sociabilidad emergente**. Su
  diseño celular permanece intacto y explícitamente posterior a I y J.
- Se actualizan roadmap, índice documental, README y ORGANISM para que I/J/K
  tengan una única secuencia y estado canónico.

Esta release incorpora la primera implementación P0 de Milestone J y solo reorganiza y cierra diseño. No implementa el codec, el nuevo
scheduler, hipótesis, predictores ni relaciones entre organismos. Se validó la
consistencia de referencias y el formato con `git diff --check`.

Milestone J P1 añade el ciclo de vida de hipótesis sobre relaciones sensoriales opacas, sin convertir correlaciones jóvenes en conocimiento consolidado.

Milestone J P1 añade seguimiento de conceptos `stranded` y una oportunidad de reparación de ruta antes del reciclaje.

Milestone J P2 incorpora evaluación predictiva en shadow mode frente a persistencia, sin promover automáticamente nodos del grafo.

El resultado cognitivo expone `stranded_concepts` y `predictive_gain` para instrumentación externa del Observatory.

El Observatory publica `stranded_concepts` y `predictive_gain` en CognitionState, manteniéndolos como observación externa.

Milestone I incorpora `PhysiologyController`: estados de viabilidad activos, estresados, dormidos, agonizantes y muertos, con muerte irreversible ante presión metabólica no recuperable.

La fisiología se incluye en checkpoint y se restaura sin reanimar organismos muertos ni perder transiciones.

Milestone K inicia un ledger de relaciones dirigidas con evidencia agregada de beneficio y coste, sin imponer objetivos sociales.

Milestone K integra intercambios explícitos y competencia por recursos finitos mediante `SocialInteractionEngine`.

Milestone J permite promover explícitamente un `ShadowPrediction` con ganancia fuera de muestra a un nodo `PREDICTOR`, sin promoción automática.

El estado canónico pasa a reflejar implementación parcial de I, J y K.

La muerte fisiológica libera una asignación de `SharedHabitat` una sola vez, preservando la contabilidad del hábitat.

---

## v0.76.26 — reordenación de milestones I y J

Se reformula la frontera posterior a H:

- **Milestone I — Fisiología integrada:** cierra el acoplamiento entre recursos,
  metabolismo, homeostasis, reparación, dormancia, degradación, viabilidad,
  reproducción y muerte.
- **Milestone J — Sociabilidad emergente:** proporciona capacidades celulares
  para relacionarse sin imponer una sociedad ni objetivos sociales.

La sociabilidad se pospone hasta que I cierre las necesidades vitales y mortales.
Ninguno de los dos milestones está implementado todavía; no se habilitan nuevas
interacciones ni autoridad del runtime.

---

## v0.76.25 — definición de Milestone I

Se cierra el diseño del siguiente milestone científico:

## Milestone I — Sociabilidad emergente

El milestone proporcionará a los Symbionts capacidades celulares para percibir,
intercambiar, competir, asociarse, separarse y revisar interacciones dentro de
hábitats autorizados. No crea una sociedad ni impone cooperación como objetivo.
Las relaciones deberán emerger de señales, costes, recursos, memoria y evidencia
locales.

El diseño normativo está en
[`docs/design/sociabilidad-y-desarrollo-predictivo.md`](design/sociabilidad-y-desarrollo-predictivo.md).

La implementación queda bloqueada hasta cerrar las deudas explícitas del
Observatory y pasar una nueva revisión de seguridad y contratos. Esta release no
habilita comunicación ni relaciones entre organismos.

Validación documental: enlaces y estado de roadmap revisados. La suite de runtime
permanece sin cambios de comportamiento.

---

## v0.76.24 — finalización automática del historial

El resumen derivado del Observatory ya no depende de que se produzca una
rotación de segmento:

- cada rotación actualiza el resumen;
- el cierre limpio del residente actualiza también los segmentos parciales;
- `JournalSink.finalize()` hace explícito el límite de ciclo de vida;
- los registros NDJSON/NDJSON.GZ no se eliminan ni se sustituyen.

La estrategia sigue siendo local, reversible y auditable. Las terminaciones
abruptas pueden dejar un resumen anterior, pero nunca pierden los registros
fuente; el siguiente arranque o rotación lo reconstruye.

Validación: `pytest -q observatory/tests` (171 tests).

---

## v0.76.23 — transición explícita del estado de UI

Se amplía el límite de transición del Observatory para que los metadatos de
interfaz y replay no se modifiquen directamente desde cada módulo:

- `updateUiState()` centraliza cambios de vista, modo, perfil, búsqueda y
  selección de replay.
- La carga de replay usa `resetInstanceProjection()` antes de ingerir el primer
  snapshot, evitando mezclar estado privilegiado o estructural anterior.
- La proyección de snapshots continúa siendo la única vía de commit de datos
  del organismo.
- Se actualizaron las pruebas estructurales para verificar el nuevo límite.

No cambia la autoridad del Observatory ni se persiste información del host.

Validación: `pytest -q observatory/tests` (170 tests).

---

## v0.76.22 — cierre del ciclo de renderizado

El desacoplamiento del ciclo de renderizado queda cerrado:

- `projection/snapshot.js` se limita a normalizar, validar y comprometer estado.
- El shell de aplicación (`app.js`) solicita el ciclo de renderizado.
- Replay, stream live y controles reutilizan el puente explícito de
  `ui/render-cycle.js`.
- Se mantiene la separación entre ingestión de datos, estado y presentación.

No se amplía la autoridad del Observatory ni se introducen acciones sobre el
organismo o el host.

Validación: `pytest -q` (suite completa).

---

## v0.76.21 — resumen automático del historial del Observatory

Esta release hace automática la compactación **derivada** del historial, sin
eliminar ni sobrescribir registros fuente.

- Cada rotación de segmento de `Journal` actualiza
  `observatory/summaries/<run_id>.summary.json`.
- El resumen contiene cobertura de ticks, versiones de esquema, estados,
  número de entradas y hashes SHA-256 por segmento.
- Los segmentos NDJSON y sus archivos `.ndjson.gz` siguen siendo la fuente
  auditable y se conservan íntegramente.
- `Journal.compact()` continúa siendo explícito y únicamente comprime segmentos
  cerrados; no existe una cuota de borrado automática.
- La inicialización del journal reconoce segmentos ya comprimidos para no
  reutilizar índices después de un reinicio.

Validación: `pytest -q observatory/tests`.

---

## v0.76.20 — version alignment after history summaries

Aligns package and canonical documentation metadata with the Observatory history
summary implementation and prior maintenance releases.

---

## v0.76.19 — derived history summaries

The Observatory now provides `history_summary.py`, a lossless-derived rollup for
raw and gzip-compressed journal segments. Summaries include segment SHA-256 hashes,
entry coverage, tick range, schema versions and organism-state counts. Raw history
is never replaced or deleted.

---

## v0.76.18 — compacted replay regression coverage

Corrected the compacted-journal contract test and retained coverage for replaying
`.ndjson.gz` archives without duplicate delivery.

---

## v0.76.17 — replay of compacted history

The Observatory server now reads `.ndjson.gz` journal archives during instance
replay. Compacted history is delivered once and then tracked by immutable line
count, while live NDJSON segments continue to use byte offsets for tailing.

---

## v0.76.16 — lossless Observatory compaction

Automatic journal deletion has been removed. Closed NDJSON segments can now be
compacted explicitly with `Journal.compact()`, which gzip-compresses them without
losing records and leaves the active segment untouched. Existing resident state
was not modified.

---

## v0.76.15 — resident journal retention and state audit

The Observatory journal now enforces a global 512 MiB retention cap across run ids,
pruning only whole historical segments and preserving the active segment. A
read-only inventory of the current resident state is recorded in
[`research/observatory-state-audit-2026-09-15.md`](../research/observatory-state-audit-2026-09-15.md).
No existing state files were modified.

---

## v0.76.14 — runtime projection contract test

The Observatory now exercises a real `OrganismRuntime` tick through the production
adapter and validates the resulting v3 snapshot against the local JSON Schema,
including BodySchema and signal knowledge surfaces.

---

## v0.76.13 — explicit Observatory UI transitions

Transport and application metadata updates now pass through
`observatory/state/transition.js`. Snapshot data remains committed atomically via
`commitSnapshotProjection`; this is the first incremental step away from direct
writes to the browser singleton.

---

## v0.76.12 — render boundary

Snapshot projection now returns a committed projection without importing the UI.
The application shell and transport/replay callers explicitly invoke the render
cycle after a successful projection, keeping ingestion and presentation boundaries
separate.

---

## v0.76.11 — release versioning policy

This hardening release defines the release lanes, contract-change requirements and
rule for documentation-only changes in [`docs/VERSIONING.md`](VERSIONING.md).
No organism behavior or Observatory schema was changed.

---

## v0.76.10 — valid knowledge-only snapshots

`observatory.adapter.project_tick()` now emits the required bounded undeveloped
BodySchema when signal knowledge is present without an explicit BodySchema. This
keeps knowledge-only projections valid under snapshot schema v3 while preserving the
organism's honest not-developed state.

---

## v0.76.9 — Observatory contract hardening

This maintenance release keeps the Milestone H runtime behavior unchanged while
closing two Observatory integration gaps:

- `observatory.resident` now supports both the documented script invocation and
  `python -m observatory.resident` with the same imports and CLI contract.
- The Observatory schema compatibility rules are centralized in
  [`schemas/CONTRACT_MATRIX.md`](../observatory/schemas/CONTRACT_MATRIX.md),
  covering snapshot versions 1–3 and bounded nested projections.

The Observatory contract suite passes in full (`163 passed`). No host write,
network transport or evaluator-facing behavior was introduced.

---

## v0.76.8

`v0.76.8` cierra el roadmap funcional hasta el Milestone H (Digital ecology).
Las versiones `v0.76.1`–`v0.76.8` son hardening, compatibilidad, métricas,
auditoría y cierre documental posteriores al cierre funcional de H:

- fisiología digital acotada: metabolismo, degradación, homeostasis, viabilidad y muerte;
- reproducción y herencia gobernadas por el hábitat;
- ecología digital con recursos finitos, intercambio offline, trust consciente de la evidencia,
  revisión con disenso y mediciones adversariales sintéticas;
- Observatory pasivo con Fleet/SSE local, replay, Phenotype/Self, topología cognitiva y
  proyección de signal knowledge;
- compatibilidad histórica de genomas, métricas poblacionales y ticks monotónicos del evaluador;
- documentación consolidada: `docs/roadmap.md` es la fuente canónica del estado.

El residente no realiza descubrimiento de pares, sockets de red, escritura en el host,
acciones autónomas, remediación ni propagación. Cualquier ampliación de esas capacidades
requiere un diseño independiente y una nueva revisión de consentimiento.

Validación registrada:

- `pytest -q observatory/tests`: 163 passed.
- `python -m compileall -q src tests observatory`: correcto.
- `git diff --check`: correcto.

La frontera posterior a H permanece sin definir; no se presenta como trabajo planificado.

## Cierre documental posterior al tag

El tag `v0.76.8` fija el estado funcional en `c70aebe`. Los commits documentales
posteriores en `main` solo organizan índices, clasificación de artefactos y
navegación; no cambian el contrato ni la versión del paquete.
