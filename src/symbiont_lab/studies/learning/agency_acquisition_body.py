"""Deterministic opaque causal body for Agency Acquisition v1 studies.

The body is apparatus, not organism knowledge.  Its ground truth — which
opaque output drives which opaque receptor, and under which experimental
condition — stays evaluator-side and is never handed to the organism.  The
organism only receives opaque receptor readings through the normal host
reading boundary and emits opaque actuations through its ActionDomain.

Receptors:

* one driven receptor per actuator (under NORMAL, actuator ``i`` drives
  receptor ``i``; PERMUTED rotates the mapping; BROKEN_EFFECTOR removes the
  first actuator's physical effect);
* one distractor receptor that jumps on an evaluator-seeded schedule with no
  dependence on action, so the organism meets effects that also occur
  without its intervention (counterfactual windows).

All readings relax toward a neutral level, so a consequence exists only while
the body is actually driven.
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable

from symbiont.actuation.sensorimotor import CompetenceDevelopmentEngine
from symbiont.actuation.surface import ActuatorSurface, derive_actuator_constitution
from symbiont.actuation.types import Actuation
from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.limits import KernelLimits
from symbiont.core.embodiment.physiology import LivingBodyState
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.contracts import AccessMode, Capability, CapabilityKind, CapabilityScope
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

_NEUTRAL = 0.5
_RELAXATION = 0.2
_GAIN = 0.5
_DISTRACTOR_RATE = 0.3


class BodyCondition(StrEnum):
    NORMAL = "normal"
    PERMUTED = "permuted"
    BROKEN_EFFECTOR = "broken_effector"


def _opaque_receptor_id(seed: int, index: int) -> str:
    digest = hashlib.sha256(f"agency-acquisition-receptor:{seed}:{index}".encode()).hexdigest()
    return f"signal.{digest[:24]}"


@dataclass(frozen=True, slots=True)
class BodyGroundTruth:
    """Evaluator-only description of the current physical mapping."""

    condition: BodyCondition
    driven_receptor_by_actuator: tuple[tuple[str, str | None], ...]
    distractor_receptor_id: str


class CausalBody:
    """Opaque synthetic body implementing the host discovery/reading boundary."""

    provider_id = "agency-acquisition-body"

    def __init__(
        self,
        *,
        actuator_count: int,
        seed: int,
        condition: BodyCondition = BodyCondition.NORMAL,
    ) -> None:
        if actuator_count < 1:
            raise ValueError("a causal body needs at least one actuator")
        self.seed = int(seed)
        self.surface: ActuatorSurface = derive_actuator_constitution(
            actuator_count, physical_contract=f"agency-acquisition-body:{actuator_count}"
        )
        self.receptor_ids = tuple(
            _opaque_receptor_id(self.seed, index) for index in range(actuator_count + 1)
        )
        self._values = {receptor_id: _NEUTRAL for receptor_id in self.receptor_ids}
        self._rng = random.Random(f"agency-acquisition-distractor:{self.seed}")
        self.condition = BodyCondition(condition)

    # -- evaluator-side ground truth -----------------------------------------
    @property
    def distractor_receptor_id(self) -> str:
        return self.receptor_ids[-1]

    def driven_receptor(self, actuator_id: str) -> str | None:
        index = self.surface.actuator_ids.index(actuator_id)
        count = len(self.surface.actuator_ids)
        if self.condition is BodyCondition.BROKEN_EFFECTOR and index == 0:
            return None
        if self.condition is BodyCondition.PERMUTED:
            index = (index + 1) % count
        return self.receptor_ids[index]

    def ground_truth(self) -> BodyGroundTruth:
        return BodyGroundTruth(
            condition=self.condition,
            driven_receptor_by_actuator=tuple(
                (actuator_id, self.driven_receptor(actuator_id))
                for actuator_id in self.surface.actuator_ids
            ),
            distractor_receptor_id=self.distractor_receptor_id,
        )

    def set_condition(self, condition: BodyCondition) -> None:
        self.condition = BodyCondition(condition)

    # -- physics ---------------------------------------------------------------
    def advance(self, actuations: Iterable[Actuation]) -> None:
        drive = {receptor_id: 0.0 for receptor_id in self.receptor_ids}
        for actuation in actuations:
            receptor_id = self.driven_receptor(actuation.actuator_id)
            if receptor_id is not None:
                drive[receptor_id] += _GAIN * float(actuation.delivered)
        for receptor_id in self.receptor_ids[:-1]:
            value = self._values[receptor_id]
            value += drive[receptor_id] - _RELAXATION * (value - _NEUTRAL)
            self._values[receptor_id] = max(0.0, min(1.0, value))
        distractor = self.distractor_receptor_id
        if self._rng.random() < _DISTRACTOR_RATE:
            self._values[distractor] = max(0.0, min(1.0, self._values[distractor] + 0.4))
        else:
            value = self._values[distractor]
            self._values[distractor] = value - _RELAXATION * (value - _NEUTRAL)

    # -- host boundary ---------------------------------------------------------
    def discover(self) -> tuple[Capability, ...]:
        return tuple(
            Capability(
                capability_id=receptor_id,
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                access=AccessMode.READ_ONLY,
                scope=CapabilityScope.LOCAL,
            )
            for receptor_id in self.receptor_ids
        )

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        now = time.monotonic_ns()
        return tuple(
            SensorReading(
                capability_id=capability.capability_id,
                source=self.provider_id,
                value=float(self._values[capability.capability_id]),
                unit=Unit.RATIO,
                monotonic_timestamp_ns=now,
                quality=ReadingQuality.NOMINAL,
                privacy_class=ReadingPrivacyClass.NON_IDENTIFYING,
            )
            for capability in capabilities
            if capability.capability_id in self._values
        )


def build_subject(
    body: CausalBody,
    *,
    organism_id: str,
    runtime_class: type[OrganismRuntime] = OrganismRuntime,
    **runtime_options: Any,
) -> OrganismRuntime:
    """A newborn canonical runtime embodied in ``body`` (no semantic senses)."""
    limits = KernelLimits()
    genome, graph = load_base_cognition(kernel_limits=limits, running_version=(0, 80, 0))
    return runtime_class(
        organism_id=organism_id,
        host_lifecycle=HostLifecycle(
            discovery=HostDiscovery(providers=(body,)),
            reading_providers=(body,),
        ),
        host_reading_providers=(body,),
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
        living_body_state=LivingBodyState(energy_reserve=1e6, max_energy=1e6),
        actuation_enabled=True,
        actuator_constitution=body.surface,
        competence_development=CompetenceDevelopmentEngine(
            body.surface.actuator_ids,
            organism_id=organism_id,
            max_concurrent=None,
            embodiment_fingerprint=body.surface.contract_fingerprint,
        ),
        bootstrap_semantic_senses=False,
        discover_senses=True,
        min_samples=1,
        interoception_mode="absent",
        **runtime_options,
    )


def run_ticks(runtime: OrganismRuntime, body: CausalBody, ticks: int) -> None:
    """Advance organism and body in lockstep: body consequences arrive next tick."""
    for _ in range(int(ticks)):
        runtime.tick()
        body.advance(runtime.last_actuations)


__all__ = [
    "BodyCondition",
    "BodyGroundTruth",
    "CausalBody",
    "build_subject",
    "run_ticks",
]
