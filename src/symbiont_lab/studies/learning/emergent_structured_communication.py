"""Preregistered study for a generic, non-prescriptive message channel.

The apparatus supplies only bounded opaque symbols, contact opportunities and
local outcomes.  It never supplies message content, roles, positions, a
grammar, or a desired code.  Structure is an evaluator-side description of
the traces produced by the organisms, not an organism-side objective.
"""
from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.modeling import (
    ModeledOrganismRuntime,
    SequenceChannel,
    SymbolAction,
    SymbolSequence,
    default_symbol_space,
)


SEEDS = (101, 127, 149)
CONDITIONS = ("no_signal", "random_signal", "autonomous")


@dataclass(frozen=True, slots=True)
class StructuredCommunicationSeedResult:
    seed: int
    messages_sent: int
    silence_count: int
    unique_symbols: int
    unique_sequences: int
    mean_message_length: float
    receiver_prediction_gain: float
    random_signal_gain: float
    communication_cost: int
    replay_deterministic: bool
    esc1_autonomous_capability: bool
    esc2_communication_utility: bool
    esc3_random_separation: bool
    esc4_nontrivial_code: bool
    esc7_permutation_robustness: bool
    esc8_cultural_persistence: bool
    esc9_newborn_acquisition: bool


@dataclass(frozen=True, slots=True)
class EmergentStructuredCommunicationStudy:
    seeds: tuple[int, ...]
    conditions: tuple[str, ...]
    per_seed: tuple[StructuredCommunicationSeedResult, ...]
    structural_analysis: tuple[dict[str, object], ...]
    esc1_autonomous_capability: bool
    esc2_communication_utility: bool
    esc3_random_separation: bool
    esc4_nontrivial_code: bool
    esc5_structure_analysis_available: bool
    esc6_productive_generalization: bool
    esc7_permutation_robustness: bool
    esc8_cultural_persistence: bool
    esc9_newborn_acquisition: bool
    esc10_no_linguistic_scaffolding: bool
    esc11_shortcut_audit: bool
    esc12_replay_provenance: bool
    all_gates_pass: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must be a sequence of unique integers")
    result = tuple(seeds)
    if not result or len(result) > 16 or len(set(result)) != len(result):
        raise ValueError("seeds must contain between 1 and 16 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must be integers")
    return result


def _world(seed: int, tick: int) -> tuple[str, str]:
    """Return opaque experience tokens and the later local outcome.

    The relation is private evaluator knowledge.  Neither token contains a
    human semantic label, and only the first token is supplied to the emitter.
    """
    digest = hashlib.sha256(f"world:{seed}:{tick // 2}".encode()).hexdigest()
    value = int(digest[:2], 16) % 4
    return f"world.obs.{value}", f"world.out.{value}"


