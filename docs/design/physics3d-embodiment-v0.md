# Physics3D Embodiment v1

Status: implemented canonical-runtime integration

## Purpose

Physics3D is a lightweight physical embodiment apparatus for the canonical
Symbiont organism. It exists to study what a Symbiont can discover and learn
when its ordinary runtime inhabits a real articulated 3D body.

PyBullet is not a second cognitive runtime and does not contain a behavioural
policy. It supplies physical state, gravity, collision and actuator
consequences.

## Canonical architecture

```text
PyBullet physical state
        |
        v
PhysicsReadingProvider
        |
        v
HostLifecycle
        |
        v
PrivateModelOrganismRuntime.tick()
  |     |       |        |
  |     |       |        +-- Private SLM experience
  |     |       +----------- BodySchemaEngine v2
  |     +------------------- physiology / homeostasis / metabolism
  +------------------------- cognition / motor discovery
        |
        v
MotorIntent -> ActuatorSystem -> Actuation
        |
        v
apparatus-owned actuator binding
        |
        v
PyBullet torque -> physical consequences -> next tick
```

There is exactly one organism runtime in this path.

The former Physics3D prototype directly executed
`Symbiont.step() -> EmbodimentSession -> Body.apply_activations()`. That path
was useful for the first visual prototype but duplicated the canonical organism
and bypassed its physiology, BodySchemaEngine, canonical actuation and Private
SLM. It is retired from Physics3D.

Frozen historical studies that intentionally use the older
`Symbiont + Body + Individual` research surface remain reproducible; they are
not silently rewritten.

## Physical body

The current PyBullet apparatus is procedural and deliberately cheap to render.
It contains pelvis, torso, head, paired arm segments and paired leg segments,
with eight physical revolute joints.

Anatomical identity exists only in `physics3d/humanoid.py`.

The organism receives 31 opaque read-only physical signals:

- joint position/velocity measurements;
- base orientation;
- base linear and angular motion;
- bounded contact indicators.

They cross into the runtime as ordinary opaque local signal capabilities. No
anatomical label is exposed.

The apparatus offers sixteen physical motor ports. The Physics3D birth genome
therefore has sixteen opaque canonical motor slots. Motor-slot ordinal is bound
to physical-port ordinal by the apparatus. The runtime does not receive the
physical meaning of that binding.

The physical apparatus pairs those ports antagonistically at each joint. A
single canonical `Actuation` therefore becomes a positive or negative torque
on one physical joint, while all non-commanded torques are explicitly zeroed
on that tick.

## Motor learning

Physics3D uses the existing canonical actuation machinery:

- `ActuatorProposer`;
- `MotorIntentSelector`;
- `ActuatorSystem`;
- pending proprioceptive consequences;
- actuator health/reliability/cost;
- canonical metabolic charging.

The initial Physics3D organism uses `motor_exploration_mode="spontaneous"`.
This avoids an experimenter-authored body-specific movement plan. Occasional
endogenous twitches provide sparse causal motor evidence; learned cognition may
later drive the active motor repertoire.

No `walk()`, `balance()`, limb names or desired posture enters cognition.

## BodySchema

The monitor now reports the canonical `BodySchemaEngine v2`, not the retired
`InferredBodySchema` from the first Physics3D prototype.

The evaluator displays:

- normalized existence confidence across learned body parts;
- sensory-part count;
- cognitive-region count;
- internal dependency-evidence count;
- exported dependency count.

Cognitive regions use direct cohesion rather than transitive connected
components. A-B and B-C therefore no longer imply one A-B-C region when A-C has
insufficient evidence. Existing low-cohesion mega-regions are revised
deterministically during continued observation, allowing multiple functional
regions and therefore learnable `co_acts_with` / `precedes` dependencies to
emerge.

The full schema remains the runtime's bounded organism-owned representation.
PyBullet anatomy is never copied into it.

## Private SLM

Physics3D uses `PrivateModelOrganismRuntime`, so private experience capture is
part of the same organism tick as perception, cognition and actuation.

Canonical opaque motor `Actuation` is captured as organism-owned experience
without anatomical semantics. Private learning episodes are now temporal:

```text
opaque state(t) + opaque action(t)
                 |
                 v
independently observed state change(t+1)
```

Raw percept values are used only transiently to classify bounded change; they
are never written to the ExperienceLedger or checkpoint. Motor delivery is
execution context, not the outcome target. A restart drops the single pending
transition rather than fabricating causality across a discontinuity.

