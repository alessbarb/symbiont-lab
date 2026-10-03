# Domain map

This reference maps the principal scientific domains to their current implementation anchors. It is intentionally implementation-facing; explanatory chapters should be preferred for first reading.

| Domain | Primary implementation | Role |
| --- | --- | --- |
| Runtime orchestration | `src/symbiont/core/orchestration/runtime.py` | Orders one organism tick and composes domains |
| Lifecycle | `src/symbiont/core/domains/lifecycle.py` | Death/release/events/journal boundaries |
| Physiology | `src/symbiont/core/domains/physiology.py`, `core/embodiment/physiology.py` | Body state, vital state, cost and ageing |
| Perception | `src/symbiont/core/domains/perception.py` | Sampling, transduction, attention, drift, signal knowledge |
| Sensory phenotype | `src/symbiont/sensory/*` | Organism-owned sensors, modalities and plasticity |
| Cognition | `src/symbiont/core/domains/cognition.py`, `core/cognition/*`, `cognition/*` | Cognitive state, evidence, graph activation and plasticity |
| Memory | `src/symbiont/core/domains/memory.py`, `modeling/episodic.py` | Retention, consolidation and episodic organisation |
| Agency | `src/symbiont/agency/*` | Affordances, intentions, prospective and outcome policy |
| Actuation | `src/symbiont/actuation/*` | Competence acquisition, control and actuator delivery |
| Embodiment | `src/symbiont/core/domains/embodiment.py`, `core/embodiment/*` | Body contract, schema, episode and reacclimation |
| Development | `src/symbiont/core/domains/development.py` | Expression and developmental state |
| Genetics | `src/symbiont/genetics/*`, `core/lineage/*` | Genome, germline, inheritance and lineage |
| Social | `src/symbiont/core/social/*` | Communication, evidence, relations and exchange |
| Generative cognition | `src/symbiont/cognition/generative/*` | Internal hypotheses, replay, rollout and consolidation |
| Provenance | `src/symbiont/provenance.py` | Bounded causal events/frontier |
| World | `src/symbiont/environment/*`, lab world modules | External dynamics and regimes |
| Physics3D | `src/symbiont_lab/physics3d/*` | Physical bodies and simulation |
| Observatory | `src/symbiont_lab/observation/*` | Passive researcher-facing projection |
| Experiments | `src/symbiont_lab/experiments/*` | Reproducible experiment definitions and runners |
