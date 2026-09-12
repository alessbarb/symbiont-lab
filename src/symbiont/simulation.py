from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable

from .agent import Agent
from .collective import CollectiveMemory
from .curiosity import CuriosityPlanner, CuriosityProbe
from .metacognition import MetacognitionEngine, MetacognitiveState
from .model import Assessment, Observation
from .reasoning import Hypothesis, ReasoningEngine
from .rng import make_rng_streams
from .world import apply_regime_shift, benign_event, make_profiles, pathogen_event


@dataclass(slots=True, frozen=True)
class EventContext:
    """Evaluator-only view of one synthetic event.

    The agent never receives this envelope. It exists so experiments can verify
    world parity and stratify outcomes without monkeypatching simulator internals.
    """

    step: int
    host_index: int
    truth_label: str
    is_threat: bool
    phase: str
    drift_state: str
    observation: Observation


@dataclass(slots=True)
class EvaluationCounts:
    events: int = 0
    threats: int = 0
    benign: int = 0
    investigated: int = 0
    predicted_threat: int = 0
    attention_tp: int = 0
    attention_fp: int = 0
    attention_fn: int = 0
    classification_tp: int = 0
    classification_fp: int = 0
    classification_tn: int = 0
    classification_fn: int = 0

    def record(self, *, is_threat: bool, investigated: bool, predicted_threat: bool) -> None:
        self.events += 1
        self.investigated += int(investigated)
        self.predicted_threat += int(predicted_threat)
        if is_threat:
            self.threats += 1
            self.attention_tp += int(investigated)
            self.attention_fn += int(not investigated)
            self.classification_tp += int(predicted_threat)
            self.classification_fn += int(not predicted_threat)
        else:
            self.benign += 1
            self.attention_fp += int(investigated)
            self.classification_fp += int(predicted_threat)
            self.classification_tn += int(not predicted_threat)

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    @property
    def attention_recall(self) -> float | None:
        return self._rate(self.attention_tp, self.threats)

    @property
    def attention_precision(self) -> float | None:
        return self._rate(self.attention_tp, self.attention_tp + self.attention_fp)

    @property
    def attention_false_positive_rate(self) -> float | None:
        return self._rate(self.attention_fp, self.benign)

    @property
    def classification_recall(self) -> float | None:
        return self._rate(self.classification_tp, self.threats)

    @property
    def classification_precision(self) -> float | None:
        return self._rate(
            self.classification_tp,
            self.classification_tp + self.classification_fp,
        )

    @property
    def classification_false_positive_rate(self) -> float | None:
        return self._rate(self.classification_fp, self.benign)

    @property
    def classification_accuracy(self) -> float | None:
        return self._rate(
            self.classification_tp + self.classification_tn,
            self.events,
        )

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload.update(
            {
                "attention_recall": self.attention_recall,
                "attention_precision": self.attention_precision,
                "attention_false_positive_rate": self.attention_false_positive_rate,
                "classification_recall": self.classification_recall,
                "classification_precision": self.classification_precision,
                "classification_false_positive_rate": self.classification_false_positive_rate,
                "classification_accuracy": self.classification_accuracy,
            }
        )
        return payload


@dataclass(slots=True)
class CalibrationBin:
    count: int = 0
    probability_sum: float = 0.0
    target_sum: float = 0.0


