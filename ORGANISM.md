# Organism changelog — the complete evolution

## Current status

**v0.80.03.** Milestones A through E2 are complete and Milestone H is implemented through its current roadmap boundary: safe real perception, adaptive host modeling, autonomous inquiry and explanation, operational/developmental embodiment, endogenous plasticity, biological memory consolidation, bounded physiology, ecological interaction, offline exchange/replay, evidence-aware trust, dissent-preserving revision, consent-bound local communication and bounded synthetic adversarial ecology. Milestone I now has irreversible physiology state, explicit metabolic intake, resource-backed repair, habitat release, a hard post-death execution boundary and an integrated longitudinal gate matrix; broader physiological generalization remains open. Milestone J adds anti-capture attention, evidence hypotheses and shadow prediction; shadow candidates now survive checkpoint/replay and promotion remains bounded, the longitudinal continuation gate is covered, while broader generalization remains open. Milestone K adds an explicitly authorized bounded social habitat, aggregate relation memory, finite-resource exchange/competition, local evidence-driven resource adaptation, explicit directional rejection/restart and competition-fed resource evidence; repeated local denials now create bounded exploration pressure that permits revision without permanent exclusion. Social exchanges and competition consume an explicit checkpointed cognitive-metabolism cost. A dedicated evaluator-only study verifies revision after repeated denials and continuation replay in an independent habitat. Broader emergence and generalization remain open. I now integrates bounded retention degradation and irreversible excretion counters. Observatory now exposes checkpointable rest intent, bounded attention concentration/entropy, rejection evidence and degradation counters as passive fields. Attention budgets now reject non-finite limits and ranking costs; NaN uncertainty cannot enter the scheduler, while +inf remains reserved for genuinely unacclimated capabilities. Network sockets, peer discovery and autonomous remediation remain disabled.

The canonical roadmap is implemented through Milestone H. Milestones I (fisiología integrada), J (desarrollo predictivo autónomo) and K (sociabilidad emergente) are implemented incrementally with explicit remaining gates. I closes vital and mortal needs; J improves hypothesis and prediction formation; K provides bounded cellular interaction capabilities without imposing social objectives.

Full milestone history and design are in [`docs/roadmap.md`](docs/roadmap.md), [`docs/design/endogenous-plasticity.md`](docs/design/endogenous-plasticity.md), and [`docs/design/reproduction-death-population.md`](docs/design/reproduction-death-population.md).

## Milestone A — Safe real perception (v0.30-v0.33)

Symbiont gained a typed contract for a single host reading (`SensorReading`: unit, monotonic timestamp, quality, and a privacy class that is always aggregate or non-identifying — there is no identifying option in the type), a cross-platform stdlib-only provider sampling real CPU load and disk usage read-only, a bounded repeated discovery-and-sampling lifecycle with per-provider backoff, and `HostAcclimation` — an initial descriptive baseline (mean/stdev/count) per capability with threat classification withheld by construction, not convention: `CapabilityBaseline`'s only public fields are `count`/`mean`/`variance`/`stdev`.

## Milestone B — Adaptive host model (v0.34-v0.37)

A real reading became a `Percept`: a platform-neutral perception identified only by a stable semantic name (`system_load`, `storage_pressure`), never by the internal `capability_id`/`source` tokens — specifically so cognition never needs to import a platform provider. `RhythmModel` learned a separate baseline per (percept, time-of-day-bucket) pair using only a coarse, cyclical four-bucket day quantization (the actual hour is read only to compute the bucket and never stored). `DriftAwareBaseline` separated a one-off `isolated` outlier from an in-progress `gradual` shift from a confirmed `regime_shift`, buffering a candidate run and only committing it once confirmed so a single spike never contaminates the baseline. `export_checkpoint`/`import_checkpoint` closed the milestone: a schema-versioned JSON document carrying only what those modules already commit to exposing, never a raw reading or timestamp.

## Milestone C — Autonomous inquiry and explanation (v0.38-v0.41)

`attend_to_host` allocated a hard, bounded attention budget across known capabilities by uncertainty-per-cost — a resource-allocation mechanism, never a threat judgment (`docs/adr/ADR-0003`). `SecondLookSession` let the organism temporarily sample one already-discovered capability at higher resolution, authorized/read-only/cancellable by construction. `EvidenceRevisionLedger` folded new evidence into the baseline while keeping a `DissentRecord` whenever the evidence significantly disagreed — contradiction is preserved, not smoothed away. `narrate_host` closed the milestone by composing belief, attention and evidence into one plain-language, classification-free `NarrativeEntry` per capability.

