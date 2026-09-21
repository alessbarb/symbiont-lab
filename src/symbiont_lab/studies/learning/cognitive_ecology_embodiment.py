from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime


@dataclass(frozen=True, slots=True)
class CognitiveEcologyEmbodimentTrial:
    seed: int
    ticks_requested: int
    ticks_completed: int
    alive: bool
    peak_predictors: int
    peak_shadow_predictions: int
    peak_promotable_shadows: int
    final_concepts: int
    final_readouts: int
    final_motor_readout_nodes: int
    final_primitive_readout_nodes: int
    peak_structural_candidates: int
    peak_structural_producers: int
    maximum_structural_wait_ticks: int
    expected_wait_bound_ticks: int
    final_maturity_nascent: int
    final_maturity_provisional: int
    final_maturity_mature: int
    final_maturity_stable: int
    final_maturity_weakening: int
    final_maturity_retiring: int
    motor_origin_cognition: int
    motor_origin_primitive: int
    motor_origin_primitive_cognition: int
    motor_origin_primitive_verification: int
    motor_origin_babbling: int
    cognitive_motor_primitives: int
    cognitive_motor_output_edges: int
    resource_progress: float
    predictor_monopoly: bool
    cognition_reached_motor_output: bool

    @property
    def architecture_gate_passed(self) -> bool:
        return (
            not self.predictor_monopoly
            and self.maximum_structural_wait_ticks <= self.expected_wait_bound_ticks
        )

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["architecture_gate_passed"] = self.architecture_gate_passed
        return payload


@dataclass(frozen=True, slots=True)
class CognitiveEcologyEmbodimentStudy:
    seeds: tuple[int, ...]
    trials: tuple[CognitiveEcologyEmbodimentTrial, ...]

    @property
    def all_architecture_gates_pass(self) -> bool:
        return all(trial.architecture_gate_passed for trial in self.trials)

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "trials": [trial.as_dict() for trial in self.trials],
            "all_architecture_gates_pass": self.all_architecture_gates_pass,
        }


def _trial(seed: int, *, ticks: int) -> CognitiveEcologyEmbodimentTrial:
    peak_predictors = 0
    peak_shadows = 0
    peak_promotable = 0
    peak_candidates = 0
    peak_producers = 0
    maximum_wait = 0
    last = None

    organism_id = f"symbiont:ecology-study:{seed}"
    with PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        organism_id=organism_id,
    ) as runtime:
        consolidation_interval = max(
            1,
            runtime.organism.genome.development.consolidation_interval_ticks,
        )
        progress_interval = max(100, ticks // 12)
        for step_index in range(ticks):
            last = runtime.step()
            if (
                (step_index + 1) % progress_interval == 0
                or not last.alive
                or step_index + 1 == ticks
            ):
                print(
                    "[cognitive-ecology] "
                    f"seed={seed} tick={step_index + 1}/{ticks} "
                    f"alive={last.alive} predictors={last.predictor_count} "
                    f"concepts={last.cognitive_concepts} "
                    f"producers={last.structural_producers}",
                    flush=True,
                )
            peak_predictors = max(peak_predictors, last.predictor_count)
            peak_shadows = max(peak_shadows, last.shadow_prediction_count)
            peak_promotable = max(peak_promotable, last.promotable_shadow_count)
            peak_candidates = max(
                peak_candidates,
                last.structural_candidates,
            )
            peak_producers = max(
                peak_producers,
                last.structural_producers,
            )
            maximum_wait = max(
                maximum_wait,
                last.oldest_structural_wait_ticks,
            )
            if not last.alive:
                break

    if last is None:
        raise RuntimeError("Physics3D ecology trial produced no ticks")

    # Monopoly is defined structurally, not by an arbitrary predictor count:
    # prediction has saturated cognition while no concept/readout substrate has
    # managed to survive. This captures the failure that motivated the redesign.
    predictor_monopoly = (
        peak_predictors > 0
        and last.cognitive_concepts == 0
        and last.cognitive_readouts == 0
    )

    return CognitiveEcologyEmbodimentTrial(
        seed=seed,
        ticks_requested=ticks,
        ticks_completed=last.tick,
        alive=last.alive,
        peak_predictors=peak_predictors,
        peak_shadow_predictions=peak_shadows,
        peak_promotable_shadows=peak_promotable,
        final_concepts=last.cognitive_concepts,
        final_readouts=last.cognitive_readouts,
        final_motor_readout_nodes=last.motor_readout_nodes,
        final_primitive_readout_nodes=last.primitive_readout_nodes,
        peak_structural_candidates=peak_candidates,
        peak_structural_producers=peak_producers,
        maximum_structural_wait_ticks=maximum_wait,
        expected_wait_bound_ticks=max(
            consolidation_interval,
            peak_producers * consolidation_interval,
        ),
        final_maturity_nascent=last.maturity_nascent,
        final_maturity_provisional=last.maturity_provisional,
        final_maturity_mature=last.maturity_mature,
        final_maturity_stable=last.maturity_stable,
        final_maturity_weakening=last.maturity_weakening,
        final_maturity_retiring=last.maturity_retiring,
        motor_origin_cognition=last.motor_origin_cognition,
        motor_origin_primitive=last.motor_origin_primitive,
        motor_origin_primitive_cognition=last.motor_origin_primitive_cognition,
        motor_origin_primitive_verification=last.motor_origin_primitive_verification,
        motor_origin_babbling=last.motor_origin_babbling,
        cognitive_motor_primitives=last.cognitive_motor_primitives,
        cognitive_motor_output_edges=last.cognitive_motor_output_edges,
        resource_progress=last.resource_progress,
        predictor_monopoly=predictor_monopoly,
        cognition_reached_motor_output=(
            last.motor_origin_cognition > 0
            or last.motor_origin_mixed > 0
            or last.motor_origin_primitive_cognition > 0
        ),
    )


def run_cognitive_ecology_embodiment_study(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    ticks: int = 3000,
) -> CognitiveEcologyEmbodimentStudy:
    seed_list = tuple(seeds)
    if not seed_list:
        raise ValueError("seeds must not be empty")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 128:
        raise ValueError("ticks must be at least 128")

    trials = tuple(_trial(seed, ticks=ticks) for seed in seed_list)
    return CognitiveEcologyEmbodimentStudy(
        seeds=seed_list,
        trials=trials,
    )


__all__ = [
    "CognitiveEcologyEmbodimentStudy",
    "CognitiveEcologyEmbodimentTrial",
    "run_cognitive_ecology_embodiment_study",
]