@dataclass(slots=True, frozen=True)
class SimulationSnapshot:
    step: int
    total_steps: int
    pathogen_events: int
    benign_events: int
    investigated: int
    true_positives: int
    false_positives: int
    false_negatives: int
    detection_rate: float
    precision: float
    false_positive_rate: float
    attention_recall: float
    attention_precision: float
    attention_false_positive_rate: float
    classification_recall: float
    classification_precision: float
    classification_false_positive_rate: float
    classification_miss_rate: float
    high_confidence_miss_rate: float
    collective_patterns: int
    open_questions: int
    forgotten_episodes: int
    consolidated_episodes: int
    mean_source_trust: float
    low_trust_sources: int
    poisoned_agents: int
    trust_gap: float
    reasoning_hypotheses: tuple[Hypothesis, ...]
    reasoning_priority: float
    curiosity_probes: tuple[CuriosityProbe, ...]
    curiosity_focus: float
    self_confidence: float
    epistemic_pressure: float
    mean_uncertainty: float
    mean_novelty: float
    disagreement_pressure: float
    metacognitive_status: str
    calibration_error: float
    brier_score: float
    overconfidence_rate: float
    blind_spot_rate: float
    drift_active: bool
    drift_step: int
    drifted_hosts: int
    drift_adaptations: int
    drift_false_positive_rate: float
    recent_drift_false_positive_rate: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SimulationResult:
    hosts: int
    steps: int
    pathogen_events: int
    benign_events: int
    investigated: int
    true_positive_investigations: int
    false_positive_investigations: int
    false_negatives: int
    classification_true_positives: int
    classification_false_positives: int
    classification_true_negatives: int
    classification_false_negatives: int
    collective_patterns: int
    open_questions: int
    forgotten_episodes: int
    consolidated_episodes: int
    mean_source_trust: float
    low_trust_sources: int
    poisoned_agents: int
    trust_gap: float
    reasoning_hypotheses: int
    top_reasoning_priority: float
    curiosity_probes: int
    top_probe_utility: float
    self_confidence: float
    epistemic_pressure: float
    metacognitive_status: str
    calibration_error: float
    brier_score: float
    overconfidence_rate: float
    blind_spot_rate: float
    high_confidence_miss_rate: float
    drift_step: int
    drifted_hosts: int
    drift_adaptations: int
    drift_false_positive_rate: float
    recent_drift_false_positive_rate: float
    evaluation_breakdown: dict[str, object]

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    @property
    def attention_recall(self) -> float | None:
        return self._rate(self.true_positive_investigations, self.pathogen_events)

    @property
    def attention_precision(self) -> float | None:
        return self._rate(self.true_positive_investigations, self.investigated)

    @property
    def attention_false_positive_rate(self) -> float | None:
        return self._rate(self.false_positive_investigations, self.benign_events)

    @property
    def classification_recall(self) -> float | None:
        return self._rate(self.classification_true_positives, self.pathogen_events)

    @property
    def classification_precision(self) -> float | None:
        return self._rate(
            self.classification_true_positives,
            self.classification_true_positives + self.classification_false_positives,
        )

    @property
    def classification_false_positive_rate(self) -> float | None:
        return self._rate(self.classification_false_positives, self.benign_events)

    @property
    def classification_miss_rate(self) -> float | None:
        return self._rate(self.classification_false_negatives, self.pathogen_events)

    # Backwards-compatible aliases. New research should use the explicit
    # attention_* names because these values describe allocation of attention,
    # not threat classification.
    @property
    def detection_rate(self) -> float:
        return self.attention_recall or 0.0

    @property
    def precision(self) -> float:
        return self.attention_precision or 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.attention_false_positive_rate or 0.0


