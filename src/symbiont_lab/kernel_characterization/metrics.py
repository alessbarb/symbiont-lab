from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping


def summarize(records: Iterable[Mapping[str, object]]) -> dict[str, object]:
    rows = list(records)
    numeric = (
        "prediction_error",
        "predictive_gain",
        "adaptation_latency",
        "retention",
        "recovery_latency",
        "nodes_used",
        "node_utilization",
        "concepts_used",
        "edges_used",
        "structural_churn",
        "cpu_time_per_tick",
        "peak_memory",
        "checkpoint_bytes",
        "saturation_events",
        "frozen_events",
        "recovery_events",
    )
    result: dict[str, object] = {"runs": len(rows), "failures": sum(bool(row.get("failure")) for row in rows)}
    for name in numeric:
        values = [float(row[name]) for row in rows if not row.get("failure") and name in row]
        if values:
            result[name] = {
                "mean": statistics.fmean(values),
                "p95": max(values) if len(values) < 20 else statistics.quantiles(values, n=20, method="inclusive")[18],
                "min": min(values),
                "max": max(values),
            }
    return result