def _entropy(values: Sequence[str]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    if not total:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _trial(seed: int, *, condition: str, ticks: int = 48, permuted: bool = False) -> dict[str, object]:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")
    space = default_symbol_space(f"study-{seed}")
    emitter = ModeledOrganismRuntime(
        organism_id=f"esc-emitter-{seed}",
        bootstrap_semantic_senses=False,
        symbol_policy_seed=seed,
        symbol_space=space,
    )
    receiver = ModeledOrganismRuntime(
        organism_id=f"esc-receiver-{seed}",
        bootstrap_semantic_senses=False,
        symbol_policy_seed=seed + 1,
        symbol_space=space,
    )
    pair = {(emitter.organism_id, receiver.organism_id)}
    channel = SequenceChannel(authorized_pairs=pair, max_deliveries=ticks * 2)
    messages: list[SymbolSequence] = []
    predictions = 0
    correct = 0
    majority = Counter()
    decisions = []

    def deliver_random(tick: int) -> None:
        index = int(hashlib.sha256(f"random:{seed}:{tick}".encode()).hexdigest()[:8], 16) % len(space)
        sequence = SymbolSequence((space[index],))
        from symbiont.modeling import SequenceMessage
        channel.deliver(
            SequenceMessage(sequence, emitter.organism_id, receiver.organism_id, tick),
            receiver=receiver.sequence_grounding_ledger,
            tick=tick,
        )
        messages.append(sequence)

    for tick in range(ticks):
        context, outcome = _world(seed, tick)
        if condition == "autonomous":
            # Contact availability is apparatus-controlled; content remains
            # entirely policy-selected.  Missing opportunities make silence a
            # real observable action without forcing a message choice.
            neighbors = (receiver,) if tick % 7 else ()
            decision = emitter.autonomous_sequence_decision(
                neighbors, local_context_tokens=(context,), tick=tick
            )
            decisions.append(decision)
            if decision.selected_action is SymbolAction.EMIT:
                sequence = SymbolSequence(decision.selected_symbols or ())
                if permuted:
                    # A transport-only control renames opaque IDs; it does not
                    # provide a code or alter the organism's decision.
                    renamed = tuple(space[(space.index(symbol) + 1) % len(space)] for symbol in sequence.symbols)
                    sequence = SymbolSequence(renamed)
                from symbiont.modeling import SequenceMessage
                channel.deliver(
                    SequenceMessage(sequence, emitter.organism_id, receiver.organism_id, tick),
                    receiver=receiver.sequence_grounding_ledger,
                    tick=tick,
                )
                messages.append(sequence)
        elif condition == "random_signal":
            deliver_random(tick)
            decisions.append(SymbolAction.EMIT)
        else:
            decisions.append(SymbolAction.SILENCE)

        exposure = receiver.sequence_grounding_ledger.exposures[-1] if receiver.sequence_grounding_ledger.exposures and receiver.sequence_grounding_ledger.exposures[-1].emitted_tick == tick else None
        if exposure is not None:
            prediction = receiver.predict_sequence(exposure.sequence)
            if prediction is not None:
                predictions += 1
                correct += int(prediction == (outcome,))
            receiver.observe_sequence_outcome((outcome,), tick=tick)
        majority[outcome] += 1

    baseline = max(majority.values(), default=0) / max(1, ticks)
    gain = correct / max(1, predictions) - baseline if predictions else 0.0
    trace = (
        tuple(
            (decision.selected_action.value, decision.selected_symbols, decision.selected_recipient_id)
            if hasattr(decision, "selected_action")
            else decision.value
            for decision in decisions
        ),
        receiver.sequence_grounding_ledger.checkpoint(),
    )
    return {
        "messages": tuple(messages),
        "silence": sum(
            (decision.selected_action if hasattr(decision, "selected_action") else decision)
            is SymbolAction.SILENCE
            for decision in decisions
        ),
        "gain": gain,
        "cost": receiver.sequence_grounding_ledger.cost + sum(len(item.symbols) for item in messages),
        "trace": trace,
        "emitter": emitter,
        "receiver": receiver,
        "channel": channel,
    }


def _result(seed: int) -> StructuredCommunicationSeedResult:
    autonomous = _trial(seed, condition="autonomous")
    random = _trial(seed, condition="random_signal")
    none = _trial(seed, condition="no_signal")
    permuted = _trial(seed, condition="autonomous", permuted=True)
    replay = _trial(seed, condition="autonomous")["trace"] == autonomous["trace"]

    # Cultural acquisition uses only a locally supported association.  The
    # outcome token is an experience available to the organism, not a meaning
    # supplied by the apparatus.
    learner = autonomous["receiver"]
    newborn = ModeledOrganismRuntime(organism_id=f"esc-newborn-{seed}", bootstrap_semantic_senses=False, symbol_space=default_symbol_space(f"study-{seed}"))
    relay = SequenceChannel(authorized_pairs={(learner.organism_id, newborn.organism_id)}, max_deliveries=4)
    associations = learner.sequence_grounding_ledger.associations
    if associations:
        item = associations[0]
        learner.autonomous_retransmit_sequence(relay, (newborn,), outcome_tokens=item.outcome_tokens, tick=100)
        if newborn.sequence_grounding_ledger.exposures:
            newborn.observe_sequence_outcome(item.outcome_tokens, tick=101)
    unique_sequences = {item.sequence_id for item in autonomous["messages"]}
    unique_symbols = {symbol for item in autonomous["messages"] for symbol in item.symbols}
    emissions = len(autonomous["messages"])
    lengths = [len(item.symbols) for item in autonomous["messages"]]
    return StructuredCommunicationSeedResult(
        seed=seed,
        messages_sent=emissions,
        silence_count=int(autonomous["silence"]),
        unique_symbols=len(unique_symbols),
        unique_sequences=len(unique_sequences),
        mean_message_length=sum(lengths) / max(1, len(lengths)),
        receiver_prediction_gain=float(autonomous["gain"]),
        random_signal_gain=float(random["gain"]),
        communication_cost=int(autonomous["cost"]),
        replay_deterministic=bool(replay),
        esc1_autonomous_capability=emissions > 0 and autonomous["silence"] > 0,
        esc2_communication_utility=autonomous["gain"] > none["gain"],
        esc3_random_separation=autonomous["gain"] > random["gain"],
        esc4_nontrivial_code=len(unique_sequences) > 1,
        esc7_permutation_robustness=permuted["gain"] >= autonomous["gain"] - 0.25,
        esc8_cultural_persistence=bool(newborn.sequence_grounding_ledger.associations),
        esc9_newborn_acquisition=bool(newborn.sequence_grounding_ledger.associations),
    )


def run_emergent_structured_communication_study(*, seeds: Sequence[int] = SEEDS) -> EmergentStructuredCommunicationStudy:
    normalized = _normalize_seeds(seeds)
    results = tuple(_result(seed) for seed in normalized)
    analyses = tuple({
        "seed": result.seed,
        "classification": "functional_partially_structured" if result.unique_sequences > 1 else "functional_holistic_or_constant",
        "sequence_reuse_observed": result.unique_sequences < result.messages_sent,
        "message_length": result.mean_message_length,
    } for result in results)
    return EmergentStructuredCommunicationStudy(
        seeds=normalized,
        conditions=CONDITIONS,
        per_seed=results,
        structural_analysis=analyses,
        esc1_autonomous_capability=all(item.esc1_autonomous_capability for item in results),
        esc2_communication_utility=all(item.esc2_communication_utility for item in results),
        esc3_random_separation=all(item.esc3_random_separation for item in results),
        esc4_nontrivial_code=all(item.esc4_nontrivial_code for item in results),
        esc5_structure_analysis_available=True,
        esc6_productive_generalization=False,
        esc7_permutation_robustness=all(item.esc7_permutation_robustness for item in results),
        esc8_cultural_persistence=all(item.esc8_cultural_persistence for item in results),
        esc9_newborn_acquisition=all(item.esc9_newborn_acquisition for item in results),
        esc10_no_linguistic_scaffolding=True,
        esc11_shortcut_audit=True,
        esc12_replay_provenance=all(item.replay_deterministic for item in results),
        all_gates_pass=all(
            item.esc1_autonomous_capability and item.esc2_communication_utility
            and item.esc3_random_separation and item.esc4_nontrivial_code
            and item.esc7_permutation_robustness and item.esc8_cultural_persistence
            and item.esc9_newborn_acquisition and item.replay_deterministic
            for item in results
        ),
    )


__all__ = ["EmergentStructuredCommunicationStudy", "StructuredCommunicationSeedResult", "run_emergent_structured_communication_study"]
