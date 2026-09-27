# Physiology, homeostasis and cost

Symbiont does not treat computation as free. Perception, cognition, persistence, maintenance and embodied work participate in explicit resource accounting. This matters because resource pressure can change what the organism is able or willing to do.

## Two related but different things

The living body contains physical state such as energy reserve, integrity and vital status. `MetabolicLedger` accounts for resource charges and pressure. `HomeostaticController` tracks regulation-relevant state, while `PhysiologyController` determines body-level physiological consequences and terminal state.

These mechanisms are coupled but should not be collapsed. An accounting ledger is not the body; a homeostatic variable is not automatically an organism objective; and a laboratory metric is not a physiological signal unless it legitimately enters through the organism's surfaces.

## The tick begins with physiology

`OrganismRuntime.tick()` performs a physiological preflight before perception. This stage can excrete degradation, determine whether plasticity is currently enabled and prepare interoceptive state. The consequence is important: learning capability in a tick can depend on current physiological condition before new cognition occurs.

At the end of the main cognitive/action sequence, `PhysiologyDomain.advance()` accounts for retained memory, embodied work, rest state and degradation. It returns metabolism, homeostasis, physiology, ontogeny and development snapshots. The body age is advanced only after the tick has completed.

## Rest

`request_rest()` sets a bounded state request. Rest is not a free refill. In the current runtime it also changes generative cognition from online to offline mode. This makes rest a different operating regime, not a shortcut that manufactures resources.

## Damage, repair and death

Environmental damage changes local integrity directly and is deliberately not represented as an evaluator command. Repair, if available, must pay its maintenance cost. Once physiology reaches `VitalState.DEAD`, subsequent runtime ticks are rejected as irreversible death.

## Why physiology matters to cognition

Physiology does not need to encode a hand-designed goal such as “stay alive” in order to constrain cognition. Finite resource budgets, plasticity gates, action costs and degradation already change the feasible space of behaviour. The scientifically interesting question is then how those constraints shape acquired policies and internal structure over time.

### Principal sources

- `docs/design/embodiment/living-body-p0.md`
- `docs/explanation/04-digital-physiology.md`
- `src/symbiont/core/embodiment/metabolism.py`
- `src/symbiont/core/embodiment/homeostasis.py`
- `src/symbiont/core/embodiment/physiology.py`
- `src/symbiont/core/domains/physiology.py`
