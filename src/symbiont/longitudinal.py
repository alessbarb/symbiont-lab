from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from statistics import mean

from .collective import CollectiveMemory
from .curiosity import CuriosityPlanner
from .heritage import SpeciesHeritage, apply_heritage, distill_heritage
from .metacognition import MetacognitionEngine
from .model import Assessment
from .reasoning import ReasoningEngine
from .simulation import (
    Evaluator,
    SimulationResult,
    _cognitive_outputs,
    _make_agents,
    _trust_gap,
    run_simulation,
)
from .world import apply_regime_shift, benign_event, make_profiles, pathogen_event


@dataclass(slots=True, frozen=True)
class GenerationComparison:
    generation: int
    seed: int
    inherited_patterns: int
    exported_patterns: int
    retained_patterns: int
    retention_rate: float
    inherited_detection_rate: float
    control_detection_rate: float
    detection_delta: float
    inherited_precision: float
    control_precision: float
    precision_delta: float
    inherited_false_positive_rate: float
    control_false_positive_rate: float
    false_positive_delta: float
    inherited_calibration_error: float
    control_calibration_error: float
    calibration_delta: float
    inherited_blind_spot_rate: float
    control_blind_spot_rate: float
    blind_spot_delta: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class LongitudinalResult:
    generations: tuple[GenerationComparison, ...]
    mean_detection_delta: float
    mean_precision_delta: float
    mean_false_positive_delta: float
    mean_calibration_delta: float
    mean_blind_spot_delta: float
    final_heritage: SpeciesHeritage

    def as_dict(self) -> dict[str, object]:
        return {
            "generations": [generation.as_dict() for generation in self.generations],
            "mean_detection_delta": self.mean_detection_delta,
            "mean_precision_delta": self.mean_precision_delta,
            "mean_false_positive_delta": self.mean_false_positive_delta,
            "mean_calibration_delta": self.mean_calibration_delta,
            "mean_blind_spot_delta": self.mean_blind_spot_delta,
            "final_heritage": self.final_heritage.as_dict(),
        }


def _run_with_heritage(
    *,
    hosts: int,
    steps: int,
    seed: int,
    threat_rate: float,
    poison_fraction: float,
    heterogeneity: float,
    drift_step: int | None,
    drift_fraction: float,
    drift_magnitude: float,
    heritage: SpeciesHeritage | None,
) -> tuple[SimulationResult, CollectiveMemory]:
    """Mirror the simulator loop while injecting only bounded inherited priors."""
    rng = random.Random(seed)
    profiles = make_profiles(hosts, rng)
    agents, poisoned_ids = _make_agents(hosts, rng, poison_fraction, heterogeneity)
    collective = CollectiveMemory()
    apply_heritage(collective, heritage)
    evaluator = Evaluator()
    reasoner = ReasoningEngine()
    curiosity = CuriosityPlanner()
    metacognition = MetacognitionEngine()
    meta = metacognition.assess([], collective)
    resolved_drift_step = max(50, int(steps * 0.55)) if drift_step is None else max(0, drift_step)
    drifted_hosts: set[int] = set()

    for step in range(steps):
        if step == resolved_drift_step:
            drifted_hosts = apply_regime_shift(
                profiles,
                rng,
                fraction=drift_fraction,
                magnitude=drift_magnitude,
            )
        step_assessments: list[Assessment] = []
        for index, (profile, agent) in enumerate(zip(profiles, agents)):
            inject = step >= 50 and rng.random() < threat_rate
            if inject:
                roll = rng.random()
                kind = "ransom_sim" if roll < 0.40 else "bot_sim" if roll < 0.72 else "stealth_sim"
                event = pathogen_event(kind, profile, rng)
            else:
                event = benign_event(profile, rng)
            assessment = agent.observe(step, event.observation, collective)
            step_assessments.append(assessment)
            evaluator.record(
                is_threat=event.is_threat,
                investigated=assessment.should_investigate,
                assessment=assessment,
                drift_context=(step >= resolved_drift_step and index in drifted_hosts),
            )
        collective.recalibrate_sources()
        meta = metacognition.assess(step_assessments, collective)

    investigated = sum(agent.investigated for agent in agents)
    hypotheses, probes = _cognitive_outputs(collective, reasoner, curiosity)
    result = SimulationResult(
        hosts=hosts,
        steps=steps,
        pathogen_events=evaluator.pathogen_events,
        benign_events=evaluator.benign_events,
        investigated=investigated,
        true_positive_investigations=evaluator.true_positives,
        false_positive_investigations=evaluator.false_positives,
        false_negatives=evaluator.false_negatives,
        collective_patterns=len(collective.patterns),
        open_questions=len(collective.open_questions()),
        forgotten_episodes=sum(agent.memory.forgotten for agent in agents),
        consolidated_episodes=sum(agent.memory.consolidated for agent in agents),
        mean_source_trust=collective.mean_source_trust,
        low_trust_sources=collective.low_trust_sources(),
        poisoned_agents=len(poisoned_ids),
        trust_gap=_trust_gap(collective, poisoned_ids),
        reasoning_hypotheses=len(hypotheses),
        top_reasoning_priority=hypotheses[0].priority if hypotheses else 0.0,
        curiosity_probes=len(probes),
        top_probe_utility=probes[0].utility if probes else 0.0,
        self_confidence=meta.self_confidence,
        epistemic_pressure=meta.epistemic_pressure,
        metacognitive_status=meta.status,
        calibration_error=evaluator.calibration_error,
        brier_score=evaluator.brier_score,
        overconfidence_rate=evaluator.overconfidence_rate,
        blind_spot_rate=evaluator.blind_spot_rate,
        drift_step=resolved_drift_step,
        drifted_hosts=len(drifted_hosts),
        drift_adaptations=sum(agent.drift_adaptations for agent in agents),
        drift_false_positive_rate=evaluator.drift_false_positive_rate,
        recent_drift_false_positive_rate=evaluator.recent_drift_false_positive_rate,
    )
    return result, collective