## Milestone D — Operational embodiment (v0.42-v0.49)

Knowledge capsules (`create_capsule`/`verify_capsule`, Ed25519-signed, identity-minimized) enabled offline, tamper-evident exchange — no network I/O, no peer discovery. `SourceTrustModel` learned local, per-source agreement between a capsule's claims and the organism's own beliefs (a known echo-chamber limitation, explicitly flagged for later evidence-aware trust work). `OrganismRuntime` replaced one-shot CLI verbs with a single continuous cognitive cycle; `GovernedOrganism` wrapped it with live-revocable consent and a hard tick/frequency budget; checkpoints gained atomic disk persistence and a migration chain; a `host-constrained-environment` CI job proved the host layer survives musl/Alpine. `DefensiveAdvisor` added a decision-gated, human-reviewed recommendation — never autonomous action — built only after the project owner resolved seven design questions on delivery, trigger, vocabulary, scope, rate limiting, persistence and consent up front. `symbiont_lab.evaluation.advisory_evaluation` closed the milestone by measuring advisories against a real operator's own judgment, one-way only, enforced by the same AST boundary that protects cognition from ground truth.

## Milestone E — Developmental embodiment (v0.50-v0.54)

The organism stopped needing a hand-written sensor catalog. `AdaptiveSenseModel` (v0.50) discovers bounded, vetted OS surfaces, assigns them opaque identities, and runs as a transparent, owner-installed `systemd --user` resident. v0.51 learned bounded same-time and lagged relations between senses and suppressed redundant ones (pairwise correlation ≥ 0.97). v0.52 developed active/probing/dormant sensory tiers, spending a rotating observation budget selectively rather than sampling everything every tick. v0.53 gave the organism a self-model: `SelfModel` learns per-sense cost (timed at the provider-call boundary), graduated health (from reading quality, not a binary success flag), and confidence (maturity × health × quality — composed from, never duplicating, existing signals) — feeding real relative-cost ranking into attention and a health gate into second-look investigation. v0.54 closed the milestone with long-run maturation: idle decay of self-model trust for a sense that's gone quiet, slow-creep detection in `DriftAwareBaseline` (a free-running fast EWMA normalized against a *frozen* noise floor — the live-stdev version was tried and rejected empirically for self-corrupting the very signal it measured), and checkpoint continuity so a restart never mistakes a freshly-active sense for one that's been idle since tick zero.

## Milestone E2 — Endogenous plasticity (v0.55-v0.59)

The organism's self-programming capability, implemented as **plasticity of data under an immutable kernel**, never generated, edited or executed code.

* **v0.55 — Genome kernel.** A closed `NodeKind`/`EdgeKind` catalog and hard, never-learnable `KernelLimits`; a declarative, versioned `Genome` validated by a strict, non-`eval` codec; genome identity via a deterministic sha256 hash; checkpoint persistence as its own bolt-on namespace.
* **v0.56 — Cognitive graph.** `PlasticNode`/`PlasticEdge` and a synchronous, double-buffered `CognitiveGraph.activate()` — deterministic regardless of construction order, because every node reads only from this tick's fresh sense inputs or last tick's frozen frame, never from a value still being computed in the same pass.
* **v0.57 — Label-free learning.** Prediction error via Huber loss, decaying eligibility traces, and bounded Oja weight updates, with no external label anywhere in the loop.
* **v0.58 — Metaplasticity and structure.** A five-dimension `LearningObjective` compared by Pareto dominance; bounded metaparameter adaptation; structural proposals, pruning lifecycle and `SafetyState` freeze.
* **v0.59 — Laboratory evolution.** `symbiont_lab/evolution/`: declarative genome mutation operators, Pareto-archive selection and cycle-protected append-only lineage. Evolution remains confined to explicit laboratory runs; the later resident reproduction capability is implemented separately and never by granting the organism access to the laboratory evolution apparatus.

