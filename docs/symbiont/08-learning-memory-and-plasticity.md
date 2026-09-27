# Learning, memory and plasticity

The word “learning” hides several different mechanisms in Symbiont. They should be studied separately because they change different kinds of state and persist for different lengths of time.

## Parametric learning

Weights, confidence values, baselines and predictive statistics can change while the surrounding structure remains fixed. This is the lightest form of adaptation and often the first stage through which evidence changes future processing.

## Structural learning

The cognitive and sensory systems can change topology. Sensors can be duplicated or rewired; cognitive structures can be proposed, matured, weakened and retired. Structural plasticity therefore changes what computations the organism is capable of expressing, not only the numbers inside a fixed computation.

## Sensorimotor learning

Action outcomes accumulate into causal evidence, agency models and motor competences. A competence is valuable only if its effects are sufficiently repeatable and controllable to justify reuse. Outcome learning then changes which competences are more or less admissible in future executive decisions.

## Predictive learning

Predictors and shadow predictions model expected future observations without being allowed to overwrite factual evidence. Prediction error can alter confidence, evidence and model selection. The distinction between shadow prediction and observed outcome is essential to avoid self-confirming cognition.

## Memory

`MemoryDomain.observe()` is invoked after cognition and before new action. Memory consolidation therefore sees the current perception and cognitive result while remaining causally upstream of the next physical action. Episodic memory, consolidation and replay are separate mechanisms: storing an episode is not the same thing as replaying it, and replay is not the same thing as changing a model.

## Persistence is not inheritance

Acquired state that survives a checkpoint is not automatically germline state. Likewise, a state that survives re-embodiment is not necessarily transmitted to offspring. Genome, germline, epigenetic priors, organism memory and cultural transmission use different persistence channels.

## How to judge whether learning is real

A changing value is not enough. A useful study should show that experience changes a later prediction, action, representation or efficiency in a way that survives appropriate controls. The project therefore uses baselines, ablations, held-out evaluation and longitudinal checkpoints for stronger claims.

### Principal implementation anchors

- `src/symbiont/core/cognition/consolidation.py`
- `src/symbiont/modeling/episodic.py`
- `src/symbiont/cognition/learning.py`
- `src/symbiont/core/cognition/structural_*`
- `src/symbiont/sensory/plasticity.py`
- `src/symbiont/actuation/sensorimotor.py`
- `src/symbiont/agency/executive_outcome.py`
