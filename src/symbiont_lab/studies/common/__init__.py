"""Common statistical, pairing, digest, causal-selection, and summary utilities."""

from .causal_selection import OrderStatisticHistory, historical_threshold, online_indices
from .digests import compute_config_digest, compute_world_digest
from .pairing import assert_disjoint_seeds, assert_paired_seeds, assert_unique_seeds
from .statistics import aggregate_metric, mean_delta, paired_deltas, safe_mean
from .summaries import format_markdown_table

__all__ = [
    "OrderStatisticHistory",
    "aggregate_metric",
    "assert_disjoint_seeds",
    "assert_paired_seeds",
    "assert_unique_seeds",
    "compute_config_digest",
    "compute_world_digest",
    "format_markdown_table",
    "historical_threshold",
    "mean_delta",
    "online_indices",
    "paired_deltas",
    "safe_mean",
]
