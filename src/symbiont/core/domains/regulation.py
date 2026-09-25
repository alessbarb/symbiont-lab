"""Regulatory phenotype and delayed homeostatic credit."""
from __future__ import annotations

from dataclasses import dataclass

from ..cognition.bridge import CognitiveBridge
from ..embodiment.homeostasis import HomeostaticController
from ..embodiment.physiology import LivingBodyState


@dataclass(frozen=True, slots=True)
class RegulationServices:
    cognitive_bridge: CognitiveBridge | None
    homeostasis: HomeostaticController
    living_body_state: LivingBodyState


class RegulationDomain:
    """Own phenotype regulation and delayed intrinsic action credit."""

    def __init__(self) -> None:
        self.pending_homeostatic_action_credit: list[
            tuple[int, str, str, tuple[str, ...], float, float]
        ] = []

    def schedule_homeostatic_action_credit(
        self,
        *,
        cognitive_bridge: CognitiveBridge | None,
        family: str,
        action_id: str,
        concept_ids: tuple[str, ...],
        baseline_error: float,
        tick: int,
    ) -> None:
        if cognitive_bridge is None or not concept_ids:
            return
        for horizon, discount in (
            (4, 1.0),
            (16, 0.85),
            (64, 0.65),
            (256, 0.40),
        ):
            self.pending_homeostatic_action_credit.append(
                (
                    int(tick) + horizon,
                    family,
                    str(action_id),
                    tuple(sorted(set(concept_ids))),
                    float(baseline_error),
                    float(discount),
                )
            )
        if len(self.pending_homeostatic_action_credit) > 4096:
            self.pending_homeostatic_action_credit.sort(
                key=lambda item: item[0]
            )
            self.pending_homeostatic_action_credit = (
                self.pending_homeostatic_action_credit[:4096]
            )

    def resolve_homeostatic_action_credit(
        self,
        *,
        services: RegulationServices,
        tick: int,
    ) -> None:
        pending = self.pending_homeostatic_action_credit
        if not pending:
            return
        if not services.living_body_state.alive:
            pending.clear()
            return
        current_error = services.homeostasis.deviation()
        remaining: list[
            tuple[int, str, str, tuple[str, ...], float, float]
        ] = []
        for (
            due_tick,
            family,
            action_id,
            concept_ids,
            baseline_error,
            discount,
        ) in pending:
            if due_tick > tick:
                remaining.append(
                    (
                        due_tick,
                        family,
                        action_id,
                        concept_ids,
                        baseline_error,
                        discount,
                    )
                )
                continue
            if services.cognitive_bridge is None:
                continue
            intrinsic_value = max(
                -1.0,
                min(
                    1.0,
                    (baseline_error - current_error) * discount,
                ),
            )
            services.cognitive_bridge.observe_homeostatic_action_outcome(
                family=family,
                action_id=action_id,
                concept_ids=concept_ids,
                value=intrinsic_value,
                tick=tick,
            )
        self.pending_homeostatic_action_credit = remaining
