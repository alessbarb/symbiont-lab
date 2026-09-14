from __future__ import annotations

from dataclasses import dataclass

from symbiont.cognition.metaplasticity import LearningObjective, dominates


@dataclass(slots=True, frozen=True)
class EvaluationResult:
    genome_id: str
    objective: LearningObjective
    regime_label: str
    seed_pair_id: str


def select_archive(results: tuple[EvaluationResult, ...], *, max_archive_size: int) -> tuple[EvaluationResult, ...]:
    front: list[EvaluationResult] = []
    for candidate in results:
        if any(dominates(other.objective, candidate.objective) for other in results if other is not candidate):
            continue
        front.append(candidate)

    if len(front) <= max_archive_size:
        return tuple(front)

    def domination_count(result: EvaluationResult) -> int:
        return sum(1 for other in results if dominates(result.objective, other.objective))

    ranked = sorted(front, key=lambda result: (-domination_count(result), result.genome_id))
    return tuple(ranked[:max_archive_size])