**Post-milestone hardening (v0.59.1-v0.59.3):** a first fresh adversarial audit closed defects in normalizer persistence, structural mutation application, safety-state enforcement, finite objectives, lifecycle reachability, bounded structural bookkeeping, metaplasticity bounds, eligibility traces, node ids and lineage ancestry. `CognitiveBridge` then wired graph activation, learning and structural plasticity into `OrganismRuntime`, and graph-state checkpoint persistence closed restart continuity for the learned mind.

**v0.59.4 — second adversarial hardening pass.** Kernel limits are now enforced where mutations and checkpoints are actually committed, not merely declared. Structural batches validate through the same `CognitiveGraph` invariants as normal construction and apply transactionally, preventing an invalid learned edge from partially changing or crashing the resident graph. Plastic learning is no longer unconditional: attention selects the reachable learning subgraph, sensory health × availability modulates the update, eligibility must be present and each edge's own `plasticity` scales Oja. Checkpoint restore rejects impossible lifecycle metadata and ambiguous booleans, topology revision survives restart, and contradiction memory persists only as bounded per-capability counts so numeric evidence is not turned into a history log. Observatory now publishes topology on the first cognitive tick, survives `run_id` rollover without discarding the new sequence zero, tails journals by file position, validates malformed local artifacts defensively, actually resolves referenced JSON schemas in contract tests, and runs its complete test directory in CI. The Observatory resident can also receive the same first-launch genome/graph inputs as the main live CLI. Package/runtime metadata is aligned at 0.59.4.

**v0.59.5 — Biological memory consolidation.** A full technical design ([`docs/design/biological-memory-consolidation.md`](docs/design/biological-memory-consolidation.md)) changed the persistence model from "serialize learned state" to "persist consolidated memory": checkpoint schema v6, a `WeightStabilityTracker` that commits an edge's weight class only after epoch-spaced stability (node-atomic — a node's changed incoming edges commit together or not at all), a consolidated-baseline codec for host statistics (signed-log center, a constant sentinel plus log buckets for scale, a monotone maturity table over real observation support), and `SelfModel`'s `RecencyClass` replacing the exact `last_observed_tick`. A bounded reacclimation period after restart keeps the cold-start transient itself from ever being misread as a salient or structural event. PR #76's earlier continuity guarantee is deliberately superseded here, not silently dropped: a restart no longer reconstructs the previous tick's activation, because seeding one from a coarse class would synthesize a microstate that never actually occurred — worse than genuinely losing continuity. `MemoryConsolidator`'s salient-event fast path — a one-shot durable trace for one exceptional, attended, reliable transition, distinct from the ordinary slow path's epoch-spaced support requirement — is wired into the real `OrganismRuntime.tick()` loop, closing the one piece of the design that had no caller in the organism until this release. All eleven exit conditions in the design's §25 are satisfied.

## Milestone F — Digital physiology (v0.60-v0.64)

Implemented. `MetabolicLedger`, `InformationAssimilator`, `DegradationQueue`, `HomeostaticController` and `ViabilityController` provide bounded intake, metabolism, maintenance, degradation, repair, dormancy and irreversible death semantics.

## Milestone G — Reproduction and heredity (v0.65-v0.69)

Implemented. `HabitatBirthAuthority` governs identity and lineage; reproductive pressure, clonal budding, paired recombination and separated genetic, epigenetic and cultural inheritance remain bounded and habitat-authorized.

## Milestone H — Digital ecology (v0.70-v0.76)

Implemented through v0.76. `SharedHabitat` and `EcologicalResourcePool` provide finite carrying capacity and resource competition. Offline exchange, replay protection, evidence-aware trust, dissent-preserving revision, revocable local communication and synthetic adversarial/population measurements are available without network discovery or evaluator leakage.

## Mantenimiento posterior a v0.76

Releases **v0.76.1-v0.76.46** are historical hardening and closure releases. v0.77.0 starts the next milestone lane. Milestones I (Fisiología integrada), J (Desarrollo predictivo autónomo) and K (Sociabilidad emergente) require their respective integration, safety and study gates. Both require design, safety and consent gates before new capabilities are enabled.

The scientific progression is now explicit: **development → physiology → ecology → society**. Cooperation remains an observable ecological outcome, never a hard-coded objective.

## Milestones I–K — implementation increments (v0.77.0-v0.79.25)

* **v0.77.0-v0.77.1 — I:** physiology became an irreversible runtime boundary:
  explicit intake, deterministic vital states, habitat release and a hard
  post-death execution stop.
