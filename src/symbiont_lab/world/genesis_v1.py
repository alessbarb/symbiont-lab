"""Canonical Genesis v1 ground truth (docs/design/symbiont-world-v1.md §7,
§13, §14). This is the one place in the repo allowed to know what a field,
resource or hazard *means* -- symbiont_world never sees GENESIS_V1_METADATA,
only the opaque ids it labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
from types import MappingProxyType
from typing import Mapping

from symbiont_world.constitution import WorldConstitution
from symbiont_world.genesis import GroundTruth
from symbiont_world.laws import HazardLaw, PeriodicFieldLaw, ResourceLaw
from symbiont_world.observation import opaque_signal_id

SCHEMA = 1
WIDTH = 64
HEIGHT = 64
SEED = 101
FOUNDERS = 8
CAPACITY = 64
CHECKPOINT_INTERVAL = 1024

# Apparatus-only labels. Never imported by symbiont_world, never reaches a
# WorldObservation field name -- only opaque_signal_id(label) does.
_FIELD_LABELS = ("field-cycle-a", "field-gradient-b", "field-noise-c", "field-rare-event-d")
_RESOURCE_LABELS = ("resource-abundant-cheap", "resource-scarce-rich", "resource-immediate-deferred", "resource-neutral")
_HAZARD_LABELS = ("hazard-cyclical", "hazard-density-coupled")

FIELD_IDS: Mapping[str, str] = MappingProxyType({label: opaque_signal_id(label) for label in _FIELD_LABELS})
RESOURCE_IDS: Mapping[str, str] = MappingProxyType({label: opaque_signal_id(label) for label in _RESOURCE_LABELS})
HAZARD_IDS: Mapping[str, str] = MappingProxyType({label: opaque_signal_id(label) for label in _HAZARD_LABELS})

# label -> opaque id, for Observatory / apparatus-side interpretation only.
GENESIS_V1_METADATA: Mapping[str, str] = MappingProxyType(
    {**FIELD_IDS, **RESOURCE_IDS, **HAZARD_IDS}
)


def _fields() -> dict[str, PeriodicFieldLaw]:
    return {
        FIELD_IDS["field-cycle-a"]: PeriodicFieldLaw(amplitude=1.0, bias=0.0, angular_frequency=0.05, phase=0.0),
        FIELD_IDS["field-gradient-b"]: PeriodicFieldLaw(amplitude=0.5, bias=0.5, angular_frequency=0.01, phase=1.2),
        FIELD_IDS["field-noise-c"]: PeriodicFieldLaw(amplitude=0.2, bias=0.0, angular_frequency=0.37, phase=2.9),
        FIELD_IDS["field-rare-event-d"]: PeriodicFieldLaw(amplitude=1.0, bias=-0.98, angular_frequency=0.002, phase=0.0),
    }


def _resources() -> dict[str, ResourceLaw]:
    return {
        # abundant, cheap: high capacity, fast renewal, no decay pressure.
        RESOURCE_IDS["resource-abundant-cheap"]: ResourceLaw(
            capacity=20.0, renewal_rate=0.4, decay_rate=0.0, initial_quantity=20.0
        ),
        # scarce, rich: low capacity, slow renewal.
        RESOURCE_IDS["resource-scarce-rich"]: ResourceLaw(
            capacity=4.0, renewal_rate=0.02, decay_rate=0.0, initial_quantity=4.0
        ),
        # TODO(deferred-cost): immediate benefit / deferred cost (§7): pool dynamics alone cannot
        # express the delayed-damage side of this resource -- that requires
        # a physiological effect mapping owned by the not-yet-built
        # symbiont_lab <-> MetabolicLedger adapter. Only the pool half of
        # the contract exists at this increment; the deferred-damage half
        # is intentionally not claimed here.
        RESOURCE_IDS["resource-immediate-deferred"]: ResourceLaw(
            capacity=10.0, renewal_rate=0.15, decay_rate=0.05, initial_quantity=10.0
        ),
        RESOURCE_IDS["resource-neutral"]: ResourceLaw(
            capacity=8.0, renewal_rate=0.1, decay_rate=0.1, initial_quantity=8.0
        ),
    }


def _hazards() -> dict[str, HazardLaw]:
    return {
        # A real temporal hazard: periodic exposure windows with zero-risk
        # troughs. No phase/period label reaches the organism.
        HAZARD_IDS["hazard-cyclical"]: HazardLaw(
            base_probability=0.006,
            density_coupling=0.0,
            temporal_amplitude=1.0,
            angular_frequency=math.tau / 160.0,
            phase=0.0,
        ),
        # Grouping risk with a very small isolated baseline. At density 0.2
        # exposure is ~0.0075; at density 1.0 ~0.0315.
        HAZARD_IDS["hazard-density-coupled"]: HazardLaw(
            base_probability=0.0015,
            density_coupling=20.0,
        ),
    }


def _hazard_region(cell) -> str:
    """Persistent apparatus-side habitat patch.

    Four-by-four axial tiles produce stable patches even in the 8x8 smoke
    world. Region names never cross the observation boundary.
    """
    band = ((cell.q // 4) + 2 * (cell.r // 4)) % 3
    return ("sheltered", "neutral", "exposed")[band]


def _regional_hazards() -> dict[str, dict[str, HazardLaw]]:
    cyc = HAZARD_IDS["hazard-cyclical"]
    den = HAZARD_IDS["hazard-density-coupled"]
    return {
        "sheltered": {
            cyc: HazardLaw(
                base_probability=0.002,
                density_coupling=0.0,
                temporal_amplitude=1.0,
                angular_frequency=math.tau / 160.0,
            ),
            den: HazardLaw(base_probability=0.0005, density_coupling=15.0),
        },
        "exposed": {
            cyc: HazardLaw(
                base_probability=0.012,
                density_coupling=0.0,
                temporal_amplitude=1.0,
                angular_frequency=math.tau / 160.0,
            ),
            den: HazardLaw(base_probability=0.002, density_coupling=25.0),
        },
    }


def build_ground_truth() -> GroundTruth:
    return GroundTruth(
        fields=_fields(),
        resources=_resources(),
        hazards=_hazards(),
        region_of=_hazard_region,
        regional_hazards=_regional_hazards(),
    )


def _laws_hash(law_repr_by_id: Mapping[str, str]) -> str:
    canonical = "|".join(f"{k}:{v}" for k, v in sorted(law_repr_by_id.items()))
    return sha256(canonical.encode("utf-8")).hexdigest()


SMOKE_WIDTH = 8
SMOKE_HEIGHT = 8


def build_constitution(
    ground_truth: GroundTruth | None = None,
    *,
    dimensions: tuple[int, int] = (WIDTH, HEIGHT),
) -> WorldConstitution:
    truth = ground_truth or build_ground_truth()
    return WorldConstitution(
        topology_schema="hex-axial",
        world_dimensions=dimensions,
        field_laws_hash=_laws_hash({k: repr(v) for k, v in truth.fields.items()}),
        resource_laws_hash=_laws_hash({k: repr(v) for k, v in truth.resources.items()}),
        hazard_laws_hash=_laws_hash({
            **{f"base:{k}": repr(v) for k, v in truth.hazards.items()},
            **{
                f"region:{region}:{hazard_id}": repr(law)
                for region, hazards in truth.regional_hazards.items()
                for hazard_id, law in hazards.items()
            },
        }),
        interaction_rules_hash=sha256(
            b"lottery-deterministic:rng-namespaced:ecology-v2:founder-rng-v2:hazard-ecology-v2:living-density-v1:hazard-patches-4x4-v1:physical-affordances-v1:decontamination-p2"
        ).hexdigest(),
        resolution_policy="lottery-deterministic",
        communication_physics="local-attenuated",
        lifecycle_contract_version=1,
        rng_scheme_version=2,
    )


@dataclass(frozen=True, slots=True)
class GenesisV1:
    ground_truth: GroundTruth
    constitution: WorldConstitution


def build_genesis_v1() -> GenesisV1:
    """Canonical Genesis-v1 (64x64, canonical terrarium)."""
    truth = build_ground_truth()
    return GenesisV1(ground_truth=truth, constitution=build_constitution(truth, dimensions=(WIDTH, HEIGHT)))


def build_genesis_smoke_v1() -> GenesisV1:
    """Genesis-Smoke-v1 (8x8, rapid verification terrarium with distinct fingerprint)."""
    truth = build_ground_truth()
    return GenesisV1(ground_truth=truth, constitution=build_constitution(truth, dimensions=(SMOKE_WIDTH, SMOKE_HEIGHT)))

