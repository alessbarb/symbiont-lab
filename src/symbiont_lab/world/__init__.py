"""symbiont_lab <-> symbiont_world adapter layer (docs/design/symbiont-world-v1.md §2).

The only package allowed to know what a field/resource/hazard means, and
the only package that imports both symbiont_world and symbiont.
"""

from .adapter import SingleOrganismGenesisRuntime, WorldDiscoveryProvider, WorldReadingProvider, WorldTickRecord
from .dashboard_server import make_server as make_dashboard_server
from .dashboard_state import WorldDashboardState
from .genesis_v1 import GENESIS_V1_METADATA, GenesisV1, build_constitution, build_genesis_v1, build_ground_truth
from .population import PopulationGenesisRuntime, PopulationTickRecord, founder_placement

__all__ = [
    "make_dashboard_server",
    "WorldDashboardState",
    "GENESIS_V1_METADATA",
    "GenesisV1",
    "build_constitution",
    "build_genesis_v1",
    "build_ground_truth",
    "SingleOrganismGenesisRuntime",
    "WorldDiscoveryProvider",
    "WorldReadingProvider",
    "WorldTickRecord",
    "PopulationGenesisRuntime",
    "PopulationTickRecord",
    "founder_placement",
]