* **v0.78.0 — J:** the predictive-development lane added bounded attention and
  evidence-driven shadow prediction without evaluator feedback.
* **v0.79.0-v0.79.4 — K/J:** an explicitly authorized `SocialHabitat`, aggregate
  relation ledger, finite-resource exchange/competition and deterministic
  milestone study harnesses were added; comparative study imports were made
  collection-safe.
* **v0.79.5 — K:** social habitat checkpoints preserve members, resources and
  relation evidence together for deterministic restart/replay.
* **v0.79.6 — I:** `OrganismRuntime.repair()` performs bounded, maintenance-backed
  repair and rejects actions after death.
* **v0.79.17 — laboratory integrity:** comparative protocol configuration now
  fails with its declared validation error when required parameters are absent.
* **v0.79.18 — K evaluation baseline:** a seeded, evaluator-only social-emergence
  study now replays finite-resource exchange and competition and reports relation
  valence plus isolated members without imposing social goals.
* **v0.79.19 — I dormancy coupling:** dormant runtime physiology now scales declared
  observation, cognition and persistence costs without generating free reserves.
* **v0.79.20 — I reproduction boundary:** runtime reproductive pressure and authorized
  clonal budding now enforce parent identity, reserve consumption and habitat capacity.
* **v0.79.21 — integrity:** reproduction imports no longer add a forbidden lineage
  module under `symbiont/`; structural boundary tests remain green.
* **v0.79.22 — I resource coupling:** successful runtime budding now charges an
  explicit, checkpointed maintenance cost; failed births remain cost-free.
* **v0.79.23 — I germinal materialization:** authorized budding can create a fresh
  child runtime with inherited genome and empty germinal graph, without copying
  acquired phenotype or physiology.
* **v0.79.24 — I replay gate:** a deterministic runtime reproduction study now
  verifies germinal child identity, generation and checkpoint replay.
* **v0.79.25 — I population boundary:** a parent/child runtime study verifies
  child death, exactly-once authority release and parent survival.
* **v0.79.26 — K interaction instrumentation:** the evaluator-only social
  emergence study now records unique unordered pairs and Shannon pair entropy,
  exposing interaction concentration without feeding metrics back into runtime
  decisions. This is measurement, not autonomous social emergence.
* **v0.79.27 — K pairwise scarcity evidence:** competitive requests now attribute
  observed scarcity to competing resident tokens when applicable, preserving
  habitat cost for solitary requests. This makes negative relations contextual
  rather than a universal evaluator label.

* **v0.79.28 — K runtime boundary:** `OrganismRuntime` can issue explicit
  exchange and competition requests through an attached authorized
  `SocialHabitat`; it never schedules peers or chooses social objectives, and
  dead runtimes are rejected.

* **v0.79.29 — J runtime shadow observability:** the runtime exposes its
  bounded shadow-prediction evidence through a read-only property, keeping
  promotion opt-in and evaluator state outside cognition.

* **v0.79.30 — J explicit promotion boundary:** runtime callers can request
  promotion of an eligible shadow candidate explicitly; the operation remains
  bounded, opt-in and unavailable after irreversible death.

* **v0.79.31 — J longitudinal runtime gate:** the evaluator now drives two
  runtime-owned cognitive bridges over repeated opaque observations; a
  predictive candidate promotes explicitly while a constant-no-gain candidate
  remains unpromoted.

* **v0.79.32 — K local relation memory:** each runtime now retains its own
  bounded relation ledger for explicit social outcomes, checkpointed with the
  organism state; competition requests cannot impersonate another resident.

* **v0.79.33 — K social death boundary:** an irreversible runtime death now
  releases its admitted social-habitat membership exactly once, alongside the
  existing ecological and birth-authority releases.

* **v0.79.34 — K replay/death study:** a deterministic study verifies local
  relation-memory replay alongside social-habitat membership/resources and
  exactly-once release when a resident dies.


These releases remain incremental: I still requires integrated dormancy and
reproduction gates; J requires longitudinal promotion evidence; K requires
reciprocity and emergence studies. None introduces network discovery, social
objectives or evaluator semantics into the organism.

* **v0.79.35 — K reciprocidad y revisión:** los intercambios inversos registran
  reciprocidad como evidencia local y un estudio evaluator-only cubre evidencia
  bidireccional, conducta unilateral, conflicto y aislamiento sin objetivos
  sociales impuestos.

