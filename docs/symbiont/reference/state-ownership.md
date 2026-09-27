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