@dataclass(slots=True)
class Evaluator:
    counts: EvaluationCounts = field(default_factory=EvaluationCounts)
    family_counts: dict[str, EvaluationCounts] = field(default_factory=dict)
    phase_counts: dict[str, EvaluationCounts] = field(default_factory=dict)
    drift_counts: dict[str, EvaluationCounts] = field(default_factory=dict)
    decisions: int = 0
    brier_sum: float = 0.0
    calibration_bins: list[CalibrationBin] = field(
        default_factory=lambda: [CalibrationBin() for _ in range(10)]
    )
    high_confidence_predictions: int = 0
    high_confidence_errors: int = 0
    high_confidence_threat_misses: int = 0
    drift_recent: list[int] = field(default_factory=list)

    def record(
        self,
        *,
        is_threat: bool,
        investigated: bool,
        assessment: Assessment,
        truth_label: str = "unknown",
        phase: str = "unknown",
        drift_state: str = "unknown",
    ) -> None:
        predicted = assessment.believes_threat
        self.counts.record(
            is_threat=is_threat,
            investigated=investigated,
            predicted_threat=predicted,
        )
        self.family_counts.setdefault(truth_label, EvaluationCounts()).record(
            is_threat=is_threat,
            investigated=investigated,
            predicted_threat=predicted,
        )
        self.phase_counts.setdefault(phase, EvaluationCounts()).record(
            is_threat=is_threat,
            investigated=investigated,
            predicted_threat=predicted,
        )
        self.drift_counts.setdefault(drift_state, EvaluationCounts()).record(
            is_threat=is_threat,
            investigated=investigated,
            predicted_threat=predicted,
        )

        probability = min(1.0, max(0.0, assessment.threat_probability))
        target = 1.0 if is_threat else 0.0
        self.decisions += 1
        self.brier_sum += (probability - target) ** 2
        bin_index = min(int(probability * len(self.calibration_bins)), len(self.calibration_bins) - 1)
        calibration_bin = self.calibration_bins[bin_index]
        calibration_bin.count += 1
        calibration_bin.probability_sum += probability
        calibration_bin.target_sum += target

        predicted_confidence = probability if predicted else 1.0 - probability
        if predicted_confidence >= 0.75:
            self.high_confidence_predictions += 1
            self.high_confidence_errors += int(predicted != is_threat)
            if is_threat and not predicted:
                self.high_confidence_threat_misses += 1

        if drift_state == "affected" and not is_threat:
            self.drift_recent.append(int(investigated))
            if len(self.drift_recent) > 200:
                self.drift_recent.pop(0)

    @property
    def pathogen_events(self) -> int:
        return self.counts.threats

    @property
    def benign_events(self) -> int:
        return self.counts.benign

    @property
    def true_positives(self) -> int:
        return self.counts.attention_tp

    @property
    def false_positives(self) -> int:
        return self.counts.attention_fp

    @property
    def false_negatives(self) -> int:
        return self.counts.attention_fn

    @property
    def classification_true_positives(self) -> int:
        return self.counts.classification_tp

    @property
    def classification_false_positives(self) -> int:
        return self.counts.classification_fp

    @property
    def classification_true_negatives(self) -> int:
        return self.counts.classification_tn

    @property
    def classification_false_negatives(self) -> int:
        return self.counts.classification_fn

    @property
    def calibration_error(self) -> float:
        if not self.decisions:
            return 0.0
        error = 0.0
        for calibration_bin in self.calibration_bins:
            if not calibration_bin.count:
                continue
            avg_probability = calibration_bin.probability_sum / calibration_bin.count
            event_rate = calibration_bin.target_sum / calibration_bin.count
            error += (
                calibration_bin.count / self.decisions
            ) * abs(avg_probability - event_rate)
        return error

    @property
    def brier_score(self) -> float:
        return self.brier_sum / self.decisions if self.decisions else 0.0

    @property
    def overconfidence_rate(self) -> float:
        if not self.high_confidence_predictions:
            return 0.0
        return self.high_confidence_errors / self.high_confidence_predictions

    @property
    def high_confidence_miss_rate(self) -> float:
        if not self.pathogen_events:
            return 0.0
        return self.high_confidence_threat_misses / self.pathogen_events

    @property
    def blind_spot_rate(self) -> float:
        """Legacy alias for high-confidence classification misses."""
        return self.high_confidence_miss_rate

    @property
    def classification_miss_rate(self) -> float:
        if not self.pathogen_events:
            return 0.0
        return self.classification_false_negatives / self.pathogen_events

    @property
    def drift_false_positive_rate(self) -> float:
        affected = self.drift_counts.get("affected")
        if affected is None or not affected.benign:
            return 0.0
        return affected.attention_fp / affected.benign

    @property
    def recent_drift_false_positive_rate(self) -> float:
        return sum(self.drift_recent) / len(self.drift_recent) if self.drift_recent else 0.0

    def breakdown(self) -> dict[str, object]:
        return {
            "global": self.counts.as_dict(),
            "families": {
                name: counts.as_dict()
                for name, counts in sorted(self.family_counts.items())
            },
            "phases": {
                name: counts.as_dict()
                for name, counts in sorted(self.phase_counts.items())
            },
            "drift": {
                name: counts.as_dict()
                for name, counts in sorted(self.drift_counts.items())
            },
            "calibration": {
                "ece": self.calibration_error,
                "brier_score": self.brier_score,
                "overconfidence_rate": self.overconfidence_rate,
                "high_confidence_miss_rate": self.high_confidence_miss_rate,
                "bins": [
                    {
                        "count": item.count,
                        "mean_probability": (
                            item.probability_sum / item.count if item.count else None
                        ),
                        "event_rate": (
                            item.target_sum / item.count if item.count else None
                        ),
                    }
                    for item in self.calibration_bins
                ],
            },
        }


def _make_agents(hosts: int, rng, poison_fraction: float, heterogeneity: float) -> tuple[list[Agent], set[str]]:
    poison_count = min(hosts, max(0, round(hosts * poison_fraction)))
    poisoned_indexes = set(rng.sample(range(hosts), poison_count)) if poison_count else set()
    agents: list[Agent] = []
    poisoned_ids: set[str] = set()
    spread = max(0.0, heterogeneity)
    for i in range(hosts):
        agent_id = f"agent-{i:03d}"
        poisoned = i in poisoned_indexes
        if poisoned:
            poisoned_ids.add(agent_id)
        agents.append(
            Agent(
                agent_id=agent_id,
                risk_scale=min(1.30, max(0.70, rng.gauss(1.0, spread))),
                curiosity_scale=min(1.35, max(0.65, rng.gauss(1.0, spread))),
                investigation_bias=rng.uniform(-0.04, 0.04) * min(spread / 0.12, 1.5),
                report_inversion=poisoned,
            )
        )
    return agents, poisoned_ids


