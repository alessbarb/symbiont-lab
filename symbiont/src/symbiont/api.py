"""Public surface of the Symbiont organism.

Everything outside the organism (Lab, Environment, Embodiment, Modality,
Observatory) should be able to hold, run, persist and identify an organism
through this module without importing organism internals. It only re-exports
existing objects; it adds no behaviour and no persisted format.

It deliberately carries no modality-, body- or physics-specific types.
"""

from symbiont import __version__
from symbiont.core.embodiment.reembodiment import begin_reembodiment, replace_body
from symbiont.core.embodiment.transition import (
    EmbodimentDescriptor,
    prepare_fresh_embodiment_checkpoint,
)
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
    # re-embodiment
    "begin_reembodiment",
    "replace_body",
    "EmbodimentDescriptor",
    "prepare_fresh_embodiment_checkpoint",
    "__version__",
]
