"""symbiont_lab <-> symbiont_world adapter layer (docs/design/symbiont-world-v1.md §2).

The only package allowed to know what a field/resource/hazard means, and
the only package that imports both symbiont_world and symbiont.
"""

from .adapter import SingleOrganismGenesisRuntime, WorldDiscoveryProvider, WorldReadingProvider, WorldTickRecord
from .runtime import WorldRuntimeState
from .genesis_v1 import (
    GENESIS_V1_METADATA,
    GenesisV1,
    build_constitution,
    build_genesis_smoke_v1,
    build_genesis_v1,
    build_ground_truth,
)
from .persistence import (
    PersistentWorldCheckpoint,
    WorldStorage,
    capture_checkpoint,
    restore_population_from_checkpoint,
)
from .population import PopulationGenesisRuntime, PopulationTickRecord, founder_placement
from .transaction import IntegratedWorldTickTransaction

__all__ = [
    "WorldRuntimeState",
    "GENESIS_V1_METADATA",
    "GenesisV1",
    "build_constitution",
    "build_genesis_smoke_v1",
    "build_genesis_v1",
    "build_ground_truth",
    "SingleOrganismGenesisRuntime",
    "WorldDiscoveryProvider",
    "WorldReadingProvider",
    "WorldTickRecord",
    "PopulationGenesisRuntime",
    "PopulationTickRecord",
    "founder_placement",
    "PersistentWorldCheckpoint",
    "WorldStorage",
    "capture_checkpoint",
    "restore_population_from_checkpoint",
    "IntegratedWorldTickTransaction",
]