Historical same-tick `life.*` records remain in the ledger until normal bounded
eviction for audit continuity, but Physics3D SLM training uses only new
`transition.*` records.

Training remains an external bounded authority, as in the rest of Symbiont:

```text
organism ExperienceLedger
        |
        | organism-owned TrainingRequest
        v
low-priority background worker
        |
        v
PrivateModelFactory
        |
        v
held-out evaluation
   |                 |
 fail              pass
   |                 |
 SHADOW           ACTIVE
```

On CPU, the worker runs at lowered OS priority and one Torch thread so training
does not compete aggressively with the 3D physics loop.

Defaults:

- minimum private records: 64;
- training cadence: 4096 ticks;
- architecture: GRU v1;
- context window: 96;
- requested parameters: 1,000,000;
- requested epochs: 2;
- requested steps: 12;
- device: CPU.

Disable for an ablation with:

```bash
symbiont-body-3d --no-slm
```

The monitor exposes total record count, temporal-transition count, model count,
ACTIVE/training state, training/attachment errors, the last held-out gate
reason, exact gain over the best trivial baseline, the winning baseline and
candidate/baseline losses.

## Portable Symbiont

The canonical organism is stored as one portable bundle:

```text
~/.local/state/symbiont/physics3d/
├── subject.symbiont             # portable organism + Private SLM artifacts
├── subject.body-v2.json         # canonical PyBullet embodiment only
├── subject.telemetry-v2.ndjson  # canonical passive evaluator telemetry
└── models/                      # local materialized cache of bundled SLM artifacts
```

`subject.symbiont` is a ZIP container with:

- the canonical `PrivateModelOrganismRuntime` checkpoint;
- private model manifests;
- private model weights;
- the tokenizer sidecars required to reconnect inference.

It does not contain the PyBullet pose or anatomy.

Consequently:

```bash
# Resume same organism and, when tick-compatible, same physical pose
symbiont-body-3d

# Same persisted organism, new physical body
symbiont-body-3d --fresh-body

# Explicitly create a different organism
symbiont-body-3d --new-symbiont
```

The bundle is written atomically every 256 cognitive ticks by default. SIGTERM and SIGHUP
are converted into graceful shutdowns so the final checkpoint is written before exit. Model
weights are stored without recompression to reduce checkpoint CPU cost.

### Legacy first Physics3D subject

The earlier prototype wrote `subject.symbiont.json` using the parallel
`Symbiont/Individual` stack. That file is deliberately not auto-migrated into
the canonical runtime, because doing so would fabricate a mapping between two
different cognitive state representations.

If present, it is preserved untouched as historical evidence. The canonical
Physics3D path starts a new `subject.symbiont` instead.

## Unified viewer

Interactive Physics3D now uses one application window.

PyBullet runs in `DIRECT` mode as the physical engine. The parent process
renders passive RGB camera frames with `getCameraImage()`; a separate Tkinter
viewer process displays those frames together with evaluator telemetry. The
native PyBullet ExampleBrowser is therefore not opened during normal use.

The single window contains:

- a large 3D scene on the left;
- a right-hand tabbed inspector with **Runtime**, **Body & Cognition** and
  **Private SLM**;
- mouse orbit on the 3D scene by left-drag;
- wheel zoom.

Camera state belongs exclusively to the evaluator. Yaw, pitch and zoom never
enter the organism, BodySchema, physical sensors or private-model experience.

The process boundary remains passive and bounded. The viewer receives only the
latest telemetry/frame through a small dropping queue; stale UI frames are
discarded instead of slowing the organism. The viewer can send only camera
parameters and a window-close request back to the parent process.

Closing the unified window requests graceful experiment shutdown at the next
canonical tick boundary, followed by the normal portable checkpoint.

The inspector displays:

- canonical tick and embodiment mode;
- BodySchema confidence, sensory parts, cognitive regions, dependency evidence
  and exported dependencies;
- predictor, live-shadow and promotable-shadow counts plus measured prediction
  error;
- active motor output, joint motion, contacts, body height and mechanical work;
- checkpoint age and realtime factor;
- Private SLM temporal records, models, ACTIVE/training state and exact held-out
  gate/baseline metrics;
- rolling prediction-error and BodySchema-confidence traces.

Disable the unified evaluator with:

```bash
symbiont-body-3d --no-monitor
```

That explicit diagnostic mode falls back to the native PyBullet GUI. Headless
mode remains fully `DIRECT`.

