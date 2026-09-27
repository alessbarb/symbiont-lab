# Foundations and epistemology

## What kind of thing is Symbiont?

Symbiont is a persistent computational subject whose internal state can be altered by its history of interaction. It is not defined by a single body, process, window or simulation run. The implementation contains cognition, sensory adaptation, physiology, action, memory, social exchange, heredity and generative processes, but none of those labels should be treated as proof of biological equivalence. They are engineering and scientific terms for functional mechanisms that can be inspected.

The safest way to study Symbiont is to distinguish three levels of statement.

**Implementation statements** describe what the code does. For example, `OrganismRuntime.tick()` invokes a perception domain before the cognition domain and closes the previous action's observed consequences before new cognition is advanced.

**Experimental statements** describe what happened under specified conditions. A locomotion study, for example, may show that a particular organism acquired recurrent motor competences under a specified body, seed and run length. That observation does not establish a universal property of all Symbionts.

**Interpretive statements** explain why a mechanism is interesting or what functional role it appears to play. These are useful, but they must not be presented as direct observations.

## The organism does not inherit the observer's vocabulary

One of the most important epistemic boundaries in the project is the separation between external semantics and organism-owned representation. A researcher may know that a physical channel corresponds to a right knee, a CPU metric or an energy reserve. That does not mean the organism receives the same name or concept.

The sensory system explicitly supports opaque, organism-owned identities. In adaptive mode `SensorySystem.ensure_identity_sensor()` uses a stable sensor identity rather than preserving an external cognitive alias. The general rule is therefore:

```text
physical meaning
    != measurement label
    != organism-owned signal identity
    != learned internal meaning
    != UI label
```

Any claim that Symbiont “knows” a semantic category must be justified by internal evidence, not by the convenience of a developer-facing label.

## Organism and laboratory

`symbiont` and `symbiont_lab` serve different epistemic roles. The organism owns its bounded internal state and mechanisms. The laboratory may hold information the organism cannot access: ground truth, evaluation metrics, experiment configuration, external traces and presentation state. The laboratory may observe and evaluate; it must not silently teach the subject through evaluator-only information.

This separation is reinforced by architecture decisions such as the two-package boundary and ground-truth isolation, and by outward-only mechanisms such as causal provenance subscribers.

## What this documentation does not claim

This documentation does not assert consciousness, subjective experience or equivalence to biological cognition. It uses terms such as perception, memory, agency and physiology in operational senses defined by the mechanisms described in later chapters.

The scientific question is not whether the metaphors sound biological. It is whether the mechanisms are well defined, causally traceable, experimentally characterisable and capable of producing persistent changes in behaviour and internal organisation.

### Principal sources

- `docs/architecture.md`
- `docs/adr/ADR-0001-two-package-boundary.md`
- `docs/adr/ADR-0002-ground-truth-isolation.md`
- `docs/explanation/concepts/01-what-is-a-symbiont.md`
- `src/symbiont/core/orchestration/runtime.py::OrganismRuntime`
- `src/symbiont/sensory/system.py::SensorySystem`