def _trust_gap(collective: CollectiveMemory, poisoned_ids: set[str]) -> float:
    honest = [
        state.score
        for source, state in collective.source_trust.items()
        if source not in poisoned_ids
    ]
    poisoned = [
        state.score
        for source, state in collective.source_trust.items()
        if source in poisoned_ids
    ]
    if not honest or not poisoned:
        return 0.0
    return sum(honest) / len(honest) - sum(poisoned) / len(poisoned)


def _cognitive_outputs(
    collective: CollectiveMemory,
    reasoner: ReasoningEngine,
    curiosity: CuriosityPlanner,
) -> tuple[tuple[Hypothesis, ...], tuple[CuriosityProbe, ...]]:
    hypotheses = reasoner.analyze(collective)
    return hypotheses, curiosity.plan(hypotheses, collective)


def _rate_or_zero(value: float | None) -> float:
    return value if value is not None else 0.0


def _snapshot(
    *,
    step: int,
    total_steps: int,
    evaluator: Evaluator,
    agents: list[Agent],
    collective: CollectiveMemory,
    poisoned_ids: set[str],
    reasoner: ReasoningEngine,
    curiosity: CuriosityPlanner,
    meta: MetacognitiveState,
    drift_step: int,
    drifted_hosts: set[int],
) -> SimulationSnapshot:
    investigated = sum(agent.investigated for agent in agents)
    hypotheses, probes = _cognitive_outputs(collective, reasoner, curiosity)
    attention_recall = _rate_or_zero(evaluator.counts.attention_recall)
    attention_precision = _rate_or_zero(evaluator.counts.attention_precision)
    attention_fpr = _rate_or_zero(evaluator.counts.attention_false_positive_rate)
    classification_recall = _rate_or_zero(evaluator.counts.classification_recall)
    classification_precision = _rate_or_zero(evaluator.counts.classification_precision)
    classification_fpr = _rate_or_zero(evaluator.counts.classification_false_positive_rate)
    return SimulationSnapshot(
        step=step,
        total_steps=total_steps,
        pathogen_events=evaluator.pathogen_events,
        benign_events=evaluator.benign_events,
        investigated=investigated,
        true_positives=evaluator.true_positives,
        false_positives=evaluator.false_positives,
        false_negatives=evaluator.false_negatives,
        detection_rate=attention_recall,
        precision=attention_precision,
        false_positive_rate=attention_fpr,
        attention_recall=attention_recall,
        attention_precision=attention_precision,
        attention_false_positive_rate=attention_fpr,
        classification_recall=classification_recall,
        classification_precision=classification_precision,
        classification_false_positive_rate=classification_fpr,
        classification_miss_rate=evaluator.classification_miss_rate,
        high_confidence_miss_rate=evaluator.high_confidence_miss_rate,
        collective_patterns=len(collective.patterns),
        open_questions=len(collective.open_questions()),
        forgotten_episodes=sum(agent.memory.forgotten for agent in agents),
        consolidated_episodes=sum(agent.memory.consolidated for agent in agents),
        mean_source_trust=collective.mean_source_trust,
        low_trust_sources=collective.low_trust_sources(),
        poisoned_agents=len(poisoned_ids),
        trust_gap=_trust_gap(collective, poisoned_ids),
        reasoning_hypotheses=hypotheses,
        reasoning_priority=hypotheses[0].priority if hypotheses else 0.0,
        curiosity_probes=probes,
        curiosity_focus=probes[0].utility if probes else 0.0,
        self_confidence=meta.self_confidence,
        epistemic_pressure=meta.epistemic_pressure,
        mean_uncertainty=meta.mean_uncertainty,
        mean_novelty=meta.mean_novelty,
        disagreement_pressure=meta.disagreement_pressure,
        metacognitive_status=meta.status,
        calibration_error=evaluator.calibration_error,
        brier_score=evaluator.brier_score,
        overconfidence_rate=evaluator.overconfidence_rate,
        blind_spot_rate=evaluator.blind_spot_rate,
        drift_active=step > drift_step,
        drift_step=drift_step,
        drifted_hosts=len(drifted_hosts),
        drift_adaptations=sum(agent.drift_adaptations for agent in agents),
        drift_false_positive_rate=evaluator.drift_false_positive_rate,
        recent_drift_false_positive_rate=evaluator.recent_drift_false_positive_rate,
    )


