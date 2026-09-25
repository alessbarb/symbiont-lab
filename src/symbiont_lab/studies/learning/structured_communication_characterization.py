"""Evaluator-only characterization of the generic communication channel.

This study measures traces produced by the already-available channel.  It does
not add a linguistic policy, targets, roles, slots, or a compositional loss.
The opaque context tokens are the only experience exposed to the organisms;
the state labels used for information-theoretic summaries remain evaluator
data and never enter cognition.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Sequence

from symbiont.modeling import (
    MAX_SEQUENCE_LENGTH,
    ModeledOrganismRuntime,
    SequenceChannel,
    SequenceMessage,
    SymbolAction,
    SymbolSequence,
)

SEEDS = (101, 127, 149)
CONDITIONS = (
    "no_signal",
    "random_signal",
    "baseline",
    "high_complexity",
    "tight_vocabulary",
    "high_complexity_tight_vocabulary",
    "high_communication_cost",
    "sequence_disabled",
    "full_channel",
)
VOCABULARY_SIZES = {
    "baseline": 8,
    "high_complexity": 8,
    "tight_vocabulary": 4,
    "high_complexity_tight_vocabulary": 4,
    "high_communication_cost": 8,
    "sequence_disabled": 8,
    "full_channel": 16,
    "no_signal": 8,
    "random_signal": 8,
}
STATE_COUNTS = {
    "baseline": 4,
    "high_complexity": 16,
    "tight_vocabulary": 4,
    "high_complexity_tight_vocabulary": 16,
    "high_communication_cost": 4,
    "sequence_disabled": 4,
    "full_channel": 64,
    "no_signal": 8,
    "random_signal": 8,
}
MAX_LENGTHS = {"sequence_disabled": 1}
COSTS = {"high_communication_cost": 3}


@dataclass(frozen=True, slots=True)
class CommunicationSeedResult:
    seed: int
    condition: str
    state_count: int
    vocabulary_size: int
    max_message_length: int
    communication_opportunities: int
    silence_count: int
    messages_sent: int
    message_delivery_count: int
    unique_symbols_used: int
    unique_sequences_used: int
    mean_message_length: float
    symbol_reuse_rate: float
    sequence_reuse_rate: float
    subsequence_reuse_rate: float
    symbol_entropy: float
    sequence_entropy: float
    message_length_entropy: float
    receiver_prediction_gain: float
    message_state_mutual_information: float
    new_message_generalization: float
    communication_cost: int
    replay_deterministic: bool
    classification: str


@dataclass(frozen=True, slots=True)
class StructuredCommunicationCharacterization:
    seeds: tuple[int, ...]
    conditions: tuple[str, ...]
    preregistered_matrix: tuple[dict[str, object], ...]
    per_seed: tuple[CommunicationSeedResult, ...]
    no_signal_control: bool
    random_signal_control: bool
    holdout_isolated: bool
    evaluator_only_metrics: bool
    no_linguistic_scaffolding: bool
    productive_generalization_observed: bool
    summary: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _entropy(values: Sequence[object]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    return -sum((n / total) * math.log2(n / total) for n in counts.values()) if total else 0.0


def _mutual_information(xs: Sequence[object], ys: Sequence[object]) -> float:
    if len(xs) != len(ys) or not xs:
        return 0.0
    joint = Counter(zip(xs, ys))
    left = Counter(xs)
    right = Counter(ys)
    total = len(xs)
    return sum(
        (n / total) * math.log2((n * total) / (left[x] * right[y])) for (x, y), n in joint.items()
    )


def _space(seed: int, size: int) -> tuple[str, ...]:
    # IDs are deliberately opaque and carry no state, factor, or role label.
    return tuple(
        f"symbol.{hashlib.sha256(f'space:{seed}:{i}'.encode()).hexdigest()[:24]}"
        for i in range(size)
    )


def _state(seed: int, tick: int, count: int) -> tuple[str, int]:
    value = (
        int(hashlib.sha256(f"environment:{seed}:{tick // 2}".encode()).hexdigest()[:8], 16) % count
    )
    return (
        f"observation.{hashlib.sha256(f'obs:{seed}:{tick // 2}'.encode()).hexdigest()[:24]}",
        value,
    )


def _trial(seed: int, condition: str, *, ticks: int = 64) -> dict[str, object]:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown characterization condition: {condition}")
    vocab = VOCABULARY_SIZES[condition]
    state_count = STATE_COUNTS[condition]
    max_length = MAX_LENGTHS.get(condition, MAX_SEQUENCE_LENGTH)
    space = _space(seed, vocab)
    emitter = ModeledOrganismRuntime(
        organism_id=f"sc-emitter-{seed}-{condition}",
        bootstrap_semantic_senses=False,
        symbol_policy_seed=seed,
        symbol_space=space,
        sequence_max_length=max_length,
    )
    receiver = ModeledOrganismRuntime(
        organism_id=f"sc-receiver-{seed}-{condition}",
        bootstrap_semantic_senses=False,
        symbol_policy_seed=seed + 1,
        symbol_space=space,
        sequence_max_length=max_length,
    )
    channel = SequenceChannel(
        authorized_pairs={(emitter.organism_id, receiver.organism_id)}, max_deliveries=ticks
    )
    messages: list[SymbolSequence] = []
    message_states: list[int] = []
    lengths: list[int] = []
    outcomes: list[tuple[str, ...]] = []
    correct = 0
    predictions = 0
    decisions = []
    for tick in range(ticks):
        context, state = _state(seed, tick, state_count)
        outcome = (f"outcome.{state}",)
        outcomes.append(outcome)
        # Keep contact availability balanced and evaluator-controlled. Content
        # is selected only by the generic organism-side policy.
        neighbors = (receiver,) if tick % 5 else ()
        if condition not in {"no_signal", "random_signal"}:
            decision = emitter.autonomous_sequence_decision(
                neighbors, local_context_tokens=(context,), tick=tick
            )
            decisions.append(decision)
            if (
                decision.selected_action is SymbolAction.EMIT
                and decision.selected_symbols is not None
            ):
                sequence = SymbolSequence(decision.selected_symbols)
                channel.deliver(
                    SequenceMessage(sequence, emitter.organism_id, receiver.organism_id, tick),
                    receiver=receiver.sequence_grounding_ledger,
                    tick=tick,
                )
                messages.append(sequence)
                message_states.append(state)
                lengths.append(len(sequence.symbols))
        elif condition == "random_signal" and neighbors:
            index = int(hashlib.sha256(f"random:{seed}:{tick}".encode()).hexdigest()[:8], 16) % len(
                space
            )
            sequence = SymbolSequence((space[index],))
            channel.deliver(
                SequenceMessage(sequence, emitter.organism_id, receiver.organism_id, tick),
                receiver=receiver.sequence_grounding_ledger,
                tick=tick,
            )
            messages.append(sequence)
            message_states.append(state)
            lengths.append(1)
            decisions.append(SymbolAction.EMIT)
        elif condition == "random_signal":
            decisions.append(SymbolAction.SILENCE)
        else:
            decisions.append(SymbolAction.SILENCE)
        exposure = (
            receiver.sequence_grounding_ledger.exposures[-1]
            if receiver.sequence_grounding_ledger.exposures
            and receiver.sequence_grounding_ledger.exposures[-1].emitted_tick == tick
            else None
        )
        if exposure:
            prediction = receiver.predict_sequence(exposure.sequence)
            if prediction is not None:
                predictions += 1
                correct += int(prediction == outcome)
            receiver.observe_sequence_outcome(outcome, tick=tick)
    message_ids = [item.sequence_id for item in messages]
    symbols = [symbol for item in messages for symbol in item.symbols]
    baseline = 1 / max(1, state_count)
    gain = (correct / predictions - baseline) if predictions else 0.0
    train_ids = {message_ids[i] for i in range(len(message_ids)) if i < len(message_ids) * 3 // 4}
    eval_pairs = [
        (message_ids[i], message_states[i])
        for i in range(len(message_ids))
        if i >= len(message_ids) * 3 // 4
    ]
    novel = [state for mid, state in eval_pairs if mid not in train_ids]
    trace = tuple(
        (d.selected_action.value, d.selected_symbols, d.selected_recipient_id)
        if hasattr(d, "selected_action")
        else (d.value, None, None)
        for d in decisions
    )
    replay = _trial_trace(seed, condition, ticks, max_length) == trace
    subsequence_reuse = sum(
        1 for symbol in set(symbols) if sum(symbol in item.symbols for item in messages) > 1
    ) / max(1, len(set(symbols)))
    # Novel message occurrence is descriptive only. This study does not have a
    # preregistered heldout utility task, so it must not be promoted to a
    # productivity classification.
    classification = (
        "no_functional_code"
        if gain <= 0
        else (
            "functional_partially_structured_code"
            if subsequence_reuse >= 0.5
            else "functional_holistic_code"
        )
    )
    return {
        "result": CommunicationSeedResult(
            seed=seed,
            condition=condition,
            state_count=state_count,
            vocabulary_size=vocab,
            max_message_length=max_length,
            communication_opportunities=ticks - (ticks // 5),
            silence_count=sum(
                (d.selected_action if hasattr(d, "selected_action") else d) is SymbolAction.SILENCE
                for d in decisions
            ),
            messages_sent=sum(
                (d.selected_action if hasattr(d, "selected_action") else d) is SymbolAction.EMIT
                for d in decisions
            ),
            message_delivery_count=len(messages),
            unique_symbols_used=len(set(symbols)),
            unique_sequences_used=len(set(message_ids)),
            mean_message_length=sum(lengths) / max(1, len(lengths)),
            symbol_reuse_rate=1 - len(set(symbols)) / max(1, len(symbols)),
            sequence_reuse_rate=1 - len(set(message_ids)) / max(1, len(message_ids)),
            subsequence_reuse_rate=subsequence_reuse,
            symbol_entropy=_entropy(symbols),
            sequence_entropy=_entropy(message_ids),
            message_length_entropy=_entropy(lengths),
            receiver_prediction_gain=gain,
            message_state_mutual_information=_mutual_information(message_ids, message_states),
            new_message_generalization=1.0 if novel else 0.0,
            communication_cost=len(symbols) * COSTS.get(condition, 1),
            replay_deterministic=replay,
            classification=classification,
        ),
        "trace": trace,
    }


def _trial_trace(
    seed: int, condition: str, ticks: int, max_length: int
) -> tuple[tuple[object, ...], ...]:
    # Re-run through the same public runtime path; this is a replay check, not
    # an alternate policy or a source of evaluator feedback.
    return _trial_unchecked_trace(seed, condition, ticks, max_length)


def _trial_unchecked_trace(
    seed: int, condition: str, ticks: int, max_length: int
) -> tuple[tuple[object, ...], ...]:
    if condition == "no_signal":
        return tuple((SymbolAction.SILENCE.value, None, None) for _ in range(ticks))
    if condition == "random_signal":
        space = _space(seed, VOCABULARY_SIZES[condition])
        # The trial records random control actions without treating their
        # generated payload as an organism decision.
        return tuple(
            (SymbolAction.EMIT.value, None, None)
            if tick % 5
            else (SymbolAction.SILENCE.value, None, None)
            for tick in range(ticks)
        )
    space = _space(seed, VOCABULARY_SIZES[condition])
    runtime = ModeledOrganismRuntime(
        organism_id=f"sc-emitter-{seed}-{condition}",
        bootstrap_semantic_senses=False,
        symbol_policy_seed=seed,
        symbol_space=space,
        sequence_max_length=max_length,
    )
    receiver = ModeledOrganismRuntime(
        organism_id=f"sc-receiver-{seed}-{condition}",
        bootstrap_semantic_senses=False,
        symbol_space=space,
        sequence_max_length=max_length,
    )
    return tuple(
        (d.selected_action.value, d.selected_symbols, d.selected_recipient_id)
        for d in (
            runtime.autonomous_sequence_decision(
                (receiver,) if tick % 5 else (),
                local_context_tokens=(_state(seed, tick, STATE_COUNTS[condition])[0],),
                tick=tick,
            )
            for tick in range(ticks)
        )
    )


def run_structured_communication_characterization(
    *, seeds: Sequence[int] = SEEDS
) -> StructuredCommunicationCharacterization:
    normalized = tuple(seeds)
    if (
        not normalized
        or len(normalized) > 16
        or len(set(normalized)) != len(normalized)
        or any(isinstance(s, bool) or not isinstance(s, int) for s in normalized)
    ):
        raise ValueError("seeds must be unique integers")
    rows = tuple(
        _trial(seed, condition)["result"] for seed in normalized for condition in CONDITIONS
    )
    matrix = tuple(
        {
            "condition": c,
            "state_count": STATE_COUNTS[c],
            "vocabulary_size": VOCABULARY_SIZES[c],
            "max_message_length": MAX_LENGTHS.get(c, MAX_SEQUENCE_LENGTH),
            "communication_cost": COSTS.get(c, 1),
        }
        for c in CONDITIONS
    )
    autonomous = [r for r in rows if r.condition in {"baseline", "full_channel"}]
    return StructuredCommunicationCharacterization(
        normalized,
        CONDITIONS,
        matrix,
        rows,
        no_signal_control=True,
        random_signal_control=True,
        holdout_isolated=True,
        evaluator_only_metrics=True,
        no_linguistic_scaffolding=True,
        productive_generalization_observed=False,
        summary={
            "autonomous_mean_prediction_gain": sum(r.receiver_prediction_gain for r in autonomous)
            / max(1, len(autonomous)),
            "classification_counts": dict(Counter(r.classification for r in rows)),
            "note": "Characterization only; no productivity or linguistic closure is claimed.",
        },
    )


__all__ = [
    "CommunicationSeedResult",
    "StructuredCommunicationCharacterization",
    "run_structured_communication_characterization",
]
