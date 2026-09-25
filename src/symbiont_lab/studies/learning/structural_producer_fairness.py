from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.core.cognition_bridge import CognitiveBridge

from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.structure import Mutation
from symbiont.cognition.types import NodeKind


@dataclass(frozen=True, slots=True)
class ProducerFairnessTrial:
    seed: int
    rounds: int
    producers: int
    attempted_flood_hypotheses: int
    accepted_flood_hypotheses: int
    maximum_pending_per_producer: int
    maximum_wait_rounds: int
    expected_wait_bound: int
    producer_wins: tuple[tuple[str, int], ...]
    service_schedule: tuple[str, ...]
    all_producers_served: bool
    bounded_waiting: bool
    multiplicity_neutral: bool

    @property
    def passed(self) -> bool:
        return self.all_producers_served and self.bounded_waiting and self.multiplicity_neutral

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["producer_wins"] = dict(self.producer_wins)
        payload["service_schedule"] = list(self.service_schedule)
        payload["passed"] = self.passed
        return payload


@dataclass(frozen=True, slots=True)
class ProducerFairnessStudy:
    seeds: tuple[int, ...]
    trials: tuple[ProducerFairnessTrial, ...]

    @property
    def all_pass(self) -> bool:
        return all(trial.passed for trial in self.trials)

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "trials": [trial.as_dict() for trial in self.trials],
            "all_pass": self.all_pass,
        }


def _proposal(node_id: str) -> tuple[Mutation, ...]:
    return (
        Mutation(
            kind="add_node",
            payload={
                "node_id": node_id,
                "kind": NodeKind.READOUT,
            },
        ),
    )


def _maximum_service_wait(
    schedule: tuple[str, ...],
    producer_ids: tuple[str, ...],
) -> int:
    """Measure initial and between-service waits in completed arbitration rounds."""
    maximum = 0
    for producer_id in producer_ids:
        positions = [index for index, served in enumerate(schedule) if served == producer_id]
        if not positions:
            return len(schedule)
        maximum = max(maximum, positions[0])
        maximum = max(
            maximum,
            max(
                (right - left - 1 for left, right in zip(positions, positions[1:])),
                default=0,
            ),
        )
    return maximum


def _trial(
    *,
    seed: int,
    rounds: int,
    producers: int,
    flood_hypotheses: int,
) -> ProducerFairnessTrial:
    limits = KernelLimits()
    genome = load_base_genome(
        kernel_limits=limits,
        running_version=(0, 80, 16),
    )
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id="readout_core", kind=NodeKind.READOUT),),
        edges=(),
        kernel_limits=limits,
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=limits,
        develop_senses=True,
    )

    # This is a lab-only scheduler stress test. Varying opaque producer IDs by
    # preregistered seed exercises different deterministic ring orders without
    # changing any organism-side scheduling rule.
    producer_ids = tuple(f"producer.synthetic.{seed}.{index}" for index in range(producers))
    candidate_index = {producer_id: 0 for producer_id in producer_ids}

    def register_next(producer_id: str) -> bool:
        index = candidate_index[producer_id]
        candidate_index[producer_id] += 1
        return bridge._register_structural_candidate(
            candidate_id=f"{producer_id}:{index}",
            family="synthetic",
            producer_id=producer_id,
            mutations=_proposal(f"readout.synthetic.{producer_id}.{index}"),
            eligible_tick=index,
        )

    for producer_id in producer_ids:
        if not register_next(producer_id):
            raise RuntimeError("failed to register initial synthetic producer proposal")

    flood_id = producer_ids[0]
    accepted_flood = 1
    for index in range(1, flood_hypotheses):
        accepted_flood += int(
            bridge._register_structural_candidate(
                candidate_id=f"{flood_id}:flood:{index}",
                family="synthetic",
                producer_id=flood_id,
                mutations=_proposal(f"readout.synthetic.flood.{seed}.{index}"),
                eligible_tick=0,
            )
        )

    wins = {producer_id: 0 for producer_id in producer_ids}
    schedule: list[str] = []
    maximum_pending = max(
        sum(
            candidate.producer_id == producer_id
            for candidate in bridge._structural_candidates.values()
        )
        for producer_id in producer_ids
    )

    for _round_index in range(rounds):
        winner_id, mutations, loser_ids = bridge._select_structural_candidate(
            graph=graph,
            mutation_slots=limits.max_structural_mutations_per_consolidation,
            node_slots=limits.max_nodes,
            edge_slots=limits.max_edges,
        )
        if winner_id is None or not mutations:
            raise RuntimeError("fairness study exhausted active producer proposals")

        winner = bridge._structural_candidates[winner_id]
        producer_id = winner.producer_id
        schedule.append(producer_id)
        wins[producer_id] += 1

        bridge._commit_contention_result(
            winner_id=winner_id,
            loser_ids=loser_ids,
        )
        if not register_next(producer_id):
            raise RuntimeError("continuous producer failed to register next proposal")

        maximum_pending = max(
            maximum_pending,
            max(
                sum(
                    candidate.producer_id == active_id
                    for candidate in bridge._structural_candidates.values()
                )
                for active_id in producer_ids
            ),
        )

    schedule_tuple = tuple(schedule)
    maximum_wait = _maximum_service_wait(schedule_tuple, producer_ids)
    expected_bound = max(0, producers - 1)
    all_served = all(value > 0 for value in wins.values())

    return ProducerFairnessTrial(
        seed=seed,
        rounds=rounds,
        producers=producers,
        attempted_flood_hypotheses=flood_hypotheses,
        accepted_flood_hypotheses=accepted_flood,
        maximum_pending_per_producer=maximum_pending,
        maximum_wait_rounds=maximum_wait,
        expected_wait_bound=expected_bound,
        producer_wins=tuple(sorted(wins.items())),
        service_schedule=schedule_tuple,
        all_producers_served=all_served,
        bounded_waiting=maximum_wait <= expected_bound,
        multiplicity_neutral=(accepted_flood == 1 and maximum_pending <= 1),
    )


def run_structural_producer_fairness_study(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    ticks: int = 64,
) -> ProducerFairnessStudy:
    seed_list = tuple(seeds)
    if not seed_list:
        raise ValueError("seeds must not be empty")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 16:
        raise ValueError("ticks must be at least 16")

    producer_count = 4
    flood_hypotheses = 1000
    trials = tuple(
        _trial(
            seed=seed,
            rounds=ticks,
            producers=producer_count,
            flood_hypotheses=flood_hypotheses,
        )
        for seed in seed_list
    )
    return ProducerFairnessStudy(seeds=seed_list, trials=trials)


__all__ = [
    "ProducerFairnessStudy",
    "ProducerFairnessTrial",
    "run_structural_producer_fairness_study",
]
