from __future__ import annotations

from collections.abc import Iterable, Mapping


def _numeric(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    return float(value)


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
            _numeric(other[benefit], field=benefit) >= _numeric(candidate[benefit], field=benefit)
            and _numeric(other[cost], field=cost) <= _numeric(candidate[cost], field=cost)
            and (
                _numeric(other[benefit], field=benefit)
                > _numeric(candidate[benefit], field=benefit)
                or _numeric(other[cost], field=cost) < _numeric(candidate[cost], field=cost)
            )
            for other in values
            if other is not candidate
        )
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier, key=lambda row: _numeric(row["max_nodes"], field="max_nodes"))
