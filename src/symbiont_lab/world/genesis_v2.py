"""Genesis v2 preset: same field/resource/hazard identities as Genesis v1
(genesis_v1.py), plus regional heterogeneity for W03 (docs/design/
symbiont-world-v2.md §3, §11). genesis_v1's preset is untouched -- this is
additive, a separate preset, not a mutation of the frozen v1 one.
"""

from __future__ import annotations

from symbiont_world.genesis import GroundTruth
from symbiont_world.laws import ResourceLaw
from symbiont_world.topology import HexCoord

from .genesis_v1 import RESOURCE_IDS, _fields, _hazards, _resources

REGION_NORTH = "region-north-hash"
REGION_SOUTH = "region-south-hash"

# Apparatus-only metadata for the two regions, never seen by symbiont_world.
REGION_METADATA = {
    REGION_NORTH: "north (q<4): scarce-rich resource abundant here",
    REGION_SOUTH: "south (q>=4): scarce-rich resource stays scarce, abundant-cheap richer",
}


def region_of(cell: HexCoord) -> str:
    return REGION_NORTH if cell.q < 4 else REGION_SOUTH


def build_ground_truth_v2() -> GroundTruth:
    scarce_rich_id = RESOURCE_IDS["resource-scarce-rich"]
    abundant_cheap_id = RESOURCE_IDS["resource-abundant-cheap"]

    regional_resources = {
        REGION_NORTH: {
            scarce_rich_id: ResourceLaw(
                capacity=14.0, renewal_rate=0.15, decay_rate=0.0, initial_quantity=14.0
            ),
        },
        REGION_SOUTH: {
            abundant_cheap_id: ResourceLaw(
                capacity=30.0, renewal_rate=0.5, decay_rate=0.0, initial_quantity=30.0
            ),
        },
    }

    return GroundTruth(
        fields=_fields(),
        resources=_resources(),
        hazards=_hazards(),
        region_of=region_of,
        regional_resources=regional_resources,
    )
