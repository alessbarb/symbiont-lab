"""Deterministic opaque causal body for Agency Acquisition v1 studies.

The body is apparatus, not organism knowledge.  Its ground truth — which
opaque output drives which opaque receptor, and under which experimental
condition — stays evaluator-side and is never handed to the organism.  The
organism only receives opaque receptor readings through the normal host
reading boundary and emits opaque actuations through its ActionDomain.

Receptors:

* one driven receptor per functional actuator (under NORMAL, actuator ``i``
  drives receptor ``i``; PERMUTED rotates the mapping; BROKEN_EFFECTOR removes
  the first actuator's physical effect);
* optional inert actuators: legal outputs with no physical consequence, so a
  dimension grounded only in them is a false-positive dimension;
* one distractor receptor that jumps on an evaluator-seeded schedule with no
  dependence on action, so the organism meets effects that also occur
  without its intervention (counterfactual windows);
* optionally (high-dimensional bodies, E8) several correlated receptors per
  actuator with decreasing gain, and receptors that drift on their own like
  posture or balance signals in a physical body.  The defaults (one receptor
  per actuator, no drift) reproduce the original body exactly.

All readings relax toward a neutral level, so a consequence exists only while
the body is actually driven.
"""

from __future__ import annotations

import hashlib
import random
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
from symbiont.core.organism_profile import HISTORICAL_V0
from symbiont.host.contracts import AccessMode, Capability, CapabilityKind, CapabilityScope
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

_NEUTRAL = 0.5
_RELAXATION = 0.2
_GAIN = 0.5
_DISTRACTOR_RATE = 0.3
_DRIFT_STEP = 0.06
_CORRELATED_GAIN_DECAY = 0.25


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
        inert_actuator_count: int = 0,
        receptors_per_actuator: int = 1,
        drifting_receptor_count: int = 0,
        actuator_mapping: tuple[int, ...] | None = None,
    ) -> None:
        if actuator_count < 1:
            raise ValueError("a causal body needs at least one actuator")
        if inert_actuator_count < 0:
            raise ValueError("inert_actuator_count must be non-negative")
        if not 1 <= receptors_per_actuator <= 4:
            raise ValueError("receptors_per_actuator must be within [1, 4]")
        if drifting_receptor_count < 0:
            raise ValueError("drifting_receptor_count must be non-negative")
        if actuator_mapping is not None:
            # Which receptor group each functional actuator drives, independent
            # of the construction seed: two bodies with the same seed and shape
            # share every identifier and differ only in this bijection.
            if sorted(actuator_mapping) != list(range(int(actuator_count))):
                raise ValueError(
                    "actuator_mapping must be a permutation of the functional actuators"
                )
            if BodyCondition(condition) is BodyCondition.PERMUTED:
                raise ValueError("actuator_mapping cannot be combined with the PERMUTED condition")
        self.actuator_mapping = None if actuator_mapping is None else tuple(actuator_mapping)
        self.receptors_per_actuator = int(receptors_per_actuator)
        self.drifting_count = int(drifting_receptor_count)
        self.seed = int(seed)
        self.functional_count = int(actuator_count)
        total = int(actuator_count) + int(inert_actuator_count)
        self.surface: ActuatorSurface = derive_actuator_constitution(
            total,
            physical_contract=f"agency-acquisition-body:{actuator_count}:{inert_actuator_count}",
        )
        # Driven receptors first, then drifting ones, then the distractor
        # last: with the defaults the ids are exactly the original body's.
        driven = actuator_count * self.receptors_per_actuator
        self.receptor_ids = tuple(
            _opaque_receptor_id(self.seed, index)
            for index in range(driven + self.drifting_count + 1)
        )
        self._drifting_ids = self.receptor_ids[driven : driven + self.drifting_count]
        self._values = {receptor_id: _NEUTRAL for receptor_id in self.receptor_ids}
        self._rng = random.Random(f"agency-acquisition-distractor:{self.seed}")
        self._drift_rng = random.Random(f"agency-acquisition-drift:{self.seed}")
        self.condition = BodyCondition(condition)
        # Apparatus time: one physical step = 100 ms.  Wall-clock time would
        # leak host timing into perception and break matched twins.
        self._steps = 0

    # -- evaluator-side ground truth -----------------------------------------
    @property
    def distractor_receptor_id(self) -> str:
        return self.receptor_ids[-1]

    def driven_receptors(self, actuator_id: str) -> tuple[str, ...]:
        """Receptors an output drives, strongest first (evaluator-only)."""
        index = self.surface.actuator_ids.index(actuator_id)
        count = self.functional_count
        if index >= count:
            return ()  # inert output: legal, but physically inconsequential
        if self.condition is BodyCondition.BROKEN_EFFECTOR and index == 0:
            return ()
        if self.condition is BodyCondition.PERMUTED:
            index = (index + 1) % count
        elif self.actuator_mapping is not None:
            index = self.actuator_mapping[index]
        k = self.receptors_per_actuator
        return self.receptor_ids[index * k : index * k + k]

    def driven_receptor(self, actuator_id: str) -> str | None:
        """The primary (strongest) receptor an output drives."""
        receptors = self.driven_receptors(actuator_id)
        return receptors[0] if receptors else None

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
        if self.actuator_mapping is not None and BodyCondition(condition) is BodyCondition.PERMUTED:
            raise ValueError("actuator_mapping cannot be combined with the PERMUTED condition")
        self.condition = BodyCondition(condition)

    # -- physics ---------------------------------------------------------------
    def advance(self, actuations: Iterable[Actuation]) -> None:
        self._steps += 1
        drive = {receptor_id: 0.0 for receptor_id in self.receptor_ids}
        for actuation in actuations:
            for rank, receptor_id in enumerate(self.driven_receptors(actuation.actuator_id)):
                gain = _GAIN * (1.0 - _CORRELATED_GAIN_DECAY * rank)
                drive[receptor_id] += gain * float(actuation.delivered)
        for receptor_id in self._drifting_ids:
            drive[receptor_id] += self._drift_rng.gauss(0.0, _DRIFT_STEP)
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
        now = self._steps * 100_000_000
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