Prediction error is shown as `N/A` when no real predictor/error observation
exists; zero is reserved for a measured zero loss.

Physics3D explicitly enables canonical `auto_promote_predictors`. A
`ShadowPrediction` must first satisfy its own evidence gate before production
may materialize a predictor.

## Installation

Physics3D now includes both PyBullet and the Private SLM runtime dependency:

```bash
pip install -e '.[physics3d]'
```

Interactive:

```bash
symbiont-body-3d
```

Headless long run:

```bash
symbiont-body-3d --headless --ticks 100000
```

### Clock separation

PyBullet integrates mechanics at 240 Hz by default while the canonical organism
runs at 12 Hz by default. One organism actuation is held across 20 physical
substeps before the next perception/decision tick. This keeps the physical
solver stable while allowing the full canonical runtime to execute in real time
on modest hardware.

The cadence is explicit and reproducible:

```bash
symbiont-body-3d --hz 240 --cognition-hz 12
```

The monitor reports cognitive-cycle milliseconds and the resulting realtime
factor. `Realtime 1.00x` means the machine is keeping up with the configured
clock.

Private SLM dataset encoding preserves the complete causal suffix
(action/epistemic/source/outcomes) when an episode exceeds its context window.
Only context tokens are trimmed, so a high-dimensional body cannot silently
truncate away every training target.

## Experimental boundary

Physics3D currently provides real mechanics but not yet a complete ecological
energy loop.

What is real now:

- gravity;
- rigid-body collision;
- joint dynamics;
- friction;
- physical contact;
- canonical motor actuation;
- measured mechanical joint work integrated as
  `|torque × angular_velocity| × dt`;
- bounded scalar transduction of that measured work into canonical maintenance
  metabolism on the following organism tick;
- canonical runtime physiology/homeostasis/metabolism;
- organism-owned BodySchema development;
- private experience and SLM state.

What remains deliberately incomplete:

- there is no food/resource ecology in the empty room;
- feet/hands and joint limits remain simplified;
- Physics3D telemetry is not yet published to Observatory.

Those gaps must remain explicit rather than being hidden behind arbitrary
rewards or hand-authored locomotion goals.

## Next scientific work

1. Continue the existing subject long enough for the corrected BodySchema to
   revise the inherited mega-region; measure region count, dependency evidence
   and exported dependencies longitudinally.
2. Accumulate at least 64 new `transition.*` experiences and inspect the first
   held-out SLM gate on the temporal objective. Do not lower the gate.
3. Investigate why the cognitive graph still has zero predictor nodes in the
   long-running embodied subject; keep prediction error as N/A until a genuine
   predictor exists.
4. Run ablations for BodySchema region formation: independent groups, bridge
   channel, dense clique and alternating regions.
5. Run SLM controls: action shuffled, next-state shuffled and no-action temporal
   baseline to demonstrate that any promoted model uses genuine temporal
   information.
6. Characterize the measured-work distribution and preregister whether the
   default `0.001 metabolic units / joule` transduction should remain fixed;
   do not tune it to improve behaviour.
7. Add realistic joint limits, feet and hands without adding behavioural goals.
8. Perform transplant experiments with `--fresh-body` only after the corrected
   first-body schema has reached a measurable multi-region regime.
9. Publish passive Physics3D state to Observatory.


## Migration boundary

The first visual Physics3D prototype used these files:

```text
subject.symbiont.json
subject.body.json
subject.telemetry.ndjson
```

The canonical-runtime implementation does not overwrite them. It uses
`subject.symbiont`, `subject.body-v2.json` and
`subject.telemetry-v2.ndjson`. This preserves the complete earlier run as
historical evidence and prevents telemetry from two different runtime
architectures being mixed in one time series.


## Mechanical work accounting

Physics3D distinguishes two motor costs:

1. the canonical actuator execution cost already charged by `ActuatorSystem`;
2. apparatus-measured external mechanical work.

For every PyBullet substep the apparatus integrates:

```text
work += abs(applied_joint_torque * observed_joint_angular_velocity) * dt
```

The apparatus reports only the resulting scalar work magnitude. It does not
report joint/anatomical identity into metabolism or cognition.

The default transduction is explicit and reproducible:

```text
0.001 metabolic maintenance units / measured joule
```

with a hard per-cognitive-tick cap of `0.05` metabolic units before entering
the organism. The canonical runtime itself additionally bounds queued embodied
work to `0.25`.

