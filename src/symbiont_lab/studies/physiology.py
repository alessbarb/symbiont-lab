"""Deterministic, evaluator-only studies for Milestone I viability semantics."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.homeostasis import HomeostaticController
from symbiont.core.physiology import PhysiologyController, VitalState
from symbiont.core.runtime import OrganismRuntime


@dataclass(frozen=True, slots=True)
class PhysiologyStudy:
    ticks: int
    states: tuple[str, ...]
    transitions: int
    death_tick: int | None
    final_reserve: float
    dormant_ticks: int = 0
    replay_equal: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RuntimeRecoveryStudy:
    """Evaluator-only proof that recovery consumes explicit resources."""

    repaired: float
    integrity_after_repair: float
    maintenance_spent: float
    rest_checkpoint_equal: bool
    resumed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SustainedRecoveryStudy:
    """Evaluator-only deficit/recovery trajectory.

    The study deliberately drives only the declared maintenance supply.  It
    does not inject labels, observations or evaluator metrics into an
    organism.  A second run starts from the deficit checkpoint so replay can
    be compared with the original recovery path.
    """

    deficit_ticks: int
    recovery_ticks: int
    dormant_ticks: int
    recovered: bool
    recovery_tick: int | None
    no_intake_recovered: bool
    checkpoint_replay_equal: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SustainedRepairStudy:
    """Evaluator-only bounded repair trajectory with checkpoint replay."""

    requested_per_cycle: float
    cycles: int
    repaired_total: float
    final_integrity: float
    no_intake_repaired: float
    checkpoint_replay_equal: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_physiology_study(
    *,
    ticks: int = 32,
    maintenance_cost: float = 0.08,
    intake: Iterable[float] = (),
    resting: Iterable[bool] = (),
) -> PhysiologyStudy:
    """Run a bounded no-free-replenishment viability trajectory.

    ``intake`` is an explicit environmental supply per tick. The study never
    feeds evaluator truth back into the organism and is independent of host
    providers, making results reproducible and suitable for archive/replay.
    """
    if ticks < 1 or maintenance_cost < 0:
        raise ValueError("invalid physiology study parameters")
    schedule = tuple(float(value) for value in intake)
    resting_schedule = tuple(bool(value) for value in resting)
    if any(value < 0 for value in schedule):
        raise ValueError("intake values must be non-negative")
    kinds = ("observation", "cognition", "persistence", "maintenance")
    ledger = MetabolicLedger(replenishment={kind: 0.0 for kind in kinds})
    controller = PhysiologyController()
    states: list[str] = []
    for tick in range(ticks):
        if tick < len(schedule):
            ledger.intake("maintenance", schedule[tick])
        ledger.advance(retained_units=maintenance_cost)
        snapshot = controller.advance(ledger.snapshot(), tick=tick,
                                     resting=tick < len(resting_schedule) and resting_schedule[tick])
        states.append(snapshot.state.value)
        if snapshot.state is VitalState.DEAD:
            break
    snapshot = ledger.snapshot()
    physiology = controller.snapshot()
    return PhysiologyStudy(len(states), tuple(states), physiology.transitions,
                           physiology.death_tick, snapshot.reserve["maintenance"],
                           sum(state == VitalState.DORMANT.value for state in states))


def run_runtime_replay_study(*, warmup_ticks: int = 2, replay_ticks: int = 2) -> bool:
    """Verify runtime physiology/metabolism continuity across a checkpoint."""
    if warmup_ticks < 1 or replay_ticks < 1:
        raise ValueError("tick counts must be positive")
    runtime = OrganismRuntime(bootstrap_semantic_senses=False, discover_senses=False,
                              investigate_ticks=0, min_samples=1, explicit_metabolism=True)
    runtime.run(warmup_ticks)
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(), min_samples=1)
    left = [result.physiology for result in runtime.run(replay_ticks)]
    right = [result.physiology for result in restored.run(replay_ticks)]
    return left == right


def run_runtime_recovery_study() -> RuntimeRecoveryStudy:
    """Exercise explicit intake, repair, rest and checkpoint continuity.

    The study intentionally supplies maintenance through the runtime's local
    ledger rather than using evaluator truth to mutate cognition.  Repair is
    bounded by the controller and consumes exactly the accepted intake.
    """
    kinds = {kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    runtime = OrganismRuntime(
        explicit_metabolism=True,
        metabolism=MetabolicLedger(replenishment=kinds),
        homeostasis=HomeostaticController(integrity=0.5),
        bootstrap_semantic_senses=False,
        discover_senses=False,
        investigate_ticks=0,
    )
    runtime.metabolism.charge("maintenance", 0.5)
    before = runtime.metabolism.snapshot().reserve["maintenance"]
    runtime.metabolism.intake("maintenance", 0.25)
    repaired = runtime.repair(0.25)
    after = runtime.metabolism.snapshot()
    runtime.request_rest()
    checkpoint = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(
        checkpoint, bootstrap_semantic_senses=False, discover_senses=False, investigate_ticks=0
    )
    rest_equal = restored.resting_requested and restored.checkpoint()["resting_requested"] is True
    restored.resume_activity()
    return RuntimeRecoveryStudy(
        repaired=repaired,
        integrity_after_repair=runtime.homeostasis.integrity,
        maintenance_spent=before + 0.25 - after.reserve["maintenance"],
        rest_checkpoint_equal=rest_equal,
        resumed=not restored.resting_requested,
    )


def run_sustained_recovery_study(
    *,
    deficit_ticks: int = 3,
    deficit_cost: float = 0.3,
    recovery_ticks: int = 4,
    recovery_intake: float = 0.3,
) -> SustainedRecoveryStudy:
    """Prove that sustained recovery needs explicit intake.

    The trajectory enters dormancy under repeated maintenance deficit, then
    returns to ``active`` only after finite maintenance is supplied.  The
    no-intake control remains non-active, and the recovery phase is replayed
    from a checkpoint captured at the deficit boundary.
    """
    if deficit_ticks < 1 or recovery_ticks < 1:
        raise ValueError("tick counts must be positive")
    if deficit_cost <= 0.0 or recovery_intake < 0.0:
        raise ValueError("cost and intake must be non-negative, with positive cost")
    if deficit_cost * deficit_ticks >= 1.0:
        raise ValueError("deficit schedule must remain recoverable")

    zero_replenishment = {kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}

    ledger = MetabolicLedger(replenishment=zero_replenishment)
    controller = PhysiologyController()
    states: list[VitalState] = []
    for tick in range(deficit_ticks):
        ledger.advance(retained_units=deficit_cost)
        states.append(controller.advance(ledger.snapshot(), tick=tick, resting=True).state)
    checkpoint = (ledger.checkpoint(), controller.checkpoint())
    dormant_ticks = sum(state is VitalState.DORMANT for state in states)

    def recover(
        current_ledger: MetabolicLedger,
        current_controller: PhysiologyController,
        *,
        supply: float,
    ) -> tuple[list[VitalState], float]:
        recovery_states: list[VitalState] = []
        for offset in range(recovery_ticks):
            current_ledger.intake("maintenance", supply)
            current_ledger.advance()
            recovery_states.append(
                current_controller.advance(
                    current_ledger.snapshot(), tick=deficit_ticks + offset, resting=False
                ).state
            )
        return recovery_states, current_ledger.snapshot().reserve["maintenance"]

    recovered_states, recovered_reserve = recover(ledger, controller, supply=recovery_intake)
    recovered = VitalState.ACTIVE in recovered_states
    recovery_tick = next(
        (deficit_ticks + index + 1 for index, state in enumerate(recovered_states)
         if state is VitalState.ACTIVE),
        None,
    )

    no_intake_ledger = MetabolicLedger.from_checkpoint(checkpoint[0])
    no_intake_controller = PhysiologyController.from_checkpoint(checkpoint[1])
    no_intake_states, _ = recover(no_intake_ledger, no_intake_controller, supply=0.0)
    no_intake_recovered = VitalState.ACTIVE in no_intake_states

    replay_ledger = MetabolicLedger.from_checkpoint(checkpoint[0])
    replay_controller = PhysiologyController.from_checkpoint(checkpoint[1])
    replay_states, replay_reserve = recover(replay_ledger, replay_controller, supply=recovery_intake)
    checkpoint_replay_equal = (
        replay_states == recovered_states
        and replay_reserve == recovered_reserve
        and replay_controller.checkpoint() == controller.checkpoint()
    )
    return SustainedRecoveryStudy(
        deficit_ticks=deficit_ticks,
        recovery_ticks=recovery_ticks,
        dormant_ticks=dormant_ticks,
        recovered=recovered,
        recovery_tick=recovery_tick,
        no_intake_recovered=no_intake_recovered,
        checkpoint_replay_equal=checkpoint_replay_equal,
    )


def run_sustained_repair_study(*, cycles: int = 4, requested_per_cycle: float = 0.2) -> SustainedRepairStudy:
    """Verify repeated repair is resource-bounded and replayable."""
    if cycles < 2 or not 0.0 < requested_per_cycle <= 1.0:
        raise ValueError("cycles must be at least 2 and requested_per_cycle must be in (0, 1]")
    zero = {kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}

    def build() -> OrganismRuntime:
        return OrganismRuntime(
            explicit_metabolism=True,
            metabolism=MetabolicLedger(replenishment=zero, reserve=zero),
            homeostasis=HomeostaticController(integrity=0.4),
            bootstrap_semantic_senses=False,
            discover_senses=False,
            investigate_ticks=0,
        )

    runtime = build()
    midpoint = cycles // 2
    repairs: list[float] = []
    checkpoint: dict[str, object] | None = None
    for cycle in range(cycles):
        runtime.metabolism.intake("maintenance", requested_per_cycle)
        repairs.append(runtime.repair(requested_per_cycle))
        if cycle + 1 == midpoint:
            checkpoint = runtime.checkpoint()
    if checkpoint is None:
        raise AssertionError("repair study did not create a checkpoint")

    no_intake = build().repair(requested_per_cycle)
    replay = OrganismRuntime.from_checkpoint(
        checkpoint, bootstrap_semantic_senses=False, discover_senses=False, investigate_ticks=0
    )
    replay_repairs: list[float] = []
    for _ in range(midpoint, cycles):
        replay.metabolism.intake("maintenance", requested_per_cycle)
        replay_repairs.append(replay.repair(requested_per_cycle))
    checkpoint_replay_equal = (
        tuple(repairs[midpoint:]) == tuple(replay_repairs)
        and runtime.homeostasis.checkpoint() == replay.homeostasis.checkpoint()
        and runtime.metabolism.checkpoint() == replay.metabolism.checkpoint()
    )
    return SustainedRepairStudy(
        requested_per_cycle=requested_per_cycle,
        cycles=cycles,
        repaired_total=sum(repairs),
        final_integrity=runtime.homeostasis.integrity,
        no_intake_repaired=no_intake,
        checkpoint_replay_equal=checkpoint_replay_equal,
    )


__all__ = [
    "PhysiologyStudy", "RuntimeRecoveryStudy", "SustainedRecoveryStudy", "SustainedRepairStudy",
    "run_physiology_study", "run_runtime_replay_study", "run_runtime_recovery_study",
    "run_sustained_recovery_study", "run_sustained_repair_study",
]
