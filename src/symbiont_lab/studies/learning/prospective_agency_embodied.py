"""Matched-checkpoint Physics3D study for L8 Prospective Agency.

The subject develops normally, including autonomous Private SLM training. The
laboratory waits until the organism itself performs a prospective selection.
Only then are matched continuations created from the same organism checkpoint
and the same physical checkpoint.

Ablations are evaluator-side manipulations of experimental twins. They never
enter the canonical organism implementation or the developmental warmup.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import MethodType
from typing import Any, Iterable

from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime
from symbiont_lab.physics3d.slm import Physics3DSlmManager


_CONDITIONS = (
    "full",
    "no_counterfactual",
    "shuffled_model",
    "shuffled_value",
    "babbling_only",
)


@dataclass(frozen=True, slots=True)
class ProspectiveEmbodiedCondition:
    condition: str
    applicable: bool
    ticks_completed: int
    alive: bool
    start_homeostatic_deviation: float
    end_homeostatic_deviation: float
    homeostatic_change: float
    reserve_change: float
    displacement_delta: float
    resource_progress_delta: float
    absorbed_energy: float
    prospective_selected_ticks: int
    primitive_prospective_ticks: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProspectiveEmbodiedTrial:
    seed: int
    warmup_ticks_requested: int
    readiness_found: bool
    readiness_tick: int | None
    readiness_reason: str
    final_tick: int
    first_cognitive_primitive_tick: int | None
    first_primitive_readout_tick: int | None
    active_model_id: str | None
    motor_primitives: int
    cognitive_primitives: int
    primitive_readout_nodes: int
    known_outcome_values: int
    primitive_candidates: int
    recurrent_primitive_candidates: int
    max_primitive_samples: int
    sample_gate_candidates: int
    controllability_gate_candidates: int
    variance_gate_candidates: int
    direction_gate_candidates: int
    full_competence_gate_candidates: int
    best_candidate_controllability: float
    best_candidate_directional_consistency: float
    lowest_recurrent_effect_variance: float | None
    cognitive_concepts: int
    cognitive_readouts: int
    structural_candidates: int
    structural_producers: int
    oldest_structural_wait_ticks: int
    peak_structural_candidates: int
    peak_structural_wait_ticks: int
    cognitive_primitive_ticks: int
    primitive_readout_ticks: int
    cognitive_without_readout_ticks: int
    cognitive_primitive_set_changes: int
    primitive_readout_set_changes: int
    unique_cognitive_primitive_ids: tuple[str, ...]
    unique_primitive_readout_ids: tuple[str, ...]
    final_cognitive_primitive_ids: tuple[str, ...]
    final_primitive_readout_ids: tuple[str, ...]
    conditions: tuple[ProspectiveEmbodiedCondition, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProspectiveEmbodiedStudy:
    seeds: tuple[int, ...]
    warmup_ticks: int
    horizon_ticks: int
    trials: tuple[ProspectiveEmbodiedTrial, ...]

    @property
    def testable_trials(self) -> int:
        return sum(trial.readiness_found for trial in self.trials)

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["testable_trials"] = self.testable_trials
        return payload


def _value_entry_count(runtime) -> int:
    agency = getattr(runtime.organism, "_prospective_agency", None)
    if agency is None:
        return 0
    return int(agency.outcome_value_ledger.known_outcome_count)


def _attach_existing_model(runtime: PyBulletEmbodimentRuntime, models_dir: Path) -> None:
    manager = Physics3DSlmManager(
        models_dir=models_dir,
        train_interval=1_000_000,
        device="cpu",
    )
    try:
        manager.attach_existing(runtime.organism)
        if (
            runtime.organism.model_registry.active is not None
            and getattr(runtime.organism, "_private_model_bridge", None) is None
        ):
            raise RuntimeError("active private model could not be attached to matched twin")
    finally:
        manager.close()


def _disable_counterfactual(runtime: PyBulletEmbodimentRuntime) -> None:
    runtime.organism._prospective_agency = None


def _shuffle_private_model_action_identity(runtime: PyBulletEmbodimentRuntime) -> bool:
    learner = getattr(runtime.organism, "_sensorimotor_learner", None)
    if learner is None:
        return False
    action_ids = tuple(sorted(learner.available_cognitive_primitive_ids()))
    if len(action_ids) < 2:
        return False

    mapping = {
        action_id: action_ids[(index + 1) % len(action_ids)]
        for index, action_id in enumerate(action_ids)
    }
    original = runtime.organism.predict_primitive_outcome

    def shuffled(self, primitive_id: str, context_tokens: tuple[str, ...]):
        mapped = mapping.get(primitive_id, primitive_id)
        return original(mapped, context_tokens)

    runtime.organism.predict_primitive_outcome = MethodType(
        shuffled,
        runtime.organism,
    )
    return True


def _shuffle_outcome_value_identity(runtime: PyBulletEmbodimentRuntime) -> bool:
    agency = getattr(runtime.organism, "_prospective_agency", None)
    if agency is None:
        return False
    ledger = agency.outcome_value_ledger
    stats = getattr(ledger, "_stats", None)
    if not isinstance(stats, dict) or len(stats) < 2:
        return False

    keys = sorted(stats)
    copied = [deepcopy(stats[key]) for key in keys]
    rotated = copied[1:] + copied[:1]
    ledger._stats = {
        key: stat
        for key, stat in zip(keys, rotated, strict=True)
    }
    return True


def _freeze_outcome_value_learning(runtime: PyBulletEmbodimentRuntime) -> None:
    runtime.organism._pending_outcome_value_credit = []

    def no_schedule(self, episode, *, baseline_deviation: float, tick: int) -> None:
        return None

    runtime.organism._schedule_observed_outcome_value_credit = MethodType(
        no_schedule,
        runtime.organism,
    )


def _apply_condition(
    runtime: PyBulletEmbodimentRuntime,
    condition: str,
) -> bool:
    if condition == "full":
        _freeze_outcome_value_learning(runtime)
        return True
    if condition == "no_counterfactual":
        _disable_counterfactual(runtime)
        return True
    if condition == "shuffled_model":
        applicable = _shuffle_private_model_action_identity(runtime)
        _freeze_outcome_value_learning(runtime)
        return applicable
    if condition == "shuffled_value":
        applicable = _shuffle_outcome_value_identity(runtime)
        _freeze_outcome_value_learning(runtime)
        return applicable
    if condition == "babbling_only":
        _disable_counterfactual(runtime)
        # This is an intentionally strong baseline. Removing the graph from the
        # matched experimental twin prevents direct cognitive/readout motor use
        # while leaving sensorimotor babbling and body mechanics intact.
        runtime.organism._cognitive_bridge = None
        return True
    raise ValueError(f"unsupported prospective condition: {condition}")


def _run_condition(
    *,
    condition: str,
    seed: int,
    runtime_checkpoint: dict[str, Any],
    physical_state: dict[str, object],
    models_dir: Path,
    horizon_ticks: int,
    physics_substeps_per_tick: int,
    start_displacement: float,
    start_progress: float,
) -> ProspectiveEmbodiedCondition:
    with PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        runtime_checkpoint=deepcopy(runtime_checkpoint),
        physical_state=deepcopy(physical_state),
        physics_substeps_per_tick=physics_substeps_per_tick,
    ) as runtime:
        _attach_existing_model(runtime, models_dir)
        applicable = _apply_condition(runtime, condition)

        start_deviation = float(runtime.organism.homeostatic_deviation)
        start_reserve = (
            runtime.organism.living_body_state.energy_reserve
            / max(1e-12, runtime.organism.living_body_state.max_energy)
        )

        last = None
        completed = 0
        selected_ticks = 0
        prospective_motor_ticks = 0
        absorbed_total = 0.0
        for _ in range(horizon_ticks):
            last = runtime.step()
            completed += 1
            absorbed_total += max(0.0, float(last.absorbed_energy))
            selected_ticks += int(last.prospective_selected)
            prospective_motor_ticks += int(
                last.motor_origin_detail == "primitive_prospective"
            )
            if not last.alive:
                break

        if last is None:
            raise RuntimeError("prospective embodied clone produced no ticks")

        end_deviation = float(runtime.organism.homeostatic_deviation)
        end_reserve = float(last.metabolic_reserve_ratio)
        return ProspectiveEmbodiedCondition(
            condition=condition,
            applicable=applicable,
            ticks_completed=completed,
            alive=last.alive,
            start_homeostatic_deviation=start_deviation,
            end_homeostatic_deviation=end_deviation,
            homeostatic_change=end_deviation - start_deviation,
            reserve_change=end_reserve - start_reserve,
            displacement_delta=last.displacement_from_origin - start_displacement,
            resource_progress_delta=last.resource_progress - start_progress,
            absorbed_energy=float(absorbed_total),
            prospective_selected_ticks=selected_ticks,
            primitive_prospective_ticks=prospective_motor_ticks,
        )


def run_prospective_embodied_trial(
    seed: int,
    *,
    warmup_ticks: int = 5000,
    horizon_ticks: int = 256,
    physics_substeps_per_tick: int = 10,
) -> ProspectiveEmbodiedTrial:
    """Develop one subject to natural L8 use, then run matched continuations."""
    if warmup_ticks < 1 or horizon_ticks < 1:
        raise ValueError("warmup_ticks and horizon_ticks must be positive")

    with TemporaryDirectory(prefix=f"symbiont-l8-{seed}-") as temporary:
        models_dir = Path(temporary) / "models"
        checkpoint: dict[str, Any] | None = None
        physical_state: dict[str, object] | None = None
        readiness_tick: int | None = None
        readiness_reason = "no_prospective_selection"
        final_tick = 0
        first_cognitive_primitive_tick: int | None = None
        first_primitive_readout_tick: int | None = None
        active_model_id: str | None = None
        motor_primitives = 0
        cognitive_primitives = 0
        primitive_readout_nodes = 0
        known_outcome_values = 0
        primitive_candidates = 0
        recurrent_primitive_candidates = 0
        max_primitive_samples = 0
        sample_gate_candidates = 0
        controllability_gate_candidates = 0
        variance_gate_candidates = 0
        direction_gate_candidates = 0
        full_competence_gate_candidates = 0
        best_candidate_controllability = 0.0
        best_candidate_directional_consistency = 0.0
        lowest_recurrent_effect_variance: float | None = None
        cognitive_concepts = 0
        cognitive_readouts = 0
        structural_candidates = 0
        structural_producers = 0
        oldest_structural_wait_ticks = 0
        peak_structural_candidates = 0
        peak_structural_wait_ticks = 0
        cognitive_primitive_ticks = 0
        primitive_readout_ticks = 0
        cognitive_without_readout_ticks = 0
        cognitive_primitive_set_changes = 0
        primitive_readout_set_changes = 0
        unique_cognitive_primitive_ids: set[str] = set()
        unique_primitive_readout_ids: set[str] = set()
        previous_cognitive_primitive_ids: tuple[str, ...] = ()
        previous_primitive_readout_ids: tuple[str, ...] = ()
        final_cognitive_primitive_ids: tuple[str, ...] = ()
        final_primitive_readout_ids: tuple[str, ...] = ()
        start_displacement = 0.0
        start_progress = 0.0

        with PyBulletEmbodimentRuntime(
            gui=False,
            seed=seed,
            organism_id=f"symbiont:prospective-embodied:{seed}",
            physics_substeps_per_tick=physics_substeps_per_tick,
        ) as runtime:
            slm = Physics3DSlmManager(
                models_dir=models_dir,
                train_interval=1,
                device="cpu",
            )
            try:
                for _ in range(warmup_ticks):
                    tick = runtime.step()

                    # Settle any worker that completed before deciding whether
                    # this tick can become the matched split. A split is valid
                    # only when no training computation remains in flight.
                    slm.poll(runtime)

                    active = runtime.organism.model_registry.active
                    active_model_id = (
                        active.model_id if active is not None else None
                    )
                    final_tick = tick.tick
                    motor_primitives = tick.motor_primitives
                    cognitive_primitives = tick.cognitive_motor_primitives
                    primitive_readout_nodes = tick.primitive_readout_nodes
                    if (
                        first_cognitive_primitive_tick is None
                        and cognitive_primitives > 0
                    ):
                        first_cognitive_primitive_tick = tick.tick
                    if (
                        first_primitive_readout_tick is None
                        and primitive_readout_nodes > 0
                    ):
                        first_primitive_readout_tick = tick.tick
                    known_outcome_values = _value_entry_count(runtime)
                    primitive_candidates = tick.primitive_candidates
                    recurrent_primitive_candidates = tick.recurrent_primitive_candidates
                    max_primitive_samples = tick.max_primitive_samples
                    sample_gate_candidates = tick.sample_gate_candidates
                    controllability_gate_candidates = tick.controllability_gate_candidates
                    variance_gate_candidates = tick.variance_gate_candidates
                    direction_gate_candidates = tick.direction_gate_candidates
                    full_competence_gate_candidates = tick.full_competence_gate_candidates
                    best_candidate_controllability = tick.best_candidate_controllability
                    best_candidate_directional_consistency = (
                        tick.best_candidate_directional_consistency
                    )
                    lowest_recurrent_effect_variance = (
                        tick.lowest_recurrent_effect_variance
                    )
                    cognitive_concepts = tick.cognitive_concepts
                    cognitive_readouts = tick.cognitive_readouts
                    structural_candidates = tick.structural_candidates
                    structural_producers = tick.structural_producers
                    oldest_structural_wait_ticks = tick.oldest_structural_wait_ticks
                    peak_structural_candidates = max(
                        peak_structural_candidates,
                        tick.structural_candidates,
                    )
                    peak_structural_wait_ticks = max(
                        peak_structural_wait_ticks,
                        tick.oldest_structural_wait_ticks,
                    )

                    learner = getattr(runtime.organism, "_sensorimotor_learner", None)
                    current_cognitive_ids = (
                        learner.available_cognitive_primitive_ids()
                        if learner is not None
                        else ()
                    )
                    bridge = getattr(runtime.organism, "_cognitive_bridge", None)
                    current_readout_ids = ()
                    if bridge is not None:
                        current_readout_ids = tuple(
                            sorted(
                                node.node_id.removeprefix("readout_primitive:")
                                for node in bridge.graph.nodes
                                if node.node_id.startswith("readout_primitive:")
                            )
                        )

                    if current_cognitive_ids:
                        cognitive_primitive_ticks += 1
                    if current_readout_ids:
                        primitive_readout_ticks += 1
                    if current_cognitive_ids and not current_readout_ids:
                        cognitive_without_readout_ticks += 1
                    if current_cognitive_ids != previous_cognitive_primitive_ids:
                        if final_tick > 1:
                            cognitive_primitive_set_changes += 1
                        previous_cognitive_primitive_ids = current_cognitive_ids
                    if current_readout_ids != previous_primitive_readout_ids:
                        if final_tick > 1:
                            primitive_readout_set_changes += 1
                        previous_primitive_readout_ids = current_readout_ids

                    unique_cognitive_primitive_ids.update(current_cognitive_ids)
                    unique_primitive_readout_ids.update(current_readout_ids)
                    final_cognitive_primitive_ids = current_cognitive_ids
                    final_primitive_readout_ids = current_readout_ids

                    if tick.prospective_selected and not slm.training:
                        checkpoint = runtime.checkpoint()
                        physical_state, physical_tick = runtime.physical_checkpoint()
                        if physical_tick != runtime.tick_count:
                            raise RuntimeError(
                                "organism and physical checkpoints are not aligned"
                            )
                        readiness_tick = tick.tick
                        readiness_reason = "natural_prospective_selection"
                        start_displacement = tick.displacement_from_origin
                        start_progress = tick.resource_progress
                        break
                    if not tick.alive:
                        readiness_reason = "organism_died_before_prospective_selection"
                        break

                    # Do not start fresh training until after the split decision.
                    # If a prospective tick occurred while a worker was still
                    # running, continue development and wait for a later clean
                    # prospective event.
                    slm.maybe_schedule(
                        runtime.organism,
                        current_tick=tick.tick,
                    )
                    if slm.training:
                        time.sleep(0.001)
            finally:
                slm.close()

        if checkpoint is None or physical_state is None:
            return ProspectiveEmbodiedTrial(
                seed=int(seed),
                warmup_ticks_requested=int(warmup_ticks),
                readiness_found=False,
                readiness_tick=readiness_tick,
                readiness_reason=readiness_reason,
                final_tick=int(final_tick),
                first_cognitive_primitive_tick=first_cognitive_primitive_tick,
                first_primitive_readout_tick=first_primitive_readout_tick,
                active_model_id=active_model_id,
                motor_primitives=int(motor_primitives),
                cognitive_primitives=int(cognitive_primitives),
                primitive_readout_nodes=int(primitive_readout_nodes),
                known_outcome_values=int(known_outcome_values),
                primitive_candidates=int(primitive_candidates),
                recurrent_primitive_candidates=int(recurrent_primitive_candidates),
                max_primitive_samples=int(max_primitive_samples),
                sample_gate_candidates=int(sample_gate_candidates),
                controllability_gate_candidates=int(controllability_gate_candidates),
                variance_gate_candidates=int(variance_gate_candidates),
                direction_gate_candidates=int(direction_gate_candidates),
                full_competence_gate_candidates=int(full_competence_gate_candidates),
                best_candidate_controllability=float(best_candidate_controllability),
                best_candidate_directional_consistency=float(
                    best_candidate_directional_consistency
                ),
                lowest_recurrent_effect_variance=lowest_recurrent_effect_variance,
                cognitive_concepts=int(cognitive_concepts),
                cognitive_readouts=int(cognitive_readouts),
                structural_candidates=int(structural_candidates),
                structural_producers=int(structural_producers),
                oldest_structural_wait_ticks=int(oldest_structural_wait_ticks),
                peak_structural_candidates=int(peak_structural_candidates),
                peak_structural_wait_ticks=int(peak_structural_wait_ticks),
                cognitive_primitive_ticks=int(cognitive_primitive_ticks),
                primitive_readout_ticks=int(primitive_readout_ticks),
                cognitive_without_readout_ticks=int(cognitive_without_readout_ticks),
                cognitive_primitive_set_changes=int(cognitive_primitive_set_changes),
                primitive_readout_set_changes=int(primitive_readout_set_changes),
                unique_cognitive_primitive_ids=tuple(sorted(unique_cognitive_primitive_ids)),
                unique_primitive_readout_ids=tuple(sorted(unique_primitive_readout_ids)),
                final_cognitive_primitive_ids=tuple(final_cognitive_primitive_ids),
                final_primitive_readout_ids=tuple(final_primitive_readout_ids),
                conditions=(),
            )

        conditions = tuple(
            _run_condition(
                condition=condition,
                seed=seed,
                runtime_checkpoint=checkpoint,
                physical_state=physical_state,
                models_dir=models_dir,
                horizon_ticks=horizon_ticks,
                physics_substeps_per_tick=physics_substeps_per_tick,
                start_displacement=start_displacement,
                start_progress=start_progress,
            )
            for condition in _CONDITIONS
        )
        return ProspectiveEmbodiedTrial(
            seed=int(seed),
            warmup_ticks_requested=int(warmup_ticks),
            readiness_found=True,
            readiness_tick=readiness_tick,
            readiness_reason=readiness_reason,
            final_tick=int(final_tick),
            first_cognitive_primitive_tick=first_cognitive_primitive_tick,
            first_primitive_readout_tick=first_primitive_readout_tick,
            active_model_id=active_model_id,
            motor_primitives=int(motor_primitives),
            cognitive_primitives=int(cognitive_primitives),
            primitive_readout_nodes=int(primitive_readout_nodes),
            known_outcome_values=int(known_outcome_values),
            primitive_candidates=int(primitive_candidates),
            recurrent_primitive_candidates=int(recurrent_primitive_candidates),
            max_primitive_samples=int(max_primitive_samples),
            sample_gate_candidates=int(sample_gate_candidates),
            controllability_gate_candidates=int(controllability_gate_candidates),
            variance_gate_candidates=int(variance_gate_candidates),
            direction_gate_candidates=int(direction_gate_candidates),
            full_competence_gate_candidates=int(full_competence_gate_candidates),
            best_candidate_controllability=float(best_candidate_controllability),
            best_candidate_directional_consistency=float(
                best_candidate_directional_consistency
            ),
            lowest_recurrent_effect_variance=lowest_recurrent_effect_variance,
            cognitive_concepts=int(cognitive_concepts),
            cognitive_readouts=int(cognitive_readouts),
            structural_candidates=int(structural_candidates),
            structural_producers=int(structural_producers),
            oldest_structural_wait_ticks=int(oldest_structural_wait_ticks),
            peak_structural_candidates=int(peak_structural_candidates),
            peak_structural_wait_ticks=int(peak_structural_wait_ticks),
            cognitive_primitive_ticks=int(cognitive_primitive_ticks),
            primitive_readout_ticks=int(primitive_readout_ticks),
            cognitive_without_readout_ticks=int(cognitive_without_readout_ticks),
            cognitive_primitive_set_changes=int(cognitive_primitive_set_changes),
            primitive_readout_set_changes=int(primitive_readout_set_changes),
            unique_cognitive_primitive_ids=tuple(sorted(unique_cognitive_primitive_ids)),
            unique_primitive_readout_ids=tuple(sorted(unique_primitive_readout_ids)),
            final_cognitive_primitive_ids=tuple(final_cognitive_primitive_ids),
            final_primitive_readout_ids=tuple(final_primitive_readout_ids),
            conditions=conditions,
        )


def run_prospective_embodied_study(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    warmup_ticks: int = 5000,
    horizon_ticks: int = 256,
    physics_substeps_per_tick: int = 10,
) -> ProspectiveEmbodiedStudy:
    normalized = tuple(int(seed) for seed in seeds)
    if not normalized or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must be non-empty and unique")
    trials = tuple(
        run_prospective_embodied_trial(
            seed,
            warmup_ticks=warmup_ticks,
            horizon_ticks=horizon_ticks,
            physics_substeps_per_tick=physics_substeps_per_tick,
        )
        for seed in normalized
    )
    return ProspectiveEmbodiedStudy(
        seeds=normalized,
        warmup_ticks=int(warmup_ticks),
        horizon_ticks=int(horizon_ticks),
        trials=trials,
    )


__all__ = [
    "ProspectiveEmbodiedCondition",
    "ProspectiveEmbodiedTrial",
    "ProspectiveEmbodiedStudy",
    "run_prospective_embodied_trial",
    "run_prospective_embodied_study",
]
