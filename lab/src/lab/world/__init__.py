"""lab <-> environment adapter layer (docs/design/archive/symbiont-world-v1.md §2).

The only package allowed to know what a field/resource/hazard means, and
the only package that imports both environment and symbiont.
"""

from lab.world.adapter import (
    SingleOrganismGenesisRuntime,
    WorldDiscoveryProvider,
    WorldReadingProvider,
    WorldTickRecord,
)
from lab.world.genesis_v1 import (
    GENESIS_V1_METADATA,
    GenesisV1,
    build_constitution,
    build_genesis_smoke_v1,
    build_genesis_v1,
    build_ground_truth,
)
from lab.world.persistence import (
    PersistentWorldCheckpoint,
    WorldStorage,
    capture_checkpoint,
    restore_population_from_checkpoint,
)
from lab.world.population import PopulationGenesisRuntime, PopulationTickRecord, founder_placement
from lab.world.runtime import WorldRuntimeState
from lab.world.transaction import IntegratedWorldTickTransaction

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
