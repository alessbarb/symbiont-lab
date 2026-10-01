#!/usr/bin/env python3
"""Focused P2 benchmark for motor-sequence matching.

Compares the current allocation-light matcher with the pre-P2 reference
formula on the same deterministic candidate pool. It also verifies every
distance and selected winner before reporting timing.
"""

from __future__ import annotations

import argparse
import random
import time

from symbiont.actuation.sensorimotor import CompetenceDevelopmentEngine


def _reference_distance(left, right) -> float:
    if len(left) != len(right):
        return 1.0
    step_distances = []
    for left_pattern, right_pattern in zip(left, right):
        left_map = dict(left_pattern)
        right_map = dict(right_pattern)
        left_ids = set(left_map)
        right_ids = set(right_map)
        union = left_ids | right_ids
        if not union:
            step_distances.append(0.0)
            continue
        amplitude = sum(
            abs(int(left_map.get(actuator_id, 0)) - int(right_map.get(actuator_id, 0)))
            for actuator_id in union
        ) / (7.0 * len(union))
        support = len(left_ids.symmetric_difference(right_ids)) / len(union)
        step_distances.append(max(amplitude, support))
    return sum(step_distances) / len(step_distances) if step_distances else 0.0


def _reference_winner(query, candidates):
    return min(
        ((_reference_distance(query, candidate), candidate) for candidate in candidates),
        key=lambda item: (item[0], item[1]),
    )


def _sequence(rng: random.Random, actuators: int, density: float):
    ids = [f"actuator.{index:03d}" for index in range(actuators)]
    steps = []
    for _ in range(4):
        pattern = tuple(
            (actuator_id, rng.randint(1, 7)) for actuator_id in ids if rng.random() < density
        )
        steps.append(pattern)
    return tuple(steps)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=int, default=512)
    parser.add_argument("--queries", type=int, default=200)
    parser.add_argument("--actuators", type=int, default=64)
    parser.add_argument("--density", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=127)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    candidates = tuple(_sequence(rng, args.actuators, args.density) for _ in range(args.candidates))
    queries = tuple(_sequence(rng, args.actuators, args.density) for _ in range(args.queries))

    for query in queries:
        reference_distance, reference_candidate = _reference_winner(query, candidates)
        best_candidate = None
        best_distance = float("inf")
        for candidate in candidates:
            distance = CompetenceDevelopmentEngine._sequence_distance(query, candidate)
            if distance != _reference_distance(query, candidate):
                raise RuntimeError("optimized distance diverged from reference")
            if (
                best_candidate is None
                or distance < best_distance
                or (distance == best_distance and candidate < best_candidate)
            ):
                best_distance = distance
                best_candidate = candidate
        if (best_distance, best_candidate) != (reference_distance, reference_candidate):
            raise RuntimeError("optimized winner diverged from reference")

    started = time.perf_counter()
    for query in queries:
        _reference_winner(query, candidates)
    reference_s = time.perf_counter() - started

    started = time.perf_counter()
    for query in queries:
        best_candidate = None
        best_distance = float("inf")
        for candidate in candidates:
            distance = CompetenceDevelopmentEngine._sequence_distance(query, candidate)
            if (
                best_candidate is None
                or distance < best_distance
                or (distance == best_distance and candidate < best_candidate)
            ):
                best_distance = distance
                best_candidate = candidate
    optimized_s = time.perf_counter() - started

    print(
        {
            "candidates": args.candidates,
            "queries": args.queries,
            "reference_seconds": round(reference_s, 6),
            "optimized_seconds": round(optimized_s, 6),
            "speedup": round(reference_s / optimized_s, 3) if optimized_s else None,
            "equivalent": True,
        }
    )


if __name__ == "__main__":
    main()