class ApparatusClock:
    """Deterministic sampling clock for the host boundary.

    Real wall-clock sampling cost would otherwise leak into the organism's
    self-model and make runs and matched twins irreproducible.  Every call
    advances by one fixed quantum, so identical histories see identical costs.
    """

    def __init__(self, quantum_s: float = 1e-4) -> None:
        self._quantum = float(quantum_s)
        self._calls = 0

    def __call__(self) -> float:
        self._calls += 1
        return self._calls * self._quantum


def subject_lifecycle(body: "CausalBody") -> HostLifecycle:
    return HostLifecycle(
        discovery=HostDiscovery(providers=(body,)),
        reading_providers=(body,),
        clock=ApparatusClock(),
    )


def build_subject(
    body: CausalBody,
    *,
    organism_id: str,
    runtime_class: type[OrganismRuntime] = OrganismRuntime,
    living_body_state: LivingBodyState | None = None,
    **runtime_options: Any,
) -> OrganismRuntime:
    """A newborn canonical runtime embodied in ``body`` (no semantic senses)."""
    limits = KernelLimits()
    genome, graph = load_base_cognition(kernel_limits=limits, running_version=(0, 80, 0))
    # Closed experiments ran this subject on the historical profile (ADR-0062);
    # a study on the canonical organism passes ``profile`` explicitly.
    runtime_options.setdefault("profile", HISTORICAL_V0)
    return runtime_class(
        organism_id=organism_id,
        host_lifecycle=subject_lifecycle(body),
        host_reading_providers=(body,),
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
        living_body_state=(
            living_body_state
            if living_body_state is not None
            else LivingBodyState(energy_reserve=1e6, max_energy=1e6)
        ),
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
    "ApparatusClock",
    "BodyGroundTruth",
    "CausalBody",
    "build_subject",
    "run_ticks",
    "subject_lifecycle",
]
