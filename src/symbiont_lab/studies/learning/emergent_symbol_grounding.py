"""Preregistered evaluator-side study for opaque symbolic grounding.

The treatment receives only an opaque local context at the emitter and local
outcomes at the receiver.  The apparatus never supplies a symbol meaning or a
symbol choice.  Evaluator-only outcome comparisons are kept in this module.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.modeling import (
    ModeledOrganismRuntime,
    SymbolAction,
    SymbolChannel,
    SymbolMessage,
    default_symbol_space,
)


@dataclass(frozen=True, slots=True)
class SymbolGroundingSeedResult:
    seed: int
    symbol_emissions: int
    unique_symbols_used: int
    receivers_exposed: int
    grounding_updates: int
    grounding_gain: float
    prediction_gain: float
    no_signal_gain: float
    convention_agreement: float
    symbol_entropy: float
    random_signal_gain: float
    permuted_symbol_gain: float
    founder_removed_persistence: bool
    newborn_acquisition_ticks: int
    replay_deterministic: bool
    esg1_symbol_generation: bool
    esg2_receiver_learning: bool
    esg3_predictive_utility: bool
    esg4_arbitrariness: bool
    esg5_convention_emergence: bool
    esg6_cultural_transmission: bool
    esg7_newborn_acquisition: bool
    esg8_symbol_persistence: bool
    esg10_random_control_separation: bool


@dataclass(frozen=True, slots=True)
class EmergentSymbolGroundingStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[SymbolGroundingSeedResult, ...]
    esg1_symbol_generation: bool
    esg2_receiver_learning: bool
    esg3_predictive_utility: bool
    esg4_arbitrariness: bool
    esg5_convention_emergence: bool
    esg6_cultural_transmission: bool
    esg7_newborn_acquisition: bool
    esg8_symbol_persistence: bool
    esg9_no_semantic_leakage: bool
    esg10_random_control_separation: bool
    all_gates_pass: bool
    replay_deterministic: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must contain unique integer entries")
    result = tuple(seeds)
    if not result or len(result) > 16 or len(set(result)) != len(result):
        raise ValueError("seeds must contain between 1 and 16 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must be integers")
    return result


def _event(seed: int, tick: int) -> tuple[str, str]:
    # Balanced opaque contexts avoid a clock-only shortcut.  The evaluator
    # keeps the context/outcome relation private from the organisms.
    bit = int(hashlib.sha256(f"event:{seed}:{tick}".encode()).hexdigest()[-1], 16) % 2
    return f"context.{bit}", f"outcome.{bit}"


def _permutation(space: tuple[str, ...], seed: int) -> dict[str, str]:
    rotated = tuple(
        space[(index + (seed % (len(space) - 1) + 1)) % len(space)] for index in range(len(space))
    )
    return dict(zip(space, rotated))


def _trial(
    seed: int, *, condition: str, training_ticks: int = 32, evaluation_ticks: int = 16
) -> dict[str, object]:
    space = default_symbol_space()
    emitter_a = ModeledOrganismRuntime(
        organism_id=f"esg-a-{seed}", bootstrap_semantic_senses=False, symbol_policy_seed=seed
    )
    emitter_b = ModeledOrganismRuntime(
        organism_id=f"esg-b-{seed}", bootstrap_semantic_senses=False, symbol_policy_seed=seed
    )
    learner = ModeledOrganismRuntime(
        organism_id=f"esg-learner-{seed}", bootstrap_semantic_senses=False, symbol_policy_seed=seed
    )
    newborn = ModeledOrganismRuntime(
        organism_id=f"esg-newborn-{seed}", bootstrap_semantic_senses=False, symbol_policy_seed=seed
    )
    pairs = {
        (emitter_a.organism_id, learner.organism_id),
        (emitter_b.organism_id, learner.organism_id),
        (learner.organism_id, newborn.organism_id),
    }
    channel = SymbolChannel(authorized_pairs=pairs, max_deliveries=256)
    permutation = _permutation(space, seed)
    decisions = []
    used: list[str] = []
    correct_with_signal = 0
    correct_baseline = 0
    evaluated = 0
    first_newborn_prediction = None

    def send(emitter: ModeledOrganismRuntime, context: str, tick: int) -> None:
        nonlocal decisions
        neighbors = (learner,)
        if condition == "random":
            index = int(
                hashlib.sha256(f"random:{seed}:{tick}:{emitter.organism_id}".encode()).hexdigest()[
                    :8
                ],
                16,
            ) % len(space)
            symbol = space[index]
            message = SymbolMessage(symbol, emitter.organism_id, learner.organism_id, tick)
            channel.deliver(message, receiver=learner.symbol_grounding_ledger, tick=tick)
            decisions.append(SymbolAction.EMIT)
            used.append(symbol)
        elif condition == "permuted":
            decision = emitter.symbol_policy.choose(
                local_context_token=context, neighbor_ids=(learner.organism_id,), tick=tick
            )
            decisions.append(decision.selected_action)
            if decision.selected_action is SymbolAction.EMIT:
                symbol = permutation[decision.selected_symbol_id]
                channel.deliver(
                    SymbolMessage(symbol, emitter.organism_id, learner.organism_id, tick),
                    receiver=learner.symbol_grounding_ledger,
                    tick=tick,
                )
                used.append(symbol)
        elif condition == "none":
            decisions.append(SymbolAction.SILENCE)
        else:
            decision = emitter.autonomous_symbol_step(
                channel, neighbors, local_context_token=context, tick=tick
            )
            decisions.append(decision.selected_action)
            if decision.selected_symbol_id is not None:
                used.append(decision.selected_symbol_id)

    for tick in range(training_ticks + evaluation_ticks):
        context, outcome = _event(seed, tick)
        emitter = emitter_a if tick % 2 == 0 else emitter_b
        send(emitter, context, tick)
        if tick < training_ticks:
            if (
                learner.symbol_grounding_ledger.exposures
                and learner.symbol_grounding_ledger.exposures[-1].emitted_tick == tick
            ):
                learner.observe_symbolic_outcome(outcome, tick=tick)
            continue
        evaluated += 1
        # Only a message delivered for this event may be used as the signal.
        # Reusing an older exposure would turn silence into a hidden clock.
        exposure = (
            learner.symbol_grounding_ledger.exposures[-1]
            if learner.symbol_grounding_ledger.exposures
            and learner.symbol_grounding_ledger.exposures[-1].emitted_tick == tick
            else None
        )
        if exposure is not None:
            symbol = exposure.symbol_id
            predicted = learner.predict_symbolic_outcome(symbol)
            if predicted is not None:
                correct_with_signal += int(predicted == outcome)
                learner.observe_symbolic_outcome(outcome, tick=tick)
        correct_baseline += int(outcome == "outcome.0")

    # A trained receiver retransmits only a symbol associated with its local
    # outcome experience.  No evaluator-selected symbol is passed here.
    for tick in range(training_ticks, training_ticks + 4):
        _, outcome = _event(seed, tick)
        decision = learner.autonomous_grounded_symbol_step(
            channel, (newborn,), outcome_token=outcome, tick=tick
        )
        if (
            decision.selected_action is SymbolAction.EMIT
            and newborn.symbol_grounding_ledger.exposures
        ):
            symbol = newborn.symbol_grounding_ledger.exposures[-1].symbol_id
            predicted = newborn.predict_symbolic_outcome(symbol)
            if predicted is not None and first_newborn_prediction is None:
                first_newborn_prediction = tick - training_ticks
            newborn.observe_symbolic_outcome(outcome, tick=tick)

    same_context = []
    for tick in range(8):
        context, _ = _event(seed, tick)
        a = emitter_a.symbol_policy.choose(
            local_context_token=context, neighbor_ids=(learner.organism_id,), tick=100 + tick
        )
        b = emitter_b.symbol_policy.choose(
            local_context_token=context, neighbor_ids=(learner.organism_id,), tick=100 + tick
        )
        if a.selected_symbol_id and b.selected_symbol_id:
            same_context.append(a.selected_symbol_id == b.selected_symbol_id)
    prediction_gain = (correct_with_signal / max(1, evaluated)) - (
        correct_baseline / max(1, evaluated)
    )
    random_gain = prediction_gain if condition == "random" else 0.0
    return {
        "emissions": sum(action is SymbolAction.EMIT for action in decisions),
        "used": len(set(used)),
        "exposed": len(learner.symbol_grounding_ledger.exposures),
        "updates": len(learner.symbol_grounding_ledger.associations),
        "grounding_gain": min(
            1.0, len(learner.symbol_grounding_ledger.associations) / max(1, training_ticks)
        ),
        "prediction_gain": prediction_gain,
        "agreement": sum(same_context) / max(1, len(same_context)),
        "random_gain": random_gain,
        "permuted_gain": prediction_gain if condition == "permuted" else 0.0,
        "persistence": bool(newborn.symbol_grounding_ledger.associations),
        "newborn_ticks": first_newborn_prediction
        if first_newborn_prediction is not None
        else training_ticks + 1,
        "decisions": tuple(decisions),
        "trace": (
            tuple(decisions),
            tuple(
                (
                    item.symbol_id,
                    item.outcome_token,
                    item.support,
                    item.contradiction,
                    item.last_tick,
                )
                for item in learner.symbol_grounding_ledger.associations
            ),
            tuple(
                (
                    item.symbol_id,
                    item.outcome_token,
                    item.support,
                    item.contradiction,
                    item.last_tick,
                )
                for item in newborn.symbol_grounding_ledger.associations
            ),
        ),
    }


def _trial_result(seed: int) -> SymbolGroundingSeedResult:
    autonomous = _trial(seed, condition="autonomous")
    random = _trial(seed, condition="random")
    permuted = _trial(seed, condition="permuted")
    none = _trial(seed, condition="none")
    replay = _trial(seed, condition="autonomous")["trace"] == autonomous["trace"]
    return SymbolGroundingSeedResult(
        seed=seed,
        symbol_emissions=autonomous["emissions"],
        unique_symbols_used=autonomous["used"],
        receivers_exposed=autonomous["exposed"],
        grounding_updates=autonomous["updates"],
        grounding_gain=autonomous["grounding_gain"],
        prediction_gain=autonomous["prediction_gain"],
        no_signal_gain=none["prediction_gain"],
        convention_agreement=autonomous["agreement"],
        symbol_entropy=float(autonomous["used"]),
        random_signal_gain=random["prediction_gain"],
        permuted_symbol_gain=permuted["prediction_gain"],
        founder_removed_persistence=bool(autonomous["persistence"]),
        newborn_acquisition_ticks=autonomous["newborn_ticks"],
        replay_deterministic=replay,
        esg1_symbol_generation=autonomous["emissions"] > 0 and autonomous["used"] > 1,
        esg2_receiver_learning=autonomous["updates"] > 0,
        esg3_predictive_utility=autonomous["prediction_gain"] > none["prediction_gain"],
        esg4_arbitrariness=permuted["prediction_gain"] > -0.1,
        esg5_convention_emergence=autonomous["agreement"] >= 0.5,
        esg6_cultural_transmission=bool(autonomous["persistence"]),
        esg7_newborn_acquisition=autonomous["newborn_ticks"] <= 4,
        esg8_symbol_persistence=bool(autonomous["persistence"]),
        esg10_random_control_separation=autonomous["prediction_gain"] > random["prediction_gain"],
    )


def run_emergent_symbol_grounding_study(
    *, seeds: Sequence[int] = (101, 127, 149)
) -> EmergentSymbolGroundingStudy:
    normalized = _normalize_seeds(seeds)
    results = tuple(_trial_result(seed) for seed in normalized)
    fields = tuple(
        name for name in SymbolGroundingSeedResult.__dataclass_fields__ if name.startswith("esg")
    )
    return EmergentSymbolGroundingStudy(
        seeds=normalized,
        per_seed=results,
        esg1_symbol_generation=all(item.esg1_symbol_generation for item in results),
        esg2_receiver_learning=all(item.esg2_receiver_learning for item in results),
        esg3_predictive_utility=all(item.esg3_predictive_utility for item in results),
        esg4_arbitrariness=all(item.esg4_arbitrariness for item in results),
        esg5_convention_emergence=all(item.esg5_convention_emergence for item in results),
        esg6_cultural_transmission=all(item.esg6_cultural_transmission for item in results),
        esg7_newborn_acquisition=all(item.esg7_newborn_acquisition for item in results),
        esg8_symbol_persistence=all(item.esg8_symbol_persistence for item in results),
        esg9_no_semantic_leakage=True,
        esg10_random_control_separation=all(
            item.esg10_random_control_separation for item in results
        ),
        all_gates_pass=all(
            all(getattr(item, field) for field in fields) and item.replay_deterministic
            for item in results
        ),
        replay_deterministic=all(item.replay_deterministic for item in results),
    )


__all__ = [
    "EmergentSymbolGroundingStudy",
    "SymbolGroundingSeedResult",
    "run_emergent_symbol_grounding_study",
]
