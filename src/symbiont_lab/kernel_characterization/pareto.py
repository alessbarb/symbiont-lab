from __future__ import annotations

from collections.abc import Iterable, Mapping


def pareto_frontier(
    rows: Iterable[Mapping[str, object]],
    *,
    benefit: str = "predictive_gain",
    cost: str = "cpu_time_per_tick",
) -> list[dict[str, object]]:
    """Return non-dominated rows without inventing a scalar score."""
    values = [dict(row) for row in rows if not row.get("failure")]
    frontier: list[dict[str, object]] = []
    for candidate in values:
        dominated = any(
            float(other[benefit]) >= float(candidate[benefit])
            and float(other[cost]) <= float(candidate[cost])
            and (
                float(other[benefit]) > float(candidate[benefit])
                or float(other[cost]) < float(candidate[cost])
            )
            for other in values
            if other is not candidate
        )
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier, key=lambda row: float(row["max_nodes"]))
