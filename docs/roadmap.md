# Symbiont organism roadmap

This roadmap prioritizes capabilities acquired by the organism. Laboratory work is introduced only when a new organism capability needs a new measurement instrument.

The sequence is directional rather than calendar-based.

The roadmap distinguishes two things that must not be conflated:

1. **developmental limitations** — capabilities the organism does not have yet but may acquire later;
2. **permanent invariants** — consent, boundedness, epistemic separation and anti-evasion constraints that remain in force even as capability grows.

## North star

Build a benevolent digital organism that can develop on a consenting host, regulate its own internal computational economy, maintain viability under finite resources, reproduce through explicit heredity mechanisms, and eventually participate in bounded digital ecologies where cooperation, competition, coexistence and specialization are observable outcomes rather than hard-coded goals.

The organizing research sequence is:

> **Development before intelligence. Physiology before ecology. Ecology before society.**

Symbiont is not intended to remain permanently solitary, read-only or non-reproductive merely because those are properties of the current release. New capabilities may be added when their semantics, consent model, resource model and experimental observability are designed first.

At the same time, increased capability must not weaken the permanent invariants: no covert persistence, no stealth or evasion, no privilege escalation, no exploitation, no hidden evaluator oracle, no learned bypass of kernel limits, and no uncontrolled propagation.

---

Full milestone history (A-H) and the per-patch tracking log are archived in
[`docs/history/roadmap-log.md`](history/roadmap-log.md).

## Permanent invariants

These constraints survive future increases in capability.

1. Real-host access remains explicit, revocable and capability-bounded.
2. Learned state cannot manufacture permissions, commands, executable code or new kernel capabilities.
3. Credentials and privilege-escalation mechanisms remain outside the organism's developmental substrate.
4. Residence and persistence remain transparent and owner-controlled.
5. No stealth, concealment or evasion is used to maintain residence or acquire resources.
6. No exploitation is used to acquire capabilities, compute, storage or access.
7. Hard CPU, memory, storage and communication ceilings remain outside learned control.
8. Reproduction never means covert or uncontrolled propagation.
9. Materializing a descendant requires an authorized habitat, carrying-capacity slot and explicit resource allocation.
10. A dead organism identity cannot be normally resumed as though continuity never closed.
11. Experimental ground truth remains outside organism cognition.
12. The laboratory may observe the organism without silently becoming its controller.
13. New write, network, action or reproduction capabilities cross an explicit design and consent gate before implementation.

These invariants do **not** imply that Symbiont must remain permanently read-only, non-communicating or non-reproductive.

---

## Birth, identity, dormancy and death

The physiology and reproduction milestones require explicit life-cycle semantics.

The project uses the following distinctions unless a later design document supersedes them:

- **birth** — creation of a new organism identity with a valid genome and authorized initial resource allocation;
- **germinal / developing / mature** — viable developmental phases of one organism identity;
- **active** — viable and executing its normal cognitive cycle;
- **stressed** — viable but physiologically constrained by resource or integrity pressure;
- **dormant** — viable but intentionally running a minimal maintenance cycle;
- **stopped** — process not running; this is not by itself death;
- **restarted** — the same organism identity resumes only if its durable viable state is valid;
- **dying** — continuity is still present but bounded recovery has failed and death finalization is pending;
- **dead / non-viable** — organism continuity is explicitly and irreversibly closed;
- **descendant** — a new organism identity created through a reproductive event, even when it has exactly the same genome as its parent.

Normal restore rejects a `DEAD` identity. Reconstructing or cloning from historical artifacts, if later allowed experimentally, creates a new identity and is not resurrection.

Organism lifecycle, cognitive topology health and reproductive readiness remain separate state dimensions. For example, an organism may simultaneously be `MATURE`, `ADAPTIVE` and `REPRODUCTIVELY_READY`.

This prevents process management concepts from silently standing in for biological ones.

---

## Merge policy

The project owner has explicitly instructed that GitHub Actions are not a merge gate.

A release can therefore merge after local/structural review even when hosted CI is unavailable.

The remaining gates are:

