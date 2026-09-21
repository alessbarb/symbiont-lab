"""Constitutive physical ontogeny for the canonical Living Body.

Ontogeny is body physiology. It never inspects cognition, learned topology,
sensor count, action experience, evaluator scores, or World semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .metabolism import MetabolicLedger
from .physiology import LivingBodyState, VitalState
from .physiology_config import PhysiologyConfig


class PhysicalLifeStage(StrEnum):
    GROWING = "growing"
    MATURE = "mature"
    SENESCENT = "senescent"
    DEAD = "dead"


@dataclass(frozen=True, slots=True)
class OntogenySnapshot:
    stage: PhysicalLifeStage
    growth_progress: float
    senescence: float
    growth_energy_cost: float
    senescence_wear: float
    reproductively_ready: bool
    reproduction_energy: float


class OntogenyController:
    """Stateless transformer over one canonical LivingBodyState."""

    def __init__(self, *, config: PhysiologyConfig, body_state: LivingBodyState) -> None:
        self._config = config
        self._body_state = body_state

    @property
    def body_state(self) -> LivingBodyState:
        return self._body_state

    @property
    def config(self) -> PhysiologyConfig:
        return self._config

    def stage(self) -> PhysicalLifeStage:
        if not self._body_state.alive:
            return PhysicalLifeStage.DEAD
        if self._body_state.growth_progress < 1.0:
            return PhysicalLifeStage.GROWING
        if self._body_state.senescence > 0.0:
            return PhysicalLifeStage.SENESCENT
        return PhysicalLifeStage.MATURE

    def reproduction_energy(self) -> float:
        return self._body_state.max_energy * self._config.reproduction_energy_fraction

    def reproductively_ready(self) -> bool:
        body = self._body_state
        return (
            body.alive
            and body.vital_state not in {VitalState.AGONIZING, VitalState.DORMANT}
            and body.growth_progress >= 1.0
            and body.senescence <= self._config.reproduction_max_senescence
            and body.structural_integrity >= self._config.reproduction_min_integrity
            and body.energy_reserve + 1e-12 >= self.reproduction_energy()
        )

    def constitutive_step(self, metabolism: MetabolicLedger) -> OntogenySnapshot:
        body = self._body_state
        growth_cost = 0.0
        senescence_wear = 0.0

        if body.alive and body.growth_progress < 1.0:
            requested_progress = min(
                self._config.growth_rate_per_tick,
                1.0 - body.growth_progress,
            )
            energy_per_progress = (
                self._config.growth_energy_fraction_per_progress
                * body.max_energy
            )
            requested_cost = requested_progress * energy_per_progress
            affordable_cost = min(requested_cost, body.energy_reserve)
            if affordable_cost > 0.0:
                metabolism.charge("maintenance", affordable_cost)
                growth_cost = affordable_cost
                body.growth_progress = min(
                    1.0,
                    body.growth_progress
                    + affordable_cost / energy_per_progress,
                )

        if (
            body.alive
            and body.growth_progress >= 1.0
            and body.age_ticks >= self._config.senescence_start_ticks
        ):
            body.senescence = min(
                1.0,
                body.senescence + self._config.senescence_rate_per_tick,
            )
            senescence_wear = body.senescence * self._config.senescence_wear_rate
            if senescence_wear > 0.0:
                body.apply_wear(senescence_wear)

        return self.snapshot(
            growth_energy_cost=growth_cost,
            senescence_wear=senescence_wear,
        )

    def snapshot(
        self,
        *,
        growth_energy_cost: float = 0.0,
        senescence_wear: float = 0.0,
    ) -> OntogenySnapshot:
        return OntogenySnapshot(
            stage=self.stage(),
            growth_progress=self._body_state.growth_progress,
            senescence=self._body_state.senescence,
            growth_energy_cost=float(growth_energy_cost),
            senescence_wear=float(senescence_wear),
            reproductively_ready=self.reproductively_ready(),
            reproduction_energy=self.reproduction_energy(),
        )


__all__ = ["OntogenyController", "OntogenySnapshot", "PhysicalLifeStage"]
