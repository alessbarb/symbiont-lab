"""Public surface of the Symbiont organism.

External callers can hold, run, persist and identify an organism through this
module. It re-exports organism-level contracts only; embodiment composition,
body transitions and physical descriptors are not part of this API.
"""

from symbiont import __version__
from symbiont.core.lineage.heritage import HeritagePattern, SpeciesHeritage
from symbiont.core.orchestration.canonical_birth import restore_resident_with_canonical_cognition
from symbiont.core.orchestration.governor import (
    ConsentRevokedError,
    GovernedOrganism,
    RateLimitedError,
    TickBudgetExhaustedError,
)
from symbiont.core.orchestration.resident import ResidentConfig, ResidentOrganism
from symbiont.core.orchestration.runtime import (
    OrganismDeadError,
    OrganismRuntime,
    RuntimeTickResult,
)
from symbiont.host.checkpoint import (
    CheckpointError,
    checkpoint_state_hash,
    lineage_history,
    load_checkpoint_file,
    save_checkpoint_atomic,
    verify_checkpoint_identity,
)

__all__ = [
    # lifecycle
    "OrganismRuntime",
    "RuntimeTickResult",
    "OrganismDeadError",
    "GovernedOrganism",
    "ConsentRevokedError",
    "RateLimitedError",
    "TickBudgetExhaustedError",
    "ResidentOrganism",
    "ResidentConfig",
    # persistence
    "load_checkpoint_file",
    "save_checkpoint_atomic",
    "restore_resident_with_canonical_cognition",
    "CheckpointError",
    # identity
    "checkpoint_state_hash",
    "verify_checkpoint_identity",
    # lineage
    "lineage_history",
    "SpeciesHeritage",
    "HeritagePattern",
    "__version__",
]
