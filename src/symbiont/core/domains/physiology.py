"""Canonical physiology/homeostasis phase of one organism tick."""
from __future__ import annotations

from dataclasses import dataclass

from ...sensory import SensorySystem
from ..cognition.bridge import CognitiveBridge
from ..embodiment.degradation import DegradationQueue
from ..embodiment.development import DevelopmentalSnapshot, DevelopmentalTracker
from ..embodiment.homeostasis import HomeostaticController, HomeostaticSnapshot
from ..embodiment.metabolism import MetabolicLedger, MetabolicSnapshot
from ..embodiment.ontogeny import OntogenyController, OntogenySnapshot
from ..embodiment.physiology import LivingBodyState, PhysiologyController, PhysiologySnapshot
from ...host.adaptive import AdaptiveSenseModel


@dataclass(frozen=True, slots=True)
class PhysiologyServices:
    metabolism: MetabolicLedger
    homeostasis: HomeostaticController
    ontogeny: OntogenyController
    physiology: PhysiologyController
    developmental_tracker: DevelopmentalTracker
    living_body_state: LivingBodyState
    degradation: DegradationQueue
    sensory_system: SensorySystem
    adaptive_senses: AdaptiveSenseModel
    cognitive_bridge: CognitiveBridge | None


@dataclass(frozen=True, slots=True)
class PhysiologyStepResult:
    metabolism: MetabolicSnapshot
    homeostasis: HomeostaticSnapshot
    physiology: PhysiologySnapshot
    ontogeny: OntogenySnapshot
    development: DevelopmentalSnapshot
    repaired_amount: float
    resting_requested: bool
    resting_for_tick: bool


class PhysiologyDomain:
    """Advance constitutive organism physiology without action semantics."""

    @staticmethod
    def advance_body_age(living_body_state: LivingBodyState) -> None:
        """Advance body age only; Symbiont time remains a separate clock."""
        living_body_state.advance_age()

    def advance(
        self,
        *,
        services: PhysiologyServices,
        retained_memory_units: float,
        embodied_work: float,
        resting_requested: bool,
        degradation_excreted: int,
    ) -> PhysiologyStepResult:
        retained_units = max(0.0, float(retained_memory_units)) + max(
            0.0, float(embodied_work)
        )
        metabolism = services.metabolism.advance(retained_units=retained_units)
        repaired_amount = services.homeostasis.constitutive_step(
            services.metabolism,
            embodied_work=max(0.0, float(embodied_work)),
            resting=bool(resting_requested),
        )
        ontogeny = services.ontogeny.constitutive_step(
            services.metabolism,
            resting=bool(resting_requested),
        )
        metabolism = services.metabolism.finalize_cycle(metabolism)
        homeostasis = services.homeostasis.regulate(metabolism.pressure)

        next_resting = bool(resting_requested)
        if metabolism.pressure.value in {"severe", "unrecoverable"}:
            next_resting = True
        elif metabolism.pressure.value == "normal" and next_resting:
            next_resting = False

        resting_for_tick = next_resting
        physiology = services.physiology.advance(
            metabolism,
            tick=services.living_body_state.age_ticks,
            resting=(
                resting_for_tick
                or homeostasis.action.value in {"pause_plasticity", "safe_mode"}
            ),
        )
        topology = getattr(services.cognitive_bridge, "topology_health", None)
        topology_health = (
            getattr(topology, "value", str(topology))
            if topology is not None
            else (
                "developing"
                if services.cognitive_bridge is not None
                else "germinal"
            )
        )
        development = services.developmental_tracker.observe(
            state=physiology.state.value,
            integrity=services.homeostasis.integrity,
            topology_health=topology_health,
            sensory_count=(
                len(services.sensory_system.sensors)
                if services.sensory_system.plasticity_enabled
                else len(services.adaptive_senses.developed_percept_names())
            ),
            action_attempts=0,
            maintenance_ratio=min(
                1.0,
                metabolism.spent["maintenance"]
                / max(0.000001, metabolism.capacity["maintenance"]),
            ),
            retained_items=len(services.degradation.items),
            degradation_excreted=int(degradation_excreted),
            repaired=repaired_amount > 0.0,
            plasticity_enabled=homeostasis.plasticity_enabled,
        )
        return PhysiologyStepResult(
            metabolism=metabolism,
            homeostasis=homeostasis,
            physiology=physiology,
            ontogeny=ontogeny,
            development=development,
            repaired_amount=float(repaired_amount),
            resting_requested=next_resting,
            resting_for_tick=resting_for_tick,
        )