* **v0.79.36 — K Observatory social evidence:** the passive Observatory now
  publishes bounded directional reciprocity, conflict and freshness anchors from
  the runtime-owned relation ledger; producer and schema validation stay
  read-only and evaluator-independent.

* **v0.79.37 — K percepción social:** el runtime puede leer presencia y estado
  de canal de residentes admitidos mediante señales opacas y acotadas; no recibe
  metadatos ni objetivos sociales.

* **v0.79.38 — K decisión local:** se añade selección de oportunidades basada en
  evidencia relacional propia y canales no suspendidos, sin planificador central,
  movimiento de recursos ni objetivos sociales impuestos.

* **v0.79.39 — I necesidades metabólicas:** el Observatory expone presión y clases
  de reserva discretas para revisar inanición, recuperación y dormancia sin
  filtrar valores numéricos ni decisiones internas.

* **v0.79.40 — I intake competido:** la adquisición metabólica pasa por recursos
  finitos del hábitat y solo la cantidad aceptada entra en la reserva, con
  rechazo post-muerte y sin reposición virtual.

* **v0.79.41 — K emergencia runtime:** el estudio determinista de varios runtimes
  verifica selección local, intercambio, diversidad de pares y reciprocidad sin
  asignar roles ni objetivos sociales.

* **v0.79.42 — K control de canal:** suspensión y reanudación pasan por la
  identidad del runtime, respetan muerte y checkpoint, y se verifican en replay.

* **v0.79.43 — K escenarios adversariales:** se verifican soporte, contención de
  recurso y aislamiento local en un hábitat sintético, sin política social central.

* **v0.79.44 — hardening de validación:** las copias locales del Observatory no
  contaminan el descubrimiento de la suite y permanecen fuera del repositorio.

* **v0.79.45 — Observatory phenotype:** la proyección visual distingue salud,
  estrés, recuperación, receptores y rutas cognitivas usando solo datos publicados.

* **v0.79.46 — K ciclo de vida:** se verifica replay social, reanudación,
  trazabilidad de nacimiento y liberación post-muerte con el hijo aún vivo.

* **v0.79.47 — Observatory evidencia relacional:** soporte, daño y frescura
  quedan visibles como evidencia agregada bounded, sin objetivos ni ranking.

* **v0.79.48 — Observatory UI social:** las relaciones acotadas se ingieren y
  se muestran como evidencia agregada, sin objetivos, etiquetas ni ranking.

* **v0.79.49 — Observatory accesibilidad social:** la tabla accesible incluye
  valencia, observaciones y frescura de la evidencia relacional publicada.

* **v0.79.50 — K decisión local:** la selección social pondera evidencia propia,
  frescura y exploración sin imponer una política social central.

* **v0.79.51 — K selección reproducible:** el estudio evaluator-only verifica
  preferencias locales basadas en evidencia sin devolver etiquetas al runtime.

* **v0.79.52 — K revisión longitudinal:** una contradicción de evidencia puede
  cambiar la selección local y reabrir exploración sin política social central.

* **v0.79.53 — K contexto multi-vecino:** el estudio bounded combina revisión,
  suspensión, aislamiento y competencia finita con varios vecinos.

* **v0.79.54 — K paridad live/replay:** la selección social multi-vecino y la
  suspensión conservan el mismo resultado después de restaurar checkpoint.


* **v0.79.55 — K continuidad generacional:** el runtime puede unir descendientes a un hábitat social autorizado y conservar presión reproductiva fresca; un estudio evaluator-only verifica tres generaciones, replay de checkpoint, trazabilidad de parentela y liberación de cada progenitor muerto.


* **v0.79.56 — K paso social autónomo:** el runtime puede tomar una oportunidad social acotada usando únicamente presencia opaca, memoria relacional local y tokens de recursos del hábitat autorizado; el estudio de emergencia ya ejercita ese camino sin suministrar pares ni etiquetas al organismo.


* **v0.79.57 — K competencia local:** el runtime puede proponer una contienda de recurso a partir de evidencia negativa propia; el hábitat adjudica propuestas simultáneas y conserva la escasez finita sin imponer etiquetas ni ganadores.


