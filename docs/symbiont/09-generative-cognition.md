# Generative cognition

Generative cognition is the part of Symbiont that can manipulate internal alternatives without confusing them with observations of the world. That separation is the key scientific property of the subsystem.

## Why a separate generative layer exists

A system that can only react to its latest observation cannot compare imagined possibilities, revisit an episode or test a counterfactual without physically executing it. Generative cognition introduces bounded internal workspaces in which hypotheses, branches and rollouts can be created, compared and reconciled.

The implementation is extensive: agendas, branches, counterfactuals, epistemic value, hypothesis registries, replay, rollouts, scheduling, reconciliation and consolidation live under `src/symbiont/cognition/generative/`.

## Reality authority

Generated content is not factual evidence merely because the organism generated it. This is a hard boundary in the design. Real sensory outcomes can update or reconcile generated hypotheses; internally generated outcomes cannot promote themselves to world truth without an evidence path.

The action loop demonstrates this explicitly. When the body produces an observed competence effect, `note_factual_outcome()` is called with an evidence reference derived from the causal sensorimotor transition.

## Online and offline modes

The runtime selects `GenerativeMode.ONLINE` during normal activity and `GenerativeMode.OFFLINE` when rest has been requested. Offline mode therefore provides a place for internal processing to continue under a different relationship to immediate action.

## Replay and stopping

Replay is not an unlimited background loop. Dedicated mechanisms account for demand, epistemic value and stopping. The point is not to maximise internal simulation, but to spend bounded cognitive resources where additional internal work can still change something meaningful.

## Consolidation

Generated material becomes scientifically interesting when it can alter persistent cognitive organisation without bypassing the evidence rules. Consolidation therefore has to distinguish hypothesis utility from factual confirmation and preserve the provenance of any resulting structure.

### Principal sources

- `docs/design/cognition/generative-cognition-v1.md`
- `docs/design/cognition/generative-cognition-v1_implementation-gap-audit-against-main.md`
- `docs/design/cognition/autonomous-experience-replay-v1.md`
- `docs/design/cognition/autonomous-replay-stopping-v1.md`
- `src/symbiont/cognition/generative/*`
