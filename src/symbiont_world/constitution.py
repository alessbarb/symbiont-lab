"""WorldConstitution: the fingerprint that identifies a reproducible world.

docs/design/symbiont-world-v1.md §9. A world_seed alone does not identify a
reproducible universe across implementations or code revisions; the
fingerprint of this frozen structure does.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

CONSTITUTION_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class WorldConstitution:
    topology_schema: str
    world_dimensions: tuple[int, int]
    field_laws_hash: str
    resource_laws_hash: str
    hazard_laws_hash: str
    interaction_rules_hash: str
    resolution_policy: str
    communication_physics: str
    lifecycle_contract_version: int
    rng_scheme_version: int
    constitution_schema_version: int = CONSTITUTION_SCHEMA_VERSION

    def canonical(self) -> str:
        payload = {
            "constitution_schema_version": self.constitution_schema_version,
            "topology_schema": self.topology_schema,
            "world_dimensions": list(self.world_dimensions),
            "field_laws_hash": self.field_laws_hash,
            "resource_laws_hash": self.resource_laws_hash,
            "hazard_laws_hash": self.hazard_laws_hash,
            "interaction_rules_hash": self.interaction_rules_hash,
            "resolution_policy": self.resolution_policy,
            "communication_physics": self.communication_physics,
            "lifecycle_contract_version": self.lifecycle_contract_version,
            "rng_scheme_version": self.rng_scheme_version,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        return sha256(self.canonical().encode("utf-8")).hexdigest()