* **v0.79.58 — I descanso explícito:** el runtime puede solicitar y cancelar descanso; la decisión queda checkpointed, reduce la transición de presión severa a dormancia y no crea reservas ni integridad gratuitamente.

* **v0.79.59 — I recuperación explícita:** el estudio evaluator-only ejercita
  intake de mantenimiento, reparación acotada, checkpoint del descanso y
  reanudación; la reparación no crea recursos gratuitamente.

* **v0.79.60 — Observatory fisiológico:** la proyección añade `resting_requested`
  al estado fisiológico, con contrato JSON cerrado y normalización browser
  bounded; el campo es observacional y no controla al runtime.

* **v0.79.61 — Observatory atención:** la proyección añade concentración y
  entropía de asignaciones, acotadas a `[0,1]` y sin valores crudos de señales.

* **v0.79.62 — J replay predictivo:** los candidatos shadow serializan muestras
  y pérdidas bounded; la promoción conserva la misma ganancia tras restaurar un
  checkpoint, sin promover automáticamente.
* **v0.79.63 — K longitudinal runtime:** se añade un estudio prolongado de
  pasos sociales autónomos con checkpoint intermedio, diversidad de pares y
  aislamiento, sin roles ni objetivos asignados por el evaluador.
* **v0.79.64 — K adaptación ecológica:** la memoria local de recursos opacos
  permite revisar la elección tras una denegación y conserva la adaptación en
  checkpoint/replay, sin asignar nichos desde el evaluador.
* **v0.79.65 — K rechazo explícito:** la memoria relacional conserva rechazos
  direccionales, el runtime puede suspender y reanudar solicitudes, y el
  Observatory proyecta el contador sin convertirlo en una valoración global.
* **v0.79.66 — K evidencia de competencia:** la contención finita alimenta la
  misma memoria local de disponibilidad que usa el intercambio, manteniendo la
  adaptación bounded sin recompensas universales.
* **v0.79.67 — K diferenciación de nicho:** un estudio sintético mide dos
  elecciones de recursos diferenciadas tras contención local y replay, sin
  asignar roles, nichos ni preferencias al evaluador.
* **v0.79.68 — K paridad del Observatory:** la normalización browser conserva
  la evidencia direccional de rechazo publicada por el runtime, manteniendo
  el contrato entre snapshot, UI y proyección pasiva.
* **v0.79.69 — K reexploración bounded:** la memoria local de recursos vuelve a
  probar tokens cuya evidencia quedó antigua, evitando convertir una denegación
  histórica en una exclusión permanente sin introducir preferencias externas.
* **v0.79.70 — K evidencia de recursos en Observatory:** el snapshot y la UI
  conservan de forma pasiva los tokens opacos, disponibilidad, denegaciones y
  frescura del ledger local, sin exponer semántica del host ni control.
* **v0.79.71 — I residuos integrados:** el runtime conecta la cola bounded de
  degradación con el ciclo de ticks y checkpoint/replay; solo expone contadores
  agregados al Observatory.
* **v0.79.72 — I recuperación sostenida:** el arnés evaluator-only fuerza un
  déficit prolongado, verifica dormancia, exige intake explícito para volver a
  actividad y compara la recuperación con replay desde el checkpoint del déficit.

* **v0.79.73 — K replay de trayectoria social:** el estudio de especialización conserva las secuencias completas de elección y compara la continuación posterior al checkpoint en un hábitat independiente, detectando divergencias de asignación finita que una igualdad de ledger aislada no revelaría.

* **v0.79.74 — K replay longitudinal:** el estudio prolongado compara la secuencia completa de pares autónomos posterior al checkpoint en un hábitat independiente, no solo la igualdad inmediata del ledger.

* **v0.79.75 — K cambio de régimen ecológico:** un estudio evaluator-only cambia de forma bounded la disponibilidad de tokens opacos y verifica que la memoria local revisa su elección, con replay de la continuación en un hábitat independiente.

* **v0.79.76 — I reparación sostenida:** el estudio evaluator-only repite reparación con intake finito, verifica el límite de integridad, control sin intake y replay desde checkpoint.

* **v0.79.77 — I intake compartido:** un estudio evaluator-only verifica que dos residentes compiten por recursos finitos del `SharedHabitat`, que la asignación queda limitada y que el resultado se conserva tras replay.