1. base/head drift is checked before merge;
2. no unresolved requested changes are knowingly ignored;
3. new resource use is bounded by construction and covered with deterministic tests;
4. privacy, consent and safety invariants accompany functional behavior;
5. ground truth remains outside organism cognition;
6. the release documents the new organism capability;
7. lineage, death and reproduction changes are transactional and replay-testable;
8. ecological changes include aggregate carrying-capacity tests, not only per-organism limits;
9. dead-organism restore and population-over-capacity paths have explicit negative tests.

---

## Decision gates

Work pauses for an explicit architectural and safety decision before any merge that:

- requests new write, execute, elevated or remote permissions;
- expands perception into identifying metadata or user content;
- enables network exchange;
- introduces hidden or non-removable persistence;
- permits autonomous real-world action;
- materializes descendants outside an existing authorized habitat;
- changes reproductive authority or carrying-capacity ownership;
- creates unbounded CPU, memory, storage, population or network use;
- weakens the separation between organism and evaluator;
- allows learned state to alter immutable kernel limits or permissions;
- materially expands a human-facing security/operational advisory beyond the already approved consultative boundary.

Transparent owner-installed residence and bounded current read-only sensory development are already explicitly approved and do not reopen those decisions.

---

## Milestone I — Fisiología integrada (implementación parcial)

Milestone I cierra el acoplamiento entre intake, metabolismo, homeostasis,
reparación, dormancia, degradación, viabilidad, reproducción, muerte y hábitat.
El diseño normativo está en
[`design/milestone-i-fisiologia-integrada.md`](design/milestone-i-fisiologia-integrada.md).

La implementación ya cubre estado fisiológico, intake explícito, checkpoint,
liberación de hábitat y frontera post-muerte. Incluye un arnés determinista de
inanición/recuperación en `symbiont_lab.studies.physiology`. Quedan gates de
integración para reparación, dormancia y reproducción; el Observatory ya
publica estos estados de forma pasiva.

## Milestone J — Desarrollo predictivo autónomo (implementación parcial)

Milestone J convierte señales opacas y relaciones estadísticas en hipótesis
contrastables, con atención anti-captura, persistencia cuantizada con cero
exacto, conceptos `stranded` y predicción en shadow mode antes de promover
nodos `PREDICTOR`. Sus métricas son externas y no otorgan semántica privilegiada
al organismo. El diseño normativo está en
[`design/milestone-j-desarrollo-predictivo.md`](design/milestone-j-desarrollo-predictivo.md).

La implementación se divide en P0 (codec y atención), P1 (hipótesis y reparación
de rutas) y P2 (predicción e instrumentación). Existe además un gate longitudinal de shadow-promotion con candidatos positivos
y sin ganancia. La promoción runtime es opt-in, bounded y persiste su contrato
en checkpoints.

## Milestone K — Sociabilidad emergente (implementación parcial)

Milestone K proporciona capacidades celulares para percibir, intercambiar,
competir, asociarse, separarse y revisar interacciones sin imponer una sociedad
ni objetivos sociales. El diseño normativo está en
[`design/milestone-k-sociabilidad-emergente.md`](design/milestone-k-sociabilidad-emergente.md).

La base implementada es un ledger de relaciones agregadas, un `SocialHabitat`
autorizado y un motor de intercambio/competencia sobre recursos finitos. Existe
un arnés determinista de intercambio/competencia para evaluación externa.
El ledger conserva ahora reciprocidad, conflictos y frescura de la evidencia,
y el hábitat permite suspender/reanudar pares explícitamente, con checkpoints
backward-readable. La validación longitudinal básica ya cuenta con estudios de suspensión,
reactivación y diferenciación de nichos. v0.79.18 añade un baseline determinista
de emergencia para el laboratorio; v0.79.19 acopla la dormancia del runtime a
costes de actividad reducidos sin reposición gratuita; v0.79.20 integra presión
reproductiva y budding clonal autorizado con identidad y capacidad acotadas; v0.79.21 conserva la frontera estructural del paquete y
v0.79.22 cobra el coste metabólico de nacimientos exitosos; v0.79.23 materializa
el runtime germinal del descendiente sin copiar el fenotipo adquirido; v0.79.24
verifica el replay determinista de padre/descendiente; v0.79.25 verifica muerte
y liberación exactly-once en una población padre/hijo. Esto
no demuestra todavía emergencia autónoma en producción ni impone ninguna meta
social o semántica humana.

---