def run_longitudinal_species(
    *,
    generations: int = 5,
    hosts: int = 100,
    steps: int = 300,
    seed: int = 7,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    heritage_limit: int = 24,
) -> LongitudinalResult:
    if generations < 1:
        raise ValueError("generations must be at least 1")
    if generations > 50:
        raise ValueError("longitudinal experiments are limited to 50 generations")

    heritage = SpeciesHeritage(generation=0)
    comparisons: list[GenerationComparison] = []

    for generation in range(1, generations + 1):
        generation_seed = seed + (generation - 1) * 1009
        inherited_result, inherited_collective = _run_with_heritage(
            hosts=hosts,
            steps=steps,
            seed=generation_seed,
            threat_rate=threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=drift_step,
            drift_fraction=drift_fraction,
            drift_magnitude=drift_magnitude,
            heritage=heritage,
        )
        control_result, _ = run_simulation(
            hosts=hosts,
            steps=steps,
            seed=generation_seed,
            threat_rate=threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=drift_step,
            drift_fraction=drift_fraction,
            drift_magnitude=drift_magnitude,
        )
        next_heritage = distill_heritage(
            inherited_collective,
            generation=generation,
            max_patterns=heritage_limit,
        )
        inherited_fingerprints = {pattern.fingerprint for pattern in heritage.patterns}
        exported_fingerprints = {pattern.fingerprint for pattern in next_heritage.patterns}
        retained = len(inherited_fingerprints & exported_fingerprints)
        retention = retained / max(len(inherited_fingerprints), 1) if inherited_fingerprints else 0.0

        comparisons.append(
            GenerationComparison(
                generation=generation,
                seed=generation_seed,
                inherited_patterns=len(heritage.patterns),
                exported_patterns=len(next_heritage.patterns),
                retained_patterns=retained,
                retention_rate=retention,
                inherited_detection_rate=inherited_result.detection_rate,
                control_detection_rate=control_result.detection_rate,
                detection_delta=inherited_result.detection_rate - control_result.detection_rate,
                inherited_precision=inherited_result.precision,
                control_precision=control_result.precision,
                precision_delta=inherited_result.precision - control_result.precision,
                inherited_false_positive_rate=inherited_result.false_positive_rate,
                control_false_positive_rate=control_result.false_positive_rate,
                false_positive_delta=inherited_result.false_positive_rate - control_result.false_positive_rate,
                inherited_calibration_error=inherited_result.calibration_error,
                control_calibration_error=control_result.calibration_error,
                calibration_delta=inherited_result.calibration_error - control_result.calibration_error,
                inherited_blind_spot_rate=inherited_result.blind_spot_rate,
                control_blind_spot_rate=control_result.blind_spot_rate,
                blind_spot_delta=inherited_result.blind_spot_rate - control_result.blind_spot_rate,
            )
        )
        heritage = next_heritage

    # Generation 1 has no inherited knowledge; including it is useful because it
    # acts as an internal parity check but does not bias the paired mean materially.
    return LongitudinalResult(
        generations=tuple(comparisons),
        mean_detection_delta=mean(item.detection_delta for item in comparisons),
        mean_precision_delta=mean(item.precision_delta for item in comparisons),
        mean_false_positive_delta=mean(item.false_positive_delta for item in comparisons),
        mean_calibration_delta=mean(item.calibration_delta for item in comparisons),
        mean_blind_spot_delta=mean(item.blind_spot_delta for item in comparisons),
        final_heritage=heritage,
    )