The cost is queued after physical integration and consumed by the next
canonical metabolism/physiology tick after ordinary replenishment. Pending work
is checkpointed so a restart cannot erase a physically incurred cost.

The scale is an apparatus calibration parameter, not a reward. It can be
changed explicitly for preregistered calibration/ablation runs:

```bash
symbiont-body-3d --work-cost-per-joule 0.001
```

The Runtime evaluator displays both raw measured joules and the resulting
bounded metabolic cost.


## Self-collision

The anthropomorphic apparatus explicitly configures self-collision for every
pair of rigid body segments. Only directly connected parent/child neighbours
are excluded because their procedural boxes intentionally overlap around the
joint pivot.

For the current 11 rigid elements (pelvis/base plus 10 links), all 55 unordered
pairs are configured explicitly:

- 10 directly joined pairs: collision disabled;
- 45 non-adjacent pairs: collision enabled.

This prevents limbs from passing through the torso, pelvis, opposite limbs or
other non-adjacent body segments. Collision identity remains apparatus-side:
cognition receives only the existing opaque bounded contact signals.

A physical checkpoint created before self-collision existed may contain a pose
with interpenetrating links. On the first resumed simulation step PyBullet is
allowed to resolve that penetration physically. The resulting transient is part
of the apparatus migration and is not hidden by scripted pose correction.


## Native GUI shutdown semantics

Closing the native PyBullet window is treated as a normal end of the current
embodiment session, not as a runtime failure.

Shutdown ordering is intentionally asymmetric:

1. persist the portable canonical Symbiont bundle first;
2. persist the newest completed physical pose second;
3. stop evaluator windows and any background SLM worker;
4. disconnect PyBullet only if its server is still connected.

The organism is authoritative. Loss of the graphics/physics server must never
prevent persistence of cognitive state.

The runtime caches the newest completed physical pose together with the organism
tick at which it was observed. If PyBullet disappears after a completed tick,
that cached pose can still be persisted. If disconnection occurs in the middle
of an organism/physics cycle, the cognitive checkpoint may be newer than the
last completed body pose. Their distinct tick markers intentionally expose that
mismatch; on the next start the stale body pose is ignored rather than being
silently paired with a newer mind.

Background Private SLM training is also terminated on application shutdown.
A worker interrupted before adoption cannot alter the organism model registry.


## Predictive hypothesis selection

The cognitive bridge no longer instantiates the full ordered Cartesian product
of node pairs as ShadowPrediction objects.

A new predictive hypothesis must first accumulate bounded lag-1 preliminary
evidence. Only SENSE sources are eligible for automatic shadow creation because
that is the source class whose lag semantics can currently be materialized
without ambiguity. Once a shadow exists, it is evaluated on every compatible
tick, including negative/boring evidence; preliminary selection never censors
the held hypothesis evaluation.

Retired shadows are removed from the live set. Both the live shadow set and the
preliminary staging map are bounded as functions of the kernel node budget.
Restoring an older checkpoint automatically discards retired shadows and shadows
whose source cannot be materialized under the current contract.

## BodySchema region consolidation

Cognitive regions use dense partial cohesion rather than either connected
components or strict cliques.

For regions with three or more members:

- at least 60% of all possible member pairs must have direct support;
- every member must have strong direct support to at least 60% of the other
  members.

This rejects bridge-only A-B-C chains while permitting dense functional groups
with occasional missing pairwise evidence.

Regions are no longer irreversible after birth. Early singleton/small regions
may merge later when accumulated evidence makes their union cohesive, while
incohesive regions may still split. Dependency evidence touching a region whose
identity changes is discarded rather than remapped, so topology revision cannot
fabricate relational history.

## New-subject preservation and identity

`--new-symbiont` preserves the preceding run automatically before creating a
new organism. Existing portable bundle, body state and telemetry are moved into
the next `archive/run-NNNN/` directory.

The bundled Private SLM artifacts already live inside `subject.symbiont`, so the
historical organism remains portable even though the materialized local model
cache is shared.

Every genuinely new Physics3D organism receives a distinct generated
`organism_id`. Resume always restores the checkpointed identity.

## Interrupt safety

SIGINT (`Ctrl+C`), SIGTERM and SIGHUP are deferred to the next completed
canonical tick boundary. They never intentionally interrupt `OrganismRuntime.tick()`.

The monitor and background SLM worker ignore terminal SIGINT; only the parent
Physics3D process owns shutdown. This prevents partial states such as signal
knowledge advancing to tick N+1 while the public runtime counter still reports
tick N.
