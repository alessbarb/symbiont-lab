"""Small current-contract Genome v2 fixtures for unit tests."""

from __future__ import annotations

import copy
import json
from importlib import resources

from symbiont.genetics.genome import Genome, GenomeCodec


def genome(
    *, genome_id: str = "genome_unit_v2", node_budget: int = 192, edge_budget: int = 1536
) -> Genome:
    payload = json.loads(
        resources.files("symbiont.genetics").joinpath("defaults/base-genome-v2.json").read_text()
    )
    payload = copy.deepcopy(payload)
    payload["genome_id"] = genome_id
    payload["development"]["soft_node_budget"] = node_budget
    payload["development"]["soft_edge_budget"] = edge_budget
    payload["development"]["sense_node_budget"] = min(
        node_budget, payload["development"]["sense_node_budget"]
    )
    return GenomeCodec().load(payload)
