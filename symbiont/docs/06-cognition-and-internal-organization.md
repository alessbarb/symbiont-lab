# Cognition and internal organisation

The cognitive system is not a single policy function. It is a collection of bounded structures that transform perceptual evidence, maintain relationships over time, generate predictions, revise beliefs, allocate attention, create or retire structure and expose some of that state to action and memory.

## Cognitive graph

`CognitiveGraph` is one of the principal organism-owned substrates. Its nodes and edges can change through learning and structural plasticity. Recurrent activation is strictly causal across time: cycles do not imply instantaneous algebraic self-support within the same update.

## Cognitive bridge

The runtime uses `CognitiveBridge` as a major integration point between sensory evidence, graph activation, self-model, prediction and downstream action. The bridge is intentionally not equivalent to the whole organism. It is a mechanism inside the wider orchestration.

## Evidence and revision

`EvidenceRevisionLedger`, beliefs and predictor mechanisms allow current observations to revise previous internal estimates. The project distinguishes evidence identity, source provenance and disagreement rather than reducing all learning to a single scalar reward.

## Self-model and metacognition

The self-model accumulates information about the organism's own sensing and cognition, including reliability, cost and confidence-like quantities. These are internal estimates, not privileged access to laboratory truth. Metacognition therefore operates on the organism's own evidence about its processes.

## Structural plasticity

Cognition can create and retire structure under bounded rules. Structural candidates, planners and lifecycle logic separate a transient correlation from a stable piece of cognitive organisation. Reversibility is important: the system should be able to weaken or remove structures that no longer earn their cost, rather than only accumulating nodes indefinitely.

## What cognition is not

Cognition is not synonymous with action. A cognitive state may never become an action. It is also not synonymous with generative cognition; offline or counterfactual processes are a specialised part of the system described separately.

### Principal implementation anchors

- `src/symbiont/cognition/graph.py`
- `src/symbiont/cognition/learning.py`
- `src/symbiont/core/cognition/bridge.py`
- `src/symbiont/core/cognition/evidence.py`
- `src/symbiont/core/cognition/self_model.py`
- `src/symbiont/core/cognition/metacognition.py`
- `src/symbiont/core/cognition/structural_*`
