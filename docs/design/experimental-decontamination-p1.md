# Experimental Decontamination P1 — Autonomy Boundary

Status: implemented; organism boundary extended by `experimental-decontamination-p2.md`

## Question

After P0 removed explicit semantic categories and typed action priors, does canonical
World still teach the subject how to explore its own body or provide a dedicated
feeding action that should instead be discovered from physical consequences?

Before P1, the answer was still partly yes.

The clean subject no longer received resource names, hazard names, reward signals
or typed actions, but the runtime itself scheduled structured ON/OFF motor probes,
rotated candidate actuators, maintained probing windows and promoted motor channels
from that experimenter-authored protocol. The seventh motor slot was also bound to
a dedicated local acquisition action.

P1 removes both shortcuts from the canonical clean World.

## Experimental claim

The canonical clean World may now claim:

> The experimenter supplies body morphology, spontaneous bodily variability,
> physical transduction, metabolism, homeostasis, plasticity and World physics.
> The experimenter does not supply a motor exploration protocol, a feeding action,
> semantic action utility, resource identity or hazard identity.

This is still not a claim that the organism has no priors. A finite body and
learning machinery remain constitutional.

## Spontaneous motor activity

Canonical clean World sets:

```text
motor_exploration_mode = spontaneous
```

The historical `structured_probe` mode remains available for controlled studies,
but the clean boundary fails closed if it is enabled.

Spontaneous mode has no:

- candidate rotation;
- paired ON/OFF schedule;
- probing windows;
- probe cursor;
- experimenter-authored exploration goal.

Instead the body has occasional deterministic-but-private constitutive motor noise.
The noise selects an opaque actuator and a continuously varying activation. This is
treated as basal bodily variability, analogous to spontaneous motor activity, not
as a designed experiment.

## Passive motor-effect learning

The existing actuator evidence model may observe the later perceptual consequence
of motor activity. In spontaneous mode, an actuator can become established from
natural covariance only after sufficient samples and effect strength.

The evidence evaluator does not schedule the action that generated the evidence.

Thus:

```text
spontaneous bodily variation
        ↓
world consequence
        ↓
later perception
        ↓
bounded covariance evidence
        ↓
possible motor competence
```

The learned fact is only that an opaque channel has a reproducible consequence.
Desirability and purpose are not supplied.

## No dedicated feeding actuator

The canonical clean motor body contains:

- six opaque channels physically bound to directional force;
- one opaque channel physically bound to a local substrate interaction;
- at least one unbound channel as a natural negative control.

The local interaction channel no longer means `acquire`, `intake` or `feed`.
It only perturbs local substrate physics.

Material exchange is resolved separately as a body/environment consequence:
delivered motor work while material is physically present may produce a bounded
exchange with that material. This can happen after any delivered motor actuation,
not through one privileged feeding organ.

The organism receives no resource identity and no action-result reward. It can only
observe later mixed receptor and somatic consequences.

## Fail-closed boundary

Canonical clean World refuses to run if:

- structured motor probing is enabled;
- a clean body contains an `acquire` binding;
- typed autonomous behavior is enabled;
- semantic bootstrap or privileged interoception is enabled;
- direct resource/hazard/substrate identities cross perception;
- automatic metabolic replenishment is non-zero.

## Remaining innate endowments

The following remain constitutional rather than discovered:

- receptor count and transfer physics;
- actuator count and physical execution costs;
- directional geometry of the embodied world;
- spontaneous motor variability;
- metabolism and homeostatic viability;
- learning/plasticity algorithms and thresholds;
- computational bounds.

These must never be reported as emergent discoveries.

## Scientific limitation

P1 reduces experimenter guidance, but passive covariance is not proof of causal
understanding. Environmental drift can still create false correlations.

Claims of learned affordance must therefore use evaluator-side controls such as:

1. remapping actuator-to-world bindings;
2. freezing the relevant physical consequence;
3. replaying identical environmental trajectories without motor coupling;
4. comparing spontaneous activity against matched sham actuators.

Those controls belong to the laboratory and must never feed back into the subject.

## Canonical interpretation

The intended starting point is now approximately:

> I have changing internal and external signals, I can produce occasional bodily
> changes, some regularities persist, and my internal state can change.

Not:

> I should experiment, this channel moves me, that channel feeds me, and this
> outcome is good.

That distinction is the P1 autonomy boundary.