* **v0.79.78 — I capacidad reproductiva:** el estudio de población verifica que una segunda cría queda bloqueada cuando la capacidad está llena y que la muerte libera la asignación una sola vez.

* **v0.79.79 — J ciclo de hipótesis shadow:** las predicciones shadow distinguen candidate, supported, contradicted y retired; los candidatos negativos se retiran tras evidencia sostenida y el estado se conserva en checkpoint/replay.

* **v0.79.80 — K revisión tras denegación:** el ledger local conserva rachas bounded de denegaciones consecutivas, reduce la prioridad de un token bajo un cambio de régimen y conserva esa evidencia en checkpoint sin convertirla en una exclusión permanente.

* **v0.79.83 — J replay longitudinal shadow:** la continuación de evidencia predictiva sobre checkpoint conserva muestras, estado soportado y ganancia frente a persistencia antes de promover un `PREDICTOR`; la divergencia numérica de pérdidas por cuantización queda observada y no retroalimenta al organismo.

* **v0.79.85 — K propagación contextual:** el runtime conserva el canal/token opaco en su propia memoria al registrar intercambios y competencia, evitando que la contextualidad se pierda al cruzar el límite del hábitat.

* **v0.79.86 — K selección contextual:** la selección social evalúa el mejor canal opaco local de cada objetivo, en lugar de dejar que un único canal arbitrario oculte evidencia favorable y desfavorable.

* **v0.79.87 — K competencia contextual:** las propuestas de competencia nacen solo de evidencia negativa fresca y seleccionan el canal opaco que la produjo, evitando competir por un recurso no relacionado.

* **v0.79.88 — K estudios contextuales:** los estudios longitudinales y de cambio de contexto registran explícitamente el canal opaco, preservando las métricas históricas sin fusionar evidencias de recursos distintos.

* **v0.79.89 — I gates integrados:** un arnés evaluator-only reúne replay de reparación, replay de reproducción con capacidad bloqueada y continuación social prolongada, manteniendo cada resultado fuera de la cognición.

* **v0.79.90 — K fiabilidad relacional:** la selección local pondera frescura, observaciones y presión de conflicto mediante una fiabilidad bounded; los conflictos reducen confianza sin convertir una relación en una etiqueta permanente.

* **v0.79.91 — cierre documental de gates:** I registra la matriz longitudinal integrada y J registra el gate de continuidad shadow cubierto; las fronteras de generalización siguen explícitamente abiertas.

* **v0.79.92 — estado canónico I/J/K:** README y ORGANISM reflejan que I dispone de su matriz de gates, J de continuidad shadow y K de relaciones contextuales; las generalizaciones pendientes permanecen visibles.

* **v0.79.93 — Observatory contextual:** la proyección pasiva publica el canal opaco y la fiabilidad bounded de cada relación, manteniendo compatibilidad con snapshots históricos y sin retroalimentar decisiones.

* **v0.79.94 — Observatory UI contextual:** el perfil individual muestra el canal opaco y la fiabilidad bounded junto a la evidencia social, manteniéndolos como observaciones y sin ranking.

* **v0.79.95 — validación relacional bounded:** la memoria social rechaza
  identificadores no textuales o excesivamente largos, valores no finitos y
  ticks ambiguos tanto al observar como al restaurar checkpoints. Los datos
  corruptos no pueden alterar valencia, fiabilidad ni selección contextual.

* **v0.79.96 — límites ecológicos bounded:** el pool social rechaza recursos,
  solicitudes y reposiciones no finitas o ambiguas, manteniendo la asignación
  proporcional y la competencia dentro de cantidades observables.

* **v0.79.97 — estudio adversarial social:** el arnés evaluator-only cubre
  cooperación, competencia por recurso finito, aislamiento y rechazo
  direccional con reanudación, manteniendo la evidencia local separada de las
  etiquetas del evaluador.

* **v0.79.98 — matriz social integrada:** un arnés evaluator-only reúne los
  límites adversariales, el replay contextual y la continuidad social de
  generaciones, verificando cooperación, competencia, aislamiento, rechazo
  reversible y trazabilidad sin retroalimentación del evaluador.

* **v0.79.99 — codec de pesos estricto:** los checkpoints cognitivos rechazan
  codecs desconocidos y pesos no finitos, manteniendo la migración explícita
  entre el esquema histórico y el codec v2 con cero exacto.