def _run_population(
    hosts: int = 100,
    steps: int = 300,
    seed: int = 7,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    on_snapshot: Callable[[SimulationSnapshot], None] | None = None,
    on_event: Callable[[EventContext], None] | None = None,
    collective: CollectiveMemory | None = None,
) -> tuple[SimulationResult, CollectiveMemory]:
    streams = make_rng_streams(seed)
    profiles = make_profiles(hosts, streams.profiles)
    agents, poisoned_ids = _make_agents(
        hosts,
        streams.agents,
        poison_fraction,
        heterogeneity,
    )
    collective = collective or CollectiveMemory()
    evaluator = Evaluator()
    reasoner = ReasoningEngine()
    curiosity = CuriosityPlanner()
    metacognition = MetacognitionEngine()
    meta = metacognition.assess([], collective)
    resolved_drift_step = (
        max(50, int(steps * 0.55))
        if drift_step is None
        else max(0, drift_step)
    )
    drifted_hosts: set[int] = set()

    for step in range(steps):
        if step == resolved_drift_step:
            drifted_hosts = apply_regime_shift(
                profiles,
                streams.drift,
                fraction=drift_fraction,
                magnitude=drift_magnitude,
            )

        step_assessments: list[Assessment] = []
        for index, (profile, agent) in enumerate(zip(profiles, agents)):
            inject = step >= 50 and streams.schedule.random() < threat_rate
            if inject:
                roll = streams.schedule.random()
                kind = (
                    "ransom_sim"
                    if roll < 0.40
                    else "bot_sim"
                    if roll < 0.72
                    else "stealth_sim"
                )
                event = pathogen_event(kind, profile, streams.observations)
            else:
                event = benign_event(profile, streams.observations)

            if step < 50:
                phase = "warmup"
            elif step < resolved_drift_step:
                phase = "pre_drift"
            else:
                phase = "post_drift"
            drift_state = (
                "pre_drift"
                if step < resolved_drift_step
                else "affected"
                if index in drifted_hosts
                else "unaffected"
            )

            if on_event is not None:
                on_event(
                    EventContext(
                        step=step,
                        host_index=index,
                        truth_label=event.truth_label,
                        is_threat=event.is_threat,
                        phase=phase,
                        drift_state=drift_state,
                        observation=event.observation,
                    )
                )

            assessment = agent.observe(step, event.observation, collective)
            step_assessments.append(assessment)
            evaluator.record(
                is_threat=event.is_threat,
                investigated=assessment.should_investigate,
                assessment=assessment,
                truth_label=event.truth_label,
                phase=phase,
                drift_state=drift_state,
            )

        collective.recalibrate_sources()
        meta = metacognition.assess(step_assessments, collective)
        if on_snapshot is not None:
            on_snapshot(
                _snapshot(
                    step=step + 1,
                    total_steps=steps,
                    evaluator=evaluator,
                    agents=agents,
                    collective=collective,
                    poisoned_ids=poisoned_ids,
                    reasoner=reasoner,
                    curiosity=curiosity,
                    meta=meta,
                    drift_step=resolved_drift_step,
                    drifted_hosts=drifted_hosts,
                )
            )

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
        classification_true_positives=evaluator.classification_true_positives,
        classification_false_positives=evaluator.classification_false_positives,
        classification_true_negatives=evaluator.classification_true_negatives,
        classification_false_negatives=evaluator.classification_false_negatives,
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
        high_confidence_miss_rate=evaluator.high_confidence_miss_rate,
        drift_step=resolved_drift_step,
        drifted_hosts=len(drifted_hosts),
        drift_adaptations=sum(agent.drift_adaptations for agent in agents),
        drift_false_positive_rate=evaluator.drift_false_positive_rate,
        recent_drift_false_positive_rate=evaluator.recent_drift_false_positive_rate,
        evaluation_breakdown=evaluator.breakdown(),
    )
    return result, collective


def run_simulation(
    hosts: int = 100,
    steps: int = 300,
    seed: int = 7,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    on_snapshot: Callable[[SimulationSnapshot], None] | None = None,
    on_event: Callable[[EventContext], None] | None = None,
) -> tuple[SimulationResult, CollectiveMemory]:
    return _run_population(
        hosts=hosts,
        steps=steps,
        seed=seed,
        threat_rate=threat_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        drift_step=drift_step,
        drift_fraction=drift_fraction,
        drift_magnitude=drift_magnitude,
        on_snapshot=on_snapshot,
        on_event=on_event,
    )
