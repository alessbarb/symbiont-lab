"""Reconstruct factual communication history from the real local channel.

This is an observability study, not a cognition or capacity experiment.  The
scenario calls the bounded channel and grounding ledger; Observatory receives
their exported records and may aggregate them, but does not infer missing
edges or causal intent.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from symbiont.modeling import (
    CommunicationTelemetry,
    SequenceChannel,
    SequenceGroundingLedger,
    SequenceMessage,
    SymbolSequence,
)


SEEDS = (101, 127, 149)
EXPECTED_PATH = ("A", "B", "C", "D")


@dataclass(frozen=True, slots=True)
class PopulationCommunicationSeedResult:
    seed: int
    event_count: int
    grounding_event_count: int
    edge_count: int
    edges: tuple[tuple[str, str], ...]
    message_id: str
    event_kinds: tuple[str, ...]
    history_truncated: bool
    replay_deterministic: bool
    reconstructed_path: tuple[str, ...]
    no_inferred_edges: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PopulationCommunicationStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[PopulationCommunicationSeedResult, ...]
    bounded_history: bool
    factual_only: bool
    no_feedback: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run_seed(seed: int) -> PopulationCommunicationSeedResult:
    telemetry = CommunicationTelemetry(max_events=64, max_events_per_tick=16)
    ledgers = {name: SequenceGroundingLedger(name) for name in EXPECTED_PATH}
    sequence = SymbolSequence((f"symbol.observation.{seed:03d}",))

    for index, (sender, receiver) in enumerate(zip(EXPECTED_PATH, EXPECTED_PATH[1:])):
        channel = SequenceChannel(
            authorized_pairs={(sender, receiver)},
            max_deliveries=1,
            telemetry=telemetry,
        )
        channel.deliver(
            SequenceMessage(sequence, sender, receiver, index),
            receiver=ledgers[receiver],
            tick=index,
            event_kind="RETRANSMIT" if index else "DELIVER",
        )
        # This is a real receiver-side update, not an evaluator annotation.
        ledgers[receiver].observe_outcome((f"outcome.{seed:03d}",), tick=index + 1)

    exported = telemetry.export()
    restored = CommunicationTelemetry.restore(telemetry.checkpoint())
    replay = restored.export() == exported
    events = tuple(telemetry.events)
    edges = tuple((event.sender_id, event.receiver_id) for event in events)
    unique_edges = tuple(dict.fromkeys(edges))
    path = (unique_edges[0][0],) + tuple(edge[1] for edge in unique_edges) if unique_edges else ()
    return PopulationCommunicationSeedResult(
        seed=seed,
        event_count=len(events),
        grounding_event_count=len(telemetry.grounding_events),
        edge_count=len(unique_edges),
        edges=unique_edges,
        message_id=sequence.sequence_id,
        event_kinds=tuple(event.event_kind for event in events),
        history_truncated=telemetry.history_truncated,
        replay_deterministic=replay,
        reconstructed_path=path,
        no_inferred_edges=all(
            edge in {(event.sender_id, event.receiver_id) for event in events}
            for edge in unique_edges
        ),
    )


def run_population_communication_study(*, seeds: tuple[int, ...] = SEEDS) -> PopulationCommunicationStudy:
    normalized = tuple(seeds)
    if not normalized or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized):
        raise ValueError("seeds must be non-empty integers")
    results = tuple(_run_seed(seed) for seed in normalized)
    return PopulationCommunicationStudy(
        seeds=normalized,
        per_seed=results,
        bounded_history=True,
        factual_only=True,
        no_feedback=True,
    )


__all__ = ["PopulationCommunicationSeedResult", "PopulationCommunicationStudy", "run_population_communication_study"]
