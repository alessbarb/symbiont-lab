# Experimental Decontamination P0

Status: implemented candidate

## Question

Can the canonical Symbiont World legitimately claim that organism-level meaning,
strategy and affordance are discovered rather than supplied by the experimenter?

Before this change the answer was **no**. The canonical World path still exposed
one-to-one resource/hazard signals, enabled typed local actions with owner-authored
expected outcomes, used a semantic bootstrap flag, supplied free metabolic
replenishment, and started the persistent World with physical actuation disabled.

P0 changes the canonical persistent World so those routes are removed from the
subject boundary.

## Experimental claim

P0 does **not** claim that a Symbiont is created without priors. That is impossible:
an organism requires a constitution.

The permitted claim is narrower and testable:

> The experimenter supplies morphology, physical transduction, metabolism,
> homeostasis, plasticity, bounded exploration machinery and World physics.
> The experimenter does not supply organism-facing semantic categories,
> named goals, action utility priors, resource/hazard identities or meanings.

## Allowed innate constitution

The following are explicitly inherited rather than discovered:

- finite sensory receptor count;
- receptor transfer functions;
- finite opaque motor channels;
- actuator execution cost/health/thresholds;
- metabolic capacities and physical accounting;
- homeostatic/viability dynamics;
- learning/plasticity rules and bounds;
- motor probing calendar and causal evidence thresholds;
- hard computational/resource limits;
- World topology and physical laws.

These are analogous to body plan and nervous-system learning machinery. Their
parameters remain part of the constitution/fingerprint and must never be reported
as learned discoveries.

## Forbidden subject priors

The canonical clean World must not expose or activate:

- semantic percept aliases;
- one signal per resource identity;
- one signal per hazard identity or hazard probability;
- local occupancy density as an organism-facing concept;
- one-to-one substrate labels such as surface-water/detritus/disturbance;
- typed autonomous actions such as REST, INTAKE, REPAIR or REPRODUCE;
- owner-authored ExpectedOutcome utility priors;
- the behavior selector's safety_value policy;
- founder behavioral loci such as behavior_exploration;
- automatic metabolic replenishment from nowhere;
- evaluator-side fertility, ecological pressure or effective permeability.

## Mixed physical receptor bank

The clean sensory body exposes eight stable opaque receptor IDs.

World apparatus state may contain fields, materials, substrate variables and
reception. The subject never receives those dimensions one-to-one.

Instead each receptor applies a deterministic signed mixture:

```text
physical apparatus variables
        ↓
normalize to bounded physical magnitudes
        ↓
fixed receptor-specific signed transfer weights
        ↓
nonlinear bounded activation
        ↓
opaque receptor IDs
```

Resource quantities therefore influence perception as local material presence but
resource identities do not cross the boundary.

Hazard exposure/probability is not included at all. A hazard must be learned from
experienced physiological consequences and correlations with ordinary physical
receptors.

Occupancy density is also excluded. Other organisms must become discoverable
through actual physical consequences such as collision, emitted signals or other
future non-semantic physical channels.

## Motor body

Clean founders receive at least eight opaque motor slots:

- six apparatus-bound directional impulse channels;
- one apparatus-bound local physical interaction channel;
- at least one intentionally unbound channel used as a natural causal negative
  control.

The organism is not told which is which.

The local interaction channel acts on all physically present resource material
proportionally. The apparatus does not select the most useful resource for the
organism.

No motor outcome event is fed to cognition. Consequences are available only
through later perception and physiology.

## No typed local behavior in canonical World

The legacy core still contains ActionKind/ExpectedOutcome behavior for historical
studies and other research modes.

Canonical clean World constructs its subject runtime with:

```text
bootstrap_semantic_senses = false
autonomous_behavior = false
interoception_mode = absent
```

and its World-side action record is only an apparatus description of whether an
opaque motor actuation occurred.

Thus the typed local action frontier is not part of the canonical subject's causal
decision path.

## Metabolism

Clean founders receive zero automatic replenishment in every metabolic reserve.

Physical local interaction may transfer material into organism metabolism. The
physiology distributes absorbed material across internal reserve dimensions; this
is constitution-level metabolism, not organism-facing meaning.

This means survival pressure is no longer satisfied automatically by a fixed
per-tick grant.

## Canonical World activation

A fresh `WorldRuntimeState` now starts with:

- experimental clean mode enabled;
- physical movement/actuation enabled;
- sensory plasticity enabled;
- sense discovery enabled.

The previous persistent-World default had movement disabled and therefore could
not exercise physical affordance discovery.

## Persistence and constitution

Persistence schema v4 stores `experimental_clean`.

The World interaction constitution includes `decontamination-p0`, so a
constitution-verified checkpoint from the previous experimental physics cannot be
silently resumed under the clean boundary.

## Fail-closed guards

Canonical World checks the boundary at startup. It refuses to run if any clean
organism has:

- semantic bootstrap enabled;
- typed autonomous behavior enabled;
- privileged interoception enabled;
- founder behavioral loci;
- nonzero automatic metabolic replenishment;
- forbidden motor effects;
- direct resource/hazard/occupancy/substrate capability IDs.

Every clean observation is also checked for leaked apparatus IDs before it reaches
the reading provider.

## What remains intentionally innate

Homeostatic repair/regulation and viability transitions remain constitution-level
physiology. P0 does not claim the organism discovered wound healing, metabolism,
death or the learning rule itself.

Reproduction, social exchange and other high-level typed actions are disabled from
the canonical behavior path rather than claimed as emergent. They require future
physical, semantic-free mechanisms before they can return to the canonical
experiment.

## Scientific gate

After P0, a claim such as "the organism discovered a resource" still requires an
experiment. Evidence must show that a recurrent receptor pattern and an opaque
motor sequence become causally associated with later endogenous benefit, above
controls where:

1. material consequences are frozen;
2. actuator→consequence mappings are shuffled;
3. receptor transfer is permuted or ablated;
4. motor probing is preserved while material transfer is disabled.

The correct P0 claim is therefore:

> The canonical World no longer supplies the subject with explicit resource,
> hazard or action semantics, and it fails closed if those channels reappear.

It is not yet evidence that a useful concept has emerged.
