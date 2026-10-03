"""Bounded organism-visible accounting for computational metabolism.

The ledger is deliberately descriptive: it does not grant or revoke host
permissions.  It turns declared work costs into finite reserve pressure that
later physiology milestones can act on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .physiology import LivingBodyState


class ResourcePressure(StrEnum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    SEVERE = "severe"
    UNRECOVERABLE = "unrecoverable"


_KINDS = ("observation", "cognition", "persistence", "maintenance")


@dataclass(frozen=True, slots=True)
class MetabolicSnapshot:
    tick: int
    capacity: dict[str, float]
    reserve: dict[str, float]
    spent: dict[str, float]
    pressure: ResourcePressure


from .physiology_config import (
    DEFAULT_PHYSIOLOGY_CONFIG,
    PhysiologyConfig,
)


class MetabolicLedger:
    """Functional cost accounting backed by one physical body-energy pool.

    Per-kind balances are bounded accounting channels, not independent physical
    currencies. Every charge draws from LivingBodyState.energy_reserve and every
    external intake increases that pool exactly once. Per-kind replenishment may
    restore accounting headroom but can never mint physical energy.
    """

    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        capacity: dict[str, float] | None = None,
        replenishment: dict[str, float] | None = None,
        reserve: dict[str, float] | None = None,
        tick: int = 0,
        physiology_config: PhysiologyConfig | None = None,
        body_state: "LivingBodyState" | None = None,
    ) -> None:
        self._config = physiology_config or DEFAULT_PHYSIOLOGY_CONFIG
        owns_fresh_body_state = body_state is None
        if body_state is None:
            from .physiology import LivingBodyState

            body_state = LivingBodyState()
        self._body_state = body_state

        state_capacity = self._body_state.metabolic_capacity
        state_replenishment = self._body_state.metabolic_replenishment
        state_reserve = self._body_state.metabolic_reserve

        resolved_capacity = self._validate(
            capacity or state_capacity or {k: 1.0 for k in _KINDS},
            "capacity",
            positive=True,
        )
        resolved_replenishment = self._validate(
            replenishment or state_replenishment or resolved_capacity,
            "replenishment",
            positive=False,
        )
        initial = (
            resolved_capacity
            if reserve is None and not state_reserve
            else (state_reserve if reserve is None else reserve)
        )
        resolved_reserve = self._validate(
            initial,
            "reserve",
            positive=False,
            allow_negative=True,
        )
        resolved_reserve = {
            k: max(-resolved_capacity[k], min(resolved_capacity[k], resolved_reserve[k]))
            for k in _KINDS
        }

        if owns_fresh_body_state:
            physical_capacity = sum(resolved_capacity.values())
            physical_reserve = min(
                physical_capacity,
                sum(max(0.0, value) for value in resolved_reserve.values()),
            )
            self._body_state.max_energy = physical_capacity
            self._body_state.energy_reserve = physical_reserve

        if state_capacity and state_capacity != resolved_capacity:
            raise ValueError("living body metabolic capacity contradicts ledger")
        if state_replenishment and state_replenishment != resolved_replenishment:
            raise ValueError("living body replenishment contradicts ledger")
        if state_reserve and state_reserve != resolved_reserve:
            raise ValueError("living body reserve contradicts ledger")

        self._body_state.metabolic_capacity = resolved_capacity
        self._body_state.metabolic_replenishment = resolved_replenishment
        self._body_state.metabolic_reserve = resolved_reserve
        self._capacity = self._body_state.metabolic_capacity
        self._replenishment = self._body_state.metabolic_replenishment
        self._reserve = self._body_state.metabolic_reserve
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be non-negative")
        self._tick = tick
        self._spent = {k: 0.0 for k in _KINDS}

    @staticmethod
    def _validate(
        values: dict[str, float],
        label: str,
        *,
        positive: bool,
        allow_negative: bool = False,
    ) -> dict[str, float]:
        if set(values) != set(_KINDS):
            raise ValueError(f"{label} must define exactly {_KINDS}")
        if any(
            isinstance(values[k], bool) or not isinstance(values[k], (int, float)) for k in _KINDS
        ):
            raise ValueError(f"{label} values must be numeric")
        result = {k: float(values[k]) for k in _KINDS}
        if any(not math.isfinite(v) for v in result.values()):
            raise ValueError(f"{label} values must be finite")
        if positive:
            if any(v <= 0.0 for v in result.values()):
                raise ValueError(f"{label} values out of bounds")
        elif not allow_negative and any(v < 0.0 for v in result.values()):
            raise ValueError(f"{label} values out of bounds")
        return result

    @property
    def body_state(self) -> "LivingBodyState":
        return self._body_state

    def bind_body_state(self, body_state: "LivingBodyState") -> None:
        """Move persistent metabolic ownership to an existing canonical state."""
        if body_state is self._body_state:
            return
        if body_state.metabolic_capacity and body_state.metabolic_capacity != self._capacity:
            raise ValueError("living body metabolic capacity contradicts ledger")
        if (
            body_state.metabolic_replenishment
            and body_state.metabolic_replenishment != self._replenishment
        ):
            raise ValueError("living body replenishment contradicts ledger")
        if body_state.metabolic_reserve and body_state.metabolic_reserve != self._reserve:
            raise ValueError("living body reserve contradicts ledger")

        if (
            abs(body_state.energy_reserve - self._body_state.energy_reserve) > 1e-12
            or abs(body_state.max_energy - self._body_state.max_energy) > 1e-12
        ):
            raise ValueError(
                f"living body physical energy contradicts ledger: {body_state.energy_reserve} != {self._body_state.energy_reserve} or {body_state.max_energy} != {self._body_state.max_energy}"
            )
        body_state.metabolic_capacity = self._capacity
        body_state.metabolic_replenishment = self._replenishment
        body_state.metabolic_reserve = self._reserve
        self._body_state = body_state
        self._capacity = body_state.metabolic_capacity
        self._replenishment = body_state.metabolic_replenishment
        self._reserve = body_state.metabolic_reserve

    @property
    def tick(self) -> int:
        return self._tick

    def charge(self, kind: str, amount: float) -> None:
        if kind not in _KINDS:
            raise ValueError(f"unknown metabolic cost kind: {kind}")
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(amount)
        ):
            raise ValueError("metabolic charge must be finite")
        amount = float(amount)
        if amount < 0.0:
            raise ValueError("metabolic charge must be non-negative")
        self._spent[kind] = min(self._capacity[kind] * 2.0, self._spent[kind] + amount)
        self._reserve[kind] = max(-self._capacity[kind], self._reserve[kind] - amount)
        self._body_state.energy_reserve = max(
            0.0,
            self._body_state.energy_reserve - amount,
        )

    def _accept_physical_energy(self, amount: float) -> float:
        """Increase the one conserved body-energy pool and return accepted input."""
        headroom = max(
            0.0,
            self._body_state.max_energy - self._body_state.energy_reserve,
        )
        accepted = min(float(amount), headroom)
        self._body_state.energy_reserve += accepted
        return accepted

    def intake(self, kind: str, amount: float) -> float:
        """Accept external energy once and credit one accounting channel."""
        if kind not in _KINDS:
            raise ValueError(f"unknown metabolic resource kind: {kind}")
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(amount)
        ):
            raise ValueError("metabolic intake must be finite")
        amount = float(amount)
        if amount < 0.0:
            raise ValueError("metabolic intake must be non-negative")
        accepted = self._accept_physical_energy(amount)
        if accepted <= 0.0:
            return 0.0
        self._reserve[kind] = min(
            self._capacity[kind],
            self._reserve[kind] + accepted,
        )
        return accepted

    def intake_untyped(self, amount: float) -> float:
        """Accept anonymous physical input without making a compartment physical."""
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(amount)
        ):
            raise ValueError("metabolic intake must be finite")
        amount = float(amount)
        if amount < 0.0:
            raise ValueError("metabolic intake must be non-negative")
        accepted = self._accept_physical_energy(amount)
        if accepted <= 0.0:
            return 0.0

        deficits = {kind: max(0.0, self._capacity[kind] - self._reserve[kind]) for kind in _KINDS}
        total_deficit = sum(deficits.values())
        if total_deficit > 0.0:
            remaining = accepted
            ordered = tuple(sorted(_KINDS))
            for index, kind in enumerate(ordered):
                if index == len(ordered) - 1:
                    share = remaining
                else:
                    share = min(
                        remaining,
                        accepted * deficits[kind] / total_deficit,
                    )
                credit = min(share, deficits[kind])
                self._reserve[kind] += credit
                remaining -= credit
                if remaining <= 1e-15:
                    break
        return accepted

    def advance(self, *, retained_units: float = 0.0) -> MetabolicSnapshot:
        if (
            isinstance(retained_units, bool)
            or not isinstance(retained_units, (int, float))
            or not math.isfinite(retained_units)
            or retained_units < 0.0
        ):
            raise ValueError("retained_units must be finite and non-negative")
        for kind in _KINDS:
            self._reserve[kind] = min(
                self._capacity[kind], self._reserve[kind] + self._replenishment[kind]
            )
        self.charge("maintenance", retained_units)
        self._tick += 1
        snapshot = self.snapshot()
        self._spent = {k: 0.0 for k in _KINDS}
        return snapshot

    @property
    def physiology_config(self) -> PhysiologyConfig:
        return self._config

    def pressure(self) -> ResourcePressure:
        ratio = self._body_state.energy_reserve / max(
            self._body_state.max_energy,
            1e-12,
        )
        if ratio <= self._config.ratio_unrecoverable:
            return ResourcePressure.UNRECOVERABLE
        if ratio < self._config.ratio_severe:
            return ResourcePressure.SEVERE
        if ratio < self._config.ratio_elevated:
            return ResourcePressure.ELEVATED
        return ResourcePressure.NORMAL

    def snapshot(self) -> MetabolicSnapshot:
        return MetabolicSnapshot(
            self._tick,
            dict(self._capacity),
            dict(self._reserve),
            dict(self._spent),
            self.pressure(),
        )

    def finalize_cycle(self, base: MetabolicSnapshot) -> MetabolicSnapshot:
        """Merge post-advance physiological costs into one tick snapshot.

        advance() records costs known at the metabolic boundary and resets
        the per-tick accumulator. Constitutive physiology may then charge
        additional costs (for example tissue repair). This method folds those
        later costs into the same causal tick and clears them so they cannot
        leak into the following tick.
        """
        if not isinstance(base, MetabolicSnapshot) or base.tick != self._tick:
            raise ValueError("base metabolic snapshot must belong to current tick")
        current = self.snapshot()
        spent = {
            kind: min(
                current.capacity[kind] * 2.0,
                base.spent[kind] + current.spent[kind],
            )
            for kind in _KINDS
        }
        finalized = MetabolicSnapshot(
            tick=current.tick,
            capacity=current.capacity,
            reserve=current.reserve,
            spent=spent,
            pressure=current.pressure,
        )
        self._spent = {kind: 0.0 for kind in _KINDS}
        return finalized

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "tick": self._tick,
            "capacity": dict(self._capacity),
            "replenishment": dict(self._replenishment),
            "reserve": dict(self._reserve),
            "physical_energy_reserve": self._body_state.energy_reserve,
            "physical_energy_capacity": self._body_state.max_energy,
        }

    @classmethod
    def from_checkpoint(
        cls,
        payload: dict[str, Any],
        *,
        physiology_config: PhysiologyConfig | None = None,
        body_state: LivingBodyState | None = None,
    ) -> "MetabolicLedger":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid metabolic checkpoint")
        tick = payload.get("tick")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("invalid metabolic checkpoint tick")
        if body_state is None:
            from .physiology import LivingBodyState

            body_state = LivingBodyState(
                energy_reserve=float(payload["physical_energy_reserve"]),
                max_energy=float(payload["physical_energy_capacity"]),
            )
        else:
            if (
                abs(body_state.energy_reserve - float(payload["physical_energy_reserve"])) > 1e-12
                or abs(body_state.max_energy - float(payload["physical_energy_capacity"])) > 1e-12
            ):
                raise ValueError("living body physical energy contradicts ledger checkpoint")
        return cls(
            capacity=payload["capacity"],
            replenishment=payload["replenishment"],
            reserve=payload["reserve"],
            tick=tick,
            physiology_config=physiology_config,
            body_state=body_state,
        )


__all__ = ["MetabolicLedger", "MetabolicSnapshot", "ResourcePressure"]
