# State ownership

Ownership determines what a state means and whether it may survive a boundary change.

| State family | Owner | Typical lifetime | Re-embodiment expectation |
| --- | --- | --- | --- |
| Organism identity / genome | Symbiont | organism/lineage | preserved |
| Cognitive graph and learned evidence | Symbiont | organism | preserved unless compatibility rule says otherwise |
| Sensory phenotype | Symbiont | organism, contract-sensitive | preserved historically; may require reacclimation/adaptation |
| Motor competences | Symbiont | organism, actuator-contract-sensitive | preserve with contract compatibility; otherwise historical/unbound |
| Body schema | Symbiont | embodiment-informed | retain history; current validity depends on new contract |
| Metabolic ledger | Symbiont/body coupling | active organism/body | restore only under explicit physiology semantics |
| Living body pose / contacts | Body | physical body | not preserved into a fresh body |
| Body integrity and body age | Body | physical body | fresh body has fresh physical state |
| Embodiment episode | Embodiment | one body relationship | closes; new episode created |
| Reacclimation state | Embodiment | transition period | reset for new episode |
| World resources / terrain | World | world | independent of organism checkpoint |
| Evaluator metrics | Lab | experiment/run | never organism state |
| Observatory layout/presentation | Lab/UI | observer session | never organism state |
| Durable causal journal | Lab | experiment/archive | preserved externally; outward-only |
| Provenance frontier | Symbiont | live causal state | checkpointed |

This table expresses intended current ownership, not a licence to infer semantics. Individual serializers and migration rules remain authoritative for exact persistence behaviour.


## Re-embodiment preservation invariant

Re-embodiment is a change of Body and Embodiment, not a rewrite of the Symbiont.

The following rule is normative:

> Re-embodiment must never erase, degrade, reset or reinterpret learned Symbiont state merely because the Body changes.

This applies to every Body transition, including same-contract, known-contract and novel-contract replacement. Cognitive topology, learned evidence, self-model, sensory learning, learned BodySchema, private models, acquired action dimensions, effects, causal evidence, competences and composition remain part of the same Symbiont.

A fresh Body may invalidate **current execution authority** only. Physical physiology, pose, actuator health, current execution bindings, in-flight commitments and other Body/Embodiment-owned transient state may be fresh. If prior knowledge does not apply to the new Body, it remains knowledge without current authority until ordinary experience revises, extends or supersedes it.
